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

    # Generate ITEM_LIST as an aesthetic HTML table
    item_list_html = '<table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: \'Inter\', sans-serif; font-size: 14px;">'
    for item in items:
        name = item.get("name", "Item")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        display_price = int(price) if price == int(price) else price
        item_list_html += f"""
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #eeeeee;">{name} <span style="color: #666666;">x{qty}</span></td>
                <td align="right" style="padding: 8px 0; border-bottom: 1px solid #eeeeee; font-weight: bold;">₹{display_price}</td>
            </tr>
        """
    item_list_html += "</table>"

    display_amount = int(amount) if amount == int(amount) else amount
    
    # Load local template
    template_path = os.path.join("public", "email_template", "order_status.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Initial status config (Placed)
        status_config = {
            "title": "We're fetching your order",
            "desc": "Your package is currently being processed at our distribution center.",
            "shipping_bg": "#000000",
            "shipping_dot": "#ffffff",
            "delivered_bg": "#ffffff",
            "delivered_dot": "#000000",
            "delivered_opacity": "0.4"
        }
        
        # Replace placeholders
        html_content = html_content.replace("{{ORDER_ID}}", order_id)
        html_content = html_content.replace("{{STATUS_TITLE}}", status_config["title"])
        html_content = html_content.replace("{{STATUS_DESC}}", status_config["desc"])
        html_content = html_content.replace("{{SHIPPING_BG_COLOR}}", status_config["shipping_bg"])
        html_content = html_content.replace("{{SHIPPING_DOT_COLOR}}", status_config["shipping_dot"])
        html_content = html_content.replace("{{DELIVERED_BG_COLOR}}", status_config["delivered_bg"])
        html_content = html_content.replace("{{DELIVERED_DOT_COLOR}}", status_config["delivered_dot"])
        html_content = html_content.replace("{{DELIVERED_OPACITY}}", status_config["delivered_opacity"])
        html_content = html_content.replace("{{ITEM_LIST}}", item_list_html)
        html_content = html_content.replace("{{TOTAL_AMOUNT}}", str(display_amount))
    else:
        print(f"Warning: Template not found at {template_path}. Falling back to simple HTML.")
        html_content = f"<h1>Order Confirmed</h1><p>Hi {user_name}, your order {order_id} has been placed.</p>{item_list_html}<p>Total: ₹{display_amount}</p>"

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart <orders@mg.bytekart.co.in>",
            "to": [user_email],
            "subject": f"ByteKart: Order Confirmation - {order_id}",
            "html": html_content
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Order confirmation email sent to {user_email}")
        return email

    except Exception as e:
        print(f"Failed to send order confirmation email: {e}")

async def send_order_status_update_email(user_email: str, user_name: str, order_id: str, new_status: str, amount: float = 0, items: list = []):
    client = get_resend_client()
    if not client:
        return

    # Generate ITEM_LIST as an aesthetic HTML table
    item_list_html = '<table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: \'Public Sans\', sans-serif; font-size: 14px; color: #000000;">'
    for item in items:
        name = item.get("name", "Item")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        display_price = int(price) if price == int(price) else price
        item_list_html += f"""
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #eeeeee;">{name} <span style="color: #666666;">x{qty}</span></td>
                <td align="right" style="padding: 8px 0; border-bottom: 1px solid #eeeeee; font-weight: bold;">₹{display_price}</td>
            </tr>
        """
    if not items:
        item_list_html += "<tr><td colspan='2' style='padding: 8px 0;'>Order details are being processed.</td></tr>"
    item_list_html += "</table>"

    # Status configuration for the template (Brutalist style)
    status_config = {
        "placed": {
            "title": "We're fetching your order",
            "desc": "Your package is currently being processed at our distribution center.",
            "shipping_bg": "#000000",
            "shipping_dot": "#ffffff",
            "delivered_bg": "#ffffff",
            "delivered_dot": "#000000",
            "delivered_opacity": "0.4"
        },
        "shipped": {
            "title": "Your order is on the way",
            "desc": "Great news! Your package has been handed over to our delivery partner and is moving towards you.",
            "shipping_bg": "#5A8A5D",
            "shipping_dot": "#ffffff",
            "delivered_bg": "#000000",
            "delivered_dot": "#ffffff",
            "delivered_opacity": "1.0"
        },
        "delivered": {
            "title": "Your order has arrived",
            "desc": "Delivered! We hope you love your new ByteKart items. Thank you for shopping with us!",
            "shipping_bg": "#5A8A5D",
            "shipping_dot": "#ffffff",
            "delivered_bg": "#5A8A5D",
            "delivered_dot": "#ffffff",
            "delivered_opacity": "1.0"
        }
    }

    config = status_config.get(new_status.lower(), status_config["placed"])
    
    import datetime
    est_delivery = (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%b %d, %Y")
    display_amount = int(amount) if amount == int(amount) else amount

    # Load local template
    template_path = os.path.join("public", "email_template", "order_status.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Replace placeholders
        html_content = html_content.replace("{{USER_NAME}}", user_name)
        html_content = html_content.replace("{{ORDER_ID}}", order_id)
        html_content = html_content.replace("{{STATUS_TITLE}}", config["title"])
        html_content = html_content.replace("{{STATUS_DESC}}", config["desc"])
        html_content = html_content.replace("{{SHIPPING_BG_COLOR}}", config["shipping_bg"])
        html_content = html_content.replace("{{SHIPPING_DOT_COLOR}}", config["shipping_dot"])
        html_content = html_content.replace("{{DELIVERED_BG_COLOR}}", config["delivered_bg"])
        html_content = html_content.replace("{{DELIVERED_DOT_COLOR}}", config["delivered_dot"])
        html_content = html_content.replace("{{DELIVERED_OPACITY}}", config["delivered_opacity"])
        html_content = html_content.replace("{{ESTIMATED_DELIVERY}}", est_delivery)
        html_content = html_content.replace("{{ITEM_LIST}}", item_list_html)
        html_content = html_content.replace("{{TOTAL_AMOUNT}}", str(display_amount))
    else:
        html_content = f"<h1>Order Status: {new_status}</h1><p>Hi {user_name}, your order {order_id} is now {new_status}.</p>{item_list_html}"

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart <orders@mg.bytekart.co.in>",
            "to": [user_email],
            "subject": f"ByteKart: Order Status Update - {order_id}",
            "html": html_content
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Order status update email sent to {user_email}")
        
        if new_status.lower() == "delivered":
            await send_thanks_after_delivery_email(user_email, user_name, order_id, amount, items)
            
        return email
    except Exception as e:
        print(f"Failed to send order status update email: {e}")

async def send_thanks_after_delivery_email(user_email: str, user_name: str, order_id: str, amount: float, items: list):
    client = get_resend_client()
    if not client:
        return

    # Generate ITEM_LIST as an aesthetic HTML table
    item_list_html = '<table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: \'Public Sans\', sans-serif; font-size: 14px; color: #000000;">'
    for item in items:
        name = item.get("name", "Item")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        display_price = int(price) if price == int(price) else price
        item_list_html += f"""
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #eeeeee;">{name} <span style="color: #666666;">x{qty}</span></td>
                <td align="right" style="padding: 8px 0; border-bottom: 1px solid #eeeeee; font-weight: bold;">₹{display_price}</td>
            </tr>
        """
    item_list_html += "</table>"
    display_amount = int(amount) if amount == int(amount) else amount

    # Load local template
    template_path = os.path.join("public", "email_template", "our_thanks.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Replace placeholders
        html_content = html_content.replace("{{USER_NAME}}", user_name)
        html_content = html_content.replace("{{ORDER_ID}}", order_id)
        html_content = html_content.replace("{{ITEM_LIST}}", item_list_html)
        html_content = html_content.replace("{{TOTAL_AMOUNT}}", str(display_amount))
    else:
        html_content = f"<h1>Thank You!</h1><p>Hi {user_name}, hope you loved your order {order_id}.</p>"

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart <orders@mg.bytekart.co.in>",
            "to": [user_email],
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
                "from": "ByteKart <orders@mg.bytekart.co.in>",
                "to": email,
                "subject": subject,
                "html": body
            }
            client.Emails.SendResponse = client.Emails.send(params)
            print(f"Email sent to admin: {subject}")
    except Exception as e:
        print(f"Failed to send email to admin: {e}")