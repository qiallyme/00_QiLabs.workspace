import smtplib, ssl
from email.message import EmailMessage
port = 587
smtp_server = "smtp.zeptomail.com"
username="emailapikey"
password = "wSsVR61//hb4W6cun2WqceZrylRTD1z2FER13wCh7XSuFqjE98c9k0GdDAGkG/VLEDJqEDcX8Lsgnh4FhztaiIh5zwtRDCiF9mqRe1U4J3x17qnvhDzKXmVVlBqOJYwMzwpommVnEskk+g=="
message = "Test email sent successfully."
msg = EmailMessage()
msg['Subject'] = "Test Email"
msg['From'] = "noreply@qially.com"
msg['To'] = "crice4485@gmail.com"
msg.set_content(message)
try:
    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(username, password)
            server.send_message(msg)
    elif port == 587:
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
    else:
        print ("use 465 / 587 as port value")
        exit()
    print ("successfully sent")
except Exception as e:
    print (e)