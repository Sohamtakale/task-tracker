import os
import sqlite3
from flask import Flask, jsonify, request, render_template_string, g

VERSION = "v1"

app = Flask(__name__)
app.config["DB_PATH"] = os.environ.get("DB_PATH", "tasks.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, "
            "done INTEGER NOT NULL DEFAULT 0)"
        )
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


PAGE = """
<!doctype html>
<title>Task Tracker</title>
<style>
  body{font-family:sans-serif;max-width:480px;margin:40px auto}
  li{margin:6px 0;cursor:pointer}
  .done span{text-decoration:line-through;color:#888}
</style>
<h1>Task Tracker <small>{{ version }}</small></h1>
<form id="f"><input id="t" placeholder="New task" required> <button>Add</button></form>
<ul id="l"></ul>
<script>
async function load() {
  const tasks = await (await fetch('/api/tasks')).json();
  const ul = document.getElementById('l');
  ul.innerHTML = '';
  tasks.forEach(t => {
    const li = document.createElement('li');
    if (t.done) li.className = 'done';
    const span = document.createElement('span');
    span.textContent = t.title;
    span.onclick = async () => { await fetch('/api/tasks/' + t.id + '/toggle', {method: 'PUT'}); load(); };
    const del = document.createElement('button');
    del.textContent = 'x';
    del.onclick = async () => { await fetch('/api/tasks/' + t.id, {method: 'DELETE'}); load(); };
    li.append(span, ' ', del);
    ul.appendChild(li);
  });
}
document.getElementById('f').onsubmit = async e => {
  e.preventDefault();
  const input = document.getElementById('t');
  await fetch('/api/tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title: input.value})
  });
  input.value = '';
  load();
};
load();
</script>
"""


@app.route("/")
def home():
    return render_template_string(PAGE, version=VERSION)


@app.route("/health")
def health():
    return jsonify(status="ok", version=VERSION)


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    rows = get_db().execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return jsonify([{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows])


@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title required"), 400
    db = get_db()
    cur = db.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
    db.commit()
    return jsonify(id=cur.lastrowid, title=title, done=False), 201


@app.route("/api/tasks/<int:task_id>/toggle", methods=["PUT"])
def toggle_task(task_id):
    db = get_db()
    cur = db.execute("UPDATE tasks SET done = 1 - done WHERE id = ?", (task_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="not found"), 404
    return jsonify(status="toggled")


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    db = get_db()
    cur = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="not found"), 404
    return jsonify(status="deleted")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
