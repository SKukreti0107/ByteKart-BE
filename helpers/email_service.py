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


async def send_return_status_email(user_email: str, user_name: str, order_id: str, return_status: str, amount: float = 0, items: list = []):
    """Send return-specific email using the return_status.html template."""
    client = get_resend_client()
    if not client:
        return

    # Generate ITEM_LIST
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

    display_amount = int(amount) if amount == int(amount) else amount

    # Status configurations for the return template
    status_configs = {
        "return_requested": {
            "hero_title": "Return<br/>Initiated",
            "hero_color": "#D97706",
            "status_title": "We've received your return request",
            "status_desc": "Our team is reviewing your return request. You'll receive an update once it's been processed. This usually takes 1-2 business days.",
            "step1_bg": "#5A8A5D", "step1_icon_color": "#ffffff", "step1_icon": "✓",
            "step2_bg": "#D97706", "step2_icon_color": "#ffffff", "step2_icon": "⟳",
            "step3_bg": "#ffffff", "step3_icon_color": "#000000", "step3_icon": "•",
            "step3_opacity": "0.4", "step3_label": "Decision",
            "subject_prefix": "Return Request Received"
        },
        "returned": {
            "hero_title": "Return<br/>Approved",
            "hero_color": "#5A8A5D",
            "status_title": "Your return has been approved",
            "status_desc": "Great news! Your return request has been approved. The refund will be processed to your original payment method within 5-7 business days.",
            "step1_bg": "#5A8A5D", "step1_icon_color": "#ffffff", "step1_icon": "✓",
            "step2_bg": "#5A8A5D", "step2_icon_color": "#ffffff", "step2_icon": "✓",
            "step3_bg": "#5A8A5D", "step3_icon_color": "#ffffff", "step3_icon": "✓",
            "step3_opacity": "1.0", "step3_label": "Approved",
            "subject_prefix": "Return Approved"
        },
        "rejected": {
            "hero_title": "Return<br/>Declined",
            "hero_color": "#DC2626",
            "status_title": "Your return request was declined",
            "status_desc": "Unfortunately, your return request could not be approved. If you have questions, please contact our support team at support@bytekart.co.in.",
            "step1_bg": "#5A8A5D", "step1_icon_color": "#ffffff", "step1_icon": "✓",
            "step2_bg": "#5A8A5D", "step2_icon_color": "#ffffff", "step2_icon": "✓",
            "step3_bg": "#DC2626", "step3_icon_color": "#ffffff", "step3_icon": "✕",
            "step3_opacity": "1.0", "step3_label": "Declined",
            "subject_prefix": "Return Declined"
        }
    }

    config = status_configs.get(return_status.lower(), status_configs["return_requested"])

    # Load return template
    template_path = os.path.join("public", "email_template", "return_status.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        html_content = html_content.replace("{{HERO_TITLE}}", config["hero_title"])
        html_content = html_content.replace("{{HERO_COLOR}}", config["hero_color"])
        html_content = html_content.replace("{{STATUS_TITLE}}", config["status_title"])
        html_content = html_content.replace("{{STATUS_DESC}}", config["status_desc"])
        html_content = html_content.replace("{{STEP1_BG}}", config["step1_bg"])
        html_content = html_content.replace("{{STEP1_ICON_COLOR}}", config["step1_icon_color"])
        html_content = html_content.replace("{{STEP1_ICON}}", config["step1_icon"])
        html_content = html_content.replace("{{STEP2_BG}}", config["step2_bg"])
        html_content = html_content.replace("{{STEP2_ICON_COLOR}}", config["step2_icon_color"])
        html_content = html_content.replace("{{STEP2_ICON}}", config["step2_icon"])
        html_content = html_content.replace("{{STEP3_BG}}", config["step3_bg"])
        html_content = html_content.replace("{{STEP3_ICON_COLOR}}", config["step3_icon_color"])
        html_content = html_content.replace("{{STEP3_ICON}}", config["step3_icon"])
        html_content = html_content.replace("{{STEP3_OPACITY}}", config["step3_opacity"])
        html_content = html_content.replace("{{STEP3_LABEL}}", config["step3_label"])
        html_content = html_content.replace("{{ORDER_ID}}", order_id)
        html_content = html_content.replace("{{ITEM_LIST}}", item_list_html)
        html_content = html_content.replace("{{TOTAL_AMOUNT}}", str(display_amount))
    else:
        html_content = f"<h1>Return {return_status}</h1><p>Hi {user_name}, your return for order {order_id} is now: {return_status}.</p>{item_list_html}"

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart <orders@mg.bytekart.co.in>",
            "to": [user_email],
            "subject": f"ByteKart: {config['subject_prefix']} - {order_id}",
            "html": html_content
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Return status email sent to {user_email}")
        return email
    except Exception as e:
        print(f"Failed to send return status email: {e}")


async def send_email_to_admin(action:str ,subject: str, body: str):
    client = get_resend_client()
    if not client:
        return

    import time 
    time.sleep(5)
    try:
        admin_emails = ["shubhamkukreti.0107@gmail.com","nathansaul20@gmail.com"]
        if action == "new_order":
            subject = "New Order Received - " + subject
        elif action == "order_cancellation":
            subject = "Order Cancellation - " + subject
        elif action == "return_request":
            subject = "Return Request - " + subject
        elif action == "support_ticket":
            subject = "New Support Ticket - " + subject
        
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


async def send_support_acknowledgement_email(user_email: str, user_name: str, subject: str, ticket_id: str):
    """Send acknowledgement email to customer when they submit a support ticket."""
    client = get_resend_client()
    if not client:
        return

    html_content = f"""
    <div style="font-family: 'Inter', 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
        <div style="background: #000000; padding: 32px; text-align: center;">
            <h1 style="color: #C6DCBA; font-size: 28px; margin: 0; letter-spacing: 4px; text-transform: uppercase;">BYTEKART</h1>
            <p style="color: #ffffff; font-size: 12px; letter-spacing: 3px; text-transform: uppercase; margin-top: 8px;">Support</p>
        </div>
        <div style="padding: 40px 32px; border: 4px solid #000000; border-top: 0;">
            <h2 style="font-size: 22px; font-weight: 900; text-transform: uppercase; margin: 0 0 16px 0; letter-spacing: 1px;">We've Got Your Message</h2>
            <p style="font-size: 14px; color: #333333; line-height: 1.6; margin: 0 0 24px 0;">
                Hi <strong>{user_name}</strong>, thanks for reaching out! We've received your support request and our team will get back to you as soon as possible.
            </p>
            <div style="background: #f5f5f5; border: 3px solid #000000; padding: 20px; margin: 0 0 24px 0;">
                <p style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #666; margin: 0 0 8px 0;"><strong>Ticket ID</strong></p>
                <p style="font-size: 16px; font-weight: bold; margin: 0 0 16px 0; font-family: monospace;">{ticket_id[:8]}</p>
                <p style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #666; margin: 0 0 8px 0;"><strong>Subject</strong></p>
                <p style="font-size: 14px; margin: 0;">{subject}</p>
            </div>
            <p style="font-size: 13px; color: #666666; line-height: 1.6; margin: 0;">
                We typically respond within 24 hours. If your issue is urgent, please mention it in a follow-up email to <strong>support@mg.bytekart.co.in</strong>.
            </p>
        </div>
        <div style="background: #000000; padding: 20px; text-align: center;">
            <p style="color: #666666; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin: 0;">© 2026 ByteKart — Greater Noida, India</p>
        </div>
    </div>
    """

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart Support <support@mg.bytekart.co.in>",
            "to": [user_email],
            "subject": f"ByteKart Support: We've received your request — {subject}",
            "html": html_content
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Support acknowledgement email sent to {user_email}")
        return email
    except Exception as e:
        print(f"Failed to send support acknowledgement email: {e}")


async def send_support_reply_email(user_email: str, user_name: str, original_subject: str, admin_reply: str, ticket_id: str):
    """Send admin's reply to a support ticket to the customer."""
    client = get_resend_client()
    if not client:
        return

    # Convert newlines to <br> for HTML display
    reply_html = admin_reply.replace("\n", "<br>")

    html_content = f"""
    <div style="font-family: 'Inter', 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
        <div style="background: #000000; padding: 32px; text-align: center;">
            <h1 style="color: #C6DCBA; font-size: 28px; margin: 0; letter-spacing: 4px; text-transform: uppercase;">BYTEKART</h1>
            <p style="color: #ffffff; font-size: 12px; letter-spacing: 3px; text-transform: uppercase; margin-top: 8px;">Support</p>
        </div>
        <div style="padding: 40px 32px; border: 4px solid #000000; border-top: 0;">
            <h2 style="font-size: 22px; font-weight: 900; text-transform: uppercase; margin: 0 0 16px 0; letter-spacing: 1px;">We've Replied</h2>
            <p style="font-size: 14px; color: #333333; line-height: 1.6; margin: 0 0 24px 0;">
                Hi <strong>{user_name}</strong>, our support team has responded to your ticket.
            </p>
            <div style="background: #f5f5f5; border: 3px solid #000000; padding: 20px; margin: 0 0 16px 0;">
                <p style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #666; margin: 0 0 8px 0;"><strong>Ticket</strong></p>
                <p style="font-size: 14px; font-weight: bold; margin: 0;">{original_subject}</p>
            </div>
            <div style="background: #C6DCBA; border: 3px solid #000000; padding: 20px; margin: 0 0 24px 0;">
                <p style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #333; margin: 0 0 12px 0;"><strong>Our Response</strong></p>
                <p style="font-size: 14px; color: #000000; line-height: 1.7; margin: 0;">{reply_html}</p>
            </div>
            <p style="font-size: 13px; color: #666666; line-height: 1.6; margin: 0;">
                If you need further assistance, simply reply to this email or write to <strong>support@mg.bytekart.co.in</strong>.
            </p>
        </div>
        <div style="background: #000000; padding: 20px; text-align: center;">
            <p style="color: #666666; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; margin: 0;">© 2026 ByteKart — Greater Noida, India</p>
        </div>
    </div>
    """

    try:
        params: client.Emails.SendParams = {
            "from": "ByteKart Support <support@mg.bytekart.co.in>",
            "to": [user_email],
            "subject": f"Re: {original_subject} — ByteKart Support",
            "html": html_content
        }
        email: client.Emails.SendResponse = client.Emails.send(params)
        print(f"Support reply email sent to {user_email}")
        return email
    except Exception as e:
        print(f"Failed to send support reply email: {e}")