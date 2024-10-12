import os
import sendgrid
from sendgrid.helpers.mail import Mail

def send_email():
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    sender_email = os.environ.get('SENDGRID_SENDER_EMAIL')
    recipient_email = os.environ.get('SENDGRID_RECIPIENT_EMAIL')

    try:
        # Check if output.html exists
        if not os.path.exists('output.html'):
            print("Error: output.html not found!")
            return

        # Read the HTML output file with explicit UTF-8 encoding
        with open('output.html', 'r', encoding='utf-8') as f:
            html_content = f.read()

        if not html_content.strip():
            print("Error: output.html is empty!")
            return

        # Create email content
        message = Mail(
            from_email=sender_email,
            to_emails=recipient_email,
            subject='Automated Jupyter Notebook Report',
            html_content=html_content
        )

        # Send the email
        response = sg.send(message)
        print(f"Email sent successfully: {response.status_code}")

    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    send_email()
