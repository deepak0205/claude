#!/bin/bash
# PreToolUse hook (matcher: Edit|Write) — enforces per-subagent write scope.
# Claude Code includes `agent_type` in the hook stdin JSON whenever the tool
# call originates inside a subagent (empty/absent for the main thread).
set -euo pipefail

ROOT="/home/labuser/agent_poc"

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
      "$ROOT"/ingestion/*|"$ROOT"/rag/*|"$ROOT"/agents/*|"$ROOT"/api/*|"$ROOT"/config/*|"$ROOT"/scripts/*|"$ROOT"/tests/*|"$ROOT"/requirements.txt|"$ROOT"/.env.example|"$ROOT"/docker-compose.yml)
        exit 0
        ;;
      *)
        deny "backend subagent may only Edit/Write within ingestion/, rag/, agents/, api/, config/, scripts/, tests/, or root config files (requirements.txt, .env.example, docker-compose.yml) — blocked path: $path"
        ;;
    esac
    ;;
  frontend)
    case "$path" in
      "$ROOT"/ui/*)
        exit 0
        ;;
      *)
        deny "frontend subagent may only Edit/Write within ui/ — blocked path: $path"
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
