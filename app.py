from flask import Flask, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
from urllib.parse import unquote
import os
import json

app = Flask(__name__)

# ---------------- FIREBASE ----------------

firebase_config = json.loads(os.environ["FIREBASE_KEY"])
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- STYLE (MOBILE READY) ----------------

STYLE = """
<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    font-family:Arial;
    background:#0f172a;
    color:white;
    min-height:100vh;
    -webkit-tap-highlight-color: transparent;
}

.container{
    max-width:1100px;
    margin:auto;
    padding:20px;
}

.topbar{
    display:flex;
    justify-content:space-between;
    flex-wrap:wrap;
    gap:10px;
    margin-bottom:20px;
}

.logo{
    font-size:28px;
    font-weight:bold;
    color:#38bdf8;
}

.menu{
    display:flex;
    flex-wrap:wrap;
    gap:8px;
}

.menu a{
    color:white;
    text-decoration:none;
    padding:6px 10px;
    background:rgba(255,255,255,0.05);
    border-radius:10px;
}

.card{
    background:rgba(255,255,255,0.05);
    padding:20px;
    border-radius:16px;
}

input,select,button{
    width:100%;
    padding:14px;
    margin-top:10px;
    border:none;
    border-radius:10px;
    font-size:16px;
}

button{
    background:linear-gradient(90deg,#06b6d4,#3b82f6);
    color:white;
    font-weight:bold;
}

table{
    width:100%;
    border-collapse:collapse;
    min-width:600px;
}

th,td{
    padding:10px;
    text-align:center;
}

th{
    background:#1e293b;
}

.table-scroll{
    overflow-x:auto;
}

.match-card{
    display:flex;
    justify-content:space-between;
    align-items:center;
    background:rgba(255,255,255,0.05);
    padding:12px;
    margin-top:10px;
    border-radius:12px;
}

.score{
    font-size:28px;
    font-weight:bold;
    color:#38bdf8;
}

.delete-btn{
    color:red;
    font-size:20px;
    text-decoration:none;
}

@media(max-width:768px){

    .container{padding:10px;}

    .topbar{
        flex-direction:column;
        align-items:center;
    }

    .menu{
        justify-content:center;
    }

    .match-card{
        flex-direction:column;
        gap:8px;
        text-align:center;
    }

    table{
        font-size:12px;
    }
}

</style>
"""

# ---------------- NAV ----------------

NAV = """
<div class="topbar">
<div class="logo">⚽ League</div>
<div class="menu">
<a href="/">Home</a>
<a href="/match">Match</a>
<a href="/table">Table</a>
<a href="/matches">History</a>
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
                ref.set({"очки":0,"победы":0,"ничьи":0,"поражения":0,"голы":0})
        return redirect("/")

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>Добавить команду</h2>
    <form method="POST">
    <input name="team" placeholder="Название команды">
    <button>Добавить</button>
    </form>
    </div>
    </div>
    """

# ---------------- MATCH ----------------

@app.route("/match", methods=["GET","POST"])
def match():

    teams = [t.id for t in db.collection("teams").stream()]

    if request.method == "POST":

        t1 = request.form.get("team1")
        t2 = request.form.get("team2")

        if t1 == t2:
            return "❌ одинаковые команды"

        s1 = int(request.form.get("score1"))
        s2 = int(request.form.get("score2"))

        r1 = db.collection("teams").document(t1)
        r2 = db.collection("teams").document(t2)

        def add(ref, field, val):
            d = ref.get().to_dict()
            ref.update({field: d.get(field,0)+val})

        add(r1,"голы",s1)
        add(r2,"голы",s2)

        if s1 > s2:
            add(r1,"очки",3); add(r1,"победы",1); add(r2,"поражения",1)
        elif s2 > s1:
            add(r2,"очки",3); add(r2,"победы",1); add(r1,"поражения",1)
        else:
            add(r1,"очки",1); add(r2,"очки",1)
            add(r1,"ничьи",1); add(r2,"ничьи",1)

        db.collection("matches").add({
            "t1":t1,
            "t2":t2,
            "s1":s1,
            "s2":s2
        })

        return redirect("/matches")

    options = "".join([f"<option>{t}</option>" for t in teams])

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>Матч</h2>

    <form method="POST">
    <select name="team1">{options}</select>
    <select name="team2">{options}</select>

    <input type="number" name="score1" placeholder="Голы 1">
    <input type="number" name="score2" placeholder="Голы 2">

    <button>Сохранить</button>
    </form>

    </div>
    </div>
    """

# ---------------- DELETE MATCH ----------------

@app.route("/delete_match/<match_id>")
def delete_match(match_id):

    ref = db.collection("matches").document(match_id)
    m = ref.get()

    if not m.exists:
        return redirect("/matches")

    d = m.to_dict()

    t1,t2 = d["t1"],d["t2"]
    s1,s2 = d["s1"],d["s2"]

    r1 = db.collection("teams").document(t1)
    r2 = db.collection("teams").document(t2)

    def sub(ref, field, val):
        d = ref.get().to_dict()
        ref.update({field: d.get(field,0)-val})

    sub(r1,"голы",s1)
    sub(r2,"голы",s2)

    if s1 > s2:
        sub(r1,"очки",3); sub(r1,"победы",1); sub(r2,"поражения",1)
    elif s2 > s1:
        sub(r2,"очки",3); sub(r2,"победы",1); sub(r1,"поражения",1)
    else:
        sub(r1,"очки",1); sub(r2,"очки",1)
        sub(r1,"ничьи",1); sub(r2,"ничьи",1)

    ref.delete()

    return redirect("/matches")

# ---------------- HISTORY ----------------

@app.route("/matches")
def matches():

    docs = db.collection("matches").stream()

    html = ""

    for m in docs:

        d = m.to_dict()
        mid = m.id

        html += f"""
        <div class="match-card">
        <div>{d['t1']}</div>

        <div class="score">{d['s1']}:{d['s2']}</div>

        <div>{d['t2']}</div>

        <a class="delete-btn"
           href="/delete_match/{mid}"
           onclick="return confirm('Удалить матч?')">✖</a>
        </div>
        """

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>История матчей</h2>
    {html}
    </div>
    </div>
    """

# ---------------- TABLE ----------------

@app.route("/table")
def table():

    teams = [(t.id,t.to_dict()) for t in db.collection("teams").stream()]
    teams.sort(key=lambda x:x[1].get("очки",0),reverse=True)

    rows=""
    i=1

    for name,d in teams:
        g = d.get("победы",0)+d.get("ничьи",0)+d.get("поражения",0)

        rows += f"""
        <tr>
        <td>{i}</td>
        <td>{name}</td>
        <td>{g}</td>
        <td>{d.get("победы",0)}</td>
        <td>{d.get("ничьи",0)}</td>
        <td>{d.get("поражения",0)}</td>
        <td>{d.get("голы",0)}</td>
        <td>{d.get("очки",0)}</td>
        </tr>
        """
        i+=1

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>Таблица</h2>

    <div class="table-scroll">
    <table>
    {rows}
    </table>
    </div>

    </div>
    </div>
    """

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)