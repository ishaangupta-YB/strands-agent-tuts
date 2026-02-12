#!/usr/bin/env bash
# chat.sh — Interactive multi-turn terminal chat for AgentCore
#
# Usage:
#   ./chat.sh            # chat against cloud deployment
#   ./chat.sh --dev      # chat against local dev server
#   ./chat.sh --dev -s my-session  # use a specific session id

set -euo pipefail

DEV_FLAG=""
SESSION_ID="chat-session-$(uuidgen | tr '[:upper:]' '[:lower:]')"

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

echo "==================================="
echo "  Multi-Turn AgentCore Chatbot"
echo "==================================="
echo "Session: $SESSION_ID"
[ -n "$DEV_FLAG" ] && echo "Mode: local dev" || echo "Mode: cloud"
echo "Type 'quit' or 'exit' to end."
echo "-----------------------------------"
echo ""

while true; do
    read -rp "You: " user_input

    # Exit on quit/exit or EOF
    if [[ -z "$user_input" ]] || [[ "$user_input" == "quit" ]] || [[ "$user_input" == "exit" ]]; then
        echo "Goodbye!"
        break
    fi

    # Escape double quotes in user input for JSON safety
    escaped_input="${user_input//\\/\\\\}"
    escaped_input="${escaped_input//\"/\\\"}"

    echo ""
    echo -n "Agent: "
    agentcore invoke $DEV_FLAG --session-id "$SESSION_ID" "{\"prompt\": \"$escaped_input\"}" 2>/dev/null
    echo ""
    echo ""
done
