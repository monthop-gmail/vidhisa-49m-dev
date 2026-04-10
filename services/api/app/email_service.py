"""Email service — send credentials via Gmail SMTP."""

import os
import smtplib
from email.mime.text import MIMEText

SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


def send_credentials_email(to_email: str, full_name: str, username: str, password: str, branch_name: str) -> bool:
    """Send login credentials to branch admin."""
    if not SMTP_USER or not SMTP_PASS:
        print(f"[EMAIL SKIP] No SMTP config — would send to {to_email}: user={username} pass={password}")
        return False

    subject = f"วิทิสา 49M — ข้อมูลเข้าสู่ระบบ สาขา{branch_name}"
    body = f"""สวัสดีค่ะ/ครับ คุณ{full_name}

สาขา {branch_name} ได้รับอนุมัติเข้าร่วมโครงการวิทิสา 49 ล้านนาทีแล้ว

ข้อมูลเข้าสู่ระบบ:
- URL: http://34.15.162.243:8080/login.html
- Username: {username}
- Password: {password}

กรุณาเปลี่ยนรหัสผ่านหลังเข้าสู่ระบบครั้งแรก

ด้วยความเคารพ
ทีมวิทิสา 49 ล้านนาที
"""

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())

        print(f"[EMAIL SENT] {to_email} — user={username}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {to_email}: {e}")
        return False
