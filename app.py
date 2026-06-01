from flask import Flask, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

app = Flask(__name__)

# ---------------- FIREBASE ----------------

firebase_config = json.loads(os.environ["FIREBASE_KEY"])
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- СТИЛЬ ----------------

STYLE = """
<style>

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    font-family:system-ui;
    background:#0f172a;
    color:white;
    min-height:100vh;
    -webkit-tap-highlight-color: transparent;
}

.container{
    max-width:1100px;
    margin:auto;
    padding:15px;
}

.topbar{
    display:flex;
    justify-content:space-between;
    flex-wrap:wrap;
    gap:10px;
    margin-bottom:15px;
}

.logo{
    font-size:26px;
    font-weight:bold;
    color:#38bdf8;
}

.menu{
    display:flex;
    flex-wrap:wrap;
    gap:6px;
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
    padding:15px;
    border-radius:16px;
    margin-bottom:15px;
}

input,select,button{
    width:100%;
    padding:12px;
    margin-top:8px;
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
    min-width:700px;
}

th,td{
    padding:8px;
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
    padding:10px;
    margin-top:10px;
    border-radius:12px;
}

.score{
    font-size:26px;
    font-weight:bold;
    color:#38bdf8;
}

.delete-btn{
    color:red;
    font-size:18px;
    text-decoration:none;
}

.edit-btn{
    color:#38bdf8;
    margin-left:8px;
    text-decoration:none;
}

@media(max-width:768px){
    .match-card{
        flex-direction:column;
        text-align:center;
        gap:8px;
    }
}

</style>

<meta http-equiv="refresh" content="10">
"""

# ---------------- МЕНЮ ----------------

NAV = """
<div class="topbar">
<div class="logo">⚽ Лига</div>
<div class="menu">
<a href="/">Главная</a>
<a href="/match">Матч</a>
<a href="/table">Таблица</a>
<a href="/matches">История</a>
</div>
</div>
"""

# ---------------- ГЛАВНАЯ ----------------

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

# ---------------- МАТЧ ----------------

@app.route("/match", methods=["GET","POST"])
def match():

    teams = [t.id for t in db.collection("teams").stream()]

    if request.method == "POST":

        t1 = request.form.get("team1")
        t2 = request.form.get("team2")

        s1 = int(request.form.get("score1"))
        s2 = int(request.form.get("score2"))

        if t1 == t2:
            return "❌ Нельзя выбрать одинаковые команды"

        # защита от дубля
        exists = db.collection("matches").where("t1","==",t1).where("t2","==",t2).stream()
        for e in exists:
            d = e.to_dict()
            if d["s1"] == s1 and d["s2"] == s2:
                return "❌ Такой матч уже есть"

        r1 = db.collection("teams").document(t1)
        r2 = db.collection("teams").document(t2)

        def add(team, field, val):
            d = team.get().to_dict()
            team.update({field: d.get(field,0)+val})

        # голы
        add(r1,"голы",s1)
        add(r2,"голы",s2)

        # результат
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

    opts = "".join([f"<option>{t}</option>" for t in teams])

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>Добавить матч</h2>

    <form method="POST">
    <select name="team1">{opts}</select>
    <select name="team2">{opts}</select>

    <input type="number" name="score1" placeholder="Голы 1">
    <input type="number" name="score2" placeholder="Голы 2">

    <button>Сохранить</button>
    </form>

    </div>
    </div>
    """

# ---------------- УДАЛЕНИЕ ----------------

@app.route("/delete/<id>")
def delete(id):
    db.collection("matches").document(id).delete()
    return redirect("/matches")

# ---------------- РЕДАКТИРОВАНИЕ (ИСПРАВЛЕНО) ----------------

@app.route("/edit/<id>", methods=["GET","POST"])
def edit(id):

    ref = db.collection("matches").document(id)
    m = ref.get()

    if not m.exists:
        return redirect("/matches")

    old = m.to_dict()

    if request.method == "POST":

        new1 = int(request.form["s1"])
        new2 = int(request.form["s2"])

        t1 = old["t1"]
        t2 = old["t2"]

        old1 = old["s1"]
        old2 = old["s2"]

        r1 = db.collection("teams").document(t1)
        r2 = db.collection("teams").document(t2)

        d1 = r1.get().to_dict()
        d2 = r2.get().to_dict()

        # откат старого
        d1["голы"] -= old1
        d2["голы"] -= old2

        if old1 > old2:
            d1["очки"] -= 3; d1["победы"] -= 1; d2["поражения"] -= 1
        elif old2 > old1:
            d2["очки"] -= 3; d2["победы"] -= 1; d1["поражения"] -= 1
        else:
            d1["очки"] -= 1; d2["очки"] -= 1
            d1["ничьи"] -= 1; d2["ничьи"] -= 1

        # новый результат
        d1["голы"] += new1
        d2["голы"] += new2

        if new1 > new2:
            d1["очки"] += 3; d1["победы"] += 1; d2["поражения"] += 1
        elif new2 > new1:
            d2["очки"] += 3; d2["победы"] += 1; d1["поражения"] += 1
        else:
            d1["очки"] += 1; d2["очки"] += 1
            d1["ничьи"] += 1; d2["ничьи"] += 1

        r1.set(d1)
        r2.set(d2)

        ref.update({"s1":new1,"s2":new2})

        return redirect("/matches")

    return f"""
    <div style="color:white;padding:20px">
    <h2>Редактировать матч</h2>
    <form method="POST">
    <input name="s1" value="{old['s1']}">
    <input name="s2" value="{old['s2']}">
    <button>Сохранить</button>
    </form>
    </div>
    """

# ---------------- ИСТОРИЯ ----------------

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

        <div>
        <a class="edit-btn" href="/edit/{mid}">✏️</a>
        <a class="delete-btn" href="/delete/{mid}">✖</a>
        </div>

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

# ---------------- ТАБЛИЦА ----------------

@app.route("/table")
def table():

    teams = [(t.id,t.to_dict()) for t in db.collection("teams").stream()]
    teams.sort(key=lambda x:x[1].get("очки",0),reverse=True)

    rows=""
    i=1

    for name,d in teams:

        games = d.get("победы",0)+d.get("ничьи",0)+d.get("поражения",0)

        rows += f"""
        <tr>
        <td>{i}</td>
        <td>{name}</td>
        <td>{games}</td>
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
    <tr>
    <th>#</th><th>Команда</th><th>Игры</th><th>Победы</th><th>Ничьи</th><th>Поражения</th><th>Голы</th><th>Очки</th>
    </tr>
    {rows}
    </table>
    </div>

    </div>
    </div>
    """

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)