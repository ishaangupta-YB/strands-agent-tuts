# Strands AI Agent Project

This project demonstrates AWS Bedrock agents using the Strands framework with Claude 4.

## Files

- **agent.py** - Simple one-shot agent demo with example queries
- **chatbot.py** - Interactive chatbot with streaming & non-streaming support

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure AWS credentials in `.env`:**
   ```env
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   AWS_DEFAULT_REGION=us-east-1
   ```

## Usage

### Run the basic agent demo:
```bash
python agent.py
```

### Run the interactive chatbot:

**Streaming mode (default) — tokens arrive in real-time:**
```bash
python chatbot.py
```

**Non-streaming mode — full response arrives at once:**
```bash
python chatbot.py --no-stream
```

## Features

### Available Tools
- **Calculator** - Perform mathematical calculations
- **Current Time** - Get the current time
- **Letter Counter** - Count specific letters in words

### Streaming vs Non-Streaming

Both are **BedrockModel configurations** — not Python async patterns:

| Mode | Flag | Behavior |
|------|------|----------|
| **Streaming** (default) | `python chatbot.py` | Tokens appear one by one as they're generated |
| **Non-streaming** | `python chatbot.py --no-stream` | Full response arrives at once |

Both modes use the **same callback handler** — Strands internally converts non-streaming responses to the same event format. Non-streaming is useful for models that don't support streaming tool use (e.g., Llama models).

## Configuration

### Model Settings
- Model: Claude 4 Sonnet on Amazon Bedrock
- Region: us-east-1 (configurable)
- Temperature: 0.7
- Boto client: Retry (3 attempts), connect timeout (5s), read timeout (60s)

### Debug Logging
Uncomment the logging configuration in the files to enable debug logs:
```python
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
```

## Requirements

- Python 3.8+
- AWS account with Bedrock access
- IAM permissions for Claude 4 model invocation
