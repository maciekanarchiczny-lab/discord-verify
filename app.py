from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# -------------------- POBIERANIE ZMIENNYCH ŚRODOWISKOWYCH --------------------
# Te zmienne ustawiasz w Render (Environment Variables)
CLIENT_ID = os.environ.get("CLIENT_ID")          # Twój Discord Client ID
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")  # Twój Discord Client Secret
BOT_TOKEN = os.environ.get("BOT_TOKEN")          # Token Twojego bota Discord
REDIRECT_URI = os.environ.get("REDIRECT_URI")    # np. https://twoja-apka.onrender.com/callback

USERS_FILE = "users.json"

# -------------------- FUNKCJE --------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_user_to_file(user_id, token):
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["token"] = token
            break
    else:
        users.append({"id": user_id, "token": token})
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)

# -------------------- STRONY --------------------
@app.route("/")
def home():
    return "Bot weryfikacja działa!"

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Brak code!"

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
        return f"Błąd tokena: {r.text}"

    user = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    save_user_to_file(user["id"], token)
    return f"Zweryfikowano użytkownika {user['id']}!"

@app.route("/dodaj/<guild_id>")
def dodaj(guild_id):
    users = load_users()
    if not users:
        return "Brak użytkowników do dodania!"

    results = []
    for u in users:
        r = requests.put(
            f"https://discord.com/api/guilds/{guild_id}/members/{u['id']}",
            json={"access_token": u["token"]},
            headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
        )
        results.append(f"{u['id']}: {r.status_code}")

    return "<br>".join(results)

# -------------------- START --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
