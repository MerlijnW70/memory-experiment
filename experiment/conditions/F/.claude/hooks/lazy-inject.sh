#!/bin/bash
# Lazy injection hook: loads rules + memory ONLY at edit time
# Token-efficient: zero cost during read/explore phase
# Injects once per module per session to avoid redundancy

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
PROJECT_DIR=$(echo "$INPUT" | jq -r '.cwd // empty')

# Skip non-source files
case "$FILE_PATH" in
    *.md|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini|*.lock|*.txt)
        exit 0
        ;;
esac

# Determine module from file path
MODULE=""
for mod in auth payments users api models utils; do
    if echo "$FILE_PATH" | grep -qi "/$mod/\|\\\\$mod\\\\"; then
        MODULE="$mod"
        break
    fi
done

# Track what we've already injected this session (avoid repeating)
INJECT_LOG="/tmp/claude-inject-${SESSION_ID}"
if [ -f "$INJECT_LOG" ] && grep -q "^${MODULE}$" "$INJECT_LOG" 2>/dev/null; then
    # Already injected for this module — allow silently
    exit 0
fi

# Build context payload
CONTEXT=""

# 1. Load rules (behavioral instructions) — only on first edit of session
if [ ! -f "$INJECT_LOG" ]; then
    RULES_FILE="$PROJECT_DIR/.claude/rules.md"
    if [ -f "$RULES_FILE" ]; then
        RULES=$(cat "$RULES_FILE")
        CONTEXT="=== ENGINEERING RULES ===\n${RULES}\n\n"
    fi
fi

# 2. Load module-specific memory
if [ -n "$MODULE" ]; then
    MEMORY_FILE="$PROJECT_DIR/.claude/memory/${MODULE}.md"
    if [ -f "$MEMORY_FILE" ]; then
        MEMORY=$(cat "$MEMORY_FILE")
        CONTEXT="${CONTEXT}=== MEMORY: ${MODULE} module ===\n${MEMORY}\n\n"
    fi

    # 3. Load decisions if they exist
    DECISIONS_FILE="$PROJECT_DIR/.claude/memory/decisions.md"
    if [ -f "$DECISIONS_FILE" ] && [ ! -f "$INJECT_LOG" ]; then
        DECISIONS=$(cat "$DECISIONS_FILE")
        CONTEXT="${CONTEXT}=== ARCHITECTURE DECISIONS ===\n${DECISIONS}\n\n"
    fi
fi

# Mark as injected
echo "$MODULE" >> "$INJECT_LOG" 2>/dev/null

# If we have context to inject, do it
if [ -n "$CONTEXT" ]; then
    CONTEXT="${CONTEXT}Apply these rules and respect these dependencies for your edit."

    echo "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"PreToolUse\",
    \"permissionDecision\": \"allow\",
    \"additionalContext\": \"$CONTEXT\"
  }
}"
    exit 0
fi

exit 0
