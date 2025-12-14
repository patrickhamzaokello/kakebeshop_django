# authentication/email_templates.py
"""
Minimalistic Email Templates for KakebeShop
Clean, elegant, monochromatic design (black and white)
"""

from django.conf import settings
from typing import Dict, Any


class EmailTemplates:
    """Minimalistic monochromatic email templates for KakebeShop"""

    @staticmethod
    def get_base_html_template() -> str:
        """Minimalistic base HTML template - clean and compact"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #000000;
            background-color: #ffffff;
            padding: 0;
            margin: 0;
        }}
        .container {{
            max-width: 560px;
            margin: 40px auto;
            background-color: #ffffff;
        }}
        .header {{
            text-align: center;
            padding: 32px 20px 24px;
            border-bottom: 2px solid #000000;
        }}
        .logo {{
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: #000000;
            text-transform: uppercase;
        }}
        .content {{
            padding: 32px 20px;
        }}
        .greeting {{
            font-size: 16px;
            color: #000000;
            margin-bottom: 16px;
            font-weight: 500;
        }}
        .message {{
            font-size: 15px;
            color: #333333;
            margin-bottom: 20px;
            line-height: 1.7;
        }}
        .code-container {{
            background-color: #f8f8f8;
            border: 1px solid #000000;
            padding: 24px;
            text-align: center;
            margin: 28px 0;
        }}
        .code-label {{
            font-size: 11px;
            color: #666666;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }}
        .code {{
            font-size: 32px;
            font-weight: 700;
            color: #000000;
            letter-spacing: 6px;
            font-family: 'Courier New', monospace;
            margin: 8px 0;
        }}
        .info-box {{
            border-left: 3px solid #000000;
            padding: 12px 16px;
            margin: 20px 0;
            background-color: #fafafa;
        }}
        .info-box p {{
            margin: 0;
            font-size: 14px;
            color: #333333;
            line-height: 1.6;
        }}
        .warning-box {{
            border: 1px solid #000000;
            padding: 16px;
            margin: 20px 0;
            background-color: #f5f5f5;
        }}
        .warning-box p {{
            margin: 0;
            font-size: 14px;
            color: #000000;
            line-height: 1.6;
        }}
        .divider {{
            height: 1px;
            background-color: #e0e0e0;
            margin: 28px 0;
        }}
        .footer {{
            padding: 24px 20px;
            text-align: center;
            border-top: 1px solid #e0e0e0;
        }}
        .footer-text {{
            font-size: 13px;
            color: #666666;
            margin: 4px 0;
            line-height: 1.5;
        }}
        .footer-brand {{
            font-weight: 600;
            color: #000000;
            font-size: 13px;
        }}
        .link {{
            color: #000000;
            text-decoration: underline;
        }}
        @media only screen and (max-width: 600px) {{
            .container {{
                margin: 20px auto;
            }}
            .content {{
                padding: 24px 16px;
            }}
            .code {{
                font-size: 28px;
                letter-spacing: 4px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{company_name}</div>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p class="footer-brand">{company_name}</p>
            <p class="footer-text">Online Marketplace</p>
            <p class="footer-text" style="margin-top: 12px;">© {year} {company_name}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

    @classmethod
    def email_verification(cls, user_name: str, verification_code: str) -> Dict[str, str]:
        """Email verification template - minimalistic design"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                Welcome to KakebeShop. Please verify your email address to activate your account.
            </p>

            <div class="code-container">
                <div class="code-label">Verification Code</div>
                <div class="code">{verification_code}</div>
            </div>

            <div class="info-box">
                <p><strong>Expires in 30 minutes</strong></p>
            </div>

            <p class="message">
                Enter this code in the application to verify your email address and complete your registration.
            </p>

            <div class="divider"></div>

            <p class="message" style="font-size: 14px; color: #666666;">
                If you didn't create an account with KakebeShop, please ignore this email.
            </p>
        """

        plain_text = f"""Hello {user_name},

Welcome to KakebeShop. Please verify your email address to activate your account.

VERIFICATION CODE: {verification_code}

This code expires in 30 minutes.

Enter this code in the application to verify your email address and complete your registration.

If you didn't create an account with KakebeShop, please ignore this email.

—
KakebeShop
Online Marketplace
© {cls._get_year()} KakebeShop. All rights reserved."""

        return {
            'subject': 'Verify Your Email – KakebeShop',
            'html': cls._wrap_html_content(content, 'Verify Your Email'),
            'plain': plain_text
        }

    @classmethod
    def resend_verification(cls, user_name: str, verification_code: str) -> Dict[str, str]:
        """Resend verification code template"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                Here is your new verification code for KakebeShop.
            </p>

            <div class="code-container">
                <div class="code-label">Verification Code</div>
                <div class="code">{verification_code}</div>
            </div>

            <div class="info-box">
                <p><strong>Expires in 30 minutes</strong></p>
            </div>

            <p class="message">
                Enter this code in the application to verify your email address.
            </p>

            <div class="divider"></div>

            <p class="message" style="font-size: 14px; color: #666666;">
                If you didn't request this code, please secure your account immediately.
            </p>
        """

        plain_text = f"""Hello {user_name},

Here is your new verification code for KakebeShop.

VERIFICATION CODE: {verification_code}

This code expires in 30 minutes.

Enter this code in the application to verify your email address.

If you didn't request this code, please secure your account immediately.

—
KakebeShop
Online Marketplace
© {cls._get_year()} KakebeShop. All rights reserved."""

        return {
            'subject': 'New Verification Code – KakebeShop',
            'html': cls._wrap_html_content(content, 'New Verification Code'),
            'plain': plain_text
        }

    @classmethod
    def password_reset(cls, user_name: str, reset_code: str) -> Dict[str, str]:
        """Password reset template"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                We received a request to reset your password for your KakebeShop account.
            </p>

            <div class="code-container">
                <div class="code-label">Reset Code</div>
                <div class="code">{reset_code}</div>
            </div>

            <div class="info-box">
                <p><strong>Expires in 15 minutes</strong></p>
            </div>

            <p class="message">
                Enter this code in the application to proceed with resetting your password.
            </p>

            <div class="warning-box">
                <p><strong>Security Notice</strong></p>
                <p style="margin-top: 8px;">If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
            </div>
        """

        plain_text = f"""Hello {user_name},

We received a request to reset your password for your KakebeShop account.

RESET CODE: {reset_code}

This code expires in 15 minutes.

Enter this code in the application to proceed with resetting your password.

SECURITY NOTICE:
If you didn't request a password reset, please ignore this email. Your password will remain unchanged.

—
KakebeShop
Online Marketplace
© {cls._get_year()} KakebeShop. All rights reserved."""

        return {
            'subject': 'Password Reset Request – KakebeShop',
            'html': cls._wrap_html_content(content, 'Password Reset Request'),
            'plain': plain_text
        }

    @classmethod
    def password_reset_success(cls, user_name: str) -> Dict[str, str]:
        """Password reset success confirmation"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                Your password has been successfully reset.
            </p>

            <div class="info-box">
                <p>You can now log in to your KakebeShop account using your new password.</p>
            </div>

            <div class="divider"></div>

            <p class="message">
                <strong>Recommended Actions:</strong>
            </p>
            <p class="message" style="font-size: 14px;">
                • Review your recent account activity<br>
                • Enable two-factor authentication<br>
                • Use a unique password for this account
            </p>

            <div class="warning-box">
                <p><strong>Didn't change your password?</strong></p>
                <p style="margin-top: 8px;">If you didn't make this change, please contact our support team immediately to secure your account.</p>
            </div>
        """

        plain_text = f"""Hello {user_name},

Your password has been successfully reset.

You can now log in to your KakebeShop account using your new password.

RECOMMENDED ACTIONS:
• Review your recent account activity
• Enable two-factor authentication
• Use a unique password for this account

DIDN'T CHANGE YOUR PASSWORD?
If you didn't make this change, please contact our support team immediately to secure your account.

—
KakebeShop
Online Marketplace
© {cls._get_year()} KakebeShop. All rights reserved."""

        return {
            'subject': 'Password Reset Successful – KakebeShop',
            'html': cls._wrap_html_content(content, 'Password Reset Successful'),
            'plain': plain_text
        }

    @classmethod
    def welcome_verified(cls, user_name: str, username: str) -> Dict[str, str]:
        """Welcome email after successful verification"""

        content = f"""
            <p class="greeting">Hello {user_name},</p>
            <p class="message">
                Your email has been verified successfully. Welcome to KakebeShop.
            </p>

            <div class="info-box">
                <p><strong>Username:</strong> @{username}</p>
                <p style="margin-top: 6px;">Your account is now fully activated.</p>
            </div>

            <div class="divider"></div>

            <p class="message">
                <strong>Getting Started:</strong>
            </p>
            <p class="message" style="font-size: 14px;">
                • Browse products from verified sellers<br>
                • Create your first listing<br>
                • Connect with the community<br>
                • Complete your profile
            </p>

            <div class="divider"></div>

            <p class="message" style="font-size: 14px; color: #666666;">
                Thank you for choosing KakebeShop. We're here to support you.
            </p>
        """

        plain_text = f"""Hello {user_name},

Your email has been verified successfully. Welcome to KakebeShop.

USERNAME: @{username}
Your account is now fully activated.

GETTING STARTED:
• Browse products from verified sellers
• Create your first listing
• Connect with the community
• Complete your profile

Thank you for choosing KakebeShop. We're here to support you.

—
KakebeShop
Online Marketplace
© {cls._get_year()} KakebeShop. All rights reserved."""

        return {
            'subject': 'Welcome to KakebeShop',
            'html': cls._wrap_html_content(content, 'Welcome to KakebeShop'),
            'plain': plain_text
        }

    @classmethod
    def _wrap_html_content(cls, content: str, subject: str) -> str:
        """Wrap content in base HTML template"""
        from datetime import datetime

        company_name = getattr(settings, 'COMPANY_NAME', 'KakebeShop')

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