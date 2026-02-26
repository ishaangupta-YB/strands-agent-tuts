import logging
from strands import Agent
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder, Swarm

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logging.getLogger("strands.multiagent").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

OUTPUT_DIR = Path(__file__).resolve().parent


# --- Model ---

model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-east-1",
)

# --- Research Swarm (3 specialist researchers) ---

medical_researcher = Agent(
    name="medical_researcher",
    model=model,
    system_prompt="You are a medical research specialist. Research the medical and healthcare aspects of the given topic. Provide detailed findings with specific examples.",
)
technology_researcher = Agent(
    name="technology_researcher",
    model=model,
    system_prompt="You are a technology research specialist. Research the technological innovations and engineering aspects of the given topic. Provide detailed findings with specific examples.",
)
economic_researcher = Agent(
    name="economic_researcher",
    model=model,
    system_prompt="You are an economic research specialist. Research the economic impact, market trends, and financial aspects of the given topic. Provide detailed findings with specific examples.",
)

research_swarm = Swarm(
    [medical_researcher, technology_researcher, economic_researcher],
    max_handoffs=10,
    max_iterations=10,
    execution_timeout=300.0,
)


# --- Analyst & Report Writer ---

analyst = Agent(
    name="analyst",
    model=model,
    system_prompt="You are an analyst specialist. Analyze the research findings from multiple researchers, identify key patterns, connections, and synthesize insights across medical, technological, and economic dimensions.",
)

report_writer = Agent(
    name="report_writer",
    model=model,
    system_prompt="You are a report writer specialist. Take the research findings and analysis to produce a comprehensive, well-structured final report in markdown format with clear sections and actionable conclusions.",
)


# --- Build graph: Swarm → Analyst → Report Writer ---

builder = GraphBuilder()

builder.add_node(research_swarm, "research_team")
builder.add_node(analyst, "analysis")
builder.add_node(report_writer, "report")

builder.add_edge("research_team", "analysis")
builder.add_edge("analysis", "report")

builder.set_entry_point("research_team")
builder.set_execution_timeout(600)

graph = builder.build()


# --- Execute ---

result = graph("Research the impact of AI on healthcare and create a comprehensive report")

# Print summary
print(f"\nStatus: {result.status}")
print(f"Execution order: {[node.node_id for node in result.execution_order]}")
print(f"Execution time: {result.execution_time}ms")

# Save final report to markdown
report_path = OUTPUT_DIR / "nested_graph_report.md"
report_path.write_text(f"# Nested Graph Report — AI Impact on Healthcare\n\n{result}\n")
print(f"\nReport saved to: {report_path}")
