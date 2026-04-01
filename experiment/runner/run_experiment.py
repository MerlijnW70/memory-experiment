#!/usr/bin/env python3
"""
Experiment Runner: MEMORY.md × Hooks Observability Experiment

Tests the hypothesis that agent decision quality correlates more strongly
with MEMORY.md completeness than with hook enforcement.

Four conditions:
  A = baseline (no memory, no hooks)
  B = memory only (full MEMORY.md, no hooks)
  C = hooks only (no memory, strict hooks)
  D = combined (full MEMORY.md + hooks)

Usage:
  python run_experiment.py --condition A --task T01
  python run_experiment.py --condition all --task all --runs 3
  python run_experiment.py --analyze
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime

EXPERIMENT_DIR = Path(__file__).parent.parent
CODEBASE_DIR = EXPERIMENT_DIR / "codebase"
CONDITIONS_DIR = EXPERIMENT_DIR / "conditions"
RESULTS_DIR = EXPERIMENT_DIR / "results"
TASKS_FILE = EXPERIMENT_DIR / "tasks.json"


def load_tasks():
    with open(TASKS_FILE) as f:
        return json.load(f)


def setup_workdir(condition: str, task_id: str, run: int) -> Path:
    """Create isolated working directory for a single run."""
    workdir = RESULTS_DIR / f"{condition}_{task_id}_run{run}" / "workspace"
    if workdir.exists():
        shutil.rmtree(workdir)

    # Copy codebase
    shutil.copytree(CODEBASE_DIR, workdir)

    # Copy condition-specific .claude directory
    condition_dir = CONDITIONS_DIR / condition
    claude_dir = workdir / ".claude"
    claude_dir.mkdir(exist_ok=True)

    # Copy settings.json
    settings_src = condition_dir / ".claude" / "settings.json"
    if settings_src.exists():
        shutil.copy2(settings_src, claude_dir / "settings.json")

    # Copy hooks if they exist
    hooks_src = condition_dir / ".claude" / "hooks"
    if hooks_src.exists():
        shutil.copytree(hooks_src, claude_dir / "hooks", dirs_exist_ok=True)

    # Copy memory if it exists (conditions B and D)
    memory_src = condition_dir / "memory"
    if not memory_src.exists():
        memory_src = condition_dir / ".claude" / "memory"
    if memory_src.exists():
        shutil.copytree(memory_src, claude_dir / "memory", dirs_exist_ok=True)

    # Copy CLAUDE.md if it exists (condition E)
    claude_md_src = condition_dir / "CLAUDE.md"
    if claude_md_src.exists():
        shutil.copy2(claude_md_src, workdir / "CLAUDE.md")

    return workdir


def run_tests(workdir: Path) -> dict:
    """Run pytest in the workspace and capture results."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=60
    )

    output = result.stdout + result.stderr

    # Parse test results
    passed = 0
    failed = 0
    errors = 0
    for line in output.split("\n"):
        if "passed" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "passed" and i > 0:
                    try:
                        passed = int(parts[i-1])
                    except ValueError:
                        pass
                if p == "failed" and i > 0:
                    try:
                        failed = int(parts[i-1])
                    except ValueError:
                        pass
                if "error" in p and i > 0:
                    try:
                        errors = int(parts[i-1])
                    except ValueError:
                        pass

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "returncode": result.returncode,
        "output": output[-2000:]  # Last 2000 chars
    }


def run_single_task(condition: str, task: dict, run: int, dry_run: bool = False) -> dict:
    """Execute a single task under a specific condition."""
    task_id = task["id"]
    print(f"\n{'='*60}")
    print(f"  Condition {condition} | Task {task_id} | Run {run}")
    print(f"  {task['category']} | {task['difficulty']} | hidden_pattern: {task.get('tests_hidden_pattern', False)}")
    print(f"{'='*60}")

    # Setup workspace
    workdir = setup_workdir(condition, task_id, run)
    result_dir = workdir.parent

    # Run baseline tests first
    print("  Running baseline tests...")
    baseline_tests = run_tests(workdir)

    # Prepare the result record
    result = {
        "condition": condition,
        "task_id": task_id,
        "run": run,
        "task": task,
        "timestamp": datetime.now().isoformat(),
        "baseline_tests": baseline_tests,
        "workdir": str(workdir),
    }

    if dry_run:
        result["status"] = "dry_run"
        result["agent_output"] = "DRY RUN - no agent invoked"
        save_result(result, result_dir)
        return result

    # Build the prompt for Claude Code
    prompt = build_agent_prompt(task, condition)

    # Run Claude Code
    print(f"  Invoking Claude Code agent...")
    start_time = time.time()

    # Save prompt for reference
    try:
        with open(result_dir / "prompt.txt", "w", encoding="utf-8") as pf:
            pf.write(prompt)
    except OSError:
        pass

    try:
        # Pass prompt via stdin pipe to avoid shell escaping issues on Windows
        agent_result = subprocess.run(
            "claude -p - --output-format json --max-turns 20 --dangerously-skip-permissions",
            cwd=workdir,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per task
            shell=True    # Needed on Windows to find .cmd files
        )
        elapsed = time.time() - start_time

        result["agent_output"] = agent_result.stdout[-5000:]
        result["agent_stderr"] = agent_result.stderr[-2000:]
        result["agent_returncode"] = agent_result.returncode
        result["elapsed_seconds"] = elapsed

        # Parse JSON output if possible
        try:
            agent_json = json.loads(agent_result.stdout)
            result["agent_json"] = agent_json
        except (json.JSONDecodeError, ValueError):
            result["agent_json"] = None

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["elapsed_seconds"] = 300
        print("  TIMEOUT after 5 minutes")
    except FileNotFoundError:
        result["status"] = "claude_not_found"
        result["agent_output"] = "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
        print("  ERROR: Claude CLI not found")

    # Run post-task tests
    print("  Running post-task tests...")
    post_tests = run_tests(workdir)
    result["post_tests"] = post_tests

    # Calculate metrics
    result["metrics"] = calculate_metrics(result, baseline_tests, post_tests)

    # Check for workarounds (files modified outside expected scope)
    result["file_changes"] = detect_file_changes(workdir)
    result["workarounds"] = detect_workarounds(task, result["file_changes"])

    # Save result
    save_result(result, result_dir)

    print(f"  Completed in {result.get('elapsed_seconds', 0):.1f}s")
    print(f"  Tests: {post_tests['passed']} passed, {post_tests['failed']} failed")
    print(f"  Workarounds detected: {len(result['workarounds'])}")

    return result


def build_agent_prompt(task: dict, condition: str) -> str:
    """Build the prompt for the Claude Code agent."""
    base_prompt = f"""You are working on a Python codebase in the CURRENT WORKING DIRECTORY.
All file paths are relative to the current directory. Use relative paths only (e.g., src/users/manager.py, not absolute paths).

Task:
{task['description']}

Requirements:
- Use the Read and Edit tools to modify files. Do NOT use Bash to write files.
- Modify only the files necessary to complete the task.
- Ensure all existing tests continue to pass.
- Add new tests for your changes in the appropriate test file.
- Follow the existing code patterns and conventions.
- Do not modify any configuration files.
- Run the tests after your changes with: python -m pytest tests/ -v"""

    return base_prompt


def calculate_metrics(result: dict, baseline: dict, post: dict) -> dict:
    """Calculate quality metrics for a task run."""
    return {
        "compiles": post["returncode"] != 2,  # returncode 2 = collection error
        "tests_pass": post["failed"] == 0 and post["errors"] == 0,
        "tests_passed_count": post["passed"],
        "tests_failed_count": post["failed"],
        "regressions": max(0, baseline["passed"] - post["passed"]),
        "new_tests_added": max(0, post["passed"] - baseline["passed"]),
        "status": result.get("status", "completed"),
    }


def detect_file_changes(workdir: Path) -> list:
    """Detect which files were changed in the workspace."""
    # Compare with original codebase
    changes = []
    for root, dirs, files in os.walk(workdir / "src"):
        for f in files:
            if f.endswith(".py"):
                current = Path(root) / f
                relative = current.relative_to(workdir)
                original = CODEBASE_DIR / relative

                if not original.exists():
                    changes.append({"file": str(relative), "type": "added"})
                else:
                    with open(current) as c, open(original) as o:
                        if c.read() != o.read():
                            changes.append({"file": str(relative), "type": "modified"})

    # Check for new test files
    for root, dirs, files in os.walk(workdir / "tests"):
        for f in files:
            if f.endswith(".py"):
                current = Path(root) / f
                relative = current.relative_to(workdir)
                original = CODEBASE_DIR / relative

                if not original.exists():
                    changes.append({"file": str(relative), "type": "added"})
                else:
                    with open(current) as c, open(original) as o:
                        if c.read() != o.read():
                            changes.append({"file": str(relative), "type": "modified"})

    return changes


def detect_workarounds(task: dict, changes: list) -> list:
    """Detect if the agent wrote code outside the expected scope."""
    expected = set(task.get("expected_files", []))
    expected_test = task.get("expected_test_impact", "")

    workarounds = []
    for change in changes:
        f = change["file"].replace("\\", "/")
        # Normalize: remove leading src/ for comparison
        is_expected = any(f.endswith(e) or e in f for e in expected)
        is_test = expected_test in f or f.startswith("tests/")

        if not is_expected and not is_test and change["type"] in ("added", "modified"):
            workarounds.append({
                "file": f,
                "type": change["type"],
                "reason": "File modified outside expected scope"
            })

    return workarounds


def save_result(result: dict, result_dir: Path):
    """Save result to JSON file."""
    result_file = result_dir / "result.json"
    # Remove non-serializable items
    clean = {k: v for k, v in result.items()}
    with open(result_file, "w") as f:
        json.dump(clean, f, indent=2, default=str)


def analyze_results():
    """Analyze all results and produce summary statistics."""
    results = []
    for entry in sorted(RESULTS_DIR.iterdir()):
        result_file = entry / "result.json"
        if result_file.exists():
            with open(result_file) as f:
                results.append(json.load(f))

    if not results:
        print("No results found. Run experiments first.")
        return

    print(f"\n{'='*70}")
    print(f"  EXPERIMENT RESULTS ANALYSIS")
    print(f"  {len(results)} runs analyzed")
    print(f"{'='*70}\n")

    # Group by condition
    by_condition = {}
    for r in results:
        cond = r["condition"]
        if cond not in by_condition:
            by_condition[cond] = []
        by_condition[cond].append(r)

    # Summary per condition
    print(f"{'Condition':<12} {'Runs':<6} {'Tests Pass':<12} {'Regressions':<13} {'Workarounds':<13} {'Avg Time':<10}")
    print("-" * 66)

    condition_stats = {}
    for cond in sorted(by_condition.keys()):
        runs = by_condition[cond]
        n = len(runs)

        tests_pass = sum(1 for r in runs if r.get("metrics", {}).get("tests_pass", False))
        regressions = sum(r.get("metrics", {}).get("regressions", 0) for r in runs)
        workarounds = sum(len(r.get("workarounds", [])) for r in runs)
        avg_time = sum(r.get("elapsed_seconds", 0) for r in runs) / max(n, 1)

        condition_stats[cond] = {
            "n": n,
            "tests_pass_rate": tests_pass / max(n, 1),
            "total_regressions": regressions,
            "avg_regressions": regressions / max(n, 1),
            "total_workarounds": workarounds,
            "avg_workarounds": workarounds / max(n, 1),
            "avg_time": avg_time,
        }

        print(f"{cond:<12} {n:<6} {tests_pass}/{n:<10} {regressions:<13} {workarounds:<13} {avg_time:<10.1f}s")

    # Hidden pattern analysis
    print(f"\n{'='*70}")
    print(f"  HIDDEN PATTERN ANALYSIS")
    print(f"  Tasks that test non-obvious code patterns")
    print(f"{'='*70}\n")

    hidden_tasks = [r for r in results if r.get("task", {}).get("tests_hidden_pattern", False)]
    normal_tasks = [r for r in results if not r.get("task", {}).get("tests_hidden_pattern", False)]

    for task_type, task_list, label in [
        ("hidden", hidden_tasks, "Hidden pattern tasks"),
        ("normal", normal_tasks, "Normal tasks"),
    ]:
        print(f"\n  {label}:")
        for cond in sorted(by_condition.keys()):
            cond_tasks = [r for r in task_list if r["condition"] == cond]
            n = len(cond_tasks)
            if n == 0:
                continue
            passes = sum(1 for r in cond_tasks if r.get("metrics", {}).get("tests_pass", False))
            regs = sum(r.get("metrics", {}).get("regressions", 0) for r in cond_tasks)
            print(f"    {cond}: {passes}/{n} pass, {regs} regressions")

    # Per-task breakdown
    print(f"\n{'='*70}")
    print(f"  PER-TASK BREAKDOWN")
    print(f"{'='*70}\n")

    task_ids = sorted(set(r["task_id"] for r in results))
    print(f"{'Task':<6} {'Cat':<10} {'Diff':<8} {'Hidden':<8} ", end="")
    for cond in sorted(by_condition.keys()):
        print(f"{cond:<8}", end="")
    print()
    print("-" * (32 + 8 * len(by_condition)))

    for tid in task_ids:
        task_runs = [r for r in results if r["task_id"] == tid]
        if not task_runs:
            continue
        task = task_runs[0].get("task", {})
        cat = task.get("category", "?")[:9]
        diff = task.get("difficulty", "?")[:7]
        hidden = "yes" if task.get("tests_hidden_pattern") else "no"

        print(f"{tid:<6} {cat:<10} {diff:<8} {hidden:<8} ", end="")
        for cond in sorted(by_condition.keys()):
            cond_runs = [r for r in task_runs if r["condition"] == cond]
            if cond_runs:
                passes = sum(1 for r in cond_runs if r.get("metrics", {}).get("tests_pass", False))
                total = len(cond_runs)
                print(f"{passes}/{total:<6}", end="")
            else:
                print(f"{'—':<8}", end="")
        print()

    # Save analysis
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "total_runs": len(results),
        "condition_stats": condition_stats,
    }
    with open(RESULTS_DIR / "analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"\nAnalysis saved to {RESULTS_DIR / 'analysis.json'}")


def main():
    parser = argparse.ArgumentParser(description="Run MEMORY.md × Hooks experiment")
    parser.add_argument("--condition", default="A", help="Condition: A, B, C, D, or 'all'")
    parser.add_argument("--task", default="T01", help="Task ID (e.g., T01) or 'all'")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per task×condition")
    parser.add_argument("--dry-run", action="store_true", help="Setup workspaces without running agent")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing results")
    parser.add_argument("--list-tasks", action="store_true", help="List all tasks")

    args = parser.parse_args()

    if args.analyze:
        analyze_results()
        return

    tasks = load_tasks()

    if args.list_tasks:
        print(f"\n{'ID':<6} {'Category':<10} {'Difficulty':<10} {'Hidden':<8} Description")
        print("-" * 80)
        for t in tasks:
            hidden = "yes" if t.get("tests_hidden_pattern") else "no"
            desc = t["description"][:50] + "..." if len(t["description"]) > 50 else t["description"]
            print(f"{t['id']:<6} {t['category']:<10} {t['difficulty']:<10} {hidden:<8} {desc}")
        return

    # Determine conditions to run
    conditions = ["A", "B", "C", "D"] if args.condition == "all" else [args.condition]

    # Determine tasks to run
    if args.task == "all":
        task_list = tasks
    else:
        task_list = [t for t in tasks if t["id"] == args.task]
        if not task_list:
            print(f"Task {args.task} not found")
            return

    # Run experiment
    RESULTS_DIR.mkdir(exist_ok=True)
    total = len(conditions) * len(task_list) * args.runs
    current = 0

    print(f"\nExperiment: {len(conditions)} conditions × {len(task_list)} tasks × {args.runs} runs = {total} total runs")
    print(f"Conditions: {', '.join(conditions)}")
    print(f"Tasks: {', '.join(t['id'] for t in task_list)}")

    for run in range(1, args.runs + 1):
        for task in task_list:
            for condition in conditions:
                current += 1
                print(f"\n[{current}/{total}]", end="")
                run_single_task(condition, task, run, dry_run=args.dry_run)

    print(f"\n\n{'='*60}")
    print(f"  Experiment complete. {total} runs finished.")
    print(f"  Results in: {RESULTS_DIR}")
    print(f"  Run analysis with: python {__file__} --analyze")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
