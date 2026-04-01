#!/bin/bash
# Hook: Pre-edit validation for Condition C (hooks only, no memory)
# Forces reflection before any code modification

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
NEW_CONTENT=""

if [ "$TOOL_NAME" = "Write" ]; then
    NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // empty')
elif [ "$TOOL_NAME" = "Edit" ]; then
    NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_string // empty')
fi

CONTENT_LENGTH=${#NEW_CONTENT}

# Critical paths that require extra scrutiny
CRITICAL=false
if echo "$FILE_PATH" | grep -qE "(payments|auth|models)"; then
    CRITICAL=true
fi

if [ "$CRITICAL" = true ]; then
    echo "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"PreToolUse\",
    \"permissionDecision\": \"ask\",
    \"permissionDecisionReason\": \"Critical path edit: $FILE_PATH\",
    \"additionalContext\": \"STOP. This file is in a critical module. Before proceeding: 1) Have you read the FULL file, not just the target function? 2) What implicit dependencies does this code have? 3) What other modules import from this file? 4) Will existing tests still pass after this change?\"
  }
}"
    exit 0
fi

# Non-critical but large edits
if [ "$CONTENT_LENGTH" -gt 300 ]; then
    echo "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"PreToolUse\",
    \"permissionDecision\": \"ask\",
    \"permissionDecisionReason\": \"Large edit ($CONTENT_LENGTH chars) in $FILE_PATH\",
    \"additionalContext\": \"This is a substantial change. Verify: does it maintain consistency with the rest of the module?\"
  }
}"
    exit 0
fi

# Allow small non-critical edits
exit 0
