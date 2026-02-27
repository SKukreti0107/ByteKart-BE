import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request as FastAPIRequest
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db import get_session
from models import SupportTicket, SupportTicketStatus
from helpers.email_service import send_support_acknowledgement_email, send_email_to_admin

router = APIRouter()


class SupportTicketData(BaseModel):
    name: str
    email: str
    subject: str
    message: str


@router.post("/support/ticket")
async def create_support_ticket(
    ticket_data: SupportTicketData,
    session: AsyncSession = Depends(get_session)
):
    ticket = SupportTicket(
        user_email=ticket_data.email,
        user_name=ticket_data.name,
        subject=ticket_data.subject,
        message=ticket_data.message,
    )
    session.add(ticket)
    try:
        await session.commit()
        await session.refresh(ticket)
    except Exception as e:
        await session.rollback()
        logging.error(f"Error saving support ticket: {e}")
        raise HTTPException(status_code=500, detail="Could not save support ticket")

    try:
        await send_support_acknowledgement_email(
            user_email=ticket.user_email,
            user_name=ticket.user_name,
            subject=ticket.subject,
            ticket_id=ticket.id
        )
    except Exception as e:
        logging.error(f"Failed to send support acknowledgement email: {e}")

    try:
        await send_email_to_admin(
            "support_ticket",
            ticket.subject,
            f"From: {ticket.user_name} ({ticket.user_email})\n\n{ticket.message}"
        )
    except Exception as e:
        logging.error(f"Failed to send support ticket admin notification: {e}")

    return {"message": "Support ticket submitted successfully", "ticket_id": ticket.id}


@router.post("/webhooks/resend")
async def resend_webhook(
    request: FastAPIRequest,
    session: AsyncSession = Depends(get_session)
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type", "")

    if event_type == "email.received":
        data = payload.get("data", {})
        from_email = data.get("from", "unknown@unknown.com")
        subject = data.get("subject", "No Subject")
        body = data.get("text", data.get("html", ""))
        sender_name = from_email.split("<")[0].strip() if "<" in from_email else from_email.split("@")[0]
        sender_email = from_email.split("<")[1].rstrip(">") if "<" in from_email else from_email

        ticket = SupportTicket(
            user_email=sender_email,
            user_name=sender_name or "Customer",
            subject=subject,
            message=body[:5000],
        )
        session.add(ticket)
        try:
            await session.commit()
            await session.refresh(ticket)
            logging.info(f"Inbound email ticket created: {ticket.id} from {sender_email}")
        except Exception as e:
            await session.rollback()
            logging.error(f"Error saving inbound email ticket: {e}")
            raise HTTPException(status_code=500, detail="Failed to process inbound email")

        try:
            await send_email_to_admin(
                "support_ticket",
                subject,
                f"Inbound email from: {sender_name} ({sender_email})\n\n{body[:1000]}"
            )
        except Exception as e:
            logging.error(f"Failed to notify admins of inbound email: {e}")

    return {"status": "ok"}
