# 02 - Chatbot: Interactive Multi-Turn (Local)

An interactive terminal chatbot that maintains conversation context across turns. Supports both streaming and non-streaming response modes.

## What You'll Learn

- Multi-turn conversations (agent reuse preserves `self.messages`)
- Streaming vs non-streaming `BedrockModel` configuration
- Custom callback handlers for real-time token display
- Building an interactive chat loop

## Run

```bash
# Streaming mode (default) — tokens appear in real-time
python 02-chatbot/chatbot.py

# Non-streaming mode — full response arrives at once
python 02-chatbot/chatbot.py --no-stream
```

Type `exit`, `quit`, or `bye` to end the session.

## Key Concepts

| Concept | Detail |
|---------|--------|
| **Multi-turn** | Same `Agent` instance reused across turns — conversation history auto-accumulates in `agent.messages` |
| **Streaming** | `streaming=True` on `BedrockModel` — tokens arrive one by one via callback |
| **Non-streaming** | `streaming=False` — full response at once (useful for models without streaming tool use, e.g., Llama) |
| **Callback handler** | Custom function receiving `data` (text chunks) and `current_tool_use` (tool invocations) |

## Streaming vs Non-Streaming

Both are **BedrockModel configurations**, not Python async patterns:

| Mode | Flag | Behavior |
|------|------|----------|
| **Streaming** (default) | `python chatbot.py` | Tokens appear one by one as generated |
| **Non-streaming** | `python chatbot.py --no-stream` | Full response arrives at once |

Both modes use the same callback handler internally — Strands converts non-streaming responses to the same event format.

## Files

- `chatbot.py` — Interactive chatbot with streaming support
