
# AI Review Automation — Complete Starter

A local Streamlit app for:
- Importing candidates from CSV/Excel
- Selecting tasks from a task bank, with optional Gemini-generated tasks when no suitable task exists
- Previewing and confirming task assignments before sending email
- Emailing coding assignments and deadlines using Gmail SMTP
- Reviewing uploaded code or public/private GitHub repositories with Gemini
- Saving readable, score-free review reports and emailing feedback
- Scheduling local follow-up records and optionally creating Google Calendar events with Google Meet links

## Requirements
- Windows 10/11
- Python 3.11 or newer
- Gemini API key
- Gmail account with 2-Step Verification and an App Password for email
- Optional Google Cloud project/OAuth credentials for Calendar and Meet
- Optional GitHub token for private repositories

## Quick start (Windows)
1. Extract this ZIP to a folder such as `C:\Users\YourName\OneDrive\Desktop\ai_review_automation`.
2. Double-click `setup_windows.bat`.
3. Open `.env` in Notepad and enter credentials. Keep this file private.
4. Double-click `run_windows.bat`.
5. Streamlit opens in your browser, usually at `http://localhost:8501`.

If the batch files do not work, open Command Prompt in the project folder and run:
```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python -m streamlit run app.py
```

## Gemini setup
1. Create a Gemini API key in Google AI Studio.
2. Put it in `.env` as `GEMINI_API_KEY=...`.
3. Set `GEMINI_MODEL` to a model available to your API key. The default is `gemini-2.5-flash`; if your account reports that model unavailable, change it to a model explicitly listed by your API.

Never paste the API key into chat, source code, candidate files, or screenshots.

## Gmail email setup
1. Enable 2-Step Verification on the Gmail account.
2. Create an App Password in your Google Account security settings.
3. Set `SMTP_EMAIL` and `SMTP_APP_PASSWORD` in `.env`.
4. In the app, first preview assignments. The email checkbox is off by default; enable it only when ready.
5. Send a test to yourself before sending to real candidates.

Do not use your regular Gmail password. Some managed/work accounts do not allow App Passwords.

## Candidate import
Required columns:
- `candidate_name`
- `email`

Optional:
- `role`
- `skill_level` (Beginner, Intermediate, Advanced)
- `task_topic`

Use the Candidates page to download a CSV template. Replace the example address with a real candidate email before sending anything.

## Assignment behavior
The app searches `data/task_bank.json` for the best matching role, level, and topic. If no match is found and the option is enabled, Gemini generates a new task. Always review the preview before confirming assignments. Generated tasks are suggestions and should be reviewed by a human before sending.

Assignment records are saved in `data/assignments.json`.

## AI code review
Select an assignment or enter task information manually. Add explicit, testable requirements. Upload code files or enter a GitHub repository URL. For private repositories, add a GitHub token to `.env` as `GITHUB_TOKEN`.

Review reports intentionally have no score. They are saved in `data/reports.json`. AI may miss defects or infer incorrectly; verify findings by running the code and tests.

## Google Calendar + Google Meet (optional)
1. Open Google Cloud Console and create/select a project.
2. Enable the Google Calendar API.
3. Configure the OAuth consent screen for your testing audience.
4. Create an OAuth Client ID of type **Desktop app**.
5. Download the JSON and save it in the project root as `credentials.json`.
6. In the app, open Follow-up Reviews and check the Google Calendar/Meet option.
7. On first use, a browser opens for consent. A `token.json` is created locally.

Keep `credentials.json` and `token.json` private. Google may require adding your account as a test user depending on the OAuth app's publishing status. Calendar event creation sends invitations to listed attendees.

## Data and privacy
- Candidate records and reports are stored locally as JSON/CSV under `data/`.
- Uploaded code is sent to Gemini for analysis when you click Review submission. Do not upload confidential or proprietary source code unless authorized.
- Email sending and Calendar event creation are external actions. Confirm recipients and details first.
- This is a prototype, not a secure multi-user HR system. Do not make employment decisions based solely on AI reports.
- `.env`, Google credentials and tokens are excluded from version control.

## Troubleshooting
- `GEMINI_API_KEY is missing`: edit `.env` in the project root and restart the app.
- Gemini model unavailable: set `GEMINI_MODEL` to a model available for your API key.
- Email login fails: verify SMTP email and Gmail App Password; remove spaces if copied incorrectly.
- Excel import fails: check that the workbook is a valid `.xlsx` or `.xls` file.
- GitHub 404: verify the repository URL; private repos require a token.
- Calendar auth fails: verify `credentials.json` is a Desktop app OAuth client and Calendar API is enabled.
- App won't start: run `python -m pip install -r requirements.txt` inside the activated `.venv`.

## Project structure
```
ai_review_automation/
├── app.py
├── services/
│   ├── storage_service.py
│   ├── task_assignment_service.py
│   ├── review_service.py
│   ├── email_service.py
│   └── calendar_service.py
├── data/
│   ├── candidates.csv
│   ├── task_bank.json
│   ├── assignments.json
│   ├── reports.json
│   └── followups.json
├── .env.example
├── requirements.txt
├── setup_windows.bat
└── run_windows.bat
```
