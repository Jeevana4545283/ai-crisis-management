import logging
from vonage import Auth, Vonage

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, api_key, api_secret):
        self.is_configured = False
        self.client = None
        
        if api_key and api_secret:
            try:
                auth = Auth(api_key=api_key, api_secret=api_secret)
                self.client = Vonage(auth=auth)
                self.is_configured = True
                logger.info("NotificationService initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Vonage client: {e}")
        else:
            logger.warning("Vonage API credentials not provided. SMS notifications disabled.")

    def send_crisis_alert(self, city, team, phone_number="918886667061"):
        if not self.is_configured or not self.client:
            logger.error("Attempted to send SMS but NotificationService is not configured.")
            return {"error": "SMS service is not configured."}, 500

        try:
            message = f"🚨 ALERT!\n{team} assigned in {city}. Immediate response required."
            
            response = self.client.sms.send({
                 "from_": "AI Crisis System",
                "to": phone_number,
                "text": message
            })

            if response["messages"][0]["status"] == "0":
                logger.info(f"SMS sent successfully for {city} to {phone_number}.")
                return {"success": True}, 200
            else:
                error_msg = response["messages"][0]["error-text"]
                logger.error(f"Failed to send SMS: {error_msg}")
                return {"error": error_msg}, 400

        except Exception as e:
            logger.error(f"Exception in send_crisis_alert: {e}")
            return {"error": "Failed to send SMS due to internal error."}, 500
