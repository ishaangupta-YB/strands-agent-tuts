from pathlib import Path
from dotenv import load_dotenv
import sys
import logging
from strands import Agent, tool
from strands_tools import calculator, current_time
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

# Load environment variables from root .env file
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Enable debug logs (optional - uncomment to see detailed logs)
# logging.getLogger("strands").setLevel(logging.DEBUG)
# logging.basicConfig(
#     format="%(levelname)s | %(name)s | %(message)s",
#     handlers=[logging.StreamHandler()]
# )


# ============================================================================
# Custom Tool
# ============================================================================

@tool
def letter_counter(word: str, letter: str) -> int:
    """
    Count occurrences of a specific letter in a word.

    Args:
        word (str): The input word to search in
        letter (str): The specific letter to count

    Returns:
        int: The number of occurrences of the letter in the word
    """
    if not isinstance(word, str) or not isinstance(letter, str):
        return 0

    if len(letter) != 1:
        raise ValueError("The 'letter' parameter must be a single character")

    return word.lower().count(letter.lower())


# ============================================================================
# Model Configuration
# ============================================================================

# Custom boto client config with retry settings
boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)

# Streaming model (default) — responses arrive in real-time chunks
# This is what makes the chatbot feel responsive (tokens appear as they're generated)
streaming_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
    temperature=0.7,
    streaming=True,  # This is the default — response streams token by token
    boto_client_config=boto_config,
)

# Non-streaming model — full response arrives at once
# Useful for models that don't support streaming tool use (e.g., Llama models)
# Non-streaming responses are internally converted to the same event format,
# so your callback handler works identically with both modes.
non_streaming_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
    temperature=0.7,
    streaming=False,  # Full response at once, no token-by-token streaming
    boto_client_config=boto_config,
)


# ============================================================================
# System Prompt
# ============================================================================

system_prompt = """
You are a friendly and helpful AI chatbot assistant.

You have access to several tools:
- Calculator for mathematical operations
- Current time checker
- Letter counter for analyzing words

Your personality:
- Be conversational and natural
- Remember context from earlier in the conversation
- Be helpful, accurate, and concise
- Use the tools when needed to provide accurate information
- If you don't know something or can't help, be honest about it

Always strive to provide the best assistance possible!
"""


# ============================================================================
# Callback Handler
# ============================================================================

# Track tool use IDs to avoid duplicate notifications
tool_use_ids = []

def callback_handler(**kwargs):
    """
    Custom callback handler invoked in real-time as the agent thinks,
    uses tools, and generates responses.

    Works identically for both streaming and non-streaming models —
    non-streaming responses are internally converted to the same event format.

    Events:
    - data: Text chunks being generated (token by token in streaming mode,
            or all at once in non-streaming mode)
    - current_tool_use: Tool invocation information
    """
    if "data" in kwargs:
        # Print text chunks as they arrive
        print(kwargs["data"], end="", flush=True)
    elif "current_tool_use" in kwargs:
        tool = kwargs["current_tool_use"]
        if tool.get("toolUseId") and tool["toolUseId"] not in tool_use_ids:
            tool_name = tool.get("name", "Unknown")
            print(f"\n[🔧 Using tool: {tool_name}]", flush=True)
            tool_use_ids.append(tool["toolUseId"])


# ============================================================================
# Agent Setup
# ============================================================================

def create_agent(streaming=True):
    """
    Create an agent with the specified streaming mode.

    Args:
        streaming: If True (default), uses streaming model for real-time
                   token-by-token output. If False, uses non-streaming model
                   where the full response arrives at once.

    Both modes use the same callback handler — Strands internally converts
    non-streaming responses to the streaming event format.
    """
    model = streaming_model if streaming else non_streaming_model
    mode = "streaming" if streaming else "non-streaming"
    print(f"[Using {mode} mode]")

    return Agent(
        model=model,
        tools=[calculator, current_time, letter_counter],
        system_prompt=system_prompt,
        callback_handler=callback_handler,
    )


# ============================================================================
# Interactive Chat Loop
# ============================================================================

def main():
    """Run an interactive chatbot session."""
    # Parse --no-stream flag
    use_streaming = "--no-stream" not in sys.argv

    print("=" * 60)
    print("🤖 Strands AI Chatbot")
    print("=" * 60)
    print("I can help you with:")
    print("  • Mathematical calculations")
    print("  • Current time")
    print("  • Counting letters in words")
    print()

    agent = create_agent(streaming=use_streaming)

    print("\nType 'exit' or 'quit' to end the conversation")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit", "bye", "q"]:
                print("\n👋 Goodbye! Thanks for chatting!")
                break

            if not user_input:
                continue

            # Callback handler prints streaming output in real-time
            print("\n🤖 Agent: ", end="", flush=True)
            response = agent(user_input)
            print("\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Thanks for chatting!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again.\n")


if __name__ == "__main__":
    main()
