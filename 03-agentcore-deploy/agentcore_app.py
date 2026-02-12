from pathlib import Path
from dotenv import load_dotenv
from strands import Agent, tool
from strands_tools import calculator, current_time, tavily, use_aws
from strands.models import BedrockModel
from botocore.config import Config as BotocoreConfig
from bedrock_agentcore.runtime import BedrockAgentCoreApp, BedrockAgentCoreContext

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

boto_config = BotocoreConfig(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)

model_config = dict(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1",
    temperature=0.7,
    streaming=True,
    boto_client_config=boto_config,
)

SYSTEM_PROMPT = """
You are a friendly and helpful AI chatbot assistant with memory and web search.

You have access to several tools:
- **Web Search (Tavily)**: Search the web for current information, news, facts, etc.
- **Calculator**: For mathematical operations
- **Current Time**: Check the current time
- **Letter Counter**: Count letter occurrences in words
- **AWS Services**: Interact with AWS services (S3, Lambda, DynamoDB, etc.)

Your personality:
- Be conversational and natural — this is a multi-turn chat
- Remember what the user said earlier in the conversation and refer back to it naturally
- Use web search when the user asks about current events, recent news, or anything you're unsure about
- Be helpful, accurate, and concise
- If you don't know something or can't help, be honest about it
"""

TOOLS = [tavily, calculator, current_time, letter_counter, use_aws]

agents_by_session: dict[str, Agent] = {}

app = BedrockAgentCoreApp()

def get_or_create_agent(session_id: str) -> Agent:
    """Return existing agent for this session, or create a new one."""
    if session_id not in agents_by_session:
        agents_by_session[session_id] = Agent(
            model=BedrockModel(**model_config),
            tools=TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )
    return agents_by_session[session_id]


@app.entrypoint
def invoke(payload):
    """Process user input with session-aware multi-turn memory."""
    session_id = BedrockAgentCoreContext.get_session_id() or "default"
    agent = get_or_create_agent(session_id)
    user_message = payload.get("prompt", "Hello")
    result = agent(user_message)
    return str(result)


if __name__ == "__main__":
    app.run()
