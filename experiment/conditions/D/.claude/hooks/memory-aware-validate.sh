#!/bin/bash
# Hook: Memory-aware validation for Condition D (hooks + memory combined)
# Checks MEMORY.md for relevant pointers before allowing edits

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
PROJECT_DIR=$(echo "$INPUT" | jq -r '.cwd // empty')

NEW_CONTENT=""
if [ "$TOOL_NAME" = "Write" ]; then
    NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')
elif [ "$TOOL_NAME" = "Edit" ]; then
    NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_string // empty')
fi

CONTENT_LENGTH=${#NEW_CONTENT}

# Determine which module is being edited
MODULE=""
if echo "$FILE_PATH" | grep -q "/auth/"; then MODULE="auth"; fi
if echo "$FILE_PATH" | grep -q "/payments/"; then MODULE="payments"; fi
if echo "$FILE_PATH" | grep -q "/users/"; then MODULE="users"; fi
if echo "$FILE_PATH" | grep -q "/api/"; then MODULE="api"; fi
if echo "$FILE_PATH" | grep -q "/models/"; then MODULE="models"; fi
if echo "$FILE_PATH" | grep -q "/utils/"; then MODULE="utils"; fi

# Find memory file for this module
MEMORY_DIR="$PROJECT_DIR/.claude/memory"
MEMORY_CONTEXT=""

if [ -n "$MODULE" ] && [ -f "$MEMORY_DIR/$MODULE.md" ]; then
    MEMORY_CONTEXT=$(cat "$MEMORY_DIR/$MODULE.md" 2>/dev/null)
fi

# Also check decisions
DECISIONS=""
if [ -f "$MEMORY_DIR/decisions.md" ]; then
    DECISIONS=$(cat "$MEMORY_DIR/decisions.md" 2>/dev/null)
fi

# Critical paths
CRITICAL=false
if echo "$FILE_PATH" | grep -qE "(payments|auth|models)"; then
    CRITICAL=true
fi

if [ "$CRITICAL" = true ] || [ "$CONTENT_LENGTH" -gt 300 ]; then
    CONTEXT_MSG="MEMORY CONTEXT for this module:\\n\\n$MEMORY_CONTEXT\\n\\nARCHITECTURE DECISIONS:\\n$DECISIONS\\n\\nBefore making this edit, verify your change is consistent with the invariants and dependencies described above. Pay special attention to implicit contracts and cross-module dependencies."

    echo "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"PreToolUse\",
    \"permissionDecision\": \"ask\",
    \"permissionDecisionReason\": \"Critical edit in $MODULE module: $FILE_PATH\",
    \"additionalContext\": \"$CONTEXT_MSG\"
  }
}"
    exit 0
fi

# Non-critical, small edits: allow but inject light context
if [ -n "$MEMORY_CONTEXT" ]; then
    SHORT_CONTEXT=$(echo "$MEMORY_CONTEXT" | head -5)
    echo "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"PreToolUse\",
    \"permissionDecision\": \"allow\",
    \"additionalContext\": \"Memory note for $MODULE: $SHORT_CONTEXT\"
  }
}"
    exit 0
fi

exit 0
