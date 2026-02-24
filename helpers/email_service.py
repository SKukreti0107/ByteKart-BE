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

    items_html = ""
    for item in items:
        name = item.get("name", "Item")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        items_html += f'''
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #333; color: #b3b3b3;">{name}</td>
            <td style="padding: 12px; text-align: center; border-bottom: 1px solid #333; color: #b3b3b3;">x{qty}</td>
            <td style="padding: 12px; text-align: right; border-bottom: 1px solid #333; color: #b3b3b3;">₹{price}</td>
        </tr>
        '''

    friendly_date = created_at[:10] if created_at else "Now"

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #121212; color: #e0e0e0; padding: 20px; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4a90e2; font-size: 20px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">BYTEKART.IN</h1>
        </div>

        <div style="background-color: #1a1a1a; border-radius: 16px; padding: 30px; border: 1px solid #333;">
            <h2 style="margin-top: 0; font-size: 24px; text-align: center; font-weight: normal;">
                <span style="background-color: #a69e6b; color: #1a1a1a; padding: 2px 8px; border-radius: 4px; font-weight: bold;">Order</span> Completed!
            </h2>
            
            <p style="text-align: center; line-height: 1.6; color: #b3b3b3; margin-top: 20px; font-size: 15px;">
                Hello {user_name}! Your <span style="background-color: #a69e6b; color: #1a1a1a; padding: 0 4px; border-radius: 2px;">order</span> with us has been processed and completed successfully.
            </p>

            <hr style="border: 0; border-top: 1px dashed #333; margin: 30px 0;" />

            <h3 style="margin-top: 0; font-size: 16px; font-weight: normal;">
                <span style="background-color: #a69e6b; color: #1a1a1a; padding: 2px 6px; border-radius: 4px; font-weight: bold;">Order</span> Details:
            </h3>

            <div style="margin-bottom: 25px; color: #b3b3b3; font-size: 14px; line-height: 1.8;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="width: 100px; display: inline-block;">Id:</span>
                    <span style="color: #e0e0e0;">{order_id}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="width: 100px; display: inline-block;">Date:</span>
                    <span style="color: #e0e0e0;">{friendly_date}</span>
                </div>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #333; border-radius: 8px; overflow: hidden; font-size: 14px;">
                <thead>
                    <tr style="background-color: #222;">
                        <th style="padding: 12px; text-align: left; font-weight: 500; color: #e0e0e0; border-bottom: 1px solid #333;">Item</th>
                        <th style="padding: 12px; text-align: center; font-weight: 500; color: #e0e0e0; border-bottom: 1px solid #333;">Quantity</th>
                        <th style="padding: 12px; text-align: right; font-weight: 500; color: #e0e0e0; border-bottom: 1px solid #333;">Price</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <div style="text-align: right; margin-top: 20px; font-size: 16px; font-weight: bold; color: #8faadb;">
                Total: ₹{amount}
            </div>
        </div>
    </div>
    """

    try:
        params :client.Emails.SendParams = {
            "from": "ByteKart <onboarding@resend.dev>",
            "to": user_email,
            "subject": f"ByteKart: Order Confirmation - {order_id}",
            "html": html_content
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Order confirmation email sent to {user_email}")
        return email

    except Exception as e:
        print(f"Failed to send order confirmation email: {e}")

async def send_order_status_update_email(user_email: str, user_name: str, order_id: str, new_status: str):
    client = get_resend_client()
    if not client:
        return

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #121212; color: #e0e0e0; padding: 20px; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #4a90e2; font-size: 20px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">BYTEKART.IN</h1>
        </div>

        <div style="background-color: #1a1a1a; border-radius: 16px; padding: 30px; border: 1px solid #333;">
            <h2 style="margin-top: 0; font-size: 24px; text-align: center; font-weight: normal;">
                <span style="background-color: #a69e6b; color: #1a1a1a; padding: 2px 8px; border-radius: 4px; font-weight: bold;">Order</span> Update!
            </h2>
            
            <p style="text-align: center; line-height: 1.6; color: #b3b3b3; margin-top: 20px; font-size: 15px;">
                Hello {user_name}! The status of your <span style="background-color: #a69e6b; color: #1a1a1a; padding: 0 4px; border-radius: 2px;">order</span> has been updated to: <strong style="color: #e0e0e0;">{new_status.upper()}</strong>
            </p>

            <hr style="border: 0; border-top: 1px dashed #333; margin: 30px 0;" />

            <div style="text-align: center; color: #b3b3b3; font-size: 14px; line-height: 1.8;">
                <p>Order Id: <span style="color: #e0e0e0;">{order_id}</span></p>
                <p>Thank you for shopping with ByteKart!</p>
            </div>
        </div>
    </div>
    """

    try:
        params:client.Emails.SendParams = {
            "from": "ByteKart <onboarding@resend.dev>",
            "to": user_email,
            "subject": f"ByteKart: Order Status Update - {order_id}",
            "html": html_content
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Order status update email sent to {user_email}")
        return email
    except Exception as e:
        print(f"Failed to send order status update email: {e}")


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