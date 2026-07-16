import java.util.Properties;
import javax.mail.Message;
import javax.mail.MessagingException;
import javax.mail.Session;
import javax.mail.Transport;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeMessage;

public class SendMail {

    public static void main(String[] args) throws Exception {

        Properties properties = System.getProperties();
        properties.setProperty("mail.smtp.host", "smtp.zeptomail.com");
        properties.put("mail.smtp.port", "587");
        properties.put("mail.smtp.auth", "true");
        properties.put("mail.smtp.starttls.enable", "true");
        properties.put("mail.smtp.from", "fromaddress");
        properties.put("mail.smtp.ssl.protocols", "TLSv1.2");
        Session session = Session.getDefaultInstance(properties);

        try {
            MimeMessage message = new MimeMessage(session);
            message.setFrom(new InternetAddress("noreply@qially.com"));
                message.addRecipient(Message.RecipientType.TO, new InternetAddress("crice4485@gmail.com"));
            message.setSubject("Test Email");
                message.setText("Test email sent successfully.");
            Transport transport = session.getTransport("smtp");
            transport.connect("smtp.zeptomail.com", 587, "emailapikey", "wSsVR61//hb4W6cun2WqceZrylRTD1z2FER13wCh7XSuFqjE98c9k0GdDAGkG/VLEDJqEDcX8Lsgnh4FhztaiIh5zwtRDCiF9mqRe1U4J3x17qnvhDzKXmVVlBqOJYwMzwpommVnEskk+g==");
            transport.sendMessage(message, message.getAllRecipients());
            transport.close();
            System.out.println("Mail successfully sent");
        } catch (Exception ex) {
            System.out.print(ex.getMessage());
        }
    }
}