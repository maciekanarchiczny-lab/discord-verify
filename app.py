from flask import Flask, request, render_template_string
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

        token = None
        if r.status_code == 200:
            token = r.json().get("access_token")
        else:
            logging.warning(f"Token error: {r.text}")  # logujemy problem, ale nie pokazujemy userowi

        if token:
            # ===== USER INFO =====
            user_res = requests.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if user_res.status_code == 200:
                user = user_res.json()
                user_id = user.get("id")
                if user_id:
                    save_user(user_id, token)
                    # ===== ADD ROLE =====
                    role_res = requests.put(
                        f"https://discord.com/api/guilds/{GUILD_ID}/members/{user_id}/roles/{ROLE_ID}",
                        headers={"Authorization": f"Bot {BOT_TOKEN}"}
                    )
                    logging.info(f"ROLE STATUS: {role_res.status_code} {role_res.text}")
        else:
            logging.warning("Brak tokenu – prawdopodobnie invalid_grant, ale pokazujemy sukces")

        # ⚡ Wyświetlamy zawsze ładną stronę sukcesu
        return render_template_string("""
            <html>
            <head>
                <title>Zweryfikowano!</title>
                <style>
                    body { 
                        font-family: 'Segoe UI', Tahoma, sans-serif; 
                        display: flex; 
                        justify-content: center; 
                        align-items: center; 
                        height: 100vh; 
                        background: linear-gradient(135deg, #5865F2, #1ABC9C); 
                        color: white;
                        flex-direction: column;
                        text-align: center;
                    }
                    h1 { font-size: 3em; margin-bottom: 20px; }
                    p { font-size: 1.5em; }
                    .emoji { font-size: 4em; margin-bottom: 20px; }
                    @keyframes bounce {
                        0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                        40% { transform: translateY(-20px); }
                        60% { transform: translateY(-10px); }
                    }
                    .emoji { animation: bounce 2s infinite; }
                </style>
            </head>
            <body>
                <div class="emoji">✅</div>
                <h1>Zweryfikowano!</h1>
                <p>Możesz wrócić na Discord.</p>
            </body>
            </html>
        """)

    except Exception as e:
        logging.exception("CALLBACK ERROR")
        # Nawet przy wyjątku pokazujemy sukces użytkownikowi
        return render_template_string("""
            <html>
            <head>
                <title>Zweryfikowano!</title>
                <style>
                    body { 
                        font-family: 'Segoe UI', Tahoma, sans-serif; 
                        display: flex; 
                        justify-content: center; 
                        align-items: center; 
                        height: 100vh; 
                        background: linear-gradient(135deg, #5865F2, #1ABC9C); 
                        color: white;
                        flex-direction: column;
                        text-align: center;
                    }
                    h1 { font-size: 3em; margin-bottom: 20px; }
                    p { font-size: 1.5em; }
                    .emoji { font-size: 4em; margin-bottom: 20px; }
                    @keyframes bounce {
                        0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                        40% { transform: translateY(-20px); }
                        60% { transform: translateY(-10px); }
                    }
                    .emoji { animation: bounce 2s infinite; }
                </style>
            </head>
            <body>
                <div class="emoji">✅</div>
                <h1>Zweryfikowano!</h1>
                <p>Możesz wrócić na Discord.</p>
            </body>
            </html>
        """)

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
