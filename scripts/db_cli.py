#!/usr/bin/env python3
"""
db_cli.py - Token-efficient database CLI for agents and automation scripts.
Provides compact JSON outputs for inspecting and managing notes without wasting tokens.
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database
from media_manager import get_attachments_dir


def print_json(data, pretty=False):
    """Outputs data as JSON. Compact by default to conserve tokens."""
    if pretty:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, separators=(",", ":"), ensure_ascii=False))


def cmd_stats(args):
    """Returns database summary statistics."""
    database.init_db()
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM notes")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT color_hex, COUNT(*) as count FROM notes GROUP BY color_hex")
        colors = {row["color_hex"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT MAX(updated_at) as last_updated FROM notes")
        row = cursor.fetchone()
        last_updated = row["last_updated"] if row else None

    # Attachments directory stats
    attach_dir = get_attachments_dir()
    attach_count = 0
    attach_bytes = 0
    if attach_dir.exists():
        for f in attach_dir.iterdir():
            if f.is_file():
                attach_count += 1
                attach_bytes += f.stat().st_size

    stats = {
        "status": "ok",
        "total_notes": total,
        "colors": colors,
        "last_updated": last_updated,
        "attachments": {
            "count": attach_count,
            "total_bytes": attach_bytes,
            "dir": str(attach_dir)
        }
    }
    print_json(stats, args.pretty)


def cmd_list(args):
    """Lists notes in token-efficient compact format."""
    database.init_db()
    notes = database.get_all_notes()
    limit = args.limit if args.limit and args.limit > 0 else len(notes)
    
    result = []
    for n in notes[:limit]:
        item = {
            "id": n["id"],
            "title": n["title"],
            "color_hex": n["color_hex"],
            "updated_at": n["updated_at"]
        }
        if args.full:
            item["content"] = n["content"]
            item["created_at"] = n["created_at"]
        else:
            # Provide snippet and length to conserve tokens
            content = n.get("content", "")
            snippet = content[:80].replace("\n", " ") + ("..." if len(content) > 80 else "")
            item["snippet"] = snippet
            item["content_len"] = len(content)
        result.append(item)

    print_json({"status": "ok", "count": len(result), "total": len(notes), "notes": result}, args.pretty)


def cmd_get(args):
    """Retrieves full content of a single note by ID."""
    database.init_db()
    note = database.get_note(args.id)
    if not note:
        print_json({"status": "error", "message": f"Note with ID '{args.id}' not found"}, args.pretty)
        sys.exit(1)
    print_json({"status": "ok", "note": note}, args.pretty)


def cmd_create(args):
    """Creates a new note."""
    database.init_db()
    color = args.color if args.color else "#FFF9C4"
    note_id = database.create_note(title=args.title, content=args.content, color_hex=color)
    print_json({"status": "ok", "action": "created", "id": note_id}, args.pretty)


def cmd_delete(args):
    """Deletes a note by ID."""
    database.init_db()
    existing = database.get_note(args.id)
    if not existing:
        print_json({"status": "error", "message": f"Note with ID '{args.id}' not found"}, args.pretty)
        sys.exit(1)
    database.delete_note(args.id)
    print_json({"status": "ok", "action": "deleted", "id": args.id}, args.pretty)


def main():
    parser = argparse.ArgumentParser(description="Token-efficient Sticky Notes Database CLI for AI Agents")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output with indentation")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # stats
    subparsers.add_parser("stats", help="Get summary database and storage statistics")

    # list
    list_p = subparsers.add_parser("list", help="List notes in compact format")
    list_p.add_argument("--limit", type=int, default=10, help="Maximum notes to return (default: 10)")
    list_p.add_argument("--full", action="store_true", help="Include full content in list (uses more tokens)")

    # get
    get_p = subparsers.add_parser("get", help="Get a single note by ID")
    get_p.add_argument("id", help="UUID of note to fetch")

    # create
    create_p = subparsers.add_parser("create", help="Create a new note")
    create_p.add_argument("--title", default="Untitled Note", help="Note title")
    create_p.add_argument("--content", default="", help="Note markdown content")
    create_p.add_argument("--color", default="#FFF9C4", help="Hex color code (default #FFF9C4)")

    # delete
    del_p = subparsers.add_parser("delete", help="Delete a note by ID")
    del_p.add_argument("id", help="UUID of note to delete")

    args = parser.parse_args()

    if args.command == "stats":
        cmd_stats(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "get":
        cmd_get(args)
    elif args.command == "create":
        cmd_create(args)
    elif args.command == "delete":
        cmd_delete(args)


if __name__ == "__main__":
    main()
