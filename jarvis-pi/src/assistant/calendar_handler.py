# src/assistant/calendar_handler.py

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from pathlib import Path
import os.path
import pickle
import os.path

class CalendarHandler:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        self.creds = None
        self.service = None
        # Get the project root directory (parent of src)
        self.project_root = Path(__file__).parent.parent.parent
        
        # Define paths relative to project root
        self.token_path = self.project_root / 'token.pickle'
        self.secrets_path = self.project_root / 'client_secrets.json'

        self._authenticate()
    
    def _authenticate(self):
        """Handle Google Calendar authentication"""
        # Token file stores user's access and refresh tokens
        token_file = self.token_path
        
        # Load existing credentials if available
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If no valid credentials available, let user log in
        if not self.creds or not self.creds.valid:
            try:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.secrets_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
                # Save credentials for future use
                with open(token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
            except Exception as e:
                print(f"Error during authentication: {e}")
                # Optionally, delete the token file to force re-authentication
                if os.path.exists(token_file):
                    print(f"🚨 Deleting token file: {token_file}")
                    os.remove(token_file)
                    
                    # TODO - add retry count limit and retry auth after deleting token file
                    # self._authenticate()
                raise e
        
        self.service = build('calendar', 'v3', credentials=self.creds)
    
    def get_events(self, time_min=None, time_max=None, max_results=10, query=None):
        """
        Get calendar events within specified timeframe
        Returns list of events with relevant details
        """
        try:
            if time_min is None:
                # TODO: update deprecated method `datetime.utcnow()`
                # tried recommeded from error message but it still didn't work
                time_min = datetime.utcnow()
            if time_max is None:
                time_max = time_min + timedelta(days=7)
                
            # Convert to RFC3339 timestamp
            time_min = time_min.isoformat() + 'Z'
            time_max = time_max.isoformat() + 'Z'
            
            # Prepare optional query parameter
            kwargs = {
                'calendarId': 'primary',
                'timeMin': time_min,
                'timeMax': time_max,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            if query:
                kwargs['q'] = query
                
            events_result = self.service.events().list(**kwargs).execute()
            events = events_result.get('items', [])
            
            # Format events for easy use
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                formatted_events.append({
                    'summary': event.get('summary', 'Untitled Event'),
                    'start': start,
                    'end': end,
                    'location': event.get('location', ''),
                    'description': event.get('description', ''),
                    'attendees': [
                        attendee['email'] 
                        for attendee in event.get('attendees', [])
                        if 'email' in attendee
                    ]
                })
                
            return formatted_events
            
        except Exception as e:
            print(f"Error fetching calendar events: {e}")
            return None
    
    def get_next_event(self):
        """Get the next upcoming event"""
        events = self.get_events(max_results=1)
        return events[0] if events else None
    
    def get_events_for_date(self, date):
        """Get all events for a specific date"""
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        return self.get_events(time_min=start, time_max=end)
    
    def search_events(self, query):
        """Search for events matching the query"""
        return self.get_events(query=query)