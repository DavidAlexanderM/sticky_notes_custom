import os
import sys
import json
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

        # Schema Migration: Add project_id and tags to notes if missing
        cursor.execute("PRAGMA table_info(notes)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "project_id" not in columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN project_id TEXT DEFAULT 'default'")
        if "tags" not in columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN tags TEXT DEFAULT '[]'")

        # Custom Tags Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                color_hex TEXT DEFAULT '#8AB4F8',
                created_at TEXT NOT NULL
            )
        """)

        # User Dictionary Table (Personal Spell Check Words)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_dictionary (
                word TEXT PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'en',
                created_at TEXT NOT NULL
            )
        """)

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

def create_project(name: str, color_hex: str = "#8AB4F8", icon: str = "folder", color: Optional[str] = None) -> str:
    """Creates a new project stack and returns its ID."""
    if color is not None:
        color_hex = color
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

def get_next_stack_name() -> str:
    """Returns the next default stack name, e.g. 'Stack 1', 'Stack 2', avoiding conflicts."""
    projects = get_all_projects()
    names = {p["name"].strip().lower() for p in projects}
    idx = 1
    while f"stack {idx}" in names:
        idx += 1
    return f"Stack {idx}"

def get_project_note_colors(project_id: str, limit: int = 3) -> List[str]:
    """Returns the background colors of the most recent notes in a project stack."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT color_hex FROM notes WHERE project_id = ? ORDER BY updated_at DESC LIMIT ?",
            (project_id, limit)
        )
        return [row["color_hex"] for row in cursor.fetchall() if row["color_hex"]]

def get_project_notes_preview(project_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Returns title and preview info of recent notes in a project stack."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content, color_hex FROM notes WHERE project_id = ? ORDER BY updated_at DESC LIMIT ?",
            (project_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]

def dissolve_project_stack(project_id: str) -> bool:
    """Reassigns all notes in project to 'default' (free notes) and deletes the project."""
    return delete_project(project_id, reassign_to_id="default")

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

SORT_MODES = {
    "created_desc": "created_at DESC",
    "created_asc": "created_at ASC",
    "updated_desc": "updated_at DESC",
    "updated_asc": "updated_at ASC",
    "title_asc": "title COLLATE NOCASE ASC",
}

def get_sort_preference() -> str:
    """Retrieves user sort preference from preferences or returns 'created_desc'."""
    pref_file = get_preferences_path()
    if pref_file.exists():
        try:
            import json
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                mode = data.get("sort_mode", "created_desc")
                if mode in SORT_MODES:
                    return mode
        except Exception:
            pass
    return "created_desc"

def set_sort_preference(sort_mode: str) -> None:
    """Saves user sort preference to preferences."""
    if sort_mode not in SORT_MODES:
        sort_mode = "created_desc"
    pref_file = get_preferences_path()
    data = {}
    if pref_file.exists():
        try:
            import json
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["sort_mode"] = sort_mode
    try:
        import json
        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

QUERIES_BY_PROJECT = {
    "created_desc": "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at DESC",
    "created_asc": "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at ASC",
    "updated_desc": "SELECT * FROM notes WHERE project_id = ? ORDER BY updated_at DESC",
    "updated_asc": "SELECT * FROM notes WHERE project_id = ? ORDER BY updated_at ASC",
    "title_asc": "SELECT * FROM notes WHERE project_id = ? ORDER BY title COLLATE NOCASE ASC",
}

QUERIES_ALL = {
    "created_desc": "SELECT * FROM notes ORDER BY created_at DESC",
    "created_asc": "SELECT * FROM notes ORDER BY created_at ASC",
    "updated_desc": "SELECT * FROM notes ORDER BY updated_at DESC",
    "updated_asc": "SELECT * FROM notes ORDER BY updated_at ASC",
    "title_asc": "SELECT * FROM notes ORDER BY title COLLATE NOCASE ASC",
}

def get_all_notes(project_id: Optional[str] = None, sort_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches all notes, optionally filtered by project stack and sorted by the specified mode."""
    mode = sort_by if sort_by in SORT_MODES else get_sort_preference()
    if mode not in SORT_MODES:
        mode = "created_desc"
    with get_connection() as conn:
        cursor = conn.cursor()
        if project_id and project_id != "all":
            cursor.execute(QUERIES_BY_PROJECT[mode], (project_id,))
        else:
            cursor.execute(QUERIES_ALL[mode])
        return [dict(row) for row in cursor.fetchall()]

def get_note(note_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single note by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_note(title: str = "Untitled Note", content: str = "", color_hex: str = "#FFF9C4", project_id: Optional[str] = None, tags: Optional[List[str]] = None) -> str:
    """Creates a new note assigned to a project stack and returns its ID."""
    note_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    pid = project_id or get_active_project_id()
    if pid == "all":
        pid = "default"
    tags_json = json.dumps(tags or [])
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (id, title, content, color_hex, project_id, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (note_id, title, content, color_hex, pid, tags_json, now, now))
        conn.commit()
    return note_id

def update_note(note_id: str, title: Optional[str] = None, content: Optional[str] = None, color_hex: Optional[str] = None, project_id: Optional[str] = None, tags: Optional[List[str]] = None) -> None:
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
    if tags is not None:
        updates.append("tags = ?")
        params.append(json.dumps(tags))
        
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
    tags_list = []
    if existing.get("tags"):
        try:
            tags_list = json.loads(existing["tags"]) if isinstance(existing["tags"], str) else existing["tags"]
        except Exception:
            tags_list = []
    return create_note(
        title=new_title,
        content=existing["content"],
        color_hex=existing["color_hex"],
        project_id=existing.get("project_id", "default"),
        tags=tags_list
    )

def delete_multiple_notes(note_ids: List[str]) -> None:
    """Deletes a list of notes by IDs in a single transaction."""
    if not note_ids:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("DELETE FROM notes WHERE id = ?", [(nid,) for nid in note_ids])
        conn.commit()


# --- Tag Management Subsystem ---

PREDETERMINED_TAGS = [
    {"id": "urgent", "key": "tag_urgent", "default_name": "Urgent", "color_hex": "#EF4444"},
    {"id": "todo", "key": "tag_todo", "default_name": "To-Do", "color_hex": "#F59E0B"},
    {"id": "work", "key": "tag_work", "default_name": "Work", "color_hex": "#3B82F6"},
    {"id": "personal", "key": "tag_personal", "default_name": "Personal", "color_hex": "#10B981"},
    {"id": "ideas", "key": "tag_ideas", "default_name": "Ideas", "color_hex": "#8B5CF6"},
]

def get_custom_tags() -> List[Dict[str, Any]]:
    """Fetches all custom tags created by the user, ordered by creation date."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM custom_tags ORDER BY created_at ASC")
        return [dict(row) for row in cursor.fetchall()]

def create_custom_tag(name: str, color_hex: str = "#8AB4F8") -> Optional[Dict[str, Any]]:
    """Creates a new custom tag if not already existing."""
    clean_name = name.strip()
    if not clean_name:
        return None
    now = datetime.now().isoformat()
    tag_id = str(uuid.uuid4())
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO custom_tags (id, name, color_hex, created_at)
                VALUES (?, ?, ?, ?)
            """, (tag_id, clean_name, color_hex, now))
            conn.commit()
            return {"id": tag_id, "name": clean_name, "color_hex": color_hex, "created_at": now}
        except sqlite3.IntegrityError:
            return None

def delete_custom_tag(name: str) -> None:
    """Deletes a custom tag and removes it from all assigned notes."""
    clean_name = name.strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM custom_tags WHERE name = ?", (clean_name,))
        cursor.execute("SELECT id, tags FROM notes WHERE tags LIKE ?", (f'%"{clean_name}"%',))
        for row in cursor.fetchall():
            try:
                tags = json.loads(row["tags"]) if row["tags"] else []
                if clean_name in tags:
                    tags.remove(clean_name)
                    cursor.execute("UPDATE notes SET tags = ? WHERE id = ?", (json.dumps(tags), row["id"]))
            except Exception:
                pass
        conn.commit()

def rename_custom_tag(old_name: str, new_name: str) -> bool:
    """Renames a custom tag and updates it on all assigned notes."""
    old_clean = old_name.strip()
    new_clean = new_name.strip()
    if not old_clean or not new_clean or old_clean == new_clean:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE custom_tags SET name = ? WHERE name = ?", (new_clean, old_clean))
            cursor.execute("SELECT id, tags FROM notes WHERE tags LIKE ?", (f'%"{old_clean}"%',))
            for row in cursor.fetchall():
                try:
                    tags = json.loads(row["tags"]) if row["tags"] else []
                    if old_clean in tags:
                        tags = [new_clean if t == old_clean else t for t in tags]
                        cursor.execute("UPDATE notes SET tags = ? WHERE id = ?", (json.dumps(tags), row["id"]))
                except Exception:
                    pass
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_note_tags(note_id: str) -> List[str]:
    """Returns the list of assigned tag names for a note."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tags FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if row and row["tags"]:
            try:
                parsed = json.loads(row["tags"])
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
    return []

def set_note_tags(note_id: str, tags: List[str]) -> None:
    """Updates the list of tags for a given note."""
    clean_tags = [t.strip() for t in tags if t.strip()]
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET tags = ?, updated_at = ? WHERE id = ?", (json.dumps(clean_tags), now, note_id))
        conn.commit()

def get_all_tag_counts() -> Dict[str, int]:
    """Returns a dictionary mapping tag names to note counts."""
    counts: Dict[str, int] = {}
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tags FROM notes WHERE tags IS NOT NULL AND tags != '[]'")
        for row in cursor.fetchall():
            try:
                t_list = json.loads(row["tags"])
                if isinstance(t_list, list):
                    for t in t_list:
                        counts[t] = counts.get(t, 0) + 1
            except Exception:
                pass
    return counts


# --- User Dictionary (Spell Check Proofing) ---

def add_dictionary_word(word: str, language: str = 'en') -> bool:
    """Adds a custom user word to the personal dictionary."""
    clean_word = word.strip().lower()
    if not clean_word:
        return False
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO user_dictionary (word, language, created_at)
            VALUES (?, ?, ?)
        """, (clean_word, language.lower(), now))
        conn.commit()
        return cursor.rowcount > 0

def remove_dictionary_word(word: str) -> bool:
    """Removes a custom word from the personal dictionary."""
    clean_word = word.strip().lower()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_dictionary WHERE word = ?", (clean_word,))
        conn.commit()
        return cursor.rowcount > 0

def get_dictionary_words(language: Optional[str] = None) -> List[str]:
    """Retrieves all custom dictionary words, optionally filtered by language."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if language:
            cursor.execute("SELECT word FROM user_dictionary WHERE language = ? ORDER BY word ASC", (language.lower(),))
        else:
            cursor.execute("SELECT word FROM user_dictionary ORDER BY word ASC")
        return [row["word"] for row in cursor.fetchall()]
