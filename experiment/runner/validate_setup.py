#!/usr/bin/env python3
"""Validate that the experiment is correctly set up before running."""

import json
import sys
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).parent.parent
CHECKS_PASSED = 0
CHECKS_FAILED = 0


def check(description: str, condition: bool, detail: str = ""):
    global CHECKS_PASSED, CHECKS_FAILED
    if condition:
        CHECKS_PASSED += 1
        print(f"  [OK] {description}")
    else:
        CHECKS_FAILED += 1
        msg = f"  [FAIL] {description}"
        if detail:
            msg += f" — {detail}"
        print(msg)


def main():
    print("\n=== Experiment Setup Validation ===\n")

    # 1. Codebase
    print("Codebase:")
    codebase = EXPERIMENT_DIR / "codebase"
    check("Codebase directory exists", codebase.is_dir())

    src_modules = ["auth", "payments", "users", "api", "models", "utils"]
    for mod in src_modules:
        check(f"Module src/{mod}/ exists", (codebase / "src" / mod).is_dir())

    check("Tests directory exists", (codebase / "tests").is_dir())

    # Count Python files
    py_files = list(codebase.rglob("*.py"))
    check(f"Python files found ({len(py_files)})", len(py_files) >= 20)

    # Run tests
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=codebase, capture_output=True, text=True, timeout=30
    )
    check(f"All tests pass (exit code {result.returncode})", result.returncode == 0,
          result.stdout.strip().split("\n")[-1] if result.stdout else "no output")

    # 2. Conditions
    print("\nConditions:")
    for cond in ["A", "B", "C", "D"]:
        cond_dir = EXPERIMENT_DIR / "conditions" / cond
        check(f"Condition {cond} directory exists", cond_dir.is_dir())

        settings = cond_dir / ".claude" / "settings.json"
        check(f"Condition {cond} has settings.json", settings.exists())

        if settings.exists():
            with open(settings) as f:
                s = json.load(f)
            has_hooks = bool(s.get("hooks", {}).get("PreToolUse"))

            if cond in ("A", "B"):
                check(f"Condition {cond} has NO hooks", not has_hooks)
            else:
                check(f"Condition {cond} HAS hooks", has_hooks)

        # Memory check
        has_memory = False
        for mem_loc in [cond_dir / "memory", cond_dir / ".claude" / "memory"]:
            if (mem_loc / "MEMORY.md").exists():
                has_memory = True
                mem_files = list(mem_loc.glob("*.md"))
                check(f"Condition {cond} memory has {len(mem_files)} files", len(mem_files) >= 1)

        if cond in ("B", "D"):
            check(f"Condition {cond} HAS memory", has_memory)
        else:
            check(f"Condition {cond} has NO memory", not has_memory,
                  "Memory found but not expected" if has_memory else "")

    # 3. Hook scripts
    print("\nHook scripts:")
    for cond in ["C", "D"]:
        hooks_dir = EXPERIMENT_DIR / "conditions" / cond / ".claude" / "hooks"
        check(f"Condition {cond} has hooks directory", hooks_dir.is_dir())
        if hooks_dir.is_dir():
            hook_files = list(hooks_dir.glob("*.sh"))
            check(f"Condition {cond} has {len(hook_files)} hook script(s)", len(hook_files) >= 1)

    # 4. Tasks
    print("\nTasks:")
    tasks_file = EXPERIMENT_DIR / "tasks.json"
    check("tasks.json exists", tasks_file.exists())

    if tasks_file.exists():
        with open(tasks_file) as f:
            tasks = json.load(f)
        check(f"Tasks loaded ({len(tasks)})", len(tasks) >= 10)

        # Task categories
        categories = set(t["category"] for t in tasks)
        check(f"Task categories: {categories}", len(categories) >= 2)

        difficulties = set(t["difficulty"] for t in tasks)
        check(f"Task difficulties: {difficulties}", len(difficulties) >= 2)

        hidden = sum(1 for t in tasks if t.get("tests_hidden_pattern"))
        check(f"Tasks testing hidden patterns: {hidden}/{len(tasks)}", hidden >= 5)

        # Verify expected files exist in codebase
        for task in tasks:
            for expected in task.get("expected_files", []):
                full_path = codebase / expected
                check(f"Task {task['id']}: expected file {expected} exists",
                      full_path.exists(),
                      f"File not found: {full_path}" if not full_path.exists() else "")

    # 5. Runner
    print("\nRunner:")
    runner = EXPERIMENT_DIR / "runner" / "run_experiment.py"
    check("run_experiment.py exists", runner.exists())

    # Check Claude CLI
    try:
        claude_check = subprocess.run(["claude", "--version"], capture_output=True, text=True, shell=True, timeout=10)
        check("Claude CLI available", claude_check.returncode == 0,
              claude_check.stdout.strip() if claude_check.returncode == 0 else "Not found — install with npm i -g @anthropic-ai/claude-code")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        check("Claude CLI available", False, "Not found — install with npm i -g @anthropic-ai/claude-code")

    # Summary
    print(f"\n{'='*50}")
    print(f"  {CHECKS_PASSED} passed, {CHECKS_FAILED} failed")
    if CHECKS_FAILED == 0:
        print("  Experiment is ready to run!")
        print(f"\n  Quick start:")
        print(f"    python {runner} --dry-run --condition A --task T01")
        print(f"    python {runner} --condition all --task all --runs 3")
    else:
        print("  Fix the failures above before running.")
    print(f"{'='*50}\n")

    return 0 if CHECKS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
