# sqlchat

Chat with an SQLite auto-parts inventory in plain English. A LangChain agent
inspects the schema, writes SQL, runs it read-only and explains the result.
Follow-ups like "now only the ones under ₹500" work because the conversation
is stored per thread in `chat_memory.db`, so it also survives restarts.

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then paste your ANTHROPIC_API_KEY into .env
python seed_db.py           # builds inventory.db with sample data
python main.py
```

## Using it

Commands: `/new` starts a fresh conversation, `/help` shows tips, `/quit` exits.
The bot prints a `[tool]` line each time the agent calls a tool, so you can
watch the loop: list tables, describe, query, answer.

Try:
- Which brake parts are out of stock?
- Show Hyundai Creta parts under ₹3000
- Now only the ones from Bosch India
- Which supplier has the most stock value?

## Files

| File | Purpose |
| --- | --- |
| `seed_db.py` | Builds `inventory.db` (suppliers, vehicles, parts, fitment, stock) |
| `db.py` | Read-only connection, SELECT-only guard, 50-row cap |
| `tools.py` | `list_tables`, `describe_table`, `run_query` |
| `agent.py` | Model, system prompt, SQLite checkpointer, agent graph |
| `main.py` | CLI loop with streaming and `/new`, `/help`, `/quit` |

## Safety

The database opens in read-only mode, only a single `SELECT` or `WITH` query
passes validation, and results are capped at 50 rows. Errors go back to the
agent as text so it can fix its SQL and retry.

## Your own database

Add `DB_PATH=C:\path\to\your.db` to `.env`. The agent discovers tables and
columns itself; you may want to adjust the prices and currency line in the
system prompt in `agent.py`.

## Troubleshooting

- `greenlet` fails to build: use Python 3.12 (for example
  `conda create -n sqlchat python=3.12`), or run
  `pip install --only-binary=:all: --upgrade greenlet` first.
- `ImportError` on `create_agent`: harmless; `agent.py` falls back to
  LangGraph's `create_react_agent` automatically.
- Weird characters instead of ₹: run `chcp 65001` in the console first.
