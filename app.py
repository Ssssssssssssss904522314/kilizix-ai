import os, secrets
from flask import Flask, render_template, session, redirect, request, jsonify
import requests

app = Flask(__name__)
app.secret_key = os.getenv("KILIZIX_SECRET_KEY", secrets.token_hex(32))

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "")
github_tokens = {}

def github_token():
    sid = session.get("github_session")
    return github_tokens.get(sid) if sid else None

def gh(method, path, **kwargs):
    token = github_token()
    if not token:
        return None, 401
    headers = kwargs.pop("headers", {})
    headers.update({
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2026-03-10",
    })
    r = requests.request(method, "https://api.github.com" + path, headers=headers, timeout=20, **kwargs)
    try:
        data = r.json()
    except Exception:
        data = {"message": r.text}
    return data, r.status_code

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/github/login")
def github_login():
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return jsonify({"error": "GitHub OAuth ещё не настроен в Render."}), 503
    state = secrets.token_urlsafe(32)
    session["github_oauth_state"] = state
    scope = "repo"
    return redirect(
        "https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&redirect_uri={requests.utils.quote(GITHUB_REDIRECT_URI, safe='')}"
        f"&scope={scope}&state={state}"
    )

@app.get("/api/github/callback")
def github_callback():
    if request.args.get("state") != session.pop("github_oauth_state", None):
        return "Недействительный OAuth state.", 400
    code = request.args.get("code")
    if not code:
        return "GitHub не вернул код авторизации.", 400
    r = requests.post(
        "https://github.com/login/oauth/access_token",
        data={"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET, "code": code},
        headers={"Accept": "application/json"},
        timeout=20,
    )
    data = r.json()
    token = data.get("access_token")
    if not token:
        return f"GitHub OAuth error: {data.get('error_description') or data.get('error') or 'unknown'}", 400
    sid = session.get("github_session") or secrets.token_urlsafe(32)
    session["github_session"] = sid
    github_tokens[sid] = token
    return redirect("/?github=connected")

@app.get("/api/github/status")
def github_status():
    data, code = gh("GET", "/user")
    if code != 200:
        return jsonify({"connected": False})
    return jsonify({"connected": True, "login": data.get("login"), "name": data.get("name") or data.get("login"), "avatar": data.get("avatar_url")})

@app.post("/api/github/logout")
def github_logout():
    sid = session.pop("github_session", None)
    if sid:
        github_tokens.pop(sid, None)
    return jsonify({"ok": True})

@app.get("/api/github/repos")
def github_repos():
    data, code = gh("GET", "/user/repos?sort=updated&per_page=50")
    if code != 200:
        return jsonify({"error": data.get("message", "GitHub error")}), code
    return jsonify({"repos": [{"name": x["name"], "full_name": x["full_name"], "private": x["private"], "default_branch": x["default_branch"], "url": x["html_url"]} for x in data]})

@app.get("/api/github/file")
def github_file():
    owner = request.args.get("owner")
    repo = request.args.get("repo")
    path = request.args.get("path", "")
    if not owner or not repo:
        return jsonify({"error": "owner и repo обязательны"}), 400
    data, code = gh("GET", f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}")
    if code != 200:
        return jsonify({"error": data.get("message", "GitHub error")}), code
    if data.get("type") != "file":
        return jsonify({"error": "Это не файл"}), 400
    import base64
    content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return jsonify({"path": data["path"], "content": content, "sha": data["sha"]})

@app.put("/api/github/file")
def github_write_file():
    body = request.get_json(silent=True) or {}
    owner, repo, path = body.get("owner"), body.get("repo"), body.get("path")
    content, sha, message = body.get("content"), body.get("sha"), body.get("message", "Update from Kilizix AI")
    if not owner or not repo or not path or content is None:
        return jsonify({"error": "owner, repo, path и content обязательны"}), 400
    import base64
    payload = {"message": message, "content": base64.b64encode(content.encode("utf-8")).decode("ascii")}
    if sha:
        payload["sha"] = sha
    data, code = gh("PUT", f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}", json=payload)
    if code not in (200, 201):
        return jsonify({"error": data.get("message", "GitHub error")}), code
    return jsonify({"ok": True, "commit": data.get("commit", {}).get("sha"), "content_sha": data.get("content", {}).get("sha")})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
