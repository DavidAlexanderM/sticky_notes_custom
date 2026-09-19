import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).parent / "notes.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initializes the database schema and seeds initial sample notes if empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                color_hex TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

        # Seed initial notes if empty
        cursor.execute("SELECT COUNT(*) as count FROM notes")
        row = cursor.fetchone()
        if row and row["count"] == 0:
            now = datetime.now().isoformat()
            sample_notes = [
                (
                    str(uuid.uuid4()),
                    "Welcome to Sticky Notes! 📝",
                    "# Markdown Features\n\n- **Double-click** any note to edit.\n- **Right-click** to choose a custom color!\n- Write *italics*, **bold**, lists, and `code`.\n- Click the **← Back arrow** to return to this grid.",
                    "#FFF9C4",  # Butter Yellow
                    now,
                    now
                ),
                (
                    str(uuid.uuid4()),
                    "Quick To-Do List ✅",
                    "### Tasks for today:\n- [x] Set up Python desktop app\n- [ ] Design custom markdown themes\n- [ ] Try keyboard shortcuts\n\n> Keep it minimal and focused!",
                    "#C8E6C9",  # Mint Green
                    now,
                    now
                ),
                (
                    str(uuid.uuid4()),
                    "Code Snippet 💻",
                    "```python\n# Python + PySide6 WinUI 3 Style\nprint('Clean, fast, and local!')\n```\nEnjoy seamless offline markdown notes.",
                    "#BBDEFB",  # Sky Blue
                    now,
                    now
                )
            ]
            cursor.executemany("""
                INSERT INTO notes (id, title, content, color_hex, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, sample_notes)
            conn.commit()

def get_all_notes() -> List[Dict[str, Any]]:
    """Fetches all notes ordered by most recently modified."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_note(note_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single note by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_note(title: str = "Untitled Note", content: str = "", color_hex: str = "#FFF9C4") -> str:
    """Creates a new note and returns its ID."""
    note_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (id, title, content, color_hex, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (note_id, title, content, color_hex, now, now))
        conn.commit()
    return note_id

def update_note(note_id: str, title: Optional[str] = None, content: Optional[str] = None, color_hex: Optional[str] = None) -> None:
    """Updates fields of an existing note."""
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if color_hex is not None:
        updates.append("color_hex = ?")
        params.append(color_hex)
        
    if not updates:
        return

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(note_id)

    query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def delete_note(note_id: str) -> None:
    """Deletes a note by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
