import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

users = []

@app.route("/")
def home():
    return "OK"

@app.route("/callback")
def callback():
    code = request.args.get("code")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    r = requests.post("https://discord.com/api/oauth2/token", data=data)
    token = r.json().get("access_token")
    if not token:
        return "❌ Błąd autoryzacji"

    user = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    users.append({"id": user["id"], "token": token})

    return "✅ Zweryfikowano!"

@app.route("/dodaj/<guild_id>")
def dodaj(guild_id):
    count = 0
    for u in users:
        try:
            r = requests.put(
                f"https://discord.com/api/guilds/{guild_id}/members/{u['id']}",
                json={"access_token": u["token"]},
                headers={
                    "Authorization": f"Bot {BOT_TOKEN}",
                    "Content-Type": "application/json"
                }
            )
            if r.status_code in [201, 204]:
                count += 1
        except Exception as e:
            print("Błąd dodawania:", e)
    return f"Dodano {count} użytkowników!"
