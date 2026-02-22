#!/usr/bin/env bash
# chat.sh — Interactive multi-turn terminal chat for the Agents-as-Tools AgentCore app
#
# Usage:
#   ./chat.sh            # chat against cloud deployment
#   ./chat.sh --dev      # chat against local dev server
#   ./chat.sh --dev -s my-session-id-here-must-be-33-plus-chars

set -euo pipefail

DEV_FLAG=""
SESSION_ID="agents-as-tools-$(uuidgen | tr '[:upper:]' '[:lower:]')"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev)
            DEV_FLAG="--dev"
            shift
            ;;
        -s|--session)
            SESSION_ID="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./chat.sh [--dev] [-s SESSION_ID]"
            exit 1
            ;;
    esac
done

echo "============================================"
echo "  Agents as Tools — AgentCore Chat"
echo "============================================"
echo "Session : $SESSION_ID"
[ -n "$DEV_FLAG" ] && echo "Mode    : local dev" || echo "Mode    : cloud"
echo "Experts : research | products | trip planning"
echo "Type 'quit' or 'exit' to end."
echo "--------------------------------------------"
echo ""

while true; do
    read -rp "You: " user_input

    if [[ -z "$user_input" ]] || [[ "$user_input" == "quit" ]] || [[ "$user_input" == "exit" ]]; then
        echo "Goodbye!"
        break
    fi

    # Escape backslashes and double-quotes for JSON safety
    escaped_input="${user_input//\\/\\\\}"
    escaped_input="${escaped_input//\"/\\\"}"

    echo ""

    raw_output=$(agentcore invoke $DEV_FLAG --session-id "$SESSION_ID" "{\"prompt\": \"$escaped_input\"}" 2>&1)

    # Detect "server not running" or other agentcore errors (output is a ╭...╰ box)
    if echo "$raw_output" | grep -q "Development Server Not Found\|Setup Required\|Error\|error"; then
        echo "ERROR: agentcore dev server is not running or misconfigured."
        echo "  1. agentcore configure --entrypoint 04-multi-agents/agents_as_tools/agentcore_app.py"
        echo "  2. agentcore dev   (in a separate terminal)"
        echo ""
        continue
    fi

    clean_output=$(echo "$raw_output" \
        | sed '/^╭/,/^╰/d' \
        | sed '/^Response:$/d' \
        | sed '/^[[:space:]]*$/d')

    echo "Agent: $clean_output"
    echo ""
done
