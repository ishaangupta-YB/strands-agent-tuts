import logging
import sys
from strands import Agent
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder
from strands.multiagent.base import Status
from strands.types.content import ContentBlock

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logging.getLogger("strands.multiagent").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

OUTPUT_DIR = Path(__file__).resolve().parent


# --- Condition helpers ---

def only_if_research_successful(state):
    """Only traverse if research node completed successfully."""
    research_node = state.results.get("research")
    if not research_node:
        return False
    result_text = str(research_node.result)
    return "successful" in result_text.lower()


def all_dependencies_complete(required_nodes: list[str]):
    """Factory: returns a condition that passes only when ALL required nodes are COMPLETED."""
    def check_all_complete(state) -> bool:
        return all(
            node_id in state.results and state.results[node_id].status == Status.COMPLETED
            for node_id in required_nodes
        )
    return check_all_complete


# --- Model & Agents ---

model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-east-1",
)

researcher = Agent(name="researcher", model=model, system_prompt="You are a researcher specialist agent. Your job is to gather information about a topic and provide a summary of your findings.")
analyst = Agent(name="analyst", model=model, system_prompt="You are an analyst specialist agent. Your job is to analyze the researcher's findings and provide insights and connections between the information.")
fact_checker = Agent(name="fact_checker", model=model, system_prompt="You are a fact checker specialist agent. Your job is to verify the accuracy of the researcher's findings and the analyst's insights.")
report_writer = Agent(name="report_writer", model=model, system_prompt="You are a report writer specialist agent. Your job is to take the researcher's findings, the analyst's insights, and the fact checker's verifications to write a comprehensive report on the topic.")


# --- Build graph ---

builder = GraphBuilder()

builder.add_node(researcher, 'research')
builder.add_node(analyst, 'analyst')
builder.add_node(fact_checker, 'fact_checker')
builder.add_node(report_writer, 'report_writer')

# research → analyst (only if research was successful)
builder.add_edge('research', 'analyst', condition=only_if_research_successful)
# research → fact_checker (always)
builder.add_edge('research', 'fact_checker')

# report_writer waits for BOTH analyst AND fact_checker to complete
builder.add_edge('analyst', 'report_writer', condition=all_dependencies_complete(["analyst", "fact_checker"]))
builder.add_edge('fact_checker', 'report_writer', condition=all_dependencies_complete(["analyst", "fact_checker"]))

builder.set_entry_point('research')
builder.set_execution_timeout(300)

graph = builder.build()


# --- Build input (text-only or image+text) ---

if len(sys.argv) > 1:
    # Image mode: python graph_agent.py <image_path> [optional prompt]
    image_path = Path(sys.argv[1])
    prompt = sys.argv[2] if len(sys.argv) > 2 else "Analyze this image in detail and provide a comprehensive report on what you see."
    image_bytes = image_path.read_bytes()
    suffix = image_path.suffix.lstrip(".").lower()
    fmt = {"jpg": "jpeg"}.get(suffix, suffix)  # normalize jpg → jpeg

    task_input = [
        ContentBlock(text=prompt),
        ContentBlock(image={"format": fmt, "source": {"bytes": image_bytes}}),
    ]
    print(f"Image mode: {image_path} ({fmt})")
else:
    # Text-only mode
    task_input = "What are the latest advancements in renewable energy technologies?"


# --- Execute ---

result = graph(task_input)

# Print summary
print(f"\nStatus: {result.status}")
print(f"Execution order: {[node.node_id for node in result.execution_order]}")
print(f"Execution time: {result.execution_time}ms")

# Save final report to markdown
report_path = OUTPUT_DIR / "graph_report.md"
report_path.write_text(f"# Graph Agent Report\n\n{result}\n")
print(f"\nReport saved to: {report_path}")
