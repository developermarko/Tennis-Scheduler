import os
import sendgrid
from sendgrid.helpers.mail import Mail

def send_email():
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    sender_email = os.environ.get('SENDGRID_SENDER_EMAIL')
    recipient_email = os.environ.get('SENDGRID_RECIPIENT_EMAIL')

    # Read the HTML output file
    with open('output.html', 'r') as f:
        html_content = f.read()

    # Create email content
    message = Mail(
        from_email='marko.nisic9@hotmail.com',
        to_emails='markonisic1998@gmail.com',
        subject='Automated Jupyter Notebook Report',
        html_content=html_content
    )

    # Send the email
    try:
        response = sg.send(message)
        print(f"Email sent successfully: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    send_email()
