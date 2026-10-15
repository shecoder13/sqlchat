"""CLI chat loop for the SQL chatbot.

Run:  python main.py
Commands: /new (fresh conversation), /help, /quit
"""
import os
import sys
import uuid
from pathlib import Path

from langchain_core.messages import AIMessageChunk

import db
from agent import build_agent

THREAD_FILE = Path(__file__).with_name(".last_thread")

HELP = """Ask anything about the parts inventory, for example:
  Which brake parts are out of stock?
  Show Hyundai Creta parts under ₹3000
  ...now only the ones from Bosch India          <- follow-ups use memory
Commands:  /new  start a fresh conversation   /help  this text   /quit  exit"""


def new_thread() -> str:
    thread_id = f"chat-{uuid.uuid4().hex[:8]}"
    THREAD_FILE.write_text(thread_id)
    return thread_id


def load_thread() -> str:
    """Reuse the last conversation so memory survives restarts."""
    if THREAD_FILE.exists():
        saved = THREAD_FILE.read_text().strip()
        if saved:
            return saved
    return new_thread()


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def ask(agent, thread_id: str, question: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [{"role": "user", "content": question}]}
    for chunk, _metadata in agent.stream(inputs, config, stream_mode="messages"):
        if not isinstance(chunk, AIMessageChunk):
            continue  # skip tool results and the echoed user message
        for call in chunk.tool_call_chunks:
            if call.get("name"):
                print(f"\n  [tool] {call['name']}", flush=True)
        text = _text(chunk.content)
        if text:
            print(text, end="", flush=True)
    print()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # so ₹ prints on Windows consoles

    if not db.db_path().exists():
        sys.exit(f"Database not found at {db.db_path()}. Run `python seed_db.py` first.")

    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key == "your-key-here":
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    agent = build_agent()

    thread_id = load_thread()
    print(f"SQL chatbot ready (conversation {thread_id}). Type /help for tips.\n")

    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue
        if question in ("/quit", "/exit"):
            break
        if question == "/help":
            print(HELP)
            continue
        if question == "/new":
            thread_id = new_thread()
            print(f"Started a fresh conversation ({thread_id}).")
            continue

        print("bot> ", end="", flush=True)
        try:
            ask(agent, thread_id, question)
        except Exception as exc:  # keep the loop alive on API or network errors
            print(f"\n[error] {type(exc).__name__}: {exc}")
        print()


if __name__ == "__main__":
    main()
