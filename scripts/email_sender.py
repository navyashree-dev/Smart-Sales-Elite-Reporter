import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
import os  # <- new import for safe path handling

def send_email(to_email, subject, body, attachment_path):
    from_email = "navyajayarama@gmail.com"  # Replace with your Gmail
    password = "cnel ejdd ciau scwn"  # Replace with the 16-character App Password (no spaces)

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Attach PDF
    if attachment_path and os.path.exists(attachment_path):
        # Use os.path.basename to get only filename for attachment
        filename = os.path.basename(attachment_path)
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(part)
    else:
        print(f"Attachment not found: {attachment_path}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)  # Login with App Password
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
