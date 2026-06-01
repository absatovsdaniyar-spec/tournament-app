from flask import Flask, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
from urllib.parse import unquote
from datetime import datetime
import os
import json

app = Flask(__name__)

# ---------------- FIREBASE ----------------

firebase_config = json.loads(os.environ["FIREBASE_KEY"])

cred = credentials.Certificate(firebase_config)

firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- STYLE ----------------

STYLE = """
<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    font-family:Arial,sans-serif;

    background:
    radial-gradient(circle at top left,#1e3a8a 0%,transparent 30%),
    radial-gradient(circle at bottom right,#7c3aed 0%,transparent 30%),
    #0f172a;

    color:white;
    min-height:100vh;
}

.container{
    max-width:1100px;
    margin:auto;
    padding:30px;
}

.topbar{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:25px;
    flex-wrap:wrap;
    gap:15px;
}

.logo{
    font-size:32px;
    font-weight:bold;
    color:#38bdf8;
}

.menu{
    display:flex;
    gap:15px;
    flex-wrap:wrap;
}

.menu a{
    color:white;
    text-decoration:none;
    transition:.2s;
    font-weight:bold;
}

.menu a:hover{
    color:#38bdf8;
}

.card{
    background:rgba(30,41,59,.75);

    backdrop-filter:blur(10px);

    border:1px solid rgba(255,255,255,.08);

    border-radius:22px;

    padding:25px;

    margin-bottom:20px;

    box-shadow:
    0 0 20px rgba(0,0,0,.35);
}

h1{
    margin-bottom:20px;
    font-size:32px;
}

input,select{
    width:100%;

    padding:14px;

    margin-top:10px;

    border:none;

    border-radius:14px;

    background:#0f172a;

    color:white;

    outline:none;

    font-size:16px;
}

button{
    width:100%;

    padding:14px;

    margin-top:15px;

    border:none;

    border-radius:14px;

    background:
    linear-gradient(90deg,#06b6d4,#3b82f6);

    color:white;

    font-size:16px;

    font-weight:bold;

    cursor:pointer;

    transition:.2s;
}

button:hover{
    transform:scale(1.02);

    box-shadow:
    0 0 15px rgba(59,130,246,.5);
}

table{
    width:100%;
    border-collapse:collapse;
}

th{
    background:#1e293b;
    color:#38bdf8;
    padding:15px;
}

td{
    padding:14px;
    text-align:center;
    border-bottom:1px solid rgba(255,255,255,.05);
}

tr:hover{
    background:rgba(255,255,255,.03);
}

.delete-btn{
    color:#ef4444;
    text-decoration:none;
    font-weight:bold;
    font-size:18px;

    padding:4px 8px;

    border-radius:8px;

    transition:.2s;
}

.delete-btn:hover{
    background:rgba(239,68,68,.15);
}

.match-card{

    display:flex;
    justify-content:space-between;
    align-items:center;

    padding:20px;

    border-radius:18px;

    background:
    linear-gradient(
    135deg,
    rgba(59,130,246,.15),
    rgba(124,58,237,.15)
    );

    margin-top:15px;
}

.team{
    font-size:22px;
    font-weight:bold;
}

.score{
    font-size:40px;
    font-weight:bold;
    color:#38bdf8;
}

.result{
    margin-top:10px;
    opacity:.8;
}

.table-wrapper{
    overflow-x:auto;
}

@media(max-width:700px){
    .container{padding:10px;}
    .team{font-size:16px;}
    .score{font-size:28px;}
    .match-card{flex-direction:column;gap:10px;text-align:center;}
}

</style>
"""

# ---------------- NAVBAR ----------------

NAVBAR = """

<div class="topbar">

    <div class="logo">
        ⚽ UZYNAGASH LEAGUE
    </div>

    <div class="menu">
        <a href="/">Главная</a>
        <a href="/match">Матчи</a>
        <a href="/table">Таблица</a>
        <a href="/matches">История</a>
    </div>

</div>

"""

# ---------------- HOME ----------------

@app.route("/", methods=["GET","POST"])
def home():

    if request.method == "POST":

        team = request.form.get("team")

        if team:

            ref = db.collection("teams").document(team)

            if not ref.get().exists:

                ref.set({
                    "очки":0,
                    "победы":0,
                    "ничьи":0,
                    "поражения":0,
                    "голы":0
                })

        return redirect("/")

    return STYLE + f"""

    <div class="container">

        {NAVBAR}

        <div class="card">

            <h1>Добавить команду</h1>

            <form method="POST">

                <input name="team" placeholder="Название команды">

                <button>Добавить</button>

            </form>

        </div>

    </div>

    """

# ---------------- DELETE ----------------

@app.route("/delete/<path:name>")
def delete(name):

    name = unquote(name)

    db.collection("teams").document(name).delete()

    return redirect("/table")


@app.route("/delete_match/<match_id>")
def delete_match(match_id):

    match_ref = db.collection("matches").document(match_id)
    match = match_ref.get()

    if not match.exists:
        return redirect("/matches")

    d = match.to_dict()

    ref1 = db.collection("teams").document(d["t1"])
    ref2 = db.collection("teams").document(d["t2"])

    def dec(ref, field, value):
        data = ref.get().to_dict()
        ref.update({field: data.get(field,0) - value})

    dec(ref1,"голы",d["s1"])
    dec(ref2,"голы",d["s2"])

    if d["s1"] > d["s2"]:
        dec(ref1,"очки",3)
        dec(ref1,"победы",1)
        dec(ref2,"поражения",1)
    elif d["s2"] > d["s1"]:
        dec(ref2,"очки",3)
        dec(ref2,"победы",1)
        dec(ref1,"поражения",1)
    else:
        dec(ref1,"очки",1)
        dec(ref2,"очки",1)
        dec(ref1,"ничьи",1)
        dec(ref2,"ничьи",1)

    match_ref.delete()
    return redirect("/matches")


# ---------------- MATCH ----------------

@app.route("/match", methods=["GET","POST"])
def match():

    teams = [t.id for t in db.collection("teams").stream()]

    if request.method == "POST":

        t1 = request.form.get("team1")
        t2 = request.form.get("team2")

        if t1 == t2:
            return "❌ Нельзя выбрать одинаковые команды"

        s1 = int(request.form.get("score1"))
        s2 = int(request.form.get("score2"))

        ref1 = db.collection("teams").document(t1)
        ref2 = db.collection("teams").document(t2)

        if not ref1.get().exists or not ref2.get().exists:
            return "❌ Команда не найдена"

        def inc(ref, field, value):

            data = ref.get().to_dict()

            old = data.get(field,0)

            ref.update({
                field: old + value
            })

        # голы

        inc(ref1,"голы",s1)
        inc(ref2,"голы",s2)

        # победа

        if s1 > s2:

            inc(ref1,"очки",3)
            inc(ref1,"победы",1)
            inc(ref2,"поражения",1)

        elif s2 > s1:

            inc(ref2,"очки",3)
            inc(ref2,"победы",1)
            inc(ref1,"поражения",1)

        else:

            inc(ref1,"очки",1)
            inc(ref2,"очки",1)

            inc(ref1,"ничьи",1)
            inc(ref2,"ничьи",1)

        # история

        db.collection("matches").add({
            "t1":t1,
            "t2":t2,
            "s1":s1,
            "s2":s2,
            "created": datetime.utcnow()
        })

        return redirect("/matches")

    options = ""

    for t in teams:
        options += f"<option>{t}</option>"

    return STYLE + f"""

    <div class="container">

        {NAVBAR}

        <div class="card">

            <h1>Добавить матч</h1>

            <form method="POST">

                <select name="team1">
                    {options}
                </select>

                <select name="team2">
                    {options}
                </select>

                <input name="score1" placeholder="Голы 1">

                <input name="score2" placeholder="Голы 2">

                <button>Сохранить матч</button>

            </form>

        </div>

    </div>

    """

# ---------------- TABLE ----------------

@app.route("/table")
def table():

    docs = db.collection("teams").stream()

    teams = [(d.id,d.to_dict()) for d in docs]

    teams.sort(
        key=lambda x:x[1].get("очки",0),
        reverse=True
    )

    rows = ""

    pos = 1

    for name,d in teams:

        wins = d.get("победы",0)
        draws = d.get("ничьи",0)
        losses = d.get("поражения",0)

        games = wins + draws + losses

        rows += f"""

        <tr>

            <td>{pos}</td>

            <td>{name}</td>

            <td>{games}</td>

            <td>{wins}</td>

            <td>{draws}</td>

            <td>{losses}</td>

            <td>{d.get("голы",0)}</td>

            <td>{d.get("очки",0)}</td>

            <td>
                <a class="delete-btn" href="/delete/{name}">
                    ✕
                </a>
            </td>

        </tr>

        """

        pos += 1

    return STYLE + f"""

    <div class="container">

        {NAVBAR}

        <div class="card">

            <h1>🏆 Турнирная таблица</h1>

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
                    <th>X</th>
                </tr>

                {rows}

            </table>

        </div>

    </div>

    """

# ---------------- HISTORY ----------------

@app.route("/matches")
def matches():

    docs = db.collection("matches").stream()

    html = ""

    for m in docs:

        d = m.to_dict()

        if "s1" not in d or "s2" not in d:
            continue

        if d["s1"] > d["s2"]:
            result = "🟢 Победа первой команды"

        elif d["s2"] > d["s1"]:
            result = "🔴 Победа второй команды"

        else:
            result = "🟡 Ничья"

        html += f"""

        <div class="match-card">

            <div class="team">
                {d['t1']}
            </div>

            <div>

                <div class="score">
                    {d['s1']} : {d['s2']}
                </div>

                <div class="result">
                    {result}
                </div>

            </div>

            <div class="team">
                {d['t2']}
            </div>

        </div>

        """

    return STYLE + f"""

    <div class="container">

        {NAVBAR}

        <div class="card">

            <h1>📜 История матчей</h1>

            {html}

        </div>

    </div>

    """

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)