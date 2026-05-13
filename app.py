print("🔥 SERVER STARTED")
print("ENV FIREBASE_KEY:", bool(os.environ.get("FIREBASE_KEY")))
from flask import Flask
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

ffirebase_config_raw = os.environ.get("FIREBASE_KEY")

if not firebase_config_raw:
    raise Exception("FIREBASE_KEY not found in ENV")

firebase_config = json.loads(firebase_config_raw)

cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)

db = firestore.client()


# ---------------- HOME ----------------
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
    <h1>⚽ Турнир (Cloud Mode)</h1>

    <form method="POST">
        <input name="team" placeholder="Команда">
        <button>Добавить</button>
    </form>

    <a href="/match">Матчи</a> |
    <a href="/table">Таблица</a>
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
                "points": Increment(3),
                "wins": Increment(1)
            })
            db.collection("teams").document(t2).update({
                "losses": Increment(1)
            })

        elif s2 > s1:
            db.collection("teams").document(t2).update({
                "points": Increment(3),
                "wins": Increment(1)
            })
            db.collection("teams").document(t1).update({
                "losses": Increment(1)
            })

        else:
            db.collection("teams").document(t1).update({
                "points": Increment(1),
                "draws": Increment(1)
            })
            db.collection("teams").document(t2).update({
                "points": Increment(1),
                "draws": Increment(1)
            })

        return redirect("/table")

    options = "".join([f"<option>{t}</option>" for t in teams])

    return f"""
    <h1>⚽ Матч</h1>

    <form method="POST">
        <select name="team1">{options}</select>
        <select name="team2">{options}</select><br><br>

        <input name="score1" placeholder="Голы 1">
        <input name="score2" placeholder="Голы 2"><br><br>

        <button>Сохранить</button>
    </form>

    <a href="/table">Таблица</a>
    """


# ---------------- TABLE ----------------
@app.route("/table")
def table():
    docs = db.collection("teams").stream()

    teams = []
    for d in docs:
        teams.append((d.id, d.to_dict()))

    teams.sort(key=lambda x: x[1]["points"], reverse=True)

    rows = ""
    place = 1

    for name, d in teams:
        rows += f"""
        <tr>
            <td>{place}</td>
            <td>{name}</td>
            <td>{d['points']}</td>
            <td>{d['wins']}</td>
            <td>{d['draws']}</td>
            <td>{d['losses']}</td>
        </tr>
        """
        place += 1

    return f"""
    <h1>🏆 Таблица (Cloud)</h1>

    <table border="1" cellpadding="8">
        <tr>
            <th>#</th>
            <th>Команда</th>
            <th>Очки</th>
            <th>В</th>
            <th>Н</th>
            <th>П</th>
        </tr>
        {rows}
    </table>

    <br>
    <a href="/">Команды</a> |
    <a href="/match">Матчи</a>
    """


# ---------------- START ----------------
if __name__ == "__main__":
    app.run()