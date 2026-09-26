#!/bin/bash
# PreToolUse hook (matcher: Edit|Write) — enforces per-subagent write scope.
# Ported from agent_poc/.claude/hooks/scope-check.sh.
set -euo pipefail

ROOT="/home/labuser/Desktop/healthcare case_stuides/chatbot"

payload=$(cat)
agent=$(printf '%s' "$payload" | jq -r '.agent_type // ""')
path=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // .tool_response.filePath // ""')

deny() {
  jq -n --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
  exit 0
}

case "$agent" in
  backend)
    case "$path" in
      "$ROOT"/backend/*|"$ROOT"/mcp_server/*|"$ROOT"/tests/*|"$ROOT"/load_test/*|"$ROOT"/specs/*|"$ROOT"/requirements.txt|"$ROOT"/.env.example|"$ROOT"/pytest.ini)
        exit 0
        ;;
      *)
        deny "backend subagent may only Edit/Write within backend/, mcp_server/, tests/, load_test/, specs/, or root config files (requirements.txt, .env.example, pytest.ini) — blocked path: $path"
        ;;
    esac
    ;;
  frontend)
    case "$path" in
      "$ROOT"/frontend/*|"$ROOT"/.streamlit/*)
        exit 0
        ;;
      *)
        deny "frontend subagent may only Edit/Write within frontend/ or .streamlit/ — blocked path: $path"
        ;;
    esac
    ;;
  p3-triage)
    deny "p3-triage subagent is read-only and must never Edit/Write — blocked path: $path"
    ;;
  *)
    exit 0
    ;;
esac
