"""Model, system prompt, persistent memory and the agent graph."""
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.sqlite import SqliteSaver

from tools import TOOLS

load_dotenv(Path(__file__).with_name(".env"))

MEMORY_DB = Path(__file__).with_name("chat_memory.db")

SYSTEM_PROMPT = """You are a careful data analyst answering questions about an auto-parts inventory stored in SQLite.

How to work:
1. If you don't know the schema, call list_tables, then describe_table for each table you need. Never guess column names.
2. Write one read-only SELECT and run it with run_query. Prefer a JOIN over several separate queries, and use LIMIT on large results.
3. If a query returns an error, read it, fix the SQL and retry. After 3 failed attempts, stop and explain what went wrong.
4. Answer in plain English using the actual rows. Prices are in Indian rupees; write them like ₹1,200.
5. This conversation has memory. Resolve follow-ups such as "only the cheap ones" or "what about Honda?" from the earlier questions and the SQL you already ran.
6. You cannot modify data. If asked to, say so.
7. If the database can't answer a question, say what is missing instead of inventing data."""

# LangChain 1.x provides create_agent; older versions use LangGraph's prebuilt agent.
try:
    from langchain.agents import create_agent

    def _build(model, tools, prompt, checkpointer):
        return create_agent(model, tools, system_prompt=prompt, checkpointer=checkpointer)

except ImportError:
    from langgraph.prebuilt import create_react_agent

    def _build(model, tools, prompt, checkpointer):
        return create_react_agent(model, tools, prompt=prompt, checkpointer=checkpointer)


def build_agent():
    model = ChatAnthropic(model=os.getenv("MODEL_NAME", "claude-sonnet-5-5"))
    # check_same_thread=False because LangGraph may touch the connection from worker threads.
    checkpointer = SqliteSaver(sqlite3.connect(MEMORY_DB, check_same_thread=False))
    return _build(model, TOOLS, SYSTEM_PROMPT, checkpointer)
