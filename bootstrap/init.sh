#!/bin/bash
# claude-bootstrap: Universal project initialization for Claude Code
# Drops into any repo and sets up CLAUDE.md + MEMORY.md + hooks
#
# Usage:
#   curl -sL <url>/init.sh | bash
#   # or
#   npx claude-bootstrap
#   # or
#   ./init.sh

set -e

PROJECT_DIR="${1:-.}"
CLAUDE_DIR="$PROJECT_DIR/.claude"

echo ""
echo "  claude-bootstrap: initializing project intelligence"
echo "  ==================================================="
echo ""

# --- Phase 1: Detect project ---

detect_stack() {
    local dir="$1"
    local languages=""
    local frameworks=""
    local package_manager=""
    local test_runner=""
    local entry_points=""

    # Languages (use find to avoid glob expansion issues)
    if find "$dir" -name "*.py" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null | head -1 | grep -q .; then
        languages="$languages python"
    fi
    if find "$dir" \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null | head -1 | grep -q .; then
        languages="$languages javascript/typescript"
    fi
    if find "$dir" -name "*.go" -not -path "*/.git/*" 2>/dev/null | head -1 | grep -q .; then
        languages="$languages go"
    fi
    if find "$dir" -name "*.rs" -not -path "*/.git/*" -not -path "*/target/*" 2>/dev/null | head -1 | grep -q .; then
        languages="$languages rust"
    fi
    if find "$dir" -name "*.java" -not -path "*/.git/*" 2>/dev/null | head -1 | grep -q .; then
        languages="$languages java"
    fi
    if find "$dir" -name "*.rb" -not -path "*/.git/*" 2>/dev/null | head -1 | grep -q .; then
        languages="$languages ruby"
    fi

    # Frameworks & package managers
    [ -f "$dir/package.json" ] && package_manager="npm" && frameworks="$frameworks node"
    [ -f "$dir/yarn.lock" ] && package_manager="yarn"
    [ -f "$dir/pnpm-lock.yaml" ] && package_manager="pnpm"
    [ -f "$dir/requirements.txt" ] || [ -f "$dir/pyproject.toml" ] || [ -f "$dir/setup.py" ] && package_manager="pip"
    [ -f "$dir/Pipfile" ] && package_manager="pipenv"
    [ -f "$dir/poetry.lock" ] && package_manager="poetry"
    [ -f "$dir/go.mod" ] && package_manager="go"
    [ -f "$dir/Cargo.toml" ] && package_manager="cargo"
    [ -f "$dir/Gemfile" ] && package_manager="bundler"

    # Frameworks
    [ -f "$dir/next.config.js" ] || [ -f "$dir/next.config.mjs" ] || [ -f "$dir/next.config.ts" ] && frameworks="$frameworks nextjs"
    [ -f "$dir/nuxt.config.ts" ] || [ -f "$dir/nuxt.config.js" ] && frameworks="$frameworks nuxt"
    [ -f "$dir/angular.json" ] && frameworks="$frameworks angular"
    [ -f "$dir/svelte.config.js" ] && frameworks="$frameworks svelte"
    grep -q "fastapi\|FastAPI" "$dir/requirements.txt" 2>/dev/null && frameworks="$frameworks fastapi"
    grep -q "django\|Django" "$dir/requirements.txt" 2>/dev/null && frameworks="$frameworks django"
    grep -q "flask\|Flask" "$dir/requirements.txt" 2>/dev/null && frameworks="$frameworks flask"
    grep -q "express" "$dir/package.json" 2>/dev/null && frameworks="$frameworks express"
    [ -f "$dir/Dockerfile" ] && frameworks="$frameworks docker"

    # Test runners
    [ -f "$dir/jest.config.js" ] || [ -f "$dir/jest.config.ts" ] && test_runner="jest"
    [ -f "$dir/vitest.config.ts" ] || [ -f "$dir/vitest.config.js" ] && test_runner="vitest"
    grep -q "pytest" "$dir/requirements.txt" "$dir/pyproject.toml" 2>/dev/null && test_runner="pytest"
    [ -f "$dir/phpunit.xml" ] && test_runner="phpunit"

    echo "LANGUAGES=\"$languages\""
    echo "FRAMEWORKS=\"$frameworks\""
    echo "PACKAGE_MANAGER=\"$package_manager\""
    echo "TEST_RUNNER=\"$test_runner\""
}

echo "  [1/4] Detecting project stack..."
eval "$(detect_stack "$PROJECT_DIR")"

echo "        Languages:       $LANGUAGES"
echo "        Frameworks:      $FRAMEWORKS"
echo "        Package manager: $PACKAGE_MANAGER"
echo "        Test runner:     $TEST_RUNNER"

# --- Phase 2: Scan structure ---

echo ""
echo "  [2/4] Scanning project structure..."

# Count files and find top-level modules
if [ -d "$PROJECT_DIR/src" ]; then
    SOURCE_DIR="src"
elif [ -d "$PROJECT_DIR/lib" ]; then
    SOURCE_DIR="lib"
elif [ -d "$PROJECT_DIR/app" ]; then
    SOURCE_DIR="app"
else
    SOURCE_DIR="."
fi

# Find top-level directories (modules/domains)
MODULES=$(find "$PROJECT_DIR/$SOURCE_DIR" -maxdepth 1 -type d ! -name ".*" ! -name "node_modules" ! -name "__pycache__" ! -name ".git" ! -name "$SOURCE_DIR" 2>/dev/null | while read d; do basename "$d"; done | sort)

# Count source files
FILE_COUNT=$(find "$PROJECT_DIR" -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.go" -o -name "*.rs" -o -name "*.java" -o -name "*.rb" \) ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/__pycache__/*" 2>/dev/null | wc -l)

echo "        Source dir:   $SOURCE_DIR/"
echo "        Modules:      $MODULES"
echo "        Source files:  $FILE_COUNT"

# --- Phase 3: Generate files ---

echo ""
echo "  [3/4] Generating configuration..."

mkdir -p "$CLAUDE_DIR/hooks"

# --- Generate CLAUDE.md ---

# Build test command
TEST_CMD=""
case "$TEST_RUNNER" in
    jest)    TEST_CMD="npx jest" ;;
    vitest)  TEST_CMD="npx vitest run" ;;
    pytest)  TEST_CMD="python -m pytest" ;;
    phpunit) TEST_CMD="./vendor/bin/phpunit" ;;
    *)
        # Guess from package.json
        if [ -f "$PROJECT_DIR/package.json" ] && grep -q '"test"' "$PROJECT_DIR/package.json"; then
            TEST_CMD="npm test"
        fi
        ;;
esac

cat > "$PROJECT_DIR/CLAUDE.md" << CLAUDEEOF
# Project Intelligence

## How you work

No quickfixes. No shortcuts. No lazy pattern matching.

You are not an autocomplete. You are an engineer. Every change you make will run in production, be maintained by others, and outlive this conversation. Act accordingly.

### Before you write a single line of code:
1. **Read first.** Read the file you're about to change. Read the files that import it. Read the tests. If you haven't read it, you don't understand it, and you will break it.
2. **Understand the system, not just the function.** A function exists in a context — other modules call it, data flows through it, invariants depend on it. Trace the dependencies before you touch anything.
3. **Ask why it's like this before you change it.** Code that looks wrong often looks that way for a reason. The previous developer might have been stupid, or they might have known something you don't. Find out which before you "fix" it.
4. **Check your assumptions with grep, not with guessing.** If you think a function is only called in one place — verify. If you think a variable is unused — verify. Assumptions are bugs waiting to happen.

### When you write code:
5. **Solve the actual problem, not a simplified version of it.** If the task is hard, it should feel hard. If your solution feels easy, you probably missed something.
6. **Match the existing patterns exactly.** Don't introduce a new style, a new abstraction, a new way of doing things. The codebase has conventions — follow them even if you'd do it differently.
7. **One change, one purpose.** Don't refactor while fixing a bug. Don't add features while refactoring. Don't clean up code you didn't change. Stay focused.
8. **Handle the edges the same way the codebase handles them.** Look at how existing code handles errors, nulls, invalid input. Do the same. Don't invent a new error handling pattern.

### After you write code:
9. **Run the tests. All of them.** Not just the ones you think are relevant. You don't know what you don't know.
10. **Read your own diff.** Before you declare success, read every line you changed as if someone else wrote it. Would you approve this PR?

### What you never do:
- Never edit a file you haven't read in this session
- Never assume a function does what its name suggests — read the implementation
- Never silence an error to make code work
- Never add a TODO or FIXME — fix it now or don't touch it
- Never say "this should work" — verify that it does
- Never import something without checking if the dependency exists in this project

### When you don't know:
Say so. "I'm not sure if this module handles X — let me check" is always better than a confident wrong answer. Check .claude/memory/ for prior context, but verify that what's in memory still matches the code.

## Stack
- Languages: $LANGUAGES
- Frameworks: $FRAMEWORKS
- Package manager: $PACKAGE_MANAGER
- Test runner: $TEST_RUNNER

## Commands
- Install: \`${PACKAGE_MANAGER:-npm} install\`
- Test: \`${TEST_CMD:-npm test}\`
- Lint: check package.json or pyproject.toml for lint command

## Critical paths
<!-- Add paths that require extra care when modifying -->
<!-- Example: src/auth/ — authentication logic, changes require review -->
<!-- Example: src/payments/ — financial logic, changes require tests -->

## Architecture decisions
<!-- Record WHY decisions were made, not just WHAT -->
<!-- Example: We use JWT over session cookies for stateless horizontal scaling -->
CLAUDEEOF

echo "        Created CLAUDE.md"

# --- Generate MEMORY.md scaffold ---

mkdir -p "$CLAUDE_DIR/memory"

# Build module index
MEMORY_CONTENT="# Project Memory\n\n## Modules\n"
for mod in $MODULES; do
    MEMORY_CONTENT="$MEMORY_CONTENT- [$mod]($mod.md) — TODO: describe purpose\n"
done

if [ -z "$MODULES" ]; then
    MEMORY_CONTENT="$MEMORY_CONTENT- No modules detected yet. Memory will be populated as you work.\n"
fi

MEMORY_CONTENT="$MEMORY_CONTENT\n## Coverage\nThe following areas have been indexed: none yet.\nEverything else is terra incognita — grep before assuming.\n"

printf "$MEMORY_CONTENT" > "$CLAUDE_DIR/memory/MEMORY.md"

# Create stub memory files per module
for mod in $MODULES; do
    cat > "$CLAUDE_DIR/memory/$mod.md" << MODEOF
---
name: $mod module
description: TODO — describe what this module does
type: project
---

## Pointers
<!-- Agent will populate this after working with the module -->

## Dependencies
<!-- Which other modules does this import from / depend on? -->

## Decisions
<!-- Why is this module structured this way? -->
MODEOF
done

echo "        Created MEMORY.md + $(echo $MODULES | wc -w) module stubs"

# --- Generate hooks ---

# Hook: pre-edit validation
cat > "$CLAUDE_DIR/hooks/pre-edit-validate.sh" << 'HOOKEOF'
#!/bin/bash
# Pre-edit validation hook
# Checks if the file being edited is in a critical path
# and injects memory context if available

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
PROJECT_DIR=$(echo "$INPUT" | jq -r '.cwd // empty')

# Skip non-source files
case "$FILE_PATH" in
    *.md|*.json|*.yaml|*.yml|*.toml|*.cfg|*.ini|*.lock)
        exit 0
        ;;
esac

# Check CLAUDE.md for critical paths
CRITICAL=false
if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
    # Extract critical paths from CLAUDE.md
    while IFS= read -r line; do
        # Match lines like: <!-- Example: src/auth/ — ... -->
        # or actual entries like: - src/auth/ — ...
        path=$(echo "$line" | grep -oP '(?:^- |^)(\S+/)' | head -1 | tr -d '- ')
        if [ -n "$path" ] && echo "$FILE_PATH" | grep -q "$path"; then
            CRITICAL=true
            break
        fi
    done < <(sed -n '/## Critical paths/,/## /p' "$PROJECT_DIR/CLAUDE.md")
fi

if [ "$CRITICAL" = true ]; then
    # Find relevant memory file
    MEMORY_CONTEXT=""
    MEMORY_DIR="$PROJECT_DIR/.claude/memory"
    if [ -d "$MEMORY_DIR" ]; then
        # Try to find module memory
        for memfile in "$MEMORY_DIR"/*.md; do
            modname=$(basename "$memfile" .md)
            if echo "$FILE_PATH" | grep -qi "$modname"; then
                MEMORY_CONTEXT=$(cat "$memfile" 2>/dev/null)
                break
            fi
        done
    fi

    CONTEXT_MSG="CRITICAL PATH: This file is marked as critical in CLAUDE.md."
    if [ -n "$MEMORY_CONTEXT" ]; then
        CONTEXT_MSG="$CONTEXT_MSG\n\nMEMORY CONTEXT:\n$MEMORY_CONTEXT"
    fi
    CONTEXT_MSG="$CONTEXT_MSG\n\nBefore editing: 1) Have you read the full file? 2) What dependencies might break? 3) Are there tests for this?"

    echo "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"PreToolUse\",
    \"permissionDecision\": \"ask\",
    \"permissionDecisionReason\": \"Critical path edit: $FILE_PATH\",
    \"additionalContext\": \"$CONTEXT_MSG\"
  }
}"
    exit 0
fi

# Non-critical: allow but inject light memory context
MEMORY_DIR="$PROJECT_DIR/.claude/memory"
if [ -d "$MEMORY_DIR" ]; then
    for memfile in "$MEMORY_DIR"/*.md; do
        modname=$(basename "$memfile" .md)
        if echo "$FILE_PATH" | grep -qi "$modname"; then
            SHORT=$(head -5 "$memfile" 2>/dev/null)
            echo "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"PreToolUse\",
    \"permissionDecision\": \"allow\",
    \"additionalContext\": \"Memory note: $SHORT\"
  }
}"
            exit 0
        fi
    done
fi

exit 0
HOOKEOF

# Hook: post-edit memory update reminder
cat > "$CLAUDE_DIR/hooks/post-edit-memory.sh" << 'HOOKEOF'
#!/bin/bash
# Post-edit hook: reminds agent to update MEMORY.md after successful edits
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only trigger for source files
case "$FILE_PATH" in
    *.md|*.json|*.yaml|*.yml|*.toml|*.lock)
        exit 0
        ;;
esac

echo "{
  \"hookSpecificOutput\": {
    \"hookEventName\": \"PostToolUse\",
    \"additionalContext\": \"File modified: $FILE_PATH. If this changes any function signatures, dependencies, or architectural patterns, update the relevant memory file in .claude/memory/.\"
  }
}"
exit 0
HOOKEOF

chmod +x "$CLAUDE_DIR/hooks/pre-edit-validate.sh" 2>/dev/null
chmod +x "$CLAUDE_DIR/hooks/post-edit-memory.sh" 2>/dev/null

# --- Generate settings.json ---

cat > "$CLAUDE_DIR/settings.json" << 'SETTINGSEOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/pre-edit-validate.sh\"",
            "timeout": 5000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/post-edit-memory.sh\"",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
SETTINGSEOF

echo "        Created hooks + settings.json"

# --- Phase 4: Summary ---

echo ""
echo "  [4/4] Done!"
echo ""
echo "  Created:"
echo "    CLAUDE.md                          ← project rules (edit this)"
echo "    .claude/settings.json              ← hook configuration"
echo "    .claude/hooks/pre-edit-validate.sh ← validates edits against critical paths"
echo "    .claude/hooks/post-edit-memory.sh  ← reminds to update memory after edits"
echo "    .claude/memory/MEMORY.md           ← module index (auto-populated)"

for mod in $MODULES; do
    echo "    .claude/memory/$mod.md             ← $mod module memory (stub)"
done

echo ""
echo "  Next steps:"
echo "    1. Edit CLAUDE.md → add your critical paths and architecture decisions"
echo "    2. Run: claude"
echo "    3. Memory will populate as you work"
echo ""
echo "  The system learns as you use it. The more you work, the better it gets."
echo ""
