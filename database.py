import os
import sys
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

def get_db_path() -> Path:
    """Returns database path. Uses %LOCALAPPDATA%/StickyNotes when packaged as an exe."""
    if getattr(sys, 'frozen', False):
        app_data = Path(os.environ.get('LOCALAPPDATA', Path.home())) / "StickyNotes"
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data / "notes.db"
    return Path(__file__).parent / "notes.db"

try:
    from .theme_manager import get_preferences_path
except ImportError:
    try:
        from theme_manager import get_preferences_path
    except ImportError:
        def get_preferences_path():
            if getattr(sys, 'frozen', False):
                app_data = Path(os.environ.get('LOCALAPPDATA', Path.home())) / "StickyNotes"
            else:
                app_data = Path(__file__).parent
            return app_data / "preferences.json"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """Initializes the database schema, handles migrations, and seeds defaults if empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        # Projects Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                color_hex TEXT NOT NULL,
                icon TEXT DEFAULT 'folder',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Notes Table
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

        # Schema Migration: Add project_id to notes if missing
        cursor.execute("PRAGMA table_info(notes)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "project_id" not in columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN project_id TEXT DEFAULT 'default'")

        # Ensure default project exists
        cursor.execute("SELECT COUNT(*) as count FROM projects WHERE id = 'default'")
        if cursor.fetchone()["count"] == 0:
            cursor.execute("""
                INSERT INTO projects (id, name, color_hex, icon, created_at, updated_at)
                VALUES ('default', 'General Notes', '#8AB4F8', 'folder', ?, ?)
            """, (now, now))

        # Reassign any NULL or orphan notes to default project
        cursor.execute("UPDATE notes SET project_id = 'default' WHERE project_id IS NULL OR project_id = ''")
        conn.commit()

        # Seed initial notes if empty
        cursor.execute("SELECT COUNT(*) as count FROM notes")
        row = cursor.fetchone()
        if row and row["count"] == 0:
            sample_notes = [
                (
                    str(uuid.uuid4()),
                    "Welcome to Sticky Notes! 📝",
                    "# Markdown Features\n\n- **Double-click** any note to edit.\n- **Right-click** to choose a custom color!\n- Write *italics*, **bold**, lists, and `code`.\n- Click the **← Back arrow** to return to this grid.",
                    "#FFF9C4",  # Butter Yellow
                    "default",
                    now,
                    now
                ),
                (
                    str(uuid.uuid4()),
                    "Quick To-Do List ✅",
                    "### Tasks for today:\n- [x] Set up Python desktop app\n- [ ] Design custom markdown themes\n- [ ] Try keyboard shortcuts\n\n> Keep it minimal and focused!",
                    "#C8E6C9",  # Mint Green
                    "default",
                    now,
                    now
                ),
                (
                    str(uuid.uuid4()),
                    "Code Snippet 💻",
                    "```python\n# Python + PySide6 WinUI 3 Style\nprint('Clean, fast, and local!')\n```\nEnjoy seamless offline markdown notes.",
                    "#BBDEFB",  # Sky Blue
                    "default",
                    now,
                    now
                )
            ]
            cursor.executemany("""
                INSERT INTO notes (id, title, content, color_hex, project_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, sample_notes)
            conn.commit()

# --- Project Operations ---

def get_all_projects() -> List[Dict[str, Any]]:
    """Fetches all project stacks with their current note counts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, COUNT(n.id) as note_count
            FROM projects p
            LEFT JOIN notes n ON p.id = n.project_id
            GROUP BY p.id
            ORDER BY CASE WHEN p.id = 'default' THEN 0 ELSE 1 END, p.created_at ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Fetches single project by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_project(name: str, color_hex: str = "#8AB4F8", icon: str = "folder") -> str:
    """Creates a new project stack and returns its ID."""
    proj_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO projects (id, name, color_hex, icon, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (proj_id, name.strip(), color_hex, icon, now, now))
        conn.commit()
    return proj_id

def update_project(project_id: str, name: Optional[str] = None, color_hex: Optional[str] = None) -> None:
    """Updates name or color of a project."""
    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name.strip())
    if color_hex is not None:
        updates.append("color_hex = ?")
        params.append(color_hex)
    if not updates:
        return
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(project_id)
    query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def delete_project(project_id: str, reassign_to_id: str = "default") -> bool:
    """Deletes a project and safely reassigns its notes to another project."""
    if project_id == "default":
        return False
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET project_id = ?, updated_at = ? WHERE project_id = ?", (reassign_to_id, now, project_id))
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    return True

def move_notes_to_project(note_ids: List[str], target_project_id: str) -> None:
    """Moves a list of notes to a target project stack."""
    if not note_ids:
        return
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE notes SET project_id = ?, updated_at = ? WHERE id = ?",
            [(target_project_id, now, nid) for nid in note_ids]
        )
        conn.commit()

def get_active_project_id() -> str:
    """Retrieves last active project ID from user preferences."""
    pref_file = get_preferences_path()
    if pref_file.exists():
        try:
            import json
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                pid = data.get("active_project_id", "default")
                if pid:
                    return pid
        except Exception:
            pass
    return "default"

def set_active_project_id(project_id: str) -> None:
    """Saves active project ID in user preferences."""
    pref_file = get_preferences_path()
    data = {}
    if pref_file.exists():
        try:
            import json
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["active_project_id"] = project_id
    try:
        import json
        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# --- Note Operations ---

def get_all_notes(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches all notes, optionally filtered by project stack."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if project_id and project_id != "all":
            cursor.execute("SELECT * FROM notes WHERE project_id = ? ORDER BY updated_at DESC", (project_id,))
        else:
            cursor.execute("SELECT * FROM notes ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_note(note_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single note by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_note(title: str = "Untitled Note", content: str = "", color_hex: str = "#FFF9C4", project_id: Optional[str] = None) -> str:
    """Creates a new note assigned to a project stack and returns its ID."""
    note_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    pid = project_id or get_active_project_id()
    if pid == "all":
        pid = "default"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (id, title, content, color_hex, project_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (note_id, title, content, color_hex, pid, now, now))
        conn.commit()
    return note_id

def update_note(note_id: str, title: Optional[str] = None, content: Optional[str] = None, color_hex: Optional[str] = None, project_id: Optional[str] = None) -> None:
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
    if project_id is not None:
        updates.append("project_id = ?")
        params.append(project_id)
        
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

def duplicate_note(note_id: str) -> Optional[str]:
    """Creates an exact copy of a note in the same project stack."""
    existing = get_note(note_id)
    if not existing:
        return None
    
    new_title = f"{existing['title']} (Copy)"
    return create_note(
        title=new_title,
        content=existing["content"],
        color_hex=existing["color_hex"],
        project_id=existing.get("project_id", "default")
    )

def delete_multiple_notes(note_ids: List[str]) -> None:
    """Deletes a list of notes by IDs in a single transaction."""
    if not note_ids:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("DELETE FROM notes WHERE id = ?", [(nid,) for nid in note_ids])
        conn.commit()

