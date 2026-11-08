"""Print today's open Google Tasks via direct API access (no MCP)."""

import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

from google_auth import SCOPES, get_credentials

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_todo_list_title(title):
    """True if a tasklist title normalizes (lowercased, spaces and hyphens
    stripped) to contain "todo" -- catches "TODOs", "To-Do List", "to do",
    etc. without hardcoding one exact list name.
    """
    normalized = title.lower().replace(" ", "").replace("-", "")
    return "todo" in normalized


def parse_tasks(items):
    """Extract {title, due} from raw Tasks API task resources.

    `due`, when present, is the Tasks API's RFC3339 due timestamp (always
    a date-only value, time component fixed at T00:00:00.000Z) parsed
    down to a plain `date`; `None` if the task has no due date set.
    """
    tasks = []
    for item in items:
        title = item.get("title", "(no title)")
        due_raw = item.get("due")
        due = (
            datetime.fromisoformat(due_raw.replace("Z", "+00:00")).date()
            if due_raw
            else None
        )
        tasks.append({"title": title, "due": due})
    return tasks


def format_tasks_summary(tasks, today=None):
    """Render the Tasks block.

    Three mutually exclusive cases, checked in this order:
      1. Any task due today or overdue (due <= today) -- bullet list, one
         task per line; an overdue task's line explicitly states its
         original due date and the word "overdue".
      2. Else, any open task with no due date at all -- one line
         reporting how many.
      3. Else -- a fixed "all clear" line.

    A task with a future due date (due > today) belongs to none of the
    three cases -- excluded from the bullet list and from the dateless
    "N open items" count, since it isn't today's business either way.
    """
    today = today or date.today()

    due_today_or_overdue = [t for t in tasks if t["due"] is not None and t["due"] <= today]
    dateless = [t for t in tasks if t["due"] is None]

    if due_today_or_overdue:
        lines = []
        for t in sorted(due_today_or_overdue, key=lambda t: t["due"]):
            if t["due"] < today:
                lines.append(f"- {t['title']} (due {t['due'].isoformat()}, overdue)")
            else:
                lines.append(f"- {t['title']}")
        return "\n".join(lines)

    if dateless:
        count = len(dateless)
        item_word = "item" if count == 1 else "items"
        return (
            f"No tasks today. You still have {count} open {item_word} "
            "on your to-do list — it's a good day to tick them off!"
        )

    return "No tasks today. Your to-do list is clear!"


def fetch_tasks():
    creds = get_credentials(SCOPES)
    service = build("tasks", "v1", credentials=creds)

    tasklists = service.tasklists().list().execute().get("items", [])
    matching_list_ids = [tl["id"] for tl in tasklists if is_todo_list_title(tl.get("title", ""))]

    items = []
    for list_id in matching_list_ids:
        result = service.tasks().list(tasklist=list_id, showCompleted=False).execute()
        items.extend(result.get("items", []))
    return items


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv(PROJECT_ROOT / ".env")

    try:
        items = fetch_tasks()
    except Exception as exc:
        print(f"Error: could not fetch Google Tasks ({exc})", file=sys.stderr)
        sys.exit(1)

    print(format_tasks_summary(parse_tasks(items)))


if __name__ == "__main__":
    main()
