# 03 - AgentCore Deploy: Multi-Turn Chatbot with Web Search

A production-grade multi-turn chatbot deployed to **AWS Bedrock AgentCore**. Features session-based conversation memory and Tavily web search.

## What You'll Learn

- Deploying a Strands agent to AgentCore Runtime
- Session-based multi-turn memory (per-session agent instances)
- Using `BedrockAgentCoreContext.get_session_id()` for session tracking
- Adding web search (Tavily) to an agent
- Testing locally with `agentcore dev` and deploying to cloud

## Architecture

```
Terminal (chat.sh)
    |
    v
agentcore invoke --session-id <id> '{"prompt": "..."}'
    |
    v
AgentCore Runtime (cloud or local dev)
    |
    v
agentcore_app.py
    |-- session_id -> agents_by_session dict
    |-- Agent(tools=[tavily, calculator, current_time, letter_counter])
    |-- Reuses same Agent instance per session (preserves conversation history)
```

## Setup

```bash
# 1. Install dependencies (from repo root)
pip install -r requirements.txt

# 2. Set env vars in root .env file
#    TAVILY_API_KEY=your-tavily-key

# 3. Configure AgentCore (first time only)
agentcore configure --entrypoint 03-agentcore-deploy/agentcore_app.py
```

## Local Development

```bash
# Start local dev server
agentcore dev

# Test single invocation
agentcore invoke --dev --session-id "test-session-00000000-0000-0000-0000-000000000001" '{"prompt": "Hi"}'

# Interactive chat (local)
./03-agentcore-deploy/chat.sh --dev
```

## Cloud Deployment

```bash
# Deploy with env vars
agentcore deploy --env TAVILY_API_KEY=$TAVILY_API_KEY

# Interactive chat (cloud)
./03-agentcore-deploy/chat.sh

# Or specify a session to resume
./03-agentcore-deploy/chat.sh -s "my-session-00000000-0000-0000-0000-000000000001"
```

## Session Memory

Multi-turn memory works via an in-memory `dict[session_id -> Agent]`:

- Each unique `--session-id` gets its own `Agent` instance
- The agent's `self.messages` list accumulates conversation history
- Same session ID = same agent = remembers previous turns
- New session ID = fresh agent = no prior context
- Sessions persist for the lifetime of the AgentCore runtime session

**Note:** AgentCore's `runtimeSessionId` requires a minimum of **33 characters**.

## Tools

| Tool | Source | Purpose |
|------|--------|---------|
| **Tavily** | `strands_tools.tavily` | Web search for current info, news, facts |
| **Calculator** | `strands_tools.calculator` | Math operations |
| **Current Time** | `strands_tools.current_time` | Get current time |
| **Letter Counter** | Custom `@tool` | Count letter occurrences in words |

## Files

- `agentcore_app.py` — Main agent app with session management + web search
- `chat.sh` — Terminal chat wrapper script for interactive sessions
