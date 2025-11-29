"""
Email Tool for sending emails via SMTP

Supports plain text and HTML emails with attachments.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import aiosmtplib

from ..base import ITool, ToolExecutionResult

logger = logging.getLogger(__name__)


class EmailTool(ITool):
    """
    Email Tool 實作

    用於發送電子郵件,支援 HTML 和純文字格式
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True,
        default_from: Optional[str] = None,
    ):
        """
        初始化 Email Tool

        Args:
            smtp_host: SMTP 伺服器主機名
            smtp_port: SMTP 伺服器埠號 (預設: 587 for TLS)
            smtp_username: SMTP 認證帳號 (optional)
            smtp_password: SMTP 認證密碼 (optional)
            use_tls: 是否使用 TLS (預設: True)
            default_from: 預設寄件者地址 (optional)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.default_from = default_from

    @property
    def name(self) -> str:
        return "email"

    @property
    def description(self) -> str:
        return "Send emails via SMTP (supports plain text and HTML)"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["to", "subject", "body"],
            "properties": {
                "to": {
                    "type": "array",
                    "description": "Recipient email addresses",
                    "items": {"type": "string", "format": "email"},
                    "minItems": 1,
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject",
                    "minLength": 1,
                },
                "body": {
                    "type": "string",
                    "description": "Email body (plain text or HTML)",
                },
                "from_addr": {
                    "type": "string",
                    "format": "email",
                    "description": "Sender email address (optional, uses default if not provided)",
                },
                "cc": {
                    "type": "array",
                    "description": "CC recipient email addresses (optional)",
                    "items": {"type": "string", "format": "email"},
                },
                "bcc": {
                    "type": "array",
                    "description": "BCC recipient email addresses (optional)",
                    "items": {"type": "string", "format": "email"},
                },
                "html": {
                    "type": "boolean",
                    "description": "Whether body is HTML (default: False)",
                    "default": False,
                },
                "attachments": {
                    "type": "array",
                    "description": "Email attachments (optional)",
                    "items": {
                        "type": "object",
                        "required": ["filename", "content"],
                        "properties": {
                            "filename": {"type": "string"},
                            "content": {"type": "string", "description": "Base64 encoded content"},
                            "content_type": {"type": "string", "default": "application/octet-stream"},
                        },
                    },
                },
            },
        }

    async def execute(self, **kwargs) -> ToolExecutionResult:
        """
        發送電子郵件

        Args:
            to: 收件者地址列表
            subject: 郵件主旨
            body: 郵件內容
            from_addr: 寄件者地址 (optional)
            cc: 副本收件者列表 (optional)
            bcc: 密件副本收件者列表 (optional)
            html: 是否為 HTML 格式 (optional)
            attachments: 附件列表 (optional)

        Returns:
            ToolExecutionResult 包含發送結果
        """
        start_time = datetime.now(timezone.utc)

        to_addrs = kwargs.get("to", [])
        subject = kwargs.get("subject")
        body = kwargs.get("body")
        from_addr = kwargs.get("from_addr", self.default_from)
        cc_addrs = kwargs.get("cc", [])
        bcc_addrs = kwargs.get("bcc", [])
        is_html = kwargs.get("html", False)
        attachments = kwargs.get("attachments", [])

        # Validate from address
        if not from_addr:
            return ToolExecutionResult(
                success=False,
                output=None,
                error_message="From address is required (set default_from or provide from_addr)",
                execution_time_ms=0,
                metadata={"smtp_host": self.smtp_host},
            )

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = from_addr
            msg["To"] = ", ".join(to_addrs)
            msg["Subject"] = subject

            if cc_addrs:
                msg["Cc"] = ", ".join(cc_addrs)

            # Attach body
            mime_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, mime_type, "utf-8"))

            # Attach files (if any)
            for attachment in attachments:
                filename = attachment.get("filename")
                content = attachment.get("content")  # Base64 encoded
                content_type = attachment.get("content_type", "application/octet-stream")

                # Decode base64 content
                import base64

                file_data = base64.b64decode(content)

                # Create attachment part
                part = MIMEBase(*content_type.split("/"))
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={filename}")
                msg.attach(part)

            # All recipients (to + cc + bcc)
            all_recipients = to_addrs + cc_addrs + bcc_addrs

            # Send email
            async with aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port) as smtp:
                if self.use_tls:
                    await smtp.starttls()

                if self.smtp_username and self.smtp_password:
                    await smtp.login(self.smtp_username, self.smtp_password)

                await smtp.send_message(msg, from_addr=from_addr, to_addrs=all_recipients)

            # Calculate execution time
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            output = {
                "sent": True,
                "recipients": {
                    "to": to_addrs,
                    "cc": cc_addrs,
                    "bcc": bcc_addrs,
                },
                "subject": subject,
                "from": from_addr,
                "attachment_count": len(attachments),
            }

            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")

            return ToolExecutionResult(
                success=True,
                output=output,
                execution_time_ms=execution_time_ms,
                metadata={
                    "smtp_host": self.smtp_host,
                    "recipient_count": len(all_recipients),
                    "has_attachments": len(attachments) > 0,
                },
            )

        except aiosmtplib.SMTPException as e:
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error(f"SMTP error while sending email: {e}")

            return ToolExecutionResult(
                success=False,
                output=None,
                error_message=f"SMTP error: {str(e)}",
                execution_time_ms=execution_time_ms,
                metadata={"smtp_host": self.smtp_host, "error_type": "smtp_error"},
            )

        except Exception as e:
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            logger.error(f"Failed to send email: {e}")

            return ToolExecutionResult(
                success=False,
                output=None,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
                metadata={"smtp_host": self.smtp_host, "error_type": type(e).__name__},
            )

    def validate_parameters(self, params: Dict[str, Any]) -> None:
        """
        驗證參數

        Args:
            params: 要驗證的參數

        Raises:
            ValueError: 參數驗證失敗
        """
        super().validate_parameters(params)

        # Validate recipients
        to_addrs = params.get("to", [])
        if not to_addrs or not isinstance(to_addrs, list) or len(to_addrs) == 0:
            raise ValueError("At least one recipient (to) is required")

        # Validate subject
        subject = params.get("subject", "")
        if not subject or not subject.strip():
            raise ValueError("Subject cannot be empty")

        # Validate body
        body = params.get("body", "")
        if body is None or not isinstance(body, str):
            raise ValueError("Body must be a string")
