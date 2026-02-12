from pathlib import Path
from dotenv import load_dotenv
import logging
from strands import Agent, tool
from strands_tools import calculator, current_time, http_request
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig

# Load environment variables from root .env file
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Define a custom tool as a Python function using the @tool decorator
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

# Custom boto client config with retry and timeout settings
boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)

# Configure the model with streaming enabled (default)
# streaming=True: Responses arrive token by token in real-time
# streaming=False: Full response arrives at once (needed for some models like Llama)
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
    temperature=0.7,
    streaming=True,  # Default — real-time token streaming
    boto_client_config=boto_config,
)

# System prompt to define agent behavior
system_prompt = """
You are a helpful AI assistant with access to various tools.
You can perform calculations, tell the current time, and count letters in words.
Always be accurate, concise, and friendly in your responses.
"""

# Create an agent with tools
# Default callback handler prints streaming output to console
agent = Agent(
    model=model,
    tools=[calculator, current_time, letter_counter,http_request],
    system_prompt=system_prompt,
    # callback_handler=None,  # Uncomment to disable real-time console output
)

# Ask the agent a question that uses the available tools
message = """
I have 4 requests:

1. What is the time right now?
2. Calculate 3111696 / 74088
3. Tell me how many letter R's are in the word "strawberry" 🍓
"""
agent(message)
