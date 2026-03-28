from flask import Flask, request
import requests

app = Flask(__name__)

CLIENT_ID = "TU_CLIENT_ID"
CLIENT_SECRET = "TU_CLIENT_SECRET"
REDIRECT_URI = "https://twoja-apka.onrender.com/callback"
BOT_TOKEN = "Bot TU_TOKEN"

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

    user = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    users.append({"id": user["id"], "token": token})

    return "✅ Zweryfikowano!"

@app.route("/dodaj/<guild_id>")
def dodaj(guild_id):
    for u in users:
        requests.put(
            f"https://discord.com/api/guilds/{guild_id}/members/{u['id']}",
            json={"access_token": u["token"]},
            headers={"Authorization": BOT_TOKEN}
        )
    return "Dodano wszystkich!"
