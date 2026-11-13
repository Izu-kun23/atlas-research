import sqlite3, json, os
from pathlib import Path


class Reports:
    def __init__(self):
        self.path = os.getenv("RESEARCH_DB", "data/reports.db")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,topic TEXT,payload TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)"
            )

    def save(self, id, state):
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO reports(id,topic,payload) VALUES(?,?,?)",
                (id, state["topic"], json.dumps(state)),
            )

    def list(self):
        with sqlite3.connect(self.path) as db:
            return [
                {"id": r[0], "topic": r[1], "created": r[2]}
                for r in db.execute(
                    "SELECT id,topic,created FROM reports ORDER BY created DESC LIMIT 50"
                )
            ]

    def get(self, id):
        with sqlite3.connect(self.path) as db:
            r = db.execute("SELECT payload FROM reports WHERE id=?", (id,)).fetchone()
        return json.loads(r[0]) if r else None
