"""
Graph Topologies & Graph-as-Tool demo.

Usage:
    python graph_topologies.py                  # interactive menu
    python graph_topologies.py tool             # graph as a tool
    python graph_topologies.py sequential       # sequential pipeline
    python graph_topologies.py parallel         # parallel + aggregation
    python graph_topologies.py branching        # branching logic
    python graph_topologies.py feedback         # feedback loop
"""

import logging
import sys
from strands import Agent
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder
from strands.multiagent.base import Status

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logging.getLogger("strands.multiagent").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)

OUTPUT_DIR = Path(__file__).resolve().parent

# Shared conciseness instruction appended to every agent's system prompt
CONCISE = " Keep your response concise — 300 words max. No filler, no fluff."

model = BedrockModel(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-east-1",
    max_tokens=4096,
)


def save_report(result, filename: str, title: str):
    """Save graph result to a markdown file and print summary."""
    print(f"\nStatus: {result.status}")
    print(f"Execution order: {[n.node_id for n in result.execution_order]}")
    print(f"Execution time: {result.execution_time}ms")

    path = OUTPUT_DIR / filename
    path.write_text(f"# {title}\n\n{result}\n")
    print(f"Report saved to: {path}")


def run_demo(name: str, fn):
    """Wrapper that catches token/timeout errors gracefully."""
    try:
        fn()
    except Exception as e:
        print(f"\n[ERROR] {name} failed: {e}")


# =============================================================================
# 1. GRAPH AS A TOOL — agent dynamically builds & runs a graph
# =============================================================================

def run_graph_as_tool():
    """An outer agent uses the `graph` tool from strands_tools to dynamically
    create and execute a graph of sub-agents on the fly."""
    from strands_tools import graph

    orchestrator = Agent(
        model=model,
        tools=[graph],
        system_prompt=(
            "You are a project planner. Given a task, use the graph tool to create a simple "
            "2-3 node graph of agents. Each agent should produce a SHORT summary (under 200 words). "
            "Do NOT ask agents to write code or long documents. Only high-level outlines. "
            "After the graph runs, give a brief final summary." + CONCISE
        ),
    )

    result = orchestrator(
        "Plan a Python CLI weather app: outline the architecture and recommend key libraries."
    )

    path = OUTPUT_DIR / "graph_as_tool_report.md"
    path.write_text(f"# Graph as Tool Report\n\n{result}\n")
    print(f"\nReport saved to: {path}")


# =============================================================================
# 2. SEQUENTIAL PIPELINE — Startup Pitch Pipeline
#    Ideator → Market Researcher → Business Strategist → Pitch Writer
# =============================================================================

def run_sequential():
    """A sequential pipeline that takes a startup idea and progressively
    refines it through 4 stages into a pitch."""

    ideator = Agent(
        name="ideator", model=model,
        system_prompt=(
            "You are a startup ideator. Define the core problem, target audience, "
            "solution, and unique value proposition." + CONCISE
        ),
    )
    market_researcher = Agent(
        name="market_researcher", model=model,
        system_prompt=(
            "You are a market analyst. Estimate TAM/SAM/SOM, identify 3 competitors, "
            "and spot market gaps." + CONCISE
        ),
    )
    strategist = Agent(
        name="strategist", model=model,
        system_prompt=(
            "You are a business strategist. Define the revenue model, go-to-market plan, "
            "and top 3 risks with mitigations." + CONCISE
        ),
    )
    pitch_writer = Agent(
        name="pitch_writer", model=model,
        system_prompt=(
            "You are a pitch writer. Synthesize all prior inputs into a short investor pitch "
            "with sections: Problem, Solution, Market, Business Model, Ask." + CONCISE
        ),
    )

    builder = GraphBuilder()
    builder.add_node(ideator, "ideation")
    builder.add_node(market_researcher, "market_research")
    builder.add_node(strategist, "strategy")
    builder.add_node(pitch_writer, "pitch")

    builder.add_edge("ideation", "market_research")
    builder.add_edge("market_research", "strategy")
    builder.add_edge("strategy", "pitch")

    builder.set_entry_point("ideation")
    builder.set_max_node_executions(8)
    builder.set_execution_timeout(300)

    graph = builder.build()
    result = graph(
        "An AI-powered personal finance app that learns spending habits "
        "and automatically negotiates better deals on recurring bills"
    )

    save_report(result, "sequential_report.md", "Sequential Pipeline — Startup Pitch")


# =============================================================================
# 3. PARALLEL PROCESSING WITH AGGREGATION — Product Audit
#    Coordinator → [UX Auditor, Security Auditor, Performance Auditor] → Summary
# =============================================================================

def run_parallel():
    """A coordinator fans out to 3 parallel specialist auditors, then an
    aggregator synthesizes all findings into a single audit report."""

    def all_audits_complete(required: list[str]):
        def check(state) -> bool:
            return all(
                nid in state.results and state.results[nid].status == Status.COMPLETED
                for nid in required
            )
        return check

    coordinator = Agent(
        name="coordinator", model=model,
        system_prompt=(
            "You are an audit coordinator. Prepare a brief for UX, security, "
            "and performance auditors." + CONCISE
        ),
    )
    ux_auditor = Agent(
        name="ux_auditor", model=model,
        system_prompt=(
            "You are a UX auditor. Evaluate usability, accessibility, and user friction. "
            "Give a severity rating per issue." + CONCISE
        ),
    )
    security_auditor = Agent(
        name="security_auditor", model=model,
        system_prompt=(
            "You are a security auditor. Check auth, data handling, input validation, "
            "and OWASP Top 10. Rate severity per finding." + CONCISE
        ),
    )
    perf_auditor = Agent(
        name="perf_auditor", model=model,
        system_prompt=(
            "You are a performance auditor. Evaluate load times, query efficiency, "
            "caching, and scalability bottlenecks." + CONCISE
        ),
    )
    aggregator = Agent(
        name="aggregator", model=model,
        system_prompt=(
            "You are an audit aggregator. Combine all audit findings into a prioritized "
            "executive summary with an action plan." + CONCISE
        ),
    )

    auditors = ["ux_audit", "security_audit", "perf_audit"]

    builder = GraphBuilder()
    builder.add_node(coordinator, "coordinator")
    builder.add_node(ux_auditor, "ux_audit")
    builder.add_node(security_auditor, "security_audit")
    builder.add_node(perf_auditor, "perf_audit")
    builder.add_node(aggregator, "summary")

    # Fan-out: coordinator → all 3 auditors
    builder.add_edge("coordinator", "ux_audit")
    builder.add_edge("coordinator", "security_audit")
    builder.add_edge("coordinator", "perf_audit")

    # Fan-in: summary waits for ALL 3 auditors
    builder.add_edge("ux_audit", "summary", condition=all_audits_complete(auditors))
    builder.add_edge("security_audit", "summary", condition=all_audits_complete(auditors))
    builder.add_edge("perf_audit", "summary", condition=all_audits_complete(auditors))

    builder.set_entry_point("coordinator")
    builder.set_max_node_executions(10)
    builder.set_execution_timeout(300)

    graph = builder.build()
    result = graph(
        "Audit a SaaS project management tool with: React frontend, Node.js REST API, "
        "PostgreSQL, JWT auth, file uploads, and WebSocket notifications."
    )

    save_report(result, "parallel_report.md", "Parallel Aggregation — Product Audit")


# =============================================================================
# 4. BRANCHING LOGIC — Support Ticket Router
#    Classifier → [Bug Handler | Feature Handler | Question Handler]
# =============================================================================

def run_branching():
    """A classifier agent reads a support ticket and routes it to the
    appropriate specialist branch based on its type."""

    def is_bug(state):
        r = state.results.get("classifier")
        return r is not None and "BUG" in str(r.result)

    def is_feature(state):
        r = state.results.get("classifier")
        return r is not None and "FEATURE" in str(r.result)

    def is_question(state):
        r = state.results.get("classifier")
        return r is not None and "QUESTION" in str(r.result)

    classifier = Agent(
        name="classifier", model=model,
        system_prompt=(
            "You are a support ticket classifier. Classify the ticket as exactly one of: "
            "BUG, FEATURE, or QUESTION. Start your response with that word in uppercase. "
            "Then give a one-sentence explanation." + CONCISE
        ),
    )
    bug_handler = Agent(
        name="bug_handler", model=model,
        system_prompt=(
            "You are a bug triage specialist. Identify repro steps, severity (P0-P3), "
            "likely root cause, and recommended fix." + CONCISE
        ),
    )
    feature_handler = Agent(
        name="feature_handler", model=model,
        system_prompt=(
            "You are a feature analyst. Assess user value, feasibility, effort estimate, "
            "and recommended priority." + CONCISE
        ),
    )
    question_handler = Agent(
        name="question_handler", model=model,
        system_prompt=(
            "You are a support specialist. Answer the question clearly with "
            "step-by-step guidance." + CONCISE
        ),
    )

    builder = GraphBuilder()
    builder.add_node(classifier, "classifier")
    builder.add_node(bug_handler, "bug_handler")
    builder.add_node(feature_handler, "feature_handler")
    builder.add_node(question_handler, "question_handler")

    builder.add_edge("classifier", "bug_handler", condition=is_bug)
    builder.add_edge("classifier", "feature_handler", condition=is_feature)
    builder.add_edge("classifier", "question_handler", condition=is_question)

    builder.set_entry_point("classifier")
    builder.set_max_node_executions(5)
    builder.set_execution_timeout(120)

    graph = builder.build()
    result = graph(
        "Ticket #4821: Uploading a CSV larger than 50MB freezes the app for 30s, "
        "then shows a blank screen. Console: 'RangeError: Maximum call stack size exceeded'. "
        "Chrome 120 and Firefox 121. Smaller files work. Blocking weekly import."
    )

    save_report(result, "branching_report.md", "Branching Logic — Support Ticket Router")


# =============================================================================
# 5. FEEDBACK LOOP — Essay Refinement Loop
#    Writer → Critic → (back to Writer if "REVISION NEEDED" | Publisher if "APPROVED")
#
#    Key guardrail: a revision counter forces the approval path after
#    MAX_REVISIONS rounds, so the graph ALWAYS reaches the publisher.
# =============================================================================

def run_feedback():
    """A writer drafts an essay, a critic reviews it and either sends it back
    for revision or approves it for publishing. Forced approval after MAX_REVISIONS."""

    MAX_REVISIONS = 2
    # Track critic completions idempotently using result object identity
    _counter = {"n": 0, "last_id": None}

    def _count_critic_runs(state):
        """Increment once per unique critic result. Idempotent — safe to call
        from multiple conditions evaluating the same critic completion."""
        r = state.results.get("critic")
        if r is None:
            return 0
        rid = id(r)
        if rid != _counter["last_id"]:
            _counter["last_id"] = rid
            _counter["n"] += 1
        return _counter["n"]

    def needs_revision(state):
        count = _count_critic_runs(state)
        if count > MAX_REVISIONS:
            return False  # force-stop: no more revisions
        r = state.results.get("critic")
        if r is None:
            return False
        return "REVISION NEEDED" in str(r.result)

    def is_approved(state):
        count = _count_critic_runs(state)
        if count > MAX_REVISIONS:
            return True   # force-approve: send to publisher
        r = state.results.get("critic")
        if r is None:
            return False
        return "APPROVED" in str(r.result)

    writer = Agent(
        name="writer", model=model,
        system_prompt=(
            "You are an essay writer. Write or revise a short essay (under 200 words) "
            "based on the topic and any feedback. If revision feedback is provided, "
            "address every point raised." + CONCISE
        ),
    )
    critic = Agent(
        name="critic", model=model,
        system_prompt=(
            "You are an essay critic. Score the essay on: thesis, arguments, evidence, "
            "structure, writing (each out of 10). "
            "If ALL scores are 5+ respond with exactly 'APPROVED' then brief praise. "
            "Be lenient — approve if the essay is coherent and makes a reasonable argument. "
            "Only respond with 'REVISION NEEDED' if there are serious structural or logical flaws. "
            "You MUST start your response with either APPROVED or REVISION NEEDED." + CONCISE
        ),
    )
    publisher = Agent(
        name="publisher", model=model,
        system_prompt=(
            "You are a publisher. Format the essay as a polished markdown document "
            "with title, author ('AI Collaborative'), and section headers. "
            "Do not change the content." + CONCISE
        ),
    )

    builder = GraphBuilder()
    builder.add_node(writer, "writer")
    builder.add_node(critic, "critic")
    builder.add_node(publisher, "publisher")

    builder.add_edge("writer", "critic")
    builder.add_edge("critic", "writer", condition=needs_revision)
    builder.add_edge("critic", "publisher", condition=is_approved)

    builder.set_entry_point("writer")
    builder.set_max_node_executions(10)    # safety net (should never hit this)
    builder.set_execution_timeout(180)     # 3 min timeout
    builder.reset_on_revisit(True)

    graph = builder.build()
    result = graph(
        "Write a short persuasive essay arguing that remote work is reshaping "
        "urban planning and city design, not just workplace culture."
    )

    save_report(result, "feedback_report.md", "Feedback Loop — Essay Refinement")


# =============================================================================
# MAIN — interactive menu or CLI arg
# =============================================================================

DEMOS = {
    "tool": ("Graph as a Tool", run_graph_as_tool),
    "sequential": ("Sequential Pipeline — Startup Pitch", run_sequential),
    "parallel": ("Parallel Aggregation — Product Audit", run_parallel),
    "branching": ("Branching Logic — Support Ticket Router", run_branching),
    "feedback": ("Feedback Loop — Essay Refinement", run_feedback),
}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        key = sys.argv[1]
        if key not in DEMOS:
            print(f"Unknown topology: {key}")
            print(f"Available: {', '.join(DEMOS.keys())}")
            sys.exit(1)
        print(f"\nRunning: {DEMOS[key][0]}\n{'=' * 60}")
        run_demo(key, DEMOS[key][1])
    else:
        print("\nGraph Topologies Demo")
        print("=" * 40)
        for i, (key, (name, _)) in enumerate(DEMOS.items(), 1):
            print(f"  {i}. {name} [{key}]")
        print()
        choice = input("Pick a number (1-5): ").strip()
        keys = list(DEMOS.keys())
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            selected = keys[int(choice) - 1]
            print(f"\nRunning: {DEMOS[selected][0]}\n{'=' * 60}")
            run_demo(selected, DEMOS[selected][1])
        else:
            print("Invalid choice.")
