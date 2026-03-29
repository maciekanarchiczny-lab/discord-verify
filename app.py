from flask import Flask, request
import requests
import base64
import json
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ===== ENV =====
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REDIRECT_URI = os.environ["REDIRECT_URI"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

GUILD_ID = os.environ["GUILD_ID"]
ROLE_ID = os.environ["ROLE_ID"]

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPO"]
GITHUB_FILE = os.environ["GITHUB_FILE"]

# ===== SAVE USER TO GITHUB =====
def save_user(user_id, access_token):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            file_data = r.json()
            content = json.loads(base64.b64decode(file_data["content"]))
            sha = file_data["sha"]
        else:
            content = []
            sha = None

        if not any(u["id"] == user_id for u in content):
            content.append({"id": user_id, "access_token": access_token})

        new_content = base64.b64encode(json.dumps(content, indent=2).encode()).decode()
        data = {"message": "update users", "content": new_content, "sha": sha}
        put_res = requests.put(url, headers=headers, json=data)
        logging.info(f"GitHub PUT status: {put_res.status_code}")
    except Exception as e:
        logging.exception("SAVE ERROR")

# ===== LOAD USERS =====
def load_users():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]))
        return []
    except Exception as e:
        logging.exception("LOAD ERROR")
        return []

# ===== ROUTES =====
@app.route("/")
def home():
    return "✅ Bot działa"

# ===== CALLBACK =====
@app.route("/callback")
def callback():
    try:
        code = request.args.get("code")
        if not code:
            return "❌ Brak kodu OAuth", 400

        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
        if r.status_code != 200:
            return f"❌ Token error: {r.text}"

        token = r.json().get("access_token")
        if not token:
            return "❌ Brak access_token"

        # ===== USER INFO =====
        user_res = requests.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if user_res.status_code != 200:
            return f"❌ User error: {user_res.text}"

        user = user_res.json()
        user_id = user.get("id")
        if not user_id:
            return "❌ Nie znaleziono user_id"

        # ===== SAVE =====
        save_user(user_id, token)

        # ===== ADD ROLE =====
        role_res = requests.put(
            f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}",
            headers={"Authorization": f"Bot {BOT_TOKEN}"}
        )
        logging.info(f"ROLE STATUS: {role_res.status_code} {role_res.text}")

        return "✅ Zweryfikowano! Możesz wrócić na Discord."

    except Exception as e:
        logging.exception("CALLBACK ERROR")
        return f"💥 ERROR: {e}"

# ===== MASS ADD =====
@app.route("/dodaj/<guild_id>")
def dodaj(guild_id):
    users = load_users()
    added = 0
    failed = []

    for u in users:
        try:
            r = requests.put(
                f"https://discord.com/api/v10/guilds/{guild_id}/members/{u['id']}",
                headers={"Authorization": f"Bot {BOT_TOKEN}"},
                json={"access_token": u["access_token"]}
            )
            if r.status_code in [201, 204]:
                added += 1
            else:
                failed.append({"id": u["id"], "status": r.status_code, "text": r.text})
        except Exception as e:
            failed.append({"id": u["id"], "error": str(e)})

    return {
        "successfully_added": added,
        "failed": failed
    }

# ===== START =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
