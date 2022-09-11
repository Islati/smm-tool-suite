"""
Email validation service module.

Performs rest request to email validation service.
"""
import requests

from bot.webapp.config import Config


class EmailValidator:
    VALID_DOMAINS = ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com')

    """
    Email validation service class. Calls Debounce API
    """

    @staticmethod
    def validate(email: str) -> bool:
        """
        Validates email address.
        :return:
        """

        for domain in EmailValidator.VALID_DOMAINS:
            if domain in email:
                return True

        response = requests.get(f"https://api.debounce.io/v1/?api={Config.EMAIL_VALIDATION_API_KEY}&email={email}")
        return int(response.json()['success']) == 1
