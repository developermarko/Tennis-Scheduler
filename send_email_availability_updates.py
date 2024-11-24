import os
import sendgrid
from sendgrid.helpers.mail import Mail

def send_email(file_name, subject):
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    sender_email = os.environ.get('SENDGRID_SENDER_EMAIL')
    recipient_email = os.environ.get('SENDGRID_RECIPIENT_EMAIL')

    try:
        # Check if the file exists
        if not os.path.exists(file_name):
            print(f"Error: {file_name} not found!")
            return

        # Read the file with explicit UTF-8 encoding
        with open(file_name, 'r', encoding='utf-8') as f:
            file_content = f.read()

        if not file_content.strip():
            print(f"Error: {file_name} is empty!")
            return

        # Create email content
        message = Mail(
            from_email=sender_email,
            to_emails=recipient_email,
            subject=subject,
            html_content=f"<pre>{file_content}</pre>"
        )

        # Send the email
        response = sg.send(message)
        print(f"Email sent successfully for {file_name}: {response.status_code}")

    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    # Send availability updates, if any
    if os.path.exists("availability_updates.html"):
        send_email("availability_updates.html", "Hourly Hackney Tennis Availability Updates")
