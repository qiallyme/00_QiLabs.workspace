// https://www.npmjs.com/package/zeptomail

// For ES6
import { SendMailClient } from "zeptomail";

// For CommonJS
// var { SendMailClient } = require("zeptomail");

const url = "https://api.zeptomail.com/v1.1/email";
const token = "Zoho-enczapikey wSsVR61//hb4W6cun2WqceZrylRTD1z2FER13wCh7XSuFqjE98c9k0GdDAGkG/VLEDJqEDcX8Lsgnh4FhztaiIh5zwtRDCiF9mqRe1U4J3x17qnvhDzKXmVVlBqOJYwMzwpommVnEskk+g==";

let client = new SendMailClient({ url, token });

client.sendMail({
    "from":
    {
        "address": "noreply@qially.com",
        "name": "noreply"
    },
    "to":
        [
            {
                "email_address":
                {
                    "address": "crice4485@gmail.com",
                    "name": "Cody"
                }
            }
        ],
    "subject": "Test Email",
    "htmlbody": "<div><b> Test email sent successfully.</b></div>",
}).then((resp) => console.log("success")).catch((error) => console.log("error"));