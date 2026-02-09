from strands import Agent, tool
from strands_tools import calculator, current_time
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from bedrock_agentcore.runtime import BedrockAgentCoreApp


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

boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
    temperature=0.7,
    streaming=True,
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
- Be helpful, accurate, and concise
- Use the tools when needed to provide accurate information
- If you don't know something or can't help, be honest about it

Always strive to provide the best assistance possible!
"""


# ============================================================================
# AgentCore App Setup
# ============================================================================

app = BedrockAgentCoreApp()

agent = Agent(
    model=model,
    tools=[calculator, current_time, letter_counter],
    system_prompt=system_prompt,
)


@app.entrypoint
def invoke(payload):
    """Process user input and return a response."""
    user_message = payload.get("prompt", "Hello")
    result = agent(user_message)
    return str(result)


if __name__ == "__main__":
    app.run()
