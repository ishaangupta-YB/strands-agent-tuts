from pathlib import Path
from dotenv import load_dotenv
import sys
import time
import logging
from threading import Lock
from strands import Agent, tool
from strands_tools import calculator, current_time, http_request
from strands.models import BedrockModel
from strands.hooks import (
    HookProvider,
    HookRegistry,
    BeforeInvocationEvent,
    AfterInvocationEvent,
    BeforeModelCallEvent,
    AfterModelCallEvent,
    BeforeToolCallEvent,
    AfterToolCallEvent,
)
from botocore.config import Config as BotocoreConfig

# Configure file logger for hooks (writes to chatbot_hooks.log, doesn't clutter terminal)
hook_logger = logging.getLogger("chatbot.hooks")
hook_logger.setLevel(logging.DEBUG)
_log_handler = logging.FileHandler(Path(__file__).resolve().parent / "chatbot_hooks.log")
_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
hook_logger.addHandler(_log_handler)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
  
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


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

class InvocationLoggingHook(HookProvider):
    """Logs the full agent lifecycle: invocation start/end, model calls, and tool calls with timing."""

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_invocation_start)
        registry.add_callback(AfterInvocationEvent, self.on_invocation_end)
        registry.add_callback(BeforeModelCallEvent, self.on_model_call_start)
        registry.add_callback(AfterModelCallEvent, self.on_model_call_end)
        registry.add_callback(BeforeToolCallEvent, self.on_tool_call_start)
        registry.add_callback(AfterToolCallEvent, self.on_tool_call_end)

    def on_invocation_start(self, event: BeforeInvocationEvent) -> None:
        self._invocation_start = time.time()
        hook_logger.info("--- Invocation started ---")

    def on_invocation_end(self, event: AfterInvocationEvent) -> None:
        elapsed = time.time() - getattr(self, "_invocation_start", time.time())
        hook_logger.info(f"--- Invocation finished ({elapsed:.2f}s) ---")

    def on_model_call_start(self, event: BeforeModelCallEvent) -> None:
        self._model_call_start = time.time()
        hook_logger.debug("Model call started")

    def on_model_call_end(self, event: AfterModelCallEvent) -> None:
        elapsed = time.time() - getattr(self, "_model_call_start", time.time())
        hook_logger.debug(f"Model call finished ({elapsed:.2f}s)")

    def on_tool_call_start(self, event: BeforeToolCallEvent) -> None:
        self._tool_call_start = time.time()
        tool_name = event.tool_use.get("name", "unknown")
        tool_input = event.tool_use.get("input", {})
        hook_logger.info(f"Tool call: {tool_name} | input: {tool_input}")

    def on_tool_call_end(self, event: AfterToolCallEvent) -> None:
        elapsed = time.time() - getattr(self, "_tool_call_start", time.time())
        tool_name = event.tool_use.get("name", "unknown")
        status = event.result.get("status", "unknown")
        hook_logger.info(f"Tool result: {tool_name} | status: {status} ({elapsed:.2f}s)")


class ToolUsageTrackerHook(HookProvider):
    """Tracks per-invocation tool usage counts and logs a summary at the end."""

    def __init__(self):
        self._counts: dict[str, int] = {}
        self._lock = Lock()

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.reset)
        registry.add_callback(AfterToolCallEvent, self.track)
        registry.add_callback(AfterInvocationEvent, self.summarize)

    def reset(self, event: BeforeInvocationEvent) -> None:
        with self._lock:
            self._counts = {}

    def track(self, event: AfterToolCallEvent) -> None:
        tool_name = event.tool_use.get("name", "unknown")
        with self._lock:
            self._counts[tool_name] = self._counts.get(tool_name, 0) + 1

    def summarize(self, event: AfterInvocationEvent) -> None:
        with self._lock:
            if self._counts:
                summary = ", ".join(f"{name}: {count}" for name, count in self._counts.items())
                hook_logger.info(f"Tool usage summary: {summary}")
            else:
                hook_logger.info("Tool usage summary: no tools used")


class LimitToolCallsHook(HookProvider):
    """Caps how many times each tool can be called per invocation to prevent runaway loops."""

    def __init__(self, max_calls_per_tool: int = 5):
        self._max = max_calls_per_tool
        self._counts: dict[str, int] = {}
        self._lock = Lock()

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.reset)
        registry.add_callback(BeforeToolCallEvent, self.check_limit)

    def reset(self, event: BeforeInvocationEvent) -> None:
        with self._lock:
            self._counts = {}

    def check_limit(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use.get("name", "unknown")
        with self._lock:
            count = self._counts.get(tool_name, 0) + 1
            self._counts[tool_name] = count

        if count > self._max:
            hook_logger.warning(f"Tool '{tool_name}' hit call limit ({self._max}), cancelling")
            event.cancel_tool = (
                f"Tool '{tool_name}' has exceeded {self._max} calls this invocation. "
                f"DO NOT CALL THIS TOOL ANYMORE."
            )


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

 
system_prompt = """
You are a friendly and helpful AI chatbot assistant.

You have access to several tools:
- Calculator for mathematical operations
- Current time checker
- Letter counter for analyzing words
- HTTP Client for fetching web content

Your personality:
- Be conversational and natural
- Remember context from earlier in the conversation
- Be helpful, accurate, and concise
- Use the tools when needed to provide accurate information
- If you don't know something or can't help, be honest about it

Always strive to provide the best assistance possible!
"""

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
    elif "message" in kwargs:
        msg = kwargs["message"]
        content = msg.get("content", [])
        
        # Check for Tool Use (Input)
        if msg.get("role") == "assistant":
            for block in content:
                if isinstance(block, dict) and "toolUse" in block:
                    tool_use = block["toolUse"]
                    print(f"\n\n--- 🔧 Tool Request: {tool_use.get('name')} ---")
                    print(f"ID: {tool_use.get('toolUseId')}")
                    print(f"Input: {tool_use.get('input')}")
                    print("------------------------------------------\n")
        
        # Check for Tool Result (Output)
        elif msg.get("role") == "user":
            for block in content:
                if isinstance(block, dict) and "toolResult" in block:
                    tool_res = block["toolResult"]
                    print(f"\n\n--- ✅ Tool Response ---")
                    print(f"ID: {tool_res.get('toolUseId')}")
                    print(f"Status: {tool_res.get('status')}")
                    # Content is a list of blocks usually
                    res_content = tool_res.get('content', [])
                    print(f"Content: {res_content}")
                    print("------------------------\n")

 
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
        tools=[calculator, current_time, letter_counter, http_request],
        system_prompt=system_prompt,
        callback_handler=callback_handler,
        hooks=[
            InvocationLoggingHook(),
            ToolUsageTrackerHook(),
            LimitToolCallsHook(max_calls_per_tool=5),
        ],
    )

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
