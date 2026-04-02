from flask import Flask, request, render_template_string
import requests
import base64
import json
import os
import logging
import datetime

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

# 🔥 LOG CHANNEL
LOG_CHANNEL_ID = "1488906067327848588"

# 🎨 GRAFIKA + EMOJI
LOGO = "https://media.discordapp.net/attachments/1394316699968213142/1488631068562292867/Copilot_20260326_211453.png"
BANNER = "https://media.discordapp.net/attachments/1394316699968213142/1488630238366793749/Copilot_20260326_221158.png?ex=69cf74b2&is=69ce2332&hm=f92fe6472372b0f6719561d0764916d0b3a7a89227877cb1bce4664dd7d93dfd&=&format=webp&quality=lossless"

EMOJI_LINE = "<:tt:1486853447889326251><:xx:1486855629799948410><:tt:1486853447889326251><:hh:1486856249885851678><:uu:1486856724655640698><:bb:1486857337997230161>"

# ===== LOAD USERS =====
def load_users():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code == 200:
            file_data = r.json()
            return json.loads(base64.b64decode(file_data["content"]))
    except Exception:
        logging.exception("LOAD ERROR")

    return []

# ===== SAVE USER =====
def save_user(user_id, access_token):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}

        r = requests.get(url, headers=headers, timeout=10)
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

        data = {
            "message": "update users",
            "content": new_content,
            "sha": sha
        }

        requests.put(url, headers=headers, json=data, timeout=10)

    except Exception:
        logging.exception("SAVE ERROR")

# ===== LOG =====
def send_log(user):
    try:
        url = f"https://discord.com/api/v10/channels/{LOG_CHANNEL_ID}/messages"

        headers = {
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json"
        }

        avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user.get("avatar") else LOGO

        embed = {
            "title": f"{EMOJI_LINE}\n✅ Nowa weryfikacja",
            "description": f"Użytkownik <@{user['id']}> został zweryfikowany!",
            "color": 5763719,
            "thumbnail": {"url": avatar_url},
            "image": {"url": BANNER},
            "fields": [
                {
                    "name": "👤 Użytkownik",
                    "value": f"{user['username']}",
                    "inline": True
                },
                {
                    "name": "🆔 ID",
                    "value": user['id'],
                    "inline": True
                }
            ],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        requests.post(url, headers=headers, json={"embeds": [embed]}, timeout=10)

    except Exception:
        logging.exception("LOG ERROR")

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

        r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers, timeout=10)

        if r.status_code != 200:
            logging.error(r.text)
            return "OAuth error", 400

        token = r.json().get("access_token")

        if token:
            user_res = requests.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            if user_res.status_code == 200:
                user = user_res.json()
                user_id = user.get("id")

                if user_id:
                    save_user(user_id, token)

                    # 🔥 LOG
                    send_log(user)

                    # ===== ADD ROLE =====
                    requests.put(
                        f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}",
                        headers={"Authorization": f"Bot {BOT_TOKEN}"},
                        timeout=10
                    )

        return render_template_string("""
        <html>
        <body style="background:#5865F2;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
            <div style="text-align:center;">
                <h1>✅ Zweryfikowano!</h1>
                <p>Możesz wrócić na Discord.</p>
            </div>
        </body>
        </html>
        """)

    except Exception:
        logging.exception("CALLBACK ERROR")
        return "Internal error", 500


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
                json={"access_token": u["access_token"]},
                timeout=10
            )

            if r.status_code in [201, 204]:
                added += 1
            else:
                failed.append({
                    "id": u["id"],
                    "status": r.status_code,
                    "text": r.text
                })

        except Exception as e:
            failed.append({
                "id": u["id"],
                "error": str(e)
            })

    return {
        "successfully_added": added,
        "failed": failed
    }

# ===== START =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
