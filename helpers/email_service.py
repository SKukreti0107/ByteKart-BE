import os
import resend

def get_resend_client():
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print("Warning: RESEND_API_KEY is not set.")
        return None
    resend.api_key = api_key
    return resend

async def send_order_confirmation_email(user_email: str, user_name: str, order_id: str, amount: float, items: list, created_at: str):
    client = get_resend_client()
    if not client:
        return

    # Generate ITEM_LIST as an HTML <ul>
    item_list_html = "<ul>"
    for item in items:
        name = item.get("name", "Item")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        display_price = int(price) if price == int(price) else price
        item_list_html += f"<li>{name} x{qty} - ₹{display_price}</li>"
    item_list_html += "</ul>"

    display_amount = int(amount) if amount == int(amount) else amount

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart <onboarding@resend.dev>",
            "to": [user_email],
            "subject": f"ByteKart: Order Confirmation - {order_id}",
            "template": {
                "id": "order-placed",
                "variables": {
                    "USER_NAME": user_name,
                    "ORDER_ID": order_id,
                    "ITEM_LIST": item_list_html,
                    "TOTAL_AMOUNT": str(display_amount)
                }
            }
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Order confirmation email sent to {user_email}")
        return email

    except Exception as e:
        print(f"Failed to send order confirmation email: {e}")

async def send_order_status_update_email(user_email: str, user_name: str, order_id: str, new_status: str, amount: float = 0):
    client = get_resend_client()
    if not client:
        return

    template_alias = "order-shipped" if new_status.lower() == "shipped" else "order-delivered"
    display_amount = int(amount) if amount == int(amount) else amount

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart <onboarding@resend.dev>",
            "to": [user_email],
            "subject": f"ByteKart: Order Status Update - {order_id}",
            "template": {
                "id": template_alias,
                "variables": {
                    "USER_NAME": user_name,
                    "ORDER_ID": order_id,
                    "TOTAL_AMOUNT": str(display_amount)
                }
            }
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Order status update email sent to {user_email}")
        
        # If delivered, also send the thanks email
        if new_status.lower() == "delivered":
            await send_thanks_after_delivery_email(user_email, user_name)
            
        return email
    except Exception as e:
        print(f"Failed to send order status update email: {e}")

async def send_thanks_after_delivery_email(user_email: str, user_name: str):
    client = get_resend_client()
    if not client:
        return

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart <onboarding@resend.dev>",
            "to": [user_email],
            "subject": "ByteKart: Thank You!",
            "template": {
                "id": "our-thanks",
                "variables": {
                    "USER_NAME": user_name
                }
            }
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Thanks email sent to {user_email}")
        return email
    except Exception as e:
        print(f"Failed to send thanks email: {e}")


async def send_email_to_admin(action:str ,subject: str, body: str):
    client = get_resend_client()
    if not client:
        return

    try:
        admin_emails = ["shubhamkukreti.0107@gmail.com","nathansaul20@gmail.com"]
        if action == "new_order":
            subject = "New Order Received - " + subject
        elif action == "order_cancellation":
            subject = "Order Cancellation - " + subject
        
        for email in admin_emails:
            params:client.Emails.SendParams = {
                "from": "ByteKart <onboarding@resend.dev>",
                "to": email,
                "subject": subject,
                "html": body
            }
            client.Emails.SendResponse = client.Emails.send(params)
            print(f"Email sent to admin: {subject}")
    except Exception as e:
        print(f"Failed to send email to admin: {e}")