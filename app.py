
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from services.storage_service import (
    ensure_data_files, load_json, save_json, load_candidates, save_candidates,
    save_report, load_reports, save_assignment
)
from services.task_assignment_service import assign_task_for_candidate
from services.email_service import send_assignment_email, send_feedback_email
from services.review_service import review_submission
from services.calendar_service import create_followup_event, calendar_setup_status

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")
ensure_data_files()

st.set_page_config(page_title="AI Review Automation", page_icon="🧪", layout="wide")
st.title("🧪 AI Review Automation")
st.caption("Candidate intake • AI task assignment • Code review • Email feedback • Follow-up scheduling")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Open", [
        "Dashboard", "Candidates", "Automatic Task Assignment",
        "Review Submission", "Review Reports", "Follow-up Reviews", "Settings & Help"
    ])
    st.divider()
    st.caption("Keep API keys and app passwords in `.env`; never upload that file.")

candidates = load_candidates()
reports = load_reports()
assignments = load_json("assignments.json", [])
followups = load_json("followups.json", [])

if page == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Candidates", len(candidates))
    c2.metric("Assignments", len(assignments))
    c3.metric("Review reports", len(reports))
    c4.metric("Follow-ups", len(followups))
    st.subheader("Recent activity")
    activity = []
    for a in assignments[-5:]:
        activity.append({"Type": "Task assignment", "Candidate": a.get("candidate_name"), "Item": a.get("task_title"), "Date": a.get("created_at", "")})
    for r in reports[-5:]:
        activity.append({"Type": "Code review", "Candidate": r.get("candidate_name"), "Item": r.get("task_name"), "Date": r.get("created_at", "")})
    if activity:
        st.dataframe(pd.DataFrame(activity).sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Start by importing candidates, then assign a task.")

elif page == "Candidates":
    st.subheader("Candidate directory")
    st.write("Required columns: `candidate_name`, `email`. Optional: `role`, `skill_level`, `task_topic`.")
    template = pd.DataFrame([{
        "candidate_name": "Demo Candidate", "email": "candidate@example.com",
        "role": "Python Developer", "skill_level": "Beginner", "task_topic": "Login Page Development"
    }])
    st.download_button("Download CSV template", template.to_csv(index=False), "candidates_template.csv", "text/csv")
    uploaded = st.file_uploader("Import candidates (CSV or Excel)", type=["csv", "xlsx", "xls"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            df.columns = [str(c).strip().lower() for c in df.columns]
            aliases = {"name": "candidate_name", "candidate": "candidate_name", "candidate email": "email", "skill": "skill_level", "topic": "task_topic"}
            df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
            if not {"candidate_name", "email"}.issubset(df.columns):
                st.error("The file must include candidate_name and email columns.")
            else:
                for col in ["role", "skill_level", "task_topic"]:
                    if col not in df.columns:
                        df[col] = ""
                df = df[["candidate_name", "email", "role", "skill_level", "task_topic"]].fillna("")
                st.dataframe(df, use_container_width=True, hide_index=True)
                if st.button("Save imported candidates"):
                    save_candidates(df.to_dict("records"))
                    st.success(f"Saved {len(df)} candidates.")
                    st.rerun()
        except Exception as e:
            st.error(f"Could not read file: {e}")
    if candidates:
        st.dataframe(pd.DataFrame(candidates), use_container_width=True, hide_index=True)
        if st.button("Clear candidate directory", type="secondary"):
            save_candidates([])
            st.rerun()
    else:
        st.info("No candidates yet. Import a CSV or Excel file above.")

elif page == "Automatic Task Assignment":
    st.subheader("Assign tasks with AI")
    st.write("The app first looks for a suitable task in the task bank. If none fits, Gemini can generate a new task. Review the preview before sending.")
    if not candidates:
        st.warning("Import candidates first on the Candidates page.")
    else:
        options = [f"{i}: {c.get('candidate_name','')} — {c.get('email','')}" for i, c in enumerate(candidates)]
        chosen = st.multiselect("Choose candidates", options)
        due_date = st.date_input("Assignment deadline", value=date.today() + timedelta(days=7))
        due_time = st.time_input("Deadline time", value=time(17, 0))
        use_ai = st.checkbox("Allow Gemini to generate a task if the bank has no suitable match", value=True)
        send_emails = st.checkbox("Send assignment emails after preview", value=False)
        if st.button("Generate task previews", type="primary", disabled=not chosen):
            preview = []
            bank = load_json("task_bank.json", [])
            for item in chosen:
                idx = int(item.split(":", 1)[0])
                candidate = candidates[idx]
                try:
                    task, origin = assign_task_for_candidate(candidate, bank, allow_generation=use_ai)
                    preview.append({
                        "candidate": candidate, "task": task, "origin": origin,
                        "deadline": datetime.combine(due_date, due_time).isoformat(timespec="minutes")
                    })
                except Exception as e:
                    st.error(f"{candidate.get('candidate_name')}: task generation failed: {e}")
            st.session_state["assignment_preview"] = preview
            st.session_state["assignment_send_emails"] = send_emails
        preview = st.session_state.get("assignment_preview", [])
        if preview:
            st.markdown("### Preview")
            for i, item in enumerate(preview):
                task = item["task"]
                with st.expander(f"{item['candidate'].get('candidate_name')} — {task.get('title', 'Task')} ({item['origin']})", expanded=True):
                    st.write(task.get("description", ""))
                    st.write("**Role / level:**", task.get("role", ""), "/", task.get("skill_level", ""))
                    st.write("**Requirements**")
                    for req in task.get("requirements", []):
                        st.write(f"- {req}")
                    st.write("**Deliverables:**", ", ".join(task.get("deliverables", [])))
                    st.write("**Deadline:**", item["deadline"])
            if st.button("Confirm assignments" + (" and send emails" if st.session_state.get("assignment_send_emails") else ""), type="primary"):
                sent, failed = 0, []
                for item in preview:
                    record = {
                        "assignment_id": f"ASG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                        "candidate_name": item["candidate"].get("candidate_name", ""),
                        "candidate_email": item["candidate"].get("email", ""),
                        "task_title": item["task"].get("title", ""),
                        "task": item["task"],
                        "task_source": item["origin"],
                        "deadline": item["deadline"],
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "email_status": "not requested"
                    }
                    if st.session_state.get("assignment_send_emails"):
                        try:
                            send_assignment_email(record["candidate_email"], record["candidate_name"], item["task"], record["deadline"])
                            record["email_status"] = "sent"
                            sent += 1
                        except Exception as e:
                            record["email_status"] = f"failed: {e}"
                            failed.append(record["candidate_email"])
                    save_assignment(record)
                st.session_state.pop("assignment_preview", None)
                st.success(f"Saved {len(preview)} assignments. Emails sent: {sent}.")
                if failed:
                    st.warning("Email failed for: " + ", ".join(failed))
                st.rerun()
            if st.button("Discard preview"):
                st.session_state.pop("assignment_preview", None)
                st.rerun()
    st.divider()
    st.markdown("#### Task bank")
    bank = load_json("task_bank.json", [])
    if bank:
        st.dataframe(pd.DataFrame([{"task_id": x.get("task_id"), "title": x.get("title"), "role": x.get("role"), "skill_level": x.get("skill_level"), "topic": x.get("topic")} for x in bank]), use_container_width=True, hide_index=True)
    with st.expander("Add a task to the bank"):
        with st.form("add_task"):
            title = st.text_input("Task title")
            role = st.text_input("Role", value="Python Developer")
            level = st.selectbox("Skill level", ["Beginner", "Intermediate", "Advanced"])
            topic = st.text_input("Topic")
            description = st.text_area("Description")
            reqs = st.text_area("Requirements (one per line)")
            deliverables = st.text_area("Deliverables (one per line)", value="Source code\nREADME file\nTests")
            hours = st.number_input("Estimated hours", min_value=1, max_value=100, value=4)
            add = st.form_submit_button("Add task")
        if add:
            if not title.strip():
                st.error("Task title is required.")
            else:
                bank.append({"task_id": f"CUSTOM{len(bank)+1:03}", "title": title.strip(), "role": role, "skill_level": level, "topic": topic, "description": description, "requirements": [x.strip() for x in reqs.splitlines() if x.strip()], "deliverables": [x.strip() for x in deliverables.splitlines() if x.strip()], "estimated_hours": int(hours), "active": True})
                save_json("task_bank.json", bank)
                st.success("Task added.")
                st.rerun()

elif page == "Review Submission":
    st.subheader("AI code review")
    assignment_labels = ["Manual / unassigned submission"] + [f"{i}: {a.get('candidate_name')} — {a.get('task_title')}" for i, a in enumerate(assignments)]
    selected = st.selectbox("Link to assignment (optional)", assignment_labels)
    linked = None
    if selected != assignment_labels[0]:
        linked = assignments[int(selected.split(":", 1)[0])]
    name = st.text_input("Candidate name", value=linked.get("candidate_name", "") if linked else "")
    email = st.text_input("Candidate email", value=linked.get("candidate_email", "") if linked else "")
    task_name = st.text_input("Task name", value=linked.get("task_title", "") if linked else "")
    task = linked.get("task", {}) if linked else {}
    req_text = "\n".join(task.get("requirements", [])) if task else ""
    requirements = st.text_area("Task requirements (one per line)", value=req_text, height=130)
    source_mode = st.radio("Submission source", ["Upload files", "GitHub repository"], horizontal=True)
    source = None
    if source_mode == "Upload files":
        uploads = st.file_uploader("Upload code / documents", accept_multiple_files=True, type=["py", "js", "ts", "jsx", "tsx", "html", "css", "json", "md", "txt", "java", "cs", "go", "rb", "php", "sql", "yml", "yaml"])
        if uploads:
            source = {"type": "files", "files": [{"name": f.name, "content": f.getvalue().decode("utf-8", errors="replace")[:40000]} for f in uploads]}
    else:
        repo = st.text_input("GitHub repository URL", placeholder="https://github.com/owner/repository")
        if repo.strip():
            source = {"type": "github", "url": repo.strip()}
    send_email = st.checkbox("Email the review report to the candidate", value=False)
    if st.button("Review submission", type="primary", disabled=not (task_name.strip() and requirements.strip() and source)):
        with st.spinner("Reviewing submission…"):
            try:
                report = review_submission(task_name, [x.strip() for x in requirements.splitlines() if x.strip()], source)
                report.update({"candidate_name": name.strip(), "candidate_email": email.strip(), "task_name": task_name.strip(), "created_at": datetime.now().isoformat(timespec="seconds"), "submission_source": source.get("url", "uploaded files") if source else ""})
                save_report(report)
                st.session_state["last_review"] = report
                if send_email:
                    if not email.strip():
                        st.warning("Report saved, but no candidate email was provided.")
                    else:
                        send_feedback_email(email.strip(), name.strip() or "Candidate", task_name.strip(), report)
                        st.success("Review report emailed.")
            except Exception as e:
                st.error(f"Review failed: {e}")
    report = st.session_state.get("last_review")
    if report:
        st.markdown("### Latest review")
        st.json(report)

elif page == "Review Reports":
    st.subheader("Saved review reports")
    if not reports:
        st.info("No reports saved yet.")
    for i, report in enumerate(reversed(reports)):
        with st.expander(f"{report.get('candidate_name') or 'Candidate'} — {report.get('task_name', 'Task')} — {report.get('created_at', '')}"):
            st.write("**Recommended status:**", report.get("recommended_status", "REVIEW_COMPLETED"))
            st.write(report.get("summary", ""))
            st.markdown("**Findings**")
            for f in report.get("findings", []):
                st.write(f"- **{f.get('status','')} · {f.get('severity','')} · {f.get('requirement','')}**")
                st.write(f"  Evidence: {f.get('evidence','Not provided')}")
                st.write(f"  Explanation: {f.get('explanation','')}")
                st.write(f"  Recommendation: {f.get('recommendation','')}")
            for label in ["strengths", "testing_gaps", "next_steps"]:
                st.markdown(f"**{label.replace('_',' ').title()}**")
                for x in report.get(label, []):
                    st.write(f"- {x}")
            st.download_button("Download report JSON", json.dumps(report, indent=2), f"review_report_{i+1}.json", "application/json", key=f"report_{i}")

elif page == "Follow-up Reviews":
    st.subheader("Schedule follow-up reviews")
    st.write("Creates a local follow-up record. Google Calendar/Meet event creation is optional and requires Google OAuth credentials.")
    if not assignments:
        st.info("Create a task assignment first.")
    else:
        labels = [f"{i}: {a.get('candidate_name')} — {a.get('task_title')}" for i, a in enumerate(assignments)]
        selected = st.selectbox("Assignment", labels)
        a = assignments[int(selected.split(":", 1)[0])]
        meeting_date = st.date_input("Meeting date", value=date.today() + timedelta(days=8))
        meeting_time = st.time_input("Meeting time", value=time(10, 0))
        duration = st.number_input("Duration (minutes)", min_value=15, max_value=180, value=30, step=15)
        attendees = st.text_input("Additional attendee emails (comma-separated)", value=a.get("candidate_email", ""))
        create_google = st.checkbox("Also create Google Calendar event and Google Meet link", value=False)
        if create_google:
            st.caption("Google setup status: " + calendar_setup_status())
        if st.button("Schedule follow-up", type="primary"):
            start = datetime.combine(meeting_date, meeting_time)
            record = {"candidate_name": a.get("candidate_name"), "candidate_email": a.get("candidate_email"), "task_title": a.get("task_title"), "start": start.isoformat(), "duration_minutes": int(duration), "attendees": [x.strip() for x in attendees.split(",") if x.strip()], "created_at": datetime.now().isoformat(timespec="seconds"), "calendar_status": "local only"}
            if create_google:
                try:
                    event = create_followup_event(record)
                    record["calendar_status"] = "created"
                    record["calendar_event_link"] = event.get("htmlLink", "")
                    record["meet_link"] = event.get("hangoutLink", event.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri", ""))
                except Exception as e:
                    record["calendar_status"] = f"failed: {e}"
            followups.append(record)
            save_json("followups.json", followups)
            st.success("Follow-up saved.")
            if record.get("calendar_event_link"):
                st.markdown(f"[Open calendar event]({record['calendar_event_link']})")
            if record.get("meet_link"):
                st.markdown(f"[Join Google Meet]({record['meet_link']})")
    if followups:
        st.markdown("### Scheduled follow-ups")
        st.dataframe(pd.DataFrame(followups), use_container_width=True, hide_index=True)

else:
    st.subheader("Settings & setup")
    st.markdown("""
1. Copy `.env.example` to `.env`.
2. Add your Gemini API key and Gmail SMTP app password to `.env`.
3. Install dependencies using `setup_windows.bat` or the commands in `README.md`.
4. Start the app using `run_windows.bat`.
5. Import candidate details and use the task assignment preview before sending email.

**Important:** This is a local prototype. Review AI findings before using them for hiring or employment decisions. Do not put secrets in candidate files or commit `.env` to Git.
""")
    st.markdown("### Configuration checks")
    import os
    checks = {
        "Gemini API key": bool(os.getenv("GEMINI_API_KEY")),
        "SMTP email": bool(os.getenv("SMTP_EMAIL")),
        "SMTP app password": bool(os.getenv("SMTP_APP_PASSWORD")),
        "Google Calendar OAuth client file": (ROOT / "credentials.json").exists(),
        "Google Calendar token": (ROOT / "token.json").exists()
    }
    st.table(pd.DataFrame([{"Setting": k, "Configured": "Yes" if v else "No"} for k, v in checks.items()]))
    st.markdown("### Security")
    st.warning("Never share your `.env`, Gemini key, Gmail app password, Google OAuth token, or candidate personal data publicly.")
