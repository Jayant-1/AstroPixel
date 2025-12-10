from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional

router = APIRouter(prefix="/api", tags=["contact"])

class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

@router.post("/contact")
async def send_contact_email(contact: ContactMessage):
    """
    Handle contact form submissions and send emails.
    """
    try:
        # Get email credentials from environment variables
        sender_email = os.getenv("CONTACT_EMAIL")
        sender_password = os.getenv("CONTACT_EMAIL_PASSWORD")
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT"))
        
        # For development without email credentials
        if not sender_password:
            return {
                "success": True,
                "message": "Message received! (Email service not configured)",
                "data": {
                    "name": contact.name,
                    "email": contact.email,
                    "subject": contact.subject,
                }
            }
        
        # Create email message
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = sender_email
        msg["Subject"] = f"New Contact Form Submission: {contact.subject}"
        
        # Email body
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #1a1a2e;">New Contact Form Submission</h2>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p><strong>From:</strong> {contact.name}</p>
                        <p><strong>Email:</strong> {contact.email}</p>
                        <p><strong>Subject:</strong> {contact.subject}</p>
                    </div>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p><strong>Message:</strong></p>
                        <p style="white-space: pre-wrap; color: #555;">{contact.message}</p>
                    </div>
                    
                    <hr style="border: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">
                        This message was sent through AstroPixel's contact form.
                    </p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(email_body, "html"))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return {
            "success": True,
            "message": "Message sent successfully!",
            "data": {
                "name": contact.name,
                "email": contact.email,
                "subject": contact.subject,
            }
        }
        
    except smtplib.SMTPException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
