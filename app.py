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

YEARS = ["2017","2016","2015","2014","2013","2012"]

# ---------------- STYLE ----------------

STYLE = """
<style>

body{
    margin:0;
    font-family:system-ui;
    background:#0f172a;
    color:white;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
}

/* главный контейнер */
.container{
    width:100%;
    max-width:900px;
    padding:20px;
    text-align:center;
}

/* верхняя панель */
.top{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:20px;
}

/* карточки */
.card{
    background:rgba(255,255,255,0.06);
    padding:20px;
    border-radius:20px;
    margin-top:15px;
}

/* ГОДА */
.year-grid{
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:15px;
    margin-top:20px;
}

/* кнопка года */
.year-box{
    background:#1e293b;
    padding:35px 10px;
    border-radius:18px;
    font-size:24px;
    font-weight:bold;
    color:white;
    text-decoration:none;
    transition:0.2s;
}

.year-box:active{
    transform:scale(0.95);
}

/* кнопки и инпуты */
input,select,button{
    width:100%;
    padding:14px;
    margin-top:10px;
    border:none;
    border-radius:12px;
    font-size:16px;
}

button{
    background:linear-gradient(90deg,#06b6d4,#3b82f6);
    color:white;
    font-weight:bold;
}

/* таблица */
table{
    width:100%;
    border-collapse:collapse;
    font-size:14px;
}

th,td{
    padding:10px;
    text-align:center;
}

th{
    background:#1e293b;
}

/* матч карточка */
.match{
    display:flex;
    justify-content:space-between;
    align-items:center;
    background:rgba(255,255,255,0.06);
    padding:12px;
    margin-top:10px;
    border-radius:12px;
}

.score{
    font-size:22px;
    color:#38bdf8;
    font-weight:bold;
}

/* мобильная адаптация */
@media(max-width:600px){
    .year-grid{
        grid-template-columns:1fr;
    }

    .year-box{
        font-size:28px;
        padding:40px;
    }
}

</style>
"""

NAV = """
<div class="top">
<h2>⚽ UZYNAGASH LEAGUE</h2>
<a href="/">Годы</a>
</div>
"""

# ---------------- HOME (YEARS) ----------------

@app.route("/")
def home():
    html = '<div class="year-grid">'
    for y in YEARS:
        html += f'<a class="year-box" href="/year/{y}">{y} г.р</a>'
    html += "</div>"

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h3>Выбери год</h3>
    {html}
    </div>
    </div>
    """

# ---------------- YEAR PAGE ----------------

@app.route("/year/<year>")
def year_page(year):

    return STYLE + f"""
    <div class="container">

    {NAV}

    <div class="card">
    <h2>{year} г.р</h2>
    </div>

    <div class="year-grid">

        <a class="year-box" href="/year/{year}/add-team">
        ➕ Команды
        </a>

        <a class="year-box" href="/year/{year}/match">
        ⚽ Матчи
        </a>

        <a class="year-box" href="/year/{year}/table">
        🏆 Таблица
        </a>

        <a class="year-box" href="/year/{year}/matches">
        📜 История
        </a>

    </div>

    </div>
    """

# ---------------- ADD TEAM ----------------

@app.route("/year/<year>/add-team", methods=["GET","POST"])
def add_team(year):

    if request.method == "POST":
       team = request.form["team"].strip()

        db.collection("teams").document(f"{year}_{team}").set({
            "name": team,
            "year": year,
            "очки":0,"победы":0,"ничьи":0,"поражения":0,"голы":0
        })

        return redirect(f"/year/{year}")

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>Добавить команду ({year})</h2>

    <form method="POST">
    <input name="team" placeholder="Название команды">
    <button>Добавить</button>
    </form>

    </div>
    </div>
    """

# ---------------- MATCH ----------------

@app.route("/year/<year>/match", methods=["GET","POST"])
def match(year):

    teams = db.collection("teams").where("year","==",year).stream()
    team_list = [t.to_dict()["name"] for t in teams]

    if request.method == "POST":

        t1 = request.form["team1"].strip()
        t2 = request.form["team2"].strip()
        s1 = int(request.form["s1"])
        s2 = int(request.form["s2"])

        if t1 == t2:
            return "Ошибка"

        mref = db.collection("matches").document()
        mref.set({
            "year":year,
            "t1":t1,
            "t2":t2,
            "s1":s1,
            "s2":s2
        })

        def upd(team, field, val):
ref = db.collection("teams").document(f"{year}_{team}")

```
doc = ref.get()

if not doc.exists:
    print(f"ОШИБКА: команда не найдена -> {year}_{team}")
    return

d = doc.to_dict() or {}

ref.set({
    field: d.get(field, 0) + val
}, merge=True)
```


        upd(t1,"голы",s1)
        upd(t2,"голы",s2)

        if s1>s2:
            upd(t1,"очки",3);upd(t1,"победы",1);upd(t2,"поражения",1)
        elif s2>s1:
            upd(t2,"очки",3);upd(t2,"победы",1);upd(t1,"поражения",1)
        else:
            upd(t1,"очки",1);upd(t2,"очки",1)
            upd(t1,"ничьи",1);upd(t2,"ничьи",1)

        return redirect(f"/year/{year}/matches")

    opts = "".join([f"<option>{t}</option>" for t in team_list])

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>Матч ({year})</h2>

    <form method="POST">
    <select name="team1">{opts}</select>
    <select name="team2">{opts}</select>
    <input name="s1" type="number" placeholder="Голы 1">
    <input name="s2" type="number" placeholder="Голы 2">
    <button>Сохранить</button>
    </form>

    </div>
    </div>
    """

# ---------------- MATCHES ----------------

@app.route("/year/<year>/matches")
def matches(year):

    docs = db.collection("matches").where("year","==",year).stream()

    html = ""

    for m in docs:
        d = m.to_dict()
        html += f"""
        <div class="match">
        <div>{d['t1']}</div>
        <div class="score">{d['s1']}:{d['s2']}</div>
        <div>{d['t2']}</div>
        </div>
        """

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>История ({year})</h2>
    {html}
    </div>
    </div>
    """

# ---------------- TABLE ----------------

@app.route("/year/<year>/table")
def table(year):

    teams = db.collection("teams").where("year","==",year).stream()
    data = []

    for t in teams:
        d = t.to_dict()
        games = d["победы"]+d["ничьи"]+d["поражения"]
        data.append((d["name"],games,d["победы"],d["ничьи"],d["поражения"],d["голы"],d["очки"]))

    data.sort(key=lambda x:x[-1],reverse=True)

    rows=""
    i=1
    for r in data:
        rows += f"""
        <tr>
        <td>{i}</td>
        <td>{r[0]}</td>
        <td>{r[1]}</td>
        <td>{r[2]}</td>
        <td>{r[3]}</td>
        <td>{r[4]}</td>
        <td>{r[5]}</td>
        <td>{r[6]}</td>
        </tr>
        """
        i+=1

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <h2>Таблица ({year})</h2>

    <table class="table">
    <tr>
    <th>#</th><th>Команда</th><th>И</th><th>В</th><th>Н</th><th>П</th><th>Г</th><th>О</th>
    </tr>
    {rows}
    </table>

    </div>
    </div>
    """

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)