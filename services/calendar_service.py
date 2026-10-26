
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]

def calendar_setup_status():
    if not (ROOT / "credentials.json").exists():
        return "not configured (credentials.json missing)"
    if not (ROOT / "token.json").exists():
        return "credentials found; first-time OAuth authorization is needed"
    return "credentials and token found"

def create_followup_event(record):
    """Create Google Calendar event and Meet conference via Google Calendar API."""
    credentials_path = ROOT / "credentials.json"
    if not credentials_path.exists():
        raise ValueError("Add Google OAuth desktop credentials as credentials.json. See README.md.")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as e:
        raise RuntimeError("Google Calendar dependencies are missing. Install requirements.txt.") from e
    scopes = ["https://www.googleapis.com/auth/calendar.events"]
    token_path = ROOT / "token.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    from datetime import datetime, timedelta
    start = datetime.fromisoformat(record["start"])
    end = start + timedelta(minutes=int(record.get("duration_minutes", 30)))
    timezone = os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata")
    event = {
        "summary": f"Follow-up review: {record.get('candidate_name','Candidate')} — {record.get('task_title','Task')}",
        "description": "Follow-up coding assignment review created by AI Review Automation.",
        "start": {"dateTime": start.isoformat(), "timeZone": timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": timezone},
        "attendees": [{"email": email} for email in record.get("attendees", [])],
        "conferenceData": {"createRequest": {"requestId": "review-" + start.strftime("%Y%m%d%H%M%S%f"), "conferenceSolutionKey": {"type": "hangoutsMeet"}}}
    }
    service = build("calendar", "v3", credentials=creds)
    return service.events().insert(calendarId="primary", body=event, conferenceDataVersion=1, sendUpdates="all").execute()
