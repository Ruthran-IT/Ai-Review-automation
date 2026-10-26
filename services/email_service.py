
import os
import smtplib
from email.message import EmailMessage

def _send(msg):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_APP_PASSWORD")
    if not user or not password:
        raise ValueError("SMTP_EMAIL and SMTP_APP_PASSWORD must be set in .env.")
    with smtplib.SMTP_SSL(host, port, timeout=30) as server:
        server.login(user, password)
        server.send_message(msg)

def send_assignment_email(recipient, candidate_name, task, deadline):
    if not recipient or "@" not in recipient:
        raise ValueError("A valid candidate email is required.")
    requirements = "\n".join(f"- {x}" for x in task.get("requirements", []))
    deliverables = "\n".join(f"- {x}" for x in task.get("deliverables", []))
    msg = EmailMessage()
    msg["Subject"] = f"Coding assignment: {task.get('title', 'Your task')}"
    msg["From"] = os.getenv("SMTP_EMAIL")
    msg["To"] = recipient
    msg.set_content(f"""Hello {candidate_name or 'Candidate'},

You have been assigned the following coding task.

Task: {task.get('title', 'Coding assignment')}
Role: {task.get('role', 'Not specified')}
Skill level: {task.get('skill_level', 'Not specified')}
Estimated effort: {task.get('estimated_hours', 'Not specified')} hours
Deadline: {deadline}

Description:
{task.get('description', '')}

Requirements:
{requirements}

Deliverables:
{deliverables}

Please reply to the assignment coordinator if you need clarification.

Regards,
AI Review Automation
""")
    _send(msg)

def send_feedback_email(recipient, candidate_name, task_name, report):
    if not recipient or "@" not in recipient:
        raise ValueError("A valid candidate email is required.")
    findings = report.get("findings", [])
    strengths = report.get("strengths", [])
    gaps = report.get("testing_gaps", [])
    next_steps = report.get("next_steps", [])
    body = [
        f"Hello {candidate_name or 'Candidate'},", "",
        f"Your code review for '{task_name}' is complete.", "",
        f"Recommended status: {report.get('recommended_status', 'REVIEW_COMPLETED')}", "",
        "Summary:", report.get("summary", "No summary was provided."), "",
        "Findings:"
    ]
    if findings:
        for f in findings:
            body.extend([
                f"- [{f.get('status','UNKNOWN')}] {f.get('requirement','Requirement')}",
                f"  Severity: {f.get('severity','Not specified')}",
                f"  Evidence: {f.get('evidence','Not provided')}",
                f"  Explanation: {f.get('explanation','')}",
                f"  Recommendation: {f.get('recommendation','')}", ""
            ])
    else:
        body.append("- No individual findings were returned.")
    for title, values in [("Strengths", strengths), ("Testing gaps", gaps), ("Next steps", next_steps)]:
        body.extend(["", f"{title}:"])
        body.extend([f"- {x}" for x in values] if values else ["- None provided."])
    body.extend(["", "Please review the feedback and contact the coordinator if anything is unclear.", "", "Regards,", "AI Review Automation"])
    msg = EmailMessage()
    msg["Subject"] = f"Code review feedback: {task_name}"
    msg["From"] = os.getenv("SMTP_EMAIL")
    msg["To"] = recipient
    msg.set_content("\n".join(body))
    _send(msg)
