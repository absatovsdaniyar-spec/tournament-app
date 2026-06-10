from flask import Flask, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
import os, json

app = Flask(__name__)

firebase_config = json.loads(os.environ["FIREBASE_KEY"])
cred = credentials.Certificate(firebase_config)

try:
    firebase_admin.get_app()
except:
    firebase_admin.initialize_app(cred)

db = firestore.client()

YEARS = ["2017","2016","2015","2014","2013","2012"]

STYLE = """
<style>
body{margin:0;font-family:system-ui;background:#0f172a;color:white}
.container{max-width:1000px;margin:auto;padding:20px}
.card{background:#1e293b;padding:20px;border-radius:16px;margin-top:15px}
.year-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:15px}
.year-box{display:block;background:#334155;padding:30px;border-radius:16px;
color:white;text-decoration:none;text-align:center;font-size:24px;font-weight:bold}
input,select,button{width:100%;padding:12px;margin-top:10px;border-radius:10px;border:none}
button{cursor:pointer}
table{width:100%;border-collapse:collapse}
th,td{padding:10px;border-bottom:1px solid #475569;text-align:center}
.match{display:flex;justify-content:space-between;align-items:center;
background:#334155;padding:10px;border-radius:10px;margin-top:10px}
.actions{display:flex;gap:5px}
.small-btn{width:auto;padding:6px 10px}
</style>
"""

NAV = '<p><a href="/" style="color:white">🏠 Годы</a></p>'

def recalc_table(year):
    teams = {}
    for t in db.collection("teams").where("year", "==", year).stream():
        d = t.to_dict()
        teams[d["name"]] = {
            "победы":0,"ничьи":0,"поражения":0,"голы":0,"очки":0
        }

    for m in db.collection("matches").where("year", "==", year).stream():
        d = m.to_dict()
        t1,t2,s1,s2 = d["t1"],d["t2"],d["s1"],d["s2"]

        if t1 not in teams or t2 not in teams:
            continue

        teams[t1]["голы"] += s1
        teams[t2]["голы"] += s2

        if s1 > s2:
            teams[t1]["очки"] += 3
            teams[t1]["победы"] += 1
            teams[t2]["поражения"] += 1
        elif s2 > s1:
            teams[t2]["очки"] += 3
            teams[t2]["победы"] += 1
            teams[t1]["поражения"] += 1
        else:
            teams[t1]["очки"] += 1
            teams[t2]["очки"] += 1
            teams[t1]["ничьи"] += 1
            teams[t2]["ничьи"] += 1

    for name, stats in teams.items():
        db.collection("teams").document(f"{year}_{name}").set(stats, merge=True)

@app.route("/")
def home():
    html = "".join(
        f'<a class="year-box" href="/year/{y}">{y} г.р</a>'
        for y in YEARS
    )
    return STYLE + f'<div class="container">{NAV}<div class="card"><div class="year-grid">{html}</div></div></div>'

@app.route("/year/<year>")
def year_page(year):
    return STYLE + f"""
    <div class="container">{NAV}
    <div class="year-grid">
    <a class="year-box" href="/year/{year}/add-team">➕ Команды</a>
    <a class="year-box" href="/year/{year}/match">⚽ Матчи</a>
    <a class="year-box" href="/year/{year}/table">🏆 Таблица</a>
    <a class="year-box" href="/year/{year}/matches">📜 История</a>
    </div></div>
    """

@app.route("/year/<year>/add-team", methods=["GET","POST"])
def add_team(year):
    if request.method == "POST":
        team = request.form["team"].strip()
        db.collection("teams").document(f"{year}_{team}").set({
            "name": team,
            "year": year
        }, merge=True)
        return redirect(f"/year/{year}")

    return STYLE + f"""
    <div class="container">{NAV}
    <div class="card">
    <form method="POST">
    <input name="team" placeholder="Название команды">
    <button>Добавить</button>
    </form></div></div>
    """

@app.route("/year/<year>/match", methods=["GET","POST"])
def match(year):
    team_list = [t.to_dict()["name"] for t in db.collection("teams").where("year","==",year).stream()]

    if request.method == "POST":
        t1 = request.form["team1"].strip()
        t2 = request.form["team2"].strip()

        if t1 == t2:
            return "Нельзя выбрать одну команду"

        db.collection("matches").add({
            "year": year,
            "t1": t1,
            "t2": t2,
            "s1": int(request.form["s1"]),
            "s2": int(request.form["s2"])
        })

        recalc_table(year)
        return redirect(f"/year/{year}/matches")

    opts = "".join(f"<option>{t}</option>" for t in team_list)

    return STYLE + f"""
    <div class="container">{NAV}<div class="card">
    <form method="POST">
    <select name="team1">{opts}</select>
    <select name="team2">{opts}</select>
    <input type="number" name="s1">
    <input type="number" name="s2">
    <button>Сохранить</button>
    </form></div></div>
    """

@app.route("/delete-match/<match_id>/<year>", methods=["POST"])
def delete_match(match_id, year):
    db.collection("matches").document(match_id).delete()
    recalc_table(year)
    return redirect(f"/year/{year}/matches")

@app.route("/year/<year>/matches")
def matches(year):
    html = ""

    for m in db.collection("matches").where("year","==",year).stream():
        d = m.to_dict()

        html += f"""
        <div class="match">
            <span>{d['t1']}</span>
            <strong>{d['s1']} : {d['s2']}</strong>
            <span>{d['t2']}</span>

            <form method="POST" action="/delete-match/{m.id}/{year}">
                <button class="small-btn">🗑</button>
            </form>
        </div>
        """

    return STYLE + f'<div class="container">{NAV}<div class="card">{html}</div></div>'

@app.route("/year/<year>/table")
def table(year):
    recalc_table(year)

    data = []

    for t in db.collection("teams").where("year","==",year).stream():
        d = t.to_dict()

        games = d.get("победы",0)+d.get("ничьи",0)+d.get("поражения",0)

        data.append([
            d["name"],
            games,
            d.get("победы",0),
            d.get("ничьи",0),
            d.get("поражения",0),
            d.get("голы",0),
            d.get("очки",0)
        ])

    data.sort(key=lambda x:x[6], reverse=True)

    rows = ""
    for i,r in enumerate(data,1):
        rows += f"<tr><td>{i}</td><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td>{r[6]}</td></tr>"

    return STYLE + f"""
    <div class="container">{NAV}<div class="card">
    <table>
    <tr><th>#</th><th>Команда</th><th>И</th><th>В</th><th>Н</th><th>П</th><th>Г</th><th>О</th></tr>
    {rows}
    </table>
    </div></div>
    """

if __name__ == "__main__":
    app.run(debug=True)
