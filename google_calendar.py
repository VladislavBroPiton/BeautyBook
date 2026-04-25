import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarManager:
    def __init__(self, calendar_id):
        self.calendar_id = calendar_id
        self.service = self._authenticate()

    def _authenticate(self):
        # Получаем содержимое JSON из переменной окружения
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        if not credentials_json:
            raise ValueError("GOOGLE_CREDENTIALS environment variable not set")

        # Загружаем данные сервисного аккаунта из JSON-строки
        creds_dict = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        return build('calendar', 'v3', credentials=creds)

    async def create_event(self, summary, description, start_time, end_time):
        """Создаёт событие в Google Календаре."""
        event_body = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'Europe/Moscow'},
            'end': {'dateTime': end_time, 'timeZone': 'Europe/Moscow'},
        }
        event = self.service.events().insert(calendarId=self.calendar_id, body=event_body).execute()
        return event.get('htmlLink')
