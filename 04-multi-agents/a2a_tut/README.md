# A2A (Agent-to-Agent) Tutorial

Hands-on walkthrough of the Strands A2A protocol — from a single remote agent to a full multi-agent orchestration system.

---

## What is A2A?

The Agent-to-Agent protocol is an open standard for AI agents to **discover, communicate, and collaborate** across platforms. Any A2A-compatible agent — regardless of which framework built it — can talk to any other.

Strands exposes this via:
- `A2AServer` — wraps a Strands agent behind an HTTP endpoint
- `A2AAgent` — client that calls a remote A2A server like a local agent
- `A2AClientToolProvider` — auto-discovers remote agents and injects them as tools

---

## Files

| File | Role | Port |
|---|---|---|
| `server.py` | **Calculator Agent** — remote math specialist | `:9000` |
| `server2.py` | **Text Analyst Agent** — remote text statistics specialist | `:9001` |
| `client.py` | All client invocation patterns (high-level + low-level raw SDK) | — |
| `app.py` | **Orchestrator** — local LLM using both remote agents + a local tool | — |
| `dynamic_discovery.py` | Auto-discovers agents from their cards, no manual tool wrappers | — |
| `run_demo.py` | Starts both servers and runs all demos in sequence | — |

---

## Prerequisites

```bash
# Core A2A support
pip install 'strands-agents[a2a]'

# For dynamic_discovery.py only
pip install 'strands-agents-tools[a2a_client]'
```

`.env` must exist at the repo root with your AWS credentials.

---

## Quickstart

```bash
# Run everything in one command
python run_demo.py

# Skip dynamic discovery if the extra isn't installed
python run_demo.py --skip-dynamic
```

Or run manually in separate terminals:

```bash
# Terminal 1
python server.py

# Terminal 2
python server2.py

# Terminal 3 — pick one
python client.py            # raw A2A client patterns
python app.py               # multi-agent orchestrator
python dynamic_discovery.py # auto-discovered tools
```

---

## Architecture

### The two servers

```
server.py  (Calculator Agent — port :9000)
  tools: strands_tools.calculator
  FastAPI lifespan for startup/shutdown hooks

server2.py (Text Analyst Agent — port :9001)
  tools: word_count, text_stats, find_longest_word, count_vowels
  FastAPI lifespan for startup/shutdown hooks
```

Each server exposes:
- `GET  /.well-known/agent.json` — agent card (name, description, skills)
- `POST /` — invoke the agent (sync or streaming)

---

### client.py — all invocation patterns

Targets the Calculator Agent on `:9000`.

```
HIGH-LEVEL: A2AAgent  (recommended)
  sync        → agent("question")
  async       → await agent.invoke_async("question")
  streaming   → async for event in agent.stream_async("question")
  agent card  → await agent.get_agent_card()

LOW-LEVEL: raw a2a.client SDK  (when you need full control)
  1. A2ACardResolver  → fetch agent card
  2. ClientFactory    → build HTTP client
  3. Message/TextPart → construct typed protocol message
  4. client.send_message → iterate raw events
```

Flow:
```
client.py ──A2A HTTP──> server.py ──Bedrock LLM──> answer
```

---

### app.py — multi-agent orchestrator

A local Strands `Agent` (the orchestrator) with three tools:

| Tool | Type | Delegates to |
|---|---|---|
| `calculate` | remote | Calculator Agent `:9000` via A2A |
| `analyze_text` | remote | Text Analyst Agent `:9001` via A2A |
| `get_current_time` | local | Python `datetime`, no remote call |

The orchestrator LLM decides which tool(s) to call and chains them for compound questions.

Flow:
```
[User question]
      │
      ▼
Orchestrator LLM  (local Bedrock call)
      ├── calculate    ──A2A──> :9000 ──Bedrock──> math result
      ├── analyze_text ──A2A──> :9001 ──Bedrock──> text stats
      └── get_time     ──local──────────────────> timestamp
      │
      ▼
Orchestrator formats and returns final answer
```

---

### dynamic_discovery.py — auto-discovered tools

Instead of manually writing a `@tool` wrapper for each remote agent, `A2AClientToolProvider` fetches agent cards at startup and builds tools automatically.

```python
provider = A2AClientToolProvider(known_agent_urls=[
    "http://127.0.0.1:9000",
    "http://127.0.0.1:9001",
])
agent = Agent(tools=provider.tools)  # tools auto-injected from cards
```

Use this when:
- You don't know agent skills at coding time
- You want to add/remove agents without changing code
- You're building an agent registry or marketplace

---

## Key concepts

**`A2AAgent` vs raw `a2a.client`**

`A2AAgent` is the high-level wrapper — it handles card resolution, HTTP client setup, message construction, and response parsing automatically. The raw `a2a.client` SDK gives you full control over each step, useful when you need custom auth headers, connection pooling, or want to inspect raw protocol events.

**Why two servers?**

A real multi-agent system has many specialized agents. Having two servers demonstrates that:
1. The orchestrator can route different query types to different experts
2. Agents are independent — they can be on different machines, built with different frameworks
3. The A2A protocol is the common language between them

**FastAPI lifespan**

Both servers use `to_fastapi_app(app_kwargs={"lifespan": ...})` instead of `serve()`. This is the production pattern — the lifespan context manager is the right place for DB connections, cache warm-up, metrics registration, and graceful shutdown logic.

---

## What the demo runner shows

```
STEP 1 — Start both servers (wait for health check)
STEP 2 — client.py  : high-level + low-level client patterns vs :9000
STEP 3 — app.py     : orchestrator with 2 remote + 1 local tool
STEP 4 — dynamic_discovery.py : auto-discovered tools from both agent cards
CLEANUP — terminate both servers, print summary
```
