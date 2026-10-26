
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

def ensure_data_files():
    defaults = {
        "candidates.json": [],
        "assignments.json": [],
        "reports.json": [],
        "followups.json": [],
        "task_bank.json": []
    }
    for name, default in defaults.items():
        path = DATA / name
        if not path.exists():
            path.write_text(json.dumps(default, indent=2), encoding="utf-8")
    csv_path = DATA / "candidates.csv"
    if not csv_path.exists():
        csv_path.write_text("candidate_name,email,role,skill_level,task_topic\n", encoding="utf-8")

def load_json(filename, default=None):
    path = DATA / filename
    if not path.exists():
        return default if default is not None else []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default if default is not None else []

def save_json(filename, value):
    (DATA / filename).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")

def load_candidates():
    items = load_json("candidates.json", [])
    if items:
        return items
    try:
        df = pd.read_csv(DATA / "candidates.csv").fillna("")
        if "candidate_name" in df.columns and "email" in df.columns:
            return df.to_dict("records")
    except Exception:
        pass
    return []

def save_candidates(records):
    clean = []
    for row in records:
        clean.append({k: ("" if pd.isna(v) else str(v).strip()) for k, v in row.items()})
    save_json("candidates.json", clean)
    pd.DataFrame(clean, columns=["candidate_name", "email", "role", "skill_level", "task_topic"]).to_csv(DATA / "candidates.csv", index=False)

def save_report(report):
    reports = load_json("reports.json", [])
    reports.append(report)
    save_json("reports.json", reports)

def load_reports():
    return load_json("reports.json", [])

def save_assignment(record):
    assignments = load_json("assignments.json", [])
    assignments.append(record)
    save_json("assignments.json", assignments)
