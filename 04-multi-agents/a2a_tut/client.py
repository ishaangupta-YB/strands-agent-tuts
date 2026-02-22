"""
A2A Client — all invocation patterns for a single remote agent.
===============================================================
Shows the difference between the high-level A2AAgent wrapper
and the low-level a2a SDK client (what A2AAgent does under the hood).

Make sure server.py is running before running this.
Usage: python client.py
"""

import asyncio
import logging
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from strands.agent.a2a_agent import A2AAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

SERVER_URL = "http://127.0.0.1:9000"

# ══════════════════════════════════════════════════════════════════════════════
#  HIGH-LEVEL: A2AAgent  (recommended for most use cases)
# ══════════════════════════════════════════════════════════════════════════════

def demo_sync():
    """Simple synchronous call — feels identical to a local Strands Agent."""
    print("\n=== [HIGH-LEVEL] Sync invocation ===")
    agent = A2AAgent(endpoint=SERVER_URL)
    result = agent("What is 42 * 13?")
    print("Response:", result.message)


async def demo_async():
    """Async invocation — useful in async web handlers."""
    print("\n=== [HIGH-LEVEL] Async invocation ===")
    agent = A2AAgent(endpoint=SERVER_URL)
    result = await agent.invoke_async("What is the square root of 256?")
    print("Response:", result.message)


async def demo_streaming():
    """Streaming — tokens printed as they arrive from the server."""
    print("\n=== [HIGH-LEVEL] Streaming invocation ===")
    agent = A2AAgent(endpoint=SERVER_URL)
    async for event in agent.stream_async("What is 2 to the power of 10?"):
        if "data" in event:
            print(event["data"], end="", flush=True)
    print()


async def demo_agent_card():
    """Fetch the remote agent's metadata (name, description, skills)."""
    print("\n=== [HIGH-LEVEL] Agent card (metadata discovery) ===")
    agent = A2AAgent(endpoint=SERVER_URL)
    card = await agent.get_agent_card()
    print(f"  Name       : {card.name}")
    print(f"  Description: {card.description}")
    print(f"  Skills     : {card.skills}")


# ══════════════════════════════════════════════════════════════════════════════
#  LOW-LEVEL: raw a2a.client SDK
#  This is exactly what A2AAgent does internally — useful when you need
#  full control over the HTTP client, timeouts, auth headers, etc.
# ══════════════════════════════════════════════════════════════════════════════

async def demo_low_level_client():
    """
    Manually drive the A2A protocol:
      1. Resolve agent card
      2. Configure HTTP client + factory
      3. Build a typed Message
      4. Send and parse raw events
    """
    from uuid import uuid4
    import httpx
    from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
    from a2a.types import Message, Part, Role, TextPart

    print("\n=== [LOW-LEVEL] Raw a2a.client SDK ===")

    async with httpx.AsyncClient(timeout=120) as http:

        # Step 1 — discover the agent
        resolver = A2ACardResolver(httpx_client=http, base_url=SERVER_URL)
        card = await resolver.get_agent_card()
        print(f"  Discovered: {card.name} — {card.description}")

        # Step 2 — build a client (non-streaming)
        config = ClientConfig(httpx_client=http, streaming=False)
        client = ClientFactory(config).create(card)

        # Step 3 — construct a typed protocol message
        msg = Message(
            kind="message",
            role=Role.user,
            parts=[Part(TextPart(kind="text", text="What is 99 * 99?"))],
            message_id=uuid4().hex,
        )

        # Step 4 — send and inspect raw events
        async for event in client.send_message(msg):
            print(f"  Event type : {type(event).__name__}")
            print(f"  Event      : {event}")


if __name__ == "__main__":
    demo_sync()
    asyncio.run(demo_async())
    asyncio.run(demo_streaming())
    asyncio.run(demo_agent_card())
    asyncio.run(demo_low_level_client())
