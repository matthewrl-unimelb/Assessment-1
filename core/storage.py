"""Saving answers into folders, in a small SQLite database (data/app.db).

SQLite is a database stored in a single file. Python has it built in, so
nothing extra needs installing.

Limitations (worth stating in the README):
- Folders are keyed by the name the user types on the welcome page. Anyone who
  enters the same name sees the same folders. That's fine for a demo, but not secure.
- On Streamlit Cloud the file lives on the app's server and is wiped when the
  app restarts or goes to sleep. Use "Download folder" to keep anything.
"""

import sqlite3
from datetime import datetime

from core.config import ROOT

DB_PATH = ROOT / "data" / "app.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us read columns by name, e.g. row["title"]
    conn.execute("""CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT, title TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS saved (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folder_id INTEGER, question TEXT, level TEXT, answer TEXT, saved_at TEXT)""")
    return conn


def _now():
    return datetime.now().strftime("%d %b %Y, %H:%M")


def create_folder(user):
    """Make a new, empty folder. Returns its id. The AI names it once something is saved."""
    with _connect() as conn:
        cur = conn.execute("INSERT INTO folders (user, title) VALUES (?, ?)", (user, "New folder"))
        return cur.lastrowid


def rename_folder(folder_id, title):
    with _connect() as conn:
        conn.execute("UPDATE folders SET title = ? WHERE id = ?", (title, folder_id))


def list_folders(user):
    with _connect() as conn:
        return conn.execute(
            "SELECT id, title FROM folders WHERE user = ? ORDER BY id DESC", (user,)).fetchall()


def delete_folder(user, folder_id):
    with _connect() as conn:
        conn.execute("DELETE FROM saved WHERE folder_id = ?", (folder_id,))
        conn.execute("DELETE FROM folders WHERE id = ? AND user = ?", (folder_id, user))


def save_to_folder(folder_id, question, level, answer):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO saved (folder_id, question, level, answer, saved_at) VALUES (?, ?, ?, ?, ?)",
            (folder_id, question, level, answer, _now()))


def folder_items(folder_id):
    with _connect() as conn:
        return conn.execute(
            "SELECT id, question, level, answer, saved_at FROM saved WHERE folder_id = ? ORDER BY id",
            (folder_id,)).fetchall()


def delete_item(item_id):
    with _connect() as conn:
        conn.execute("DELETE FROM saved WHERE id = ?", (item_id,))


def folder_as_markdown(title, items):
    """Turn a folder into a Markdown document the user can download."""
    lines = [f"# {title}", "", "Saved answers about MNR v Cameron [1974] SCR 1062", ""]
    for it in items:
        lines += [f"## {it['question']}", f"*{it['level']} · saved {it['saved_at']}*", "", it["answer"], ""]
    return "\n".join(lines)