print("🔥 SERVER STARTED")

from flask import Flask
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# ---------------- FIREBASE ----------------
firebase_config_raw = os.environ.get("FIREBASE_KEY")

print("ENV FIREBASE_KEY:", bool(firebase_config_raw))

if not firebase_config_raw:
    raise Exception("FIREBASE_KEY not found in ENV")

try:
    firebase_config = json.loads(firebase_config_raw)
except Exception as e:
    raise Exception(f"Firebase JSON error: {e}")

cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)

db = firestore.client()


# ---------------- HOME (ADD TEAM) ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("team")

        if name:
            db.collection("teams").document(name).set({
                "points": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0
            })

        return redirect("/")

    return """
    <h1>⚽ Tournament</h1>
    <form method="POST">
        <input name="team" placeholder="Team name">
        <button>Add</button>
    </form>

    <br>
    <a href="/match">Match</a> |
    <a href="/table">Table</a>
    """


# ---------------- MATCH ----------------
@app.route("/match", methods=["GET", "POST"])
def match():
    teams = [doc.id for doc in db.collection("teams").stream()]

    if request.method == "POST":
        t1 = request.form.get("team1")
        t2 = request.form.get("team2")
        s1 = int(request.form.get("score1"))
        s2 = int(request.form.get("score2"))

        if s1 > s2:
            db.collection("teams").document(t1).update({
                "points": firestore.Increment(3),
                "wins": firestore.Increment(1)
            })
            db.collection("teams").document(t2).update({
                "losses": firestore.Increment(1)
            })

        elif s2 > s1:
            db.collection("teams").document(t2).update({
                "points": firestore.Increment(3),
                "wins": firestore.Increment(1)
            })
            db.collection("teams").document(t1).update({
                "losses": firestore.Increment(1)
            })

        else:
            db.collection("teams").document(t1).update({
                "points": firestore.Increment(1),
                "draws": firestore.Increment(1)
            })
            db.collection("teams").document(t2).update({
                "points": firestore.Increment(1),
                "draws": firestore.Increment(1)
            })

        return redirect("/table")

    options = "".join([f"<option value='{t}'>{t}</option>" for t in teams])

    return f"""
    <h1>⚽ Match</h1>

    <form method="POST">
        <select name="team1">{options}</select>
        <select name="team2">{options}</select><br><br>

        <input name="score1" placeholder="Goals 1">
        <input name="score2" placeholder="Goals 2"><br><br>

        <button>Save</button>
    </form>

    <br>
    <a href="/table">Table</a>
    """


# ---------------- TABLE ----------------
@app.route("/table")
def table():
    docs = db.collection("teams").stream()

    teams = [(d.id, d.to_dict()) for d in docs]
    teams.sort(key=lambda x: x[1].get("points", 0), reverse=True)

    rows = ""
    i = 1

    for name, d in teams:
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>{name}</td>
            <td>{d.get('points', 0)}</td>
            <td>{d.get('wins', 0)}</td>
            <td>{d.get('draws', 0)}</td>
            <td>{d.get('losses', 0)}</td>
        </tr>
        """
        i += 1

    return f"""
    <h1>🏆 Tournament Table</h1>

    <table border="1" cellpadding="8">
        <tr>
            <th>#</th>
            <th>Team</th>
            <th>Points</th>
            <th>W</th>
            <th>D</th>
            <th>L</th>
        </tr>
        {rows}
    </table>

    <br>
    <a href="/">Teams</a> |
    <a href="/match">Match</a>
    """


# ---------------- START ----------------
if __name__ == "__main__":
    app.run()