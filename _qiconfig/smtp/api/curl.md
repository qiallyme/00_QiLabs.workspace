curl "<https://api.zeptomail.com/v1.1/email>" \
        -X POST \
        -H "Accept: application/json" \
        -H "Content-Type: application/json" \
        -H "Authorization:Zoho-enczapikey wSsVR61//hb4W6cun2WqceZrylRTD1z2FER13wCh7XSuFqjE98c9k0GdDAGkG/VLEDJqEDcX8Lsgnh4FhztaiIh5zwtRDCiF9mqRe1U4J3x17qnvhDzKXmVVlBqOJYwMzwpommVnEskk+g==" \
        -d '{
        "from": {"address": "<noreply@qially.com>"},
        "to": [{"email_address": {"address": "crice4485@gmail.com","name": "Cody"}}],
        "subject":"Test Email",
        "htmlbody":"<div><b> Test email sent successfully. </b></div>"}'
