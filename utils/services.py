

from requests import post
import os
from dotenv import load_dotenv
load_dotenv()

class Services:
    def __getTokenApi():
        response = post(
            f'{os.getenv("API_GF_URL")}/login',
            data={
                'username': os.getenv('API_GF_USERNAME'),
                'password': os.getenv('API_GF_PASSWORD')
            }
        )
        data = response.json()
        print(data['access_token'])
        access_token = data['access_token']
        return access_token

    def sendEmail(body, subject, emailsTo, country=None, imageHeader=None, imageFooter=None):
        token = Services.__getTokenApi()
        headers = {
            'Authorization': f'Bearer {token}'
        }
        data = {
            'body': body,
            'subject': subject,
            'emails_to': emailsTo,
            'country': country,
            'image_header': imageHeader,
            'image_footer': imageFooter,
        }
        response = post(
            f'{os.getenv("API_GF_URL")}/sendMail',
            headers=headers,
            data=data
        )
        return response.status_code