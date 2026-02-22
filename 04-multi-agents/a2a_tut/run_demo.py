"""
A2A Full Demo Runner
====================
Starts BOTH servers, then runs all three client demos in sequence.
Shows exactly what's happening at each step with clear flow diagrams.

Usage: python run_demo.py [--skip-dynamic]
  --skip-dynamic   Skip dynamic_discovery.py (needs extra pip install)
"""

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = sys.executable


# ── Helpers ────────────────────────────────────────────────────────────────────

def wait_for_server(url: str, label: str, timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    print(f"  Waiting for {label}", end="", flush=True)
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url + "/.well-known/agent.json", timeout=2)
            print(" ready!")
            return True
        except Exception:
            print(".", end="", flush=True)
            time.sleep(0.5)
    print(" TIMEOUT")
    return False


def section(title: str):
    bar = "═" * 62
    print(f"\n{bar}")
    print(f"  {title}")
    print(f"{bar}\n")


def run_script(script: str):
    result = subprocess.run([PYTHON, HERE / script], text=True)
    if result.returncode not in (0, 1):   # 1 = SystemExit from missing import
        print(f"[!] {script} exited with code {result.returncode}")


# ── STEP 1: Start both A2A servers ────────────────────────────────────────────

section("STEP 1 — Starting two A2A servers")

print("  server.py  → Calculator Agent   on http://127.0.0.1:9000")
print("  server2.py → Text Analyst Agent on http://127.0.0.1:9001")
print()

srv1 = subprocess.Popen([PYTHON, HERE / "server.py"],  text=True)
srv2 = subprocess.Popen([PYTHON, HERE / "server2.py"], text=True)

ok1 = wait_for_server("http://127.0.0.1:9000", "Calculator Agent (:9000)")
ok2 = wait_for_server("http://127.0.0.1:9001", "Text Analyst Agent (:9001)")

if not (ok1 and ok2):
    print("\n[!] One or more servers failed to start. Aborting.")
    srv1.terminate(); srv2.terminate()
    sys.exit(1)

print()
print("  Both servers are up. Architecture so far:")
print()
print("  ┌──────────────────────────────────────────────────────────┐")
print("  │               A2A Server Ecosystem                       │")
print("  │                                                          │")
print("  │  [Calculator Agent]      [Text Analyst Agent]           │")
print("  │   strands_tools.calculator   word_count, text_stats     │")
print("  │   port :9000                 find_longest_word          │")
print("  │                              count_vowels               │")
print("  │                              port :9001                 │")
print("  └──────────────────────────────────────────────────────────┘")

try:

    # ── STEP 2: Raw client (high-level + low-level) ───────────────────────────

    section("STEP 2 — Raw A2A client (client.py)")
    print("  Demonstrates all invocation patterns against server 1.")
    print("  No local LLM — client talks directly to the remote agent.\n")
    print("  Patterns:")
    print("    HIGH-LEVEL  A2AAgent  → sync / async / streaming / agent-card")
    print("    LOW-LEVEL   a2a.client SDK → raw protocol messages & events\n")
    print("  FLOW:")
    print("  client.py ──A2A HTTP──> server.py ──Bedrock──> answer")
    print()
    run_script("client.py")

    # ── STEP 3: Multi-agent orchestrator ─────────────────────────────────────

    section("STEP 3 — Multi-agent orchestrator (app.py)")
    print("  A LOCAL orchestrator LLM wraps BOTH remote agents as tools,")
    print("  plus one local tool (get_current_time).\n")
    print("  FLOW (compound query example):")
    print()
    print("  [User question]")
    print("       │")
    print("       ▼")
    print("  Orchestrator LLM  (local Bedrock call)")
    print("       ├── calculate    ──A2A──> Calculator Agent :9000 ──> result")
    print("       ├── analyze_text ──A2A──> Text Analyst   :9001 ──> result")
    print("       └── get_time     ──local──────────────────────────> result")
    print("       │")
    print("       ▼")
    print("  Orchestrator formats final answer\n")
    run_script("app.py")

    # ── STEP 4: Dynamic discovery ─────────────────────────────────────────────

    skip_dynamic = "--skip-dynamic" in sys.argv
    section("STEP 4 — Dynamic discovery (dynamic_discovery.py)")

    if skip_dynamic:
        print("  Skipped (--skip-dynamic flag set).")
    else:
        print("  A2AClientToolProvider auto-discovers both agents at runtime.")
        print("  No manual @tool wrappers — tools are injected from agent cards.\n")
        print("  Requires: pip install 'strands-agents-tools[a2a_client]'")
        print("  (will print an install hint and exit cleanly if missing)\n")
        print("  FLOW:")
        print("  dynamic_discovery.py")
        print("    ──fetch agent cards──> :9000, :9001")
        print("    ──build tools auto──>  [calc_tool, text_tool, ...]")
        print("    ──inject into Agent──> orchestrator uses them naturally\n")
        run_script("dynamic_discovery.py")

finally:

    # ── Cleanup ───────────────────────────────────────────────────────────────

    section("CLEANUP — Stopping both servers")
    srv1.terminate(); srv1.wait()
    srv2.terminate(); srv2.wait()
    print("  Both servers stopped.\n")
    print("  Summary")
    print("  ┌─────────────────────────┬──────────────────────────────────────┐")
    print("  │ server.py               │ Calculator Agent, port :9000         │")
    print("  │ server2.py              │ Text Analyst Agent, port :9001       │")
    print("  │ client.py               │ All client patterns (high + low lvl) │")
    print("  │ app.py                  │ Orchestrator: 2 remote + 1 local tool│")
    print("  │ dynamic_discovery.py    │ Auto-discovered tools from cards     │")
    print("  └─────────────────────────┴──────────────────────────────────────┘")
    print()
    print("  Key insight:")
    print("  client.py  → you control every call manually")
    print("  app.py     → LLM decides which remote agent to call and when")
    print("  dynamic    → LLM discovers AND decides, with no hardcoded tools")
