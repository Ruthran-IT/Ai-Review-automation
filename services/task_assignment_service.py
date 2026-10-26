
import json
import os
import requests

def _norm(value):
    return str(value or "").strip().lower()

def find_bank_task(candidate, task_bank):
    active = [t for t in task_bank if t.get("active", True)]
    role = _norm(candidate.get("role"))
    level = _norm(candidate.get("skill_level"))
    topic = _norm(candidate.get("task_topic"))
    scored = []
    for task in active:
        score = 0
        if role and _norm(task.get("role")) == role: score += 3
        if level and _norm(task.get("skill_level")) == level: score += 3
        if topic and topic in " ".join([_norm(task.get("topic")), _norm(task.get("title")), _norm(task.get("description"))]): score += 4
        if score:
            scored.append((score, task))
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]

def _generate_task(candidate):
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing in .env. Add it, or turn off task generation and use the task bank.")
    prompt = f"""Create a practical coding assignment suitable for this candidate. Return ONLY valid JSON, no markdown.
Candidate: {json.dumps({k:candidate.get(k,'') for k in ['candidate_name','role','skill_level','task_topic']})}
Return keys: task_id, title, role, skill_level, topic, description, requirements (array of 4-7 testable requirements), deliverables (array), estimated_hours (integer), active (true).
Make requirements specific and verifiable. Do not include scoring or a numeric grade."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    response = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}], "generationConfig":{"temperature":0.3, "responseMimeType":"application/json"}}, timeout=60)
    if not response.ok:
        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text[:700]}")
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    task = json.loads(text)
    task.setdefault("task_id", "AI-GENERATED")
    task.setdefault("role", candidate.get("role", ""))
    task.setdefault("skill_level", candidate.get("skill_level", "Intermediate"))
    task.setdefault("topic", candidate.get("task_topic", ""))
    task.setdefault("requirements", [])
    task.setdefault("deliverables", ["Source code", "README file", "Tests"])
    task.setdefault("estimated_hours", 4)
    task["active"] = True
    return task

def assign_task_for_candidate(candidate, task_bank, allow_generation=True):
    task = find_bank_task(candidate, task_bank)
    if task:
        return dict(task), "task bank"
    if allow_generation:
        return _generate_task(candidate), "Gemini-generated"
    raise ValueError("No suitable task found in task bank. Add a task or enable Gemini generation.")
