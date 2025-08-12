"""
Email sending utilities for user verification and notifications.
"""
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor
import logging

from app.core.config import settings
from app.utils.jwt_handler import jwt_handler

logger = logging.getLogger(__name__)


class EmailSender:
    """Email service for sending verification and notification emails."""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.email_from = settings.email_from or settings.smtp_username
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection."""
        if not self.smtp_username or not self.smtp_password:
            raise ValueError("SMTP credentials not configured")
        
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        server.starttls()
        server.login(self.smtp_username, self.smtp_password)
        return server
    
    def _send_email_sync(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Synchronous email sending method."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_from
            msg['To'] = to_email
            
            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with self._create_smtp_connection() as server:
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Send email asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._send_email_sync,
            to_email,
            subject,
            html_content,
            text_content
        )
    
    async def send_verification_email(self, email: str, username: str, base_url: str = "http://localhost:8000") -> bool:
        """Send email verification email to user."""
        try:
            # Create verification token
            verification_token = jwt_handler.create_email_verification_token(email)
            verification_url = f"{base_url}/auth/verify/{verification_token}"
            
            # Email subject
            subject = f"Verify your email address - {settings.app_name}"
            
            # HTML email template
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Email Verification</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .button {{ 
                        display: inline-block; 
                        padding: 12px 24px; 
                        background-color: #007bff; 
                        color: white; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                    }}
                    .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to {settings.app_name}!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {username},</h2>
                        <p>Thank you for registering with {settings.app_name}. To complete your registration, please verify your email address by clicking the button below:</p>
                        
                        <div style="text-align: center;">
                            <a href="{verification_url}" class="button">Verify Email Address</a>
                        </div>
                        
                        <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; color: #007bff;">{verification_url}</p>
                        
                        <p><strong>Important:</strong> This verification link will expire in 24 hours.</p>
                        
                        <p>If you didn't create an account with us, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>This email was sent by {settings.app_name}</p>
                        <p>Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_content = f"""
            Welcome to {settings.app_name}!
            
            Hi {username},
            
            Thank you for registering with {settings.app_name}. To complete your registration, please verify your email address by visiting this link:
            
            {verification_url}
            
            Important: This verification link will expire in 24 hours.
            
            If you didn't create an account with us, please ignore this email.
            
            ---
            This email was sent by {settings.app_name}
            Please do not reply to this email.
            """
            
            return await self.send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False
    
    async def send_password_reset_email(self, email: str, username: str, reset_token: str, base_url: str = "http://localhost:8000") -> bool:
        """Send password reset email to user."""
        try:
            reset_url = f"{base_url}/auth/reset-password/{reset_token}"
            
            subject = f"Password Reset Request - {settings.app_name}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Password Reset</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .button {{ 
                        display: inline-block; 
                        padding: 12px 24px; 
                        background-color: #dc3545; 
                        color: white; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                    }}
                    .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Reset Request</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {username},</h2>
                        <p>We received a request to reset your password for your {settings.app_name} account.</p>
                        
                        <div style="text-align: center;">
                            <a href="{reset_url}" class="button">Reset Password</a>
                        </div>
                        
                        <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; color: #dc3545;">{reset_url}</p>
                        
                        <p><strong>Important:</strong> This reset link will expire in 1 hour.</p>
                        
                        <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
                    </div>
                    <div class="footer">
                        <p>This email was sent by {settings.app_name}</p>
                        <p>Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Password Reset Request
            
            Hi {username},
            
            We received a request to reset your password for your {settings.app_name} account.
            
            To reset your password, please visit this link:
            {reset_url}
            
            Important: This reset link will expire in 1 hour.
            
            If you didn't request a password reset, please ignore this email. Your password will remain unchanged.
            
            ---
            This email was sent by {settings.app_name}
            Please do not reply to this email.
            """
            
            return await self.send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False
    
    async def send_welcome_email(self, email: str, username: str) -> bool:
        """Send welcome email after successful verification."""
        try:
            subject = f"Welcome to {settings.app_name}!"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Welcome</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to {settings.app_name}!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {username},</h2>
                        <p>Congratulations! Your email has been successfully verified and your account is now active.</p>
                        
                        <p>You can now enjoy all the features of {settings.app_name}:</p>
                        <ul>
                            <li>Real-time chat with other users</li>
                            <li>Access to available services</li>
                            <li>Secure authentication and data protection</li>
                        </ul>
                        
                        <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
                        
                        <p>Thank you for joining {settings.app_name}!</p>
                    </div>
                    <div class="footer">
                        <p>This email was sent by {settings.app_name}</p>
                        <p>Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Welcome to {settings.app_name}!
            
            Hi {username},
            
            Congratulations! Your email has been successfully verified and your account is now active.
            
            You can now enjoy all the features of {settings.app_name}:
            - Real-time chat with other users
            - Access to available services
            - Secure authentication and data protection
            
            If you have any questions or need assistance, please don't hesitate to contact our support team.
            
            Thank you for joining {settings.app_name}!
            
            ---
            This email was sent by {settings.app_name}
            Please do not reply to this email.
            """
            
            return await self.send_email(email, subject, html_content, text_content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {str(e)}")
            return False


# Global email sender instance
email_sender = EmailSender()