import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta

CREDENTIALS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarManager:
    def __init__(self, calendar_id):
        self.calendar_id = calendar_id
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return build('calendar', 'v3', credentials=creds)

    async def create_event(self, summary, description, start_time, end_time):
        event_body = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'Europe/Moscow'},
            'end': {'dateTime': end_time, 'timeZone': 'Europe/Moscow'},
        }
        event = self.service.events().insert(calendarId=self.calendar_id, body=event_body).execute()
        return event.get('htmlLink')
