# Strands Agents: From Scratch to Production

A hands-on learning repo for building AI agents with **AWS Strands Agents SDK** and deploying them to **Amazon Bedrock AgentCore**. Each folder is a progressive step — from a basic one-shot agent to a production-deployed multi-turn chatbot with web search.

## Project Structure

```
strands-test/
├── 01-basics/                  # One-shot agent fundamentals
│   └── agent.py
├── 02-chatbot/                 # Interactive multi-turn chatbot (local)
│   └── chatbot.py
├── 03-agentcore-deploy/        # Production deploy to AgentCore
│   ├── agentcore_app.py        # Multi-turn + web search + sessions
│   └── chat.sh                 # Terminal chat wrapper
├── docs/
│   └── agentcore-reference.md  # AgentCore deployment reference
├── requirements.txt            # Shared Python dependencies
├── .env                        # AWS creds + API keys (gitignored)
└── CLAUDE.md                   # Project context for Claude Code
```

## Learning Path

| Step | Folder | What You Build | Key Concepts |
|------|--------|---------------|--------------|
| 1 | `01-basics/` | One-shot agent | `Agent`, `BedrockModel`, `@tool`, built-in tools |
| 2 | `02-chatbot/` | Local chatbot | Multi-turn memory, streaming vs non-streaming, callbacks |
| 3 | `03-agentcore-deploy/` | Cloud chatbot | AgentCore deploy, session management, Tavily web search |

## Quick Start

### 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure `.env`

```env
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=us-east-1
TAVILY_API_KEY=your-tavily-key
```

### 3. Run each step

```bash
# Step 1: Basic one-shot agent
python 01-basics/agent.py

# Step 2: Interactive local chatbot
python 02-chatbot/chatbot.py

# Step 3: Deploy to AgentCore
agentcore configure --entrypoint 03-agentcore-deploy/agentcore_app.py
agentcore deploy --env TAVILY_API_KEY=$TAVILY_API_KEY
./03-agentcore-deploy/chat.sh
```

## Tech Stack

- **[Strands Agents SDK](https://github.com/strands-agents/sdk-python)** — Agent framework
- **[Amazon Bedrock](https://aws.amazon.com/bedrock/)** — Claude Sonnet model hosting
- **[Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)** — Agent deployment runtime
- **[Tavily](https://tavily.com/)** — Web search API for agents

## Model Configuration

All examples use the same base model config:

| Setting | Value |
|---------|-------|
| Model | Claude Sonnet (`us.anthropic.claude-sonnet-4-20250514-v1:0`) |
| Region | `us-east-1` |
| Temperature | `0.7` |
| Retries | 3 attempts, standard mode |
| Timeouts | Connect: 5s, Read: 60s |

## Requirements

- Python 3.10+
- AWS account with Bedrock access (Claude Sonnet enabled)
- Tavily API key (for step 3 web search)
