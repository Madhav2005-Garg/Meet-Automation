import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Built-in in Python 3.9+
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def authenticate_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0, prompt='consent')
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return creds

def read_email_content():
    content_file = 'content.txt'
    if os.path.exists(content_file):
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return content
    return 'This meeting is restricted to invited attendees.'

@app.get("/")
async def serve_homepage():
    """Serves index.html when opening http://127.0.0.1:8000"""
    return FileResponse("index.html")

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    start_time: str = Form(...),          # Format: "YYYY-MM-DDTHH:MM"
    duration: int = Form(...),            # Duration in minutes
    timezone: str = Form("Asia/Kolkata")  # Explicit user timezone
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")
    
    try:
        # 1. Parse Excel and extract ALL email addresses
        df = pd.read_excel(file.file)
        
        if "Email Address" not in df.columns:
            raise HTTPException(status_code=400, detail='Column "Email Address" not found in the uploaded file.')
            
        raw_emails = df["Email Address"].dropna().tolist()
        emails = list(set(str(e).strip() for e in raw_emails if str(e).strip()))
        
        if not emails:
            raise HTTPException(status_code=400, detail="No valid email addresses found in the column.")

        # 2. Attach explicit ZoneInfo timezone offset (e.g. +05:30)
        tz_obj = ZoneInfo(timezone)
        naive_dt = datetime.fromisoformat(start_time)
        start_dt = naive_dt.replace(tzinfo=tz_obj)  # Aware datetime with timezone
        end_dt = start_dt + timedelta(minutes=duration)

        meeting_description = read_email_content()
        creds = authenticate_google()
        service = build('calendar', 'v3', credentials=creds)

        # 3. Build single attendees array
        attendees_payload = [{'email': email} for email in emails]

        # Format display time for title (e.g., "08:00 PM IST")
        formatted_time = start_dt.strftime("%I:%M %p")

        event_body = {
            # Including explicit time in summary prevents confusion across all accounts
            'summary': f'Git & GitHub Workshop ({formatted_time} IST) | Daksh Dynamics',
            'description': meeting_description,
            'start': {
                'dateTime': start_dt.isoformat(),  # Sends exact RFC 3339 string: "2026-09-22T20:00:00+05:30"
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': timezone,
            },
            'attendees': attendees_payload,
            'guestsCanInviteOthers': False,
            'guestsCanModify': False,
            'guestsCanSeeOtherGuests': False,
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }

        # 4. SINGLE API EXECUTION
        event_result = service.events().insert(
            calendarId='primary',
            sendUpdates='all',
            conferenceDataVersion=1,
            body=event_body
        ).execute()

        shared_meet_link = event_result.get('hangoutLink')

        return JSONResponse(content={
            "status": "Success",
            "message": "Single meeting created and invites sent successfully!",
            "meet_link": shared_meet_link,
            "start_time": start_dt.strftime("%Y-%m-%d %I:%M %p"),
            "end_time": end_dt.strftime("%Y-%m-%d %I:%M %p"),
            "timezone": timezone,
            "invited_count": len(emails),
            "emails": emails
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating meeting: {str(e)}")

# Serve static files (style.css, script.js)
app.mount("/", StaticFiles(directory="."), name="static")

if __name__ == '__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)