from flask import Flask, request
import requests
import os

app = Flask(__name__)

# 🔐 WSTAW SWOJE DANE
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIRECT_URI = os.getenv("REDIRECT_URI")

users = []


@app.route("/")
def home():
    return "Strona działa"


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
    token_json = r.json()

    access_token = token_json.get("access_token")

    if not access_token:
        return f"Błąd tokena: {token_json}"

    user = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    user_id = user.get("id")

    if not user_id:
        return "Błąd pobierania usera"

    # zapis (bez duplikatów)
    for u in users:
        if u["id"] == user_id:
            u["token"] = access_token
            break
    else:
        users.append({"id": user_id, "token": access_token})

    return "Zweryfikowano poprawnie!"


@app.route("/dodaj/<guild_id>")
def dodaj(guild_id):
    added = 0

    for u in users:
        r = requests.put(
            f"https://discord.com/api/guilds/{guild_id}/members/{u['id']}",
            json={"access_token": u["token"]},
            headers={
                "Authorization": BOT_TOKEN,
                "Content-Type": "application/json"
            }
        )

        if r.status_code in [201, 204]:
            added += 1

    return f"Dodano {added} użytkowników"


# 🔴 NAJWAŻNIEJSZE — PORT DLA RENDER
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
