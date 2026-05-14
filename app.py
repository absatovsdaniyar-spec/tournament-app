from flask import Flask, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
from urllib.parse import unquote
import os
import json

app = Flask(__name__)

# ---------------- FIREBASE (FIXED FOR RENDER) ----------------
firebase_config_raw = os.environ.get("FIREBASE_KEY")

if not firebase_config_raw:
    raise Exception("FIREBASE_KEY not found in ENV")

firebase_config = json.loads(firebase_config_raw)

cred = credentials.Certificate(firebase_config)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- STYLE ----------------
STYLE = """
<style>
body{
    margin:0;
    font-family:Arial;
    background:#0f172a;
    color:white;
}

.container{max-width:1000px;margin:auto;padding:20px;}

.card{
    background:#1e293b;
    padding:20px;
    border-radius:15px;
    margin-bottom:15px;
}

input,select{
    padding:10px;
    margin:5px;
    border-radius:10px;
    border:none;
}

button{
    padding:10px 15px;
    border-radius:10px;
    border:none;
    background:#22c55e;
    color:white;
    cursor:pointer;
}

table{
    width:100%;
    border-collapse:collapse;
}

th,td{
    padding:10px;
    text-align:center;
    border-bottom:1px solid #334155;
}

th{background:#334155;}

a{color:#38bdf8;text-decoration:none;margin-right:10px;}
</style>
"""

# ---------------- HOME ----------------
@app.route("/", methods=["GET","POST"])
def index():

    if request.method == "POST":
        name = request.form.get("team")

        if name:
            ref = db.collection("teams").document(name)

            if not ref.get().exists:
                ref.set({
                    "очки": 0,
                    "победы": 0,
                    "ничьи": 0,
                    "поражения": 0,
                    "голы": 0
                })

        return redirect("/")

    return STYLE + """
    <div class="container">
        <div class="card">
            <h1>⚽ Турнир</h1>

            <form method="POST">
                <input name="team" placeholder="Команда">
                <button>Добавить</button>
            </form>

            <br>
            <a href="/match">Матчи</a>
            <a href="/table">Таблица</a>
            <a href="/matches">История</a>
        </div>
    </div>
    """

# ---------------- DELETE ----------------
@app.route("/delete/<path:name>")
def delete(name):
    name = unquote(name)
    db.collection("teams").document(name).delete()
    return redirect("/table")

# ---------------- MATCH ----------------
@app.route("/match", methods=["GET","POST"])
def match():

    teams = [t.id for t in db.collection("teams").stream()]

    if request.method == "POST":

        t1 = request.form.get("team1")
        t2 = request.form.get("team2")

        if t1 == t2:
            return "❌ Нельзя выбрать одну и ту же команду"

        s1 = int(request.form.get("score1") or 0)
        s2 = int(request.form.get("score2") or 0)

        ref1 = db.collection("teams").document(t1)
        ref2 = db.collection("teams").document(t2)

        d1 = ref1.get()
        d2 = ref2.get()

        if not d1.exists or not d2.exists:
            return "❌ Команда не найдена"

        # SAFE UPDATE FUNCTION
        def inc(ref, field, value):
            data = ref.get().to_dict() or {}
            old = data.get(field, 0)
            ref.update({field: old + value})

        inc(ref1, "голы", s1)
        inc(ref2, "голы", s2)

        if s1 > s2:
            inc(ref1, "очки", 3)
            inc(ref1, "победы", 1)
            inc(ref2, "поражения", 1)

        elif s2 > s1:
            inc(ref2, "очки", 3)
            inc(ref2, "победы", 1)
            inc(ref1, "поражения", 1)

        else:
            inc(ref1, "очки", 1)
            inc(ref2, "очки", 1)
            inc(ref1, "ничьи", 1)
            inc(ref2, "ничьи", 1)

        db.collection("matches").add({
            "t1": t1,
            "t2": t2,
            "s1": s1,
            "s2": s2
        })

        return redirect("/matches")

    options = "".join([f"<option value='{t}'>{t}</option>" for t in teams])

    return STYLE + f"""
    <div class="container">
        <div class="card">
            <h1>⚽ Матч</h1>

            <form method="POST">
                <select name="team1">{options}</select>
                <select name="team2">{options}</select><br>

                <input name="score1" placeholder="Голы 1">
                <input name="score2" placeholder="Голы 2"><br>

                <button>Сохранить</button>
            </form>
        </div>
    </div>
    """

# ---------------- TABLE ----------------
@app.route("/table")
def table():

    docs = db.collection("teams").stream()

    teams = [(d.id, d.to_dict()) for d in docs]
    teams.sort(key=lambda x: x[1].get("очки",0), reverse=True)

    rows = ""
    i = 1

    for name,d in teams:

        wins = d.get("победы",0)
        draws = d.get("ничьи",0)
        losses = d.get("поражения",0)
        goals = d.get("голы",0)
        points = d.get("очки",0)

        games = wins + draws + losses

        rows += f"""
        <tr>
            <td>{i}</td>
            <td>{name}</td>
            <td>{games}</td>
            <td>{wins}</td>
            <td>{draws}</td>
            <td>{losses}</td>
            <td>{goals}</td>
            <td>{points}</td>
            <td><a href="/delete/{name}" style="color:red;">❌ удалить</a></td>
        </tr>
        """
        i += 1

    return STYLE + f"""
    <div class="container">
        <div class="card">
            <h1>🏆 Таблица</h1>

            <table>
                <tr>
                    <th>#</th>
                    <th>Команда</th>
                    <th>Игры</th>
                    <th>Победы</th>
                    <th>Ничьи</th>
                    <th>Поражения</th>
                    <th>Голы</th>
                    <th>Очки</th>
                    <th>Удалить</th>
                </tr>
                {rows}
            </table>
        </div>
    </div>
    """

# ---------------- MATCH HISTORY ----------------
@app.route("/matches")
def matches():

    docs = db.collection("matches").stream()

    html = ""

    for m in docs:
        d = m.to_dict()

        s1 = d.get("s1", 0)
        s2 = d.get("s2", 0)

        if s1 > s2:
            r = "Победа 1 🟢"
        elif s2 > s1:
            r = "Победа 2 🔴"
        else:
            r = "Ничья 🟡"

        html += f"""
        <div class="card">
            <h2>{d.get('t1')} {s1} - {s2} {d.get('t2')}</h2>
            <p>{r}</p>
        </div>
        """

    return STYLE + f"""
    <div class="container">
        <div class="card">
            <h1>📜 История матчей</h1>
            <a href="/">Главная</a>
        </div>
        {html}
    </div>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)