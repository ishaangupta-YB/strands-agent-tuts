# Swarm Multi-Agent Tutorial

Hands-on walkthrough of the Strands **Swarm** pattern — a network of peer agents
that hand off control to each other to collaboratively solve a task.

---

## What is a Swarm?

A Swarm is a set of agents connected as **peers**. Instead of a central orchestrator
deciding who does what, each agent decides for itself whether to keep working or hand
off to a more appropriate agent. Handoffs happen via a special `handoff_to_agent` tool
that the `Swarm` class automatically injects into every agent.

### Comparison with other multi-agent patterns

| Pattern | Who decides routing? | Communication | Topology |
|---|---|---|---|
| A2A orchestrator | Central LLM (orchestrator) | HTTP between processes | Hub + spoke |
| Agents as tools | Outer agent calls inner agents as tools | In-process function calls | Hierarchical |
| **Swarm** | **Each agent decides** | In-process handoff tool | **Flat peer network** |

---

## Architecture

```
[Task]
   │
   ▼
researcher ──handoff──> architect ──handoff──> coder ──handoff──> reviewer
    ^                       │                    │                    │
    └─── (if unclear) ──────┘                    └──── (revision) ────┘
                            ^
                            └────────────── (design flaw) ────────────
```

Any agent can hand off to any other. The `Swarm` class tracks history and enforces
safety limits (max handoffs, timeouts, loop detection).

---

## Files

| File | Role |
|---|---|
| `agents.py` | Defines 4 specialized agents with rich system prompts |
| `swarm.py` | Creates the Swarm, runs the sample task, displays results |

No extra `requirements.txt` needed — root `requirements.txt` already covers all deps.

---

## Quickstart

```bash
# From repo root
python 04-multi-agents/swarm-tut/swarm.py
```

No servers to start. No extra installs. The entire Swarm runs in a **single process**.

---

## What happens when you run it

1. The task is passed to the **researcher**, who clarifies scope and produces a
   structured requirements document (Entities, Core Operations, Constraints, API Style).
2. Researcher calls `handoff_to_agent(agent_name="architect", ...)`.
3. The **architect** designs the API: data model, endpoints table, tech stack, ADR.
4. Architect calls `handoff_to_agent(agent_name="coder", ...)`.
5. The **coder** writes a complete, runnable FastAPI implementation.
6. Coder calls `handoff_to_agent(agent_name="reviewer", ...)`.
7. The **reviewer** inspects the code. If it needs changes → hands back to coder.
   If it's good → writes "APPROVED" and the Swarm ends.

Watch **stderr** for `[DEBUG] strands.multiagent` lines showing each handoff event.
Watch **stdout** for each agent's streaming token output as it thinks.

---

## SwarmResult fields

After `result = swarm(TASK)`:

| Field | Type | Meaning |
|---|---|---|
| `result.status` | `str` | `"complete"`, `"max_handoffs_reached"`, `"timeout"`, etc. |
| `result.execution_time` | `float` | Wall-clock seconds for the whole run |
| `result.execution_count` | `int` | Total LLM calls across all agents |
| `result.node_history` | `list[SwarmNode]` | Ordered list of agents that ran (`.node_id` = agent name) |
| `result.results` | `dict[str, result]` | Last output per agent name |
| `result.accumulated_usage` | `dict` | Aggregated token counts across all agents |

---

## Swarm safety parameters

| Parameter | Value in tutorial | Purpose |
|---|---|---|
| `max_handoffs` | 20 | Hard stop after N agent transfers |
| `max_iterations` | 20 | Hard stop after N total LLM calls |
| `execution_timeout` | 900.0 | Wall-clock timeout (15 min) |
| `node_timeout` | 300.0 | Per-agent timeout per turn (5 min) |
| `repetitive_handoff_detection_window` | 8 | Look-back window to detect A→B→A loops |
| `repetitive_handoff_min_unique_agents` | 3 | Min distinct agents required in window |

---

## Key concepts

**Why is `handoff_to_agent` auto-injected?**

Every agent in a Swarm needs it. Rather than requiring `tools=[handoff_to_agent]`
in every `Agent(...)` call, `Swarm` injects it at runtime. Agents defined outside
a Swarm (standalone) will not have this tool — which is correct behavior.

**What is `entry_point`?**

The first agent to receive the task. Omitting it uses the first agent in the list.
Explicit entry points make the flow self-documenting.

**What happens on a loop (A→B→A→B)?**

`repetitive_handoff_detection_window` watches the last N handoffs. If fewer than
`repetitive_handoff_min_unique_agents` distinct agents appear in that window, the
Swarm stops with `status="repetitive_handoffs_detected"`.

**Can I add tools to individual agents?**

Yes — add any `strands_tools` in `agents.py`. For example, give the researcher
`tavily` for real web search, or give the coder a code execution tool. The
`handoff_to_agent` tool is always added on top of whatever tools you specify.

**Can I run it asynchronously?**

Yes:
```python
import asyncio
result = asyncio.run(swarm.invoke_async(TASK))
```

**Can I stream events?**

Yes, using `swarm.stream_async`:
```python
async for event in swarm.stream_async(TASK):
    if event.get("type") == "multiagent_handoff":
        print(f"Handoff: {event['from_node_ids']} → {event['to_node_ids']}")
    elif event.get("type") == "multiagent_result":
        print(f"Done: {event['result'].status}")
```
