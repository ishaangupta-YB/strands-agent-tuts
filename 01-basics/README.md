# 01 - Basics: One-Shot Agent

A simple one-shot Strands agent that demonstrates the fundamentals — tools, model configuration, and a single agent invocation.

## What You'll Learn

- Creating a Strands `Agent` with `BedrockModel`
- Defining custom tools with `@tool` decorator
- Using built-in tools (`calculator`, `current_time`)
- Configuring boto client (retries, timeouts)
- Running a one-shot agent call (no conversation memory)

## Run

```bash
# From repo root
python 01-basics/agent.py
```

The script sends a single multi-part request asking the agent to:
1. Get the current time
2. Calculate `3111696 / 74088`
3. Count the letter R's in "strawberry"

## Key Concepts

| Concept | Detail |
|---------|--------|
| **Agent** | `strands.Agent` — orchestrates model + tools |
| **Model** | `BedrockModel` with Claude Sonnet on Bedrock |
| **Tools** | `calculator`, `current_time`, custom `letter_counter` |
| **Mode** | One-shot — single `agent(message)` call, no memory |

## Files

- `agent.py` — Complete one-shot agent demo
