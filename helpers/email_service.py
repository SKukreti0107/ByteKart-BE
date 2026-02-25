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
        # Format price to remove .0 if it's a whole number
        display_price = int(price) if price == int(price) else price
        items_html += f'''
        <tr>
            <td style="padding: 6px 0; border-bottom: 1px dashed rgba(0, 0, 153, 0.15); color: #000099; font-weight: bold; line-height: 1.2;">{name}</td>
            <td style="padding: 6px 0; text-align: center; border-bottom: 1px dashed rgba(0, 0, 153, 0.15); color: #000099; font-weight: bold; width: 40px;">x{qty}</td>
            <td style="padding: 6px 0; text-align: right; border-bottom: 1px dashed rgba(0, 0, 153, 0.15); color: #000099; font-weight: bold; width: 80px;">₹{display_price}</td>
        </tr>
        '''

    friendly_date = str(created_at)[:10] if created_at else "Now"
    
    # Format total amount
    display_amount = int(amount) if amount == int(amount) else amount

    # Read the HTML template
    template_path = os.path.join("public", "email_template", "order_placed.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        print(f"Error reading email template: {e}")
        # Fallback to a simple message if template is missing
        template_content = f"Order Confirmation: {order_id}. Total: ₹{amount}"

    # Replace placeholders
    base_api_url = os.getenv("BASE_API_URL", "https://api.bytekart.co.in")
    html_content = template_content.replace("{{user_name}}", user_name)
    html_content = html_content.replace("{{order_id}}", order_id)
    html_content = html_content.replace("{{friendly_date}}", friendly_date)
    html_content = html_content.replace("{{items_html}}", items_html)
    html_content = html_content.replace("{{amount}}", str(display_amount))
    html_content = html_content.replace("{{base_api_url}}", base_api_url)

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

    # Select template based on status
    template_file = "order_shipped.html" if new_status.lower() == "shipped" else "order_delivered.html"
    template_path = os.path.join("public", "email_template", template_file)
    
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        print(f"Error reading email template: {e}")
        template_content = f"Order {order_id} status updated to: {new_status}"

    base_api_url = os.getenv("BASE_API_URL", "https://api.bytekart.co.in")
    html_content = template_content.replace("{{user_name}}", user_name)
    html_content = html_content.replace("{{order_id}}", order_id)
    html_content = html_content.replace("{{base_api_url}}", base_api_url)

    try:
        params:client.Emails.SendParams = {
            "from": "ByteKart <onboarding@resend.dev>",
            "to": user_email,
            "subject": f"ByteKart: Order Status Update - {order_id}",
            "html": html_content
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

    template_path = os.path.join("public", "email_template", "thanks_after_delivery.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
    except Exception as e:
        print(f"Error reading email template: {e}")
        template_content = f"Thank you for shopping with ByteKart, {user_name}!"

    base_api_url = os.getenv("BASE_API_URL", "https://api.bytekart.co.in")
    html_content = template_content.replace("{{user_name}}", user_name)
    html_content = html_content.replace("{{base_api_url}}", base_api_url)

    try:
        params:client.Emails.SendParams = {
            "from": "ByteKart <onboarding@resend.dev>",
            "to": user_email,
            "subject": "ByteKart: Thank You!",
            "html": html_content
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