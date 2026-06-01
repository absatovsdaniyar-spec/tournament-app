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

# ---------------- STYLE ----------------

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
    font-size:24px;
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
    font-size:13px;
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
    font-size:24px;
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
        gap:8px;
        text-align:center;
    }
}

</style>

<meta http-equiv="refresh" content="10">
"""

# ---------------- NAV ----------------

NAV = """
<div class="topbar">
<div class="logo">⚽ UZYNAGASH LEAGUE</div>
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
    return STYLE + f"<div class='container'>{NAV}<div class='card'><form method='POST'><input name='team' placeholder='Team'><button>Add</button></form></div></div>"

# ---------------- MATCH ----------------

@app.route("/match", methods=["GET","POST"])
def match():

    teams = [t.id for t in db.collection("teams").stream()]

    if request.method == "POST":

        t1 = request.form.get("team1")
        t2 = request.form.get("team2")

        s1 = int(request.form.get("score1"))
        s2 = int(request.form.get("score2"))

        if t1 == t2:
            return "same teams"

        # DUPLICATE CHECK
        existing = db.collection("matches").where("t1","==",t1).where("t2","==",t2).stream()
        for e in existing:
            d = e.to_dict()
            if d["s1"] == s1 and d["s2"] == s2:
                return "duplicate match"

        r1 = db.collection("teams").document(t1)
        r2 = db.collection("teams").document(t2)

        def add(r,f,v):
            d=r.get().to_dict()
            r.update({f:d.get(f,0)+v})

        add(r1,"голы",s1)
        add(r2,"голы",s2)

        if s1>s2:
            add(r1,"очки",3); add(r1,"победы",1); add(r2,"поражения",1)
        elif s2>s1:
            add(r2,"очки",3); add(r2,"победы",1); add(r1,"поражения",1)
        else:
            add(r1,"очки",1); add(r2,"очки",1)
            add(r1,"ничьи",1); add(r2,"ничьи",1)

        db.collection("matches").add({"t1":t1,"t2":t2,"s1":s1,"s2":s2})

        return redirect("/matches")

    opts = "".join([f"<option>{t}</option>" for t in teams])

    return STYLE + f"""
    <div class="container">
    {NAV}
    <div class="card">
    <form method="POST">
    <select name="team1">{opts}</select>
    <select name="team2">{opts}</select>
    <input type="number" name="score1">
    <input type="number" name="score2">
    <button>Save</button>
    </form>
    </div>
    </div>
    """

# ---------------- DELETE ----------------

@app.route("/delete/<id>")
def delete(id):

    db.collection("matches").document(id).delete()

    return redirect("/matches")

# ---------------- EDIT ----------------

@app.route("/edit/<id>", methods=["GET","POST"])
def edit(id):

    ref = db.collection("matches").document(id)
    m = ref.get()

    if not m.exists:
        return redirect("/matches")

    d = m.to_dict()

    if request.method=="POST":

        new1=int(request.form["s1"])
        new2=int(request.form["s2"])

        # rollback old
        t1,t2=d["t1"],d["t2"]
        s1,s2=d["s1"],d["s2"]

        r1=db.collection("teams").document(t1)
        r2=db.collection("teams").document(t2)

        def sub(r,f,v):
            d=r.get().to_dict()
            r.update({f:d.get(f,0)-v})

        def add(r,f,v):
            d=r.get().to_dict()
            r.update({f:d.get(f,0)+v})

        sub(r1,"голы",s1); sub(r2,"голы",s2)

        if s1>s2:
            sub(r1,"очки",3); sub(r1,"победы",1); sub(r2,"поражения",1)
        elif s2>s1:
            sub(r2,"очки",3); sub(r2,"победы",1); sub(r1,"поражения",1)
        else:
            sub(r1,"очки",1); sub(r2,"очки",1)
            sub(r1,"ничьи",1); sub(r2,"ничьи",1)

        add(r1,"голы",new1)
        add(r2,"голы",new2)

        if new1>new2:
            add(r1,"очки",3); add(r1,"победы",1); add(r2,"поражения",1)
        elif new2>new1:
            add(r2,"очки",3); add(r2,"победы",1); add(r1,"поражения",1)
        else:
            add(r1,"очки",1); add(r2,"очки",1)
            add(r1,"ничьи",1); add(r2,"ничьи",1)

        ref.update({"s1":new1,"s2":new2})

        return redirect("/matches")

    return f"""
    <form method="POST">
    <input name="s1" value="{d['s1']}">
    <input name="s2" value="{d['s2']}">
    <button>Save</button>
    </form>
    """

# ---------------- MATCHES ----------------

@app.route("/matches")
def matches():

    docs=db.collection("matches").stream()

    html=""

    for m in docs:

        d=m.to_dict()
        mid=m.id

        html+=f"""
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

    return STYLE + f"<div class='container'>{NAV}<div class='card'>{html}</div></div>"

# ---------------- TABLE ----------------

@app.route("/table")
def table():

    teams=[(t.id,t.to_dict()) for t in db.collection("teams").stream()]
    teams.sort(key=lambda x:x[1].get("очки",0),reverse=True)

    rows=""
    i=1

    for n,d in teams:

        g=d.get("победы",0)+d.get("ничьи",0)+d.get("поражения",0)

        rows+=f"""
        <tr>
        <td>{i}</td>
        <td>{n}</td>
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
    <div class='container'>
    {NAV}
    <div class='card'>
    <div class='table-scroll'>
    <table>
    <tr><th>#</th><th>Team</th><th>Games</th><th>W</th><th>D</th><th>L</th><th>Goals</th><th>Points</th></tr>
    {rows}
    </table>
    </div>
    </div>
    </div>
    """

# ---------------- RUN ----------------

if __name__=="__main__":
    app.run(debug=True)