"""
A2A Server 1 — Calculator Agent  (port 9000)
=============================================
Exposes a Strands calculator agent via the A2A protocol.

Advanced pattern: uses FastAPI lifespan so you can hook startup/shutdown
logic (DB connections, warm-up calls, metrics, etc.) without subclassing.

Run: python server.py
"""

import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import uvicorn
from strands import Agent
from strands.multiagent.a2a import A2AServer
from strands_tools import calculator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Agent ──────────────────────────────────────────────────────────────────────

agent = Agent(
    name="Calculator Agent",
    description="A specialized agent for arithmetic and mathematical calculations.",
    model="us.anthropic.claude-sonnet-4-20250514-v1:0",
    tools=[calculator],
    callback_handler=None,
)

# ── A2A server ─────────────────────────────────────────────────────────────────

a2a_server = A2AServer(
    agent=agent,
    host="127.0.0.1",
    port=9000,
)

# ── FastAPI lifespan ───────────────────────────────────────────────────────────
# to_fastapi_app() returns a real FastAPI app — you can add middleware,
# custom routes, or any FastAPI config via app_kwargs.

@asynccontextmanager
async def lifespan(app):
    """Log startup/shutdown. Replace with real init logic (DB, cache, etc.)."""
    logger.info("Calculator A2A server STARTED on http://127.0.0.1:9000")
    logger.info("  Agent card : http://127.0.0.1:9000/.well-known/agent.json")
    logger.info("  Invoke     : POST http://127.0.0.1:9000/")
    yield
    logger.info("Calculator A2A server STOPPED.")


fastapi_app = a2a_server.to_fastapi_app(app_kwargs={"lifespan": lifespan})

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="127.0.0.1", port=9000)
