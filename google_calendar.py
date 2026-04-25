import os
import json
import pickle
import tempfile
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Имя переменной окружения, где лежит содержимое credentials.json
ENV_CREDENTIALS = "GOOGLE_CREDENTIALS"
# Путь к локальному файлу (для разработки)
LOCAL_CREDENTIALS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarManager:
    def __init__(self, calendar_id):
        self.calendar_id = calendar_id
        self.service = self._authenticate()

    def _get_credentials_file_path(self):
        """
        Возвращает путь к файлу с учётными данными.
        Если задана переменная окружения, создаёт временный файл.
        """
        credentials_content = os.getenv(ENV_CREDENTIALS)
        if credentials_content:
            # Создаём временный файл и записываем в него содержимое
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
            temp_file.write(credentials_content)
            temp_file.flush()
            return temp_file.name
        else:
            # Используем локальный файл (для разработки)
            return LOCAL_CREDENTIALS_FILE

    def _authenticate(self):
        creds = None
        # Файл для хранения токена (необязательно, но полезно)
        token_file = 'token.pickle'
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Получаем путь к файлу с учётными данными
                creds_path = self._get_credentials_file_path()
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
                # Удаляем временный файл после использования (если создавали)
                if os.getenv(ENV_CREDENTIALS) and os.path.exists(creds_path):
                    os.unlink(creds_path)
            # Сохраняем токен для будущих запусков
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

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
