# Project Context

This is a hands-on learning repo for **AWS Strands Agents SDK** + **Amazon Bedrock AgentCore** deployment.

## Repo Structure

- `01-basics/agent.py` — One-shot agent demo (local, beginner)
- `02-chatbot/chatbot.py` — Interactive multi-turn chatbot (local, streaming/non-streaming)
- `03-agentcore-deploy/agentcore_app.py` — Production chatbot deployed to AgentCore (multi-turn sessions + Tavily web search)
- `03-agentcore-deploy/chat.sh` — Terminal chat wrapper for `agentcore invoke`
- `docs/agentcore-reference.md` — AgentCore deployment reference documentation
- `requirements.txt` — Shared dependencies (root level)
- `.env` — AWS credentials + TAVILY_API_KEY (gitignored)

## Key Patterns

- **Multi-turn memory**: Strands `Agent` auto-maintains `self.messages` across calls. Reuse same agent instance = conversation memory.
- **Session management** (AgentCore): `agents_by_session = {}` dict keyed by `BedrockAgentCoreContext.get_session_id()`. Each session gets its own agent instance.
- **AgentCore session IDs**: Must be **33+ characters** (e.g., UUID-based). Short IDs will fail with validation error.
- **load_dotenv paths**: Scripts in subfolders use `Path(__file__).resolve().parent.parent / ".env"` to find root `.env`.
- **Model**: All examples use `us.anthropic.claude-sonnet-4-20250514-v1:0` on Bedrock (`us-east-1`).

## Deployment Workflow

```bash
# Configure (first time or after moving entrypoint)
agentcore configure --entrypoint 03-agentcore-deploy/agentcore_app.py

# Local dev
agentcore dev

# Deploy to cloud
agentcore deploy --env TAVILY_API_KEY=$TAVILY_API_KEY

# Chat
./03-agentcore-deploy/chat.sh          # cloud
./03-agentcore-deploy/chat.sh --dev    # local
```

## Common Issues

- **Session ID too short**: AgentCore requires `runtimeSessionId` >= 33 chars. Use UUID-based IDs.
- **`.env` not found**: Scripts in subfolders resolve `.env` relative to `__file__`, not `cwd`. Always keep `.env` at repo root.
- **`.bedrock_agentcore.yaml` missing**: Gitignored. Regenerate with `agentcore configure`.
