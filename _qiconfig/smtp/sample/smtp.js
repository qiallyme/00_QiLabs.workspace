var nodemailer = require('nodemailer');
var transport = nodemailer.createTransport({
    host: "smtp.zeptomail.com",
    port: 587,
    auth: {
        user: "emailapikey",
        pass: "wSsVR61//hb4W6cun2WqceZrylRTD1z2FER13wCh7XSuFqjE98c9k0GdDAGkG/VLEDJqEDcX8Lsgnh4FhztaiIh5zwtRDCiF9mqRe1U4J3x17qnvhDzKXmVVlBqOJYwMzwpommVnEskk+g=="
    }
});

var mailOptions = {
    from: '"Example Team" <noreply@qially.com>',
    to: 'crice4485@gmail.com',
    subject: 'Test Email',
    html: 'Test email sent successfully.',
};

transport.sendMail(mailOptions, (error, info) => {
    if (error) {
        return console.log(error);
    }
    console.log('Successfully sent');
});