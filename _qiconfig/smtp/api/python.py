import requests

url = "https://api.zeptomail.com/v1.1/email"

payload = "{\n\"from\": { \"address\": \"noreply@qially.com\"},\n\"to\": [{\"email_address\": {\"address\": \"crice4485@gmail.com\",\"name\": \"Cody\"}}],\n\"subject\":\"Test Email\",\n\"htmlbody\":\"<div><b> Test email sent successfully.  </b></div>\"\n}"
headers = {
'accept': "application/json",
'content-type': "application/json",
'authorization': "Zoho-enczapikey wSsVR61//hb4W6cun2WqceZrylRTD1z2FER13wCh7XSuFqjE98c9k0GdDAGkG/VLEDJqEDcX8Lsgnh4FhztaiIh5zwtRDCiF9mqRe1U4J3x17qnvhDzKXmVVlBqOJYwMzwpommVnEskk+g==",
}

response = requests.request("POST", url, data=payload, headers=headers)

print(response.text)