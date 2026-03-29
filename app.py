from flask import Flask, request
import requests
import base64
import json
import os

app = Flask(__name__)

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

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        }

        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            file_data = r.json()
            content = json.loads(base64.b64decode(file_data["content"]))
            sha = file_data["sha"]
        else:
            content = []
            sha = None

        # dodaj usera (bez duplikatów)
        if not any(u["id"] == user_id for u in content):
            content.append({
                "id": user_id,
                "access_token": access_token
            })

        new_content = base64.b64encode(json.dumps(content, indent=2).encode()).decode()

        data = {
            "message": "update users",
            "content": new_content,
            "sha": sha
        }

        requests.put(url, headers=headers, json=data)

    except Exception as e:
        print("SAVE ERROR:", e)

# ===== LOAD USERS =====
def load_users():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}"
        }

        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            content = json.loads(base64.b64decode(r.json()["content"]))
            return content
        else:
            return []

    except Exception as e:
        print("LOAD ERROR:", e)
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

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

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

        print("ROLE STATUS:", role_res.status_code, role_res.text)

        return "✅ Zweryfikowano! Możesz wrócić na Discord."

    except Exception as e:
        return f"💥 ERROR: {e}"

# ===== MASS ADD =====
@app.route("/dodaj/<guild_id>")
def dodaj(guild_id):
    users = load_users()
    added = 0

    for u in users:
        try:
            r = requests.put(
                f"https://discord.com/api/guilds/{guild_id}/members/{u['id']}",
                json={"access_token": u["access_token"]},
                headers={"Authorization": f"Bot {BOT_TOKEN}"}
            )

            if r.status_code in [201, 204]:
                added += 1

        except Exception as e:
            print("ADD ERROR:", e)

    return f"✅ Dodano {added} użytkowników"

# ===== START =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
