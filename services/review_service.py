
import json
import os
import re
import requests

def _github_files(url):
    match = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", url.strip())
    if not match:
        raise ValueError("Please provide a GitHub repository URL such as https://github.com/owner/repo.")
    owner, repo = match.group(1), match.group(2).removesuffix(".git")
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    api = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    response = requests.get(api, headers=headers, timeout=30)
    if not response.ok:
        raise RuntimeError(f"GitHub API error {response.status_code}. For private repositories set GITHUB_TOKEN in .env.")
    tree = response.json().get("tree", [])
    code_ext = {".py",".js",".ts",".jsx",".tsx",".html",".css",".json",".md",".txt",".java",".cs",".go",".rb",".php",".sql",".yml",".yaml"}
    chosen = [x for x in tree if x.get("type") == "blob" and any(x.get("path","").lower().endswith(e) for e in code_ext) and x.get("size",0) < 150000][:35]
    files = []
    for item in chosen:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{item['path']}"
        r = requests.get(raw_url, headers=headers, timeout=20)
        if r.ok:
            files.append({"name": item["path"], "content": r.text[:20000]})
    if not files:
        raise ValueError("No readable source files were found in this repository.")
    return files

def review_submission(task_name, requirements, source):
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing in .env.")
    files = _github_files(source["url"]) if source.get("type") == "github" else source.get("files", [])
    if not files:
        raise ValueError("No source files provided.")
    # Bound total payload to keep the request manageable.
    code = "\n\n".join(f"FILE: {f.get('name','unnamed')}\n```text\n{f.get('content','')[:20000]}\n```" for f in files)[:90000]
    prompt = f"""You are a careful code reviewer. Review code against explicit requirements, using only evidence visible in the submitted files. Do not invent runtime results. If UI behavior is claimed but no UI code exists, say so.
Task: {task_name}
Requirements:
{json.dumps(requirements, ensure_ascii=False)}
Submission:
{code}

Return ONLY JSON with keys:
summary (string), recommended_status (one of READY_FOR_REVIEW, NEEDS_CHANGES, INCOMPLETE, REVIEW_COMPLETED),
findings (array of objects with requirement, status [PASS/FAIL/PARTIAL/NOT_VERIFIABLE], severity [LOW/MEDIUM/HIGH], evidence, explanation, recommendation),
strengths (array of strings), testing_gaps (array of strings), next_steps (array of strings).
Do not include a score, points, percentage, or numeric grade. Keep feedback constructive and concise."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    response = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}], "generationConfig":{"temperature":0.2, "responseMimeType":"application/json"}}, timeout=90)
    if not response.ok:
        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text[:900]}")
    data = response.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    report = json.loads(raw)
    report.pop("score", None)
    report.pop("points", None)
    report.pop("percentage", None)
    return report
