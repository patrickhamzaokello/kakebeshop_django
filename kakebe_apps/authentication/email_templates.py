# authentication/email_templates.py
"""
Email templates for authentication system
Supports both plain text and HTML formats
"""

from django.conf import settings
from typing import Dict, Any


class EmailTemplates:
    """Centralized email templates with HTML and plain text versions"""

    @staticmethod
    def get_base_html_template() -> str:
        """Base HTML template with styling"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 0;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .greeting {{
            font-size: 18px;
            color: #333;
            margin-bottom: 20px;
        }}
        .message {{
            font-size: 16px;
            color: #555;
            margin-bottom: 30px;
            line-height: 1.8;
        }}
        .code-container {{
            background-color: #f8f9fa;
            border: 2px dashed #667eea;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 30px 0;
        }}
        .code {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            letter-spacing: 8px;
            font-family: 'Courier New', monospace;
        }}
        .code-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .expiry {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .expiry-icon {{
            color: #ffc107;
            margin-right: 8px;
        }}
        .warning {{
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            color: #721c24;
        }}
        .footer {{
            background-color: #f8f9fa;
            padding: 30px;
            text-align: center;
            border-top: 1px solid #e9ecef;
        }}
        .footer p {{
            margin: 5px 0;
            font-size: 14px;
            color: #6c757d;
        }}
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background-color: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: 600;
        }}
        .social-links {{
            margin-top: 20px;
        }}
        .social-links a {{
            color: #667eea;
            text-decoration: none;
            margin: 0 10px;
        }}
        @media only screen and (max-width: 600px) {{
            .content {{
                padding: 30px 20px;
            }}
            .code {{
                font-size: 28px;
                letter-spacing: 6px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 {company_name}</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p><strong>{company_name}</strong></p>
            <p>Building the future of secure authentication</p>
            <p style="margin-top: 15px; font-size: 12px;">
                © {year} {company_name}. All rights reserved.
            </p>
            <div class="social-links">
                <a href="#">Twitter</a> •
                <a href="#">LinkedIn</a> •
                <a href="#">Support</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

    @classmethod
    def email_verification(cls, user_name: str, verification_code: str) -> Dict[str, str]:
        """Email verification template"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                Welcome aboard! 🎉 We're excited to have you join our community. 
                To get started and secure your account, please verify your email address.
            </p>

            <div class="code-container">
                <div class="code-label">Your Verification Code</div>
                <div class="code">{verification_code}</div>
            </div>

            <div class="expiry">
                <span class="expiry-icon">⏰</span>
                <strong>Important:</strong> This code will expire in 30 minutes for security reasons.
            </div>

            <p class="message">
                Simply enter this code in the app to verify your email address and 
                unlock all the amazing features we have prepared for you.
            </p>

            <div class="warning">
                <strong>⚠️ Didn't create an account?</strong><br>
                If you didn't sign up for an account, you can safely ignore this email. 
                Your email address will not be used without verification.
            </div>

            <p class="message" style="margin-top: 30px;">
                Need help? Our support team is here for you 24/7. Just reply to this email.
            </p>
        """

        plain_text = f"""Hello {user_name},

Welcome aboard! We're excited to have you join our community.

To get started and secure your account, please verify your email address.

YOUR VERIFICATION CODE: {verification_code}

⏰ IMPORTANT: This code will expire in 30 minutes for security reasons.

Simply enter this code in the app to verify your email address and unlock all the amazing features we have prepared for you.

⚠️ DIDN'T CREATE AN ACCOUNT?
If you didn't sign up for an account, you can safely ignore this email. Your email address will not be used without verification.

Need help? Our support team is here for you 24/7. Just reply to this email.

Best regards,
The AEACBIO Team

© {cls._get_year()} AEACBIO. All rights reserved."""

        return {
            'subject': '🔐 Verify Your Email Address',
            'html': cls._wrap_html_content(content, 'Verify Your Email Address'),
            'plain': plain_text
        }

    @classmethod
    def resend_verification(cls, user_name: str, verification_code: str) -> Dict[str, str]:
        """Resend verification code template"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                You requested a new verification code. Here it is! 
            </p>

            <div class="code-container">
                <div class="code-label">Your New Verification Code</div>
                <div class="code">{verification_code}</div>
            </div>

            <div class="expiry">
                <span class="expiry-icon">⏰</span>
                <strong>Expires in:</strong> 30 minutes
            </div>

            <p class="message">
                Enter this code in the app to complete your email verification.
            </p>

            <div class="warning">
                <strong>⚠️ Security Note:</strong><br>
                If you didn't request this code, please secure your account immediately 
                by contacting our support team.
            </div>
        """

        plain_text = f"""Hello {user_name},

You requested a new verification code. Here it is!

YOUR NEW VERIFICATION CODE: {verification_code}

⏰ Expires in: 30 minutes

Enter this code in the app to complete your email verification.

⚠️ SECURITY NOTE:
If you didn't request this code, please secure your account immediately by contacting our support team.

Best regards,
The AEACBIO Team

© {cls._get_year()} AEACBIO. All rights reserved."""

        return {
            'subject': '🔐 New Verification Code',
            'html': cls._wrap_html_content(content, 'New Verification Code'),
            'plain': plain_text
        }

    @classmethod
    def password_reset(cls, user_name: str, reset_code: str) -> Dict[str, str]:
        """Password reset template"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                We received a request to reset your password. No worries, we've got you covered! 
            </p>

            <div class="code-container">
                <div class="code-label">Your Password Reset Code</div>
                <div class="code">{reset_code}</div>
            </div>

            <div class="expiry">
                <span class="expiry-icon">⏰</span>
                <strong>Act quickly!</strong> This code will expire in 15 minutes for your security.
            </div>

            <p class="message">
                Enter this code in the app to proceed with resetting your password. 
                After verification, you'll be able to create a new, secure password.
            </p>

            <div class="warning">
                <strong>⚠️ Didn't request a password reset?</strong><br>
                If you didn't request this, please ignore this email. Your password will remain unchanged. 
                Consider enabling two-factor authentication for added security.
            </div>

            <p class="message" style="margin-top: 30px; font-size: 14px; color: #666;">
                <strong>Security Tips:</strong><br>
                • Never share your reset code with anyone<br>
                • Our team will never ask for your password or reset code<br>
                • Use a strong, unique password for your account
            </p>
        """

        plain_text = f"""Hello {user_name},

We received a request to reset your password. No worries, we've got you covered!

YOUR PASSWORD RESET CODE: {reset_code}

⏰ ACT QUICKLY! This code will expire in 15 minutes for your security.

Enter this code in the app to proceed with resetting your password. After verification, you'll be able to create a new, secure password.

⚠️ DIDN'T REQUEST A PASSWORD RESET?
If you didn't request this, please ignore this email. Your password will remain unchanged. Consider enabling two-factor authentication for added security.

SECURITY TIPS:
• Never share your reset code with anyone
• Our team will never ask for your password or reset code
• Use a strong, unique password for your account

Need help? Contact our support team immediately.

Best regards,
The AEACBIO Team

© {cls._get_year()} AEACBIO. All rights reserved."""

        return {
            'subject': '🔒 Password Reset Request',
            'html': cls._wrap_html_content(content, 'Password Reset Request'),
            'plain': plain_text
        }

    @classmethod
    def password_reset_success(cls, user_name: str) -> Dict[str, str]:
        """Password reset success confirmation"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                ✅ <strong>Success!</strong> Your password has been successfully reset.
            </p>

            <p class="message">
                You can now log in to your account using your new password. 
                Make sure to keep it secure and don't share it with anyone.
            </p>

            <div class="warning">
                <strong>⚠️ Didn't reset your password?</strong><br>
                If you didn't make this change, your account may be compromised. 
                Please contact our support team immediately at support@aeacbio.com
            </div>

            <p class="message" style="margin-top: 30px;">
                <strong>Security Recommendations:</strong><br>
                • Enable two-factor authentication<br>
                • Use a unique password for this account<br>
                • Review your recent account activity<br>
                • Update your password regularly
            </p>
        """

        plain_text = f"""Hello {user_name},

✅ SUCCESS! Your password has been successfully reset.

You can now log in to your account using your new password. Make sure to keep it secure and don't share it with anyone.

⚠️ DIDN'T RESET YOUR PASSWORD?
If you didn't make this change, your account may be compromised. Please contact our support team immediately at support@aeacbio.com

SECURITY RECOMMENDATIONS:
• Enable two-factor authentication
• Use a unique password for this account
• Review your recent account activity
• Update your password regularly

Best regards,
The AEACBIO Team

© {cls._get_year()} AEACBIO. All rights reserved."""

        return {
            'subject': '✅ Password Successfully Reset',
            'html': cls._wrap_html_content(content, 'Password Successfully Reset'),
            'plain': plain_text
        }

    @classmethod
    def welcome_verified(cls, user_name: str, username: str) -> Dict[str, str]:
        """Welcome email after successful verification"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                🎉 <strong>Congratulations!</strong> Your email has been verified successfully. 
                Welcome to AEACBIO!
            </p>

            <p class="message">
                Your account (<strong>@{username}</strong>) is now fully activated and ready to use. 
                You have access to all our amazing features.
            </p>

            <div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; font-size: 16px; color: #0066cc;">
                    <strong>🚀 Getting Started:</strong>
                </p>
                <ul style="margin: 10px 0; color: #333;">
                    <li>Complete your profile</li>
                    <li>Explore the dashboard</li>
                    <li>Connect with the community</li>
                    <li>Set up two-factor authentication (recommended)</li>
                </ul>
            </div>

            <p class="message">
                Need help getting started? Check out our 
                <a href="#" style="color: #667eea; text-decoration: none;">Quick Start Guide</a> 
                or reach out to our support team anytime.
            </p>

            <p class="message" style="margin-top: 30px;">
                Thank you for choosing AEACBIO. We're here to support you every step of the way!
            </p>
        """

        plain_text = f"""Hello {user_name},

🎉 CONGRATULATIONS! Your email has been verified successfully. Welcome to AEACBIO!

Your account (@{username}) is now fully activated and ready to use. You have access to all our amazing features.

🚀 GETTING STARTED:
• Complete your profile
• Explore the dashboard
• Connect with the community
• Set up two-factor authentication (recommended)

Need help getting started? Check out our Quick Start Guide or reach out to our support team anytime.

Thank you for choosing AEACBIO. We're here to support you every step of the way!

Best regards,
The AEACBIO Team

© {cls._get_year()} AEACBIO. All rights reserved."""

        return {
            'subject': '🎉 Welcome to AEACBIO - Email Verified!',
            'html': cls._wrap_html_content(content, 'Welcome to AEACBIO'),
            'plain': plain_text
        }

    @classmethod
    def _wrap_html_content(cls, content: str, subject: str) -> str:
        """Wrap content in base HTML template"""
        from datetime import datetime

        company_name = getattr(settings, 'COMPANY_NAME', 'AEACBIO')

        return cls.get_base_html_template().format(
            subject=subject,
            company_name=company_name,
            content=content,
            year=datetime.now().year
        )

    @staticmethod
    def _get_year() -> int:
        """Get current year"""
        from datetime import datetime
        return datetime.now().year


# Convenience function to get email data
def get_email_template(template_type: str, **kwargs) -> Dict[str, Any]:
    """
    Get email template by type

    Args:
        template_type: Type of email template
        **kwargs: Template variables

    Returns:
        Dictionary with subject, html, and plain text content
    """
    templates = {
        'email_verification': EmailTemplates.email_verification,
        'resend_verification': EmailTemplates.resend_verification,
        'password_reset': EmailTemplates.password_reset,
        'password_reset_success': EmailTemplates.password_reset_success,
        'welcome_verified': EmailTemplates.welcome_verified,
    }

    template_func = templates.get(template_type)
    if not template_func:
        raise ValueError(f"Unknown template type: {template_type}")

    return template_func(**kwargs)