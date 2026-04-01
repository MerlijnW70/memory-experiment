#!/usr/bin/env python3
"""Analyze tool call sequences from experiment transcripts."""

import json
import os

conditions = {
    'A': 'ad67933d-3703-4977-b1f7-c120ce5f44bd',
    'B': '28dc4ee2-8658-4207-966c-d11a37071d6a',
    'C': '38fbd501-7733-4bd3-8b4a-19dfd96a70b7',
    'D': '7269248c-30aa-47a9-8133-cdd3c890b42d',
    'E': 'dfeebab0-dec8-4bea-917b-98ad09970a69',
    'F': 'f76968de-0c68-4acd-aa8d-867025db5219',
}

for cond, sid in conditions.items():
    path = os.path.join(
        os.path.expanduser("~"), ".claude", "projects",
        f"D--memory-experiment-results-{cond}-T04-run1-workspace",
        f"{sid}.jsonl"
    )
    print(f"=== Condition {cond}: Tool call sequence ===")

    tools = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                obj = json.loads(line)
                if obj.get("type") == "assistant":
                    content = obj.get("message", {}).get("content", [])
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name", "")
                            inp = block.get("input", {})
                            fp = inp.get("file_path", "")
                            pat = inp.get("pattern", "")
                            cmd = inp.get("command", "")[:80] if inp.get("command") else ""

                            # Simplify path
                            detail = fp
                            for sep in ["workspace\\", "workspace/"]:
                                if sep in detail:
                                    detail = detail.split(sep)[-1]

                            if not detail:
                                detail = pat or cmd

                            # Classify
                            if name in ("Read", "Glob", "Grep"):
                                action = "READ "
                            elif name in ("Edit", "Write"):
                                action = "WRITE"
                            elif name == "Bash":
                                action = "BASH "
                            else:
                                action = name[:5]

                            tools.append((action, name, detail))
    except FileNotFoundError:
        print(f"  Transcript not found: {path}")
        print()
        continue

    for i, (action, name, detail) in enumerate(tools, 1):
        print(f"  {i:2d}. [{action}] {name:5s}  {detail}")

    # Analysis
    reads_before_write = 0
    files_read = set()
    files_written = set()
    first_write_idx = None

    for i, (action, name, detail) in enumerate(tools):
        fname = detail.replace("\\", "/").split("/")[-1] if detail else ""
        if action == "READ ":
            files_read.add(fname)
            if first_write_idx is None:
                reads_before_write += 1
        elif action == "WRITE":
            files_written.add(fname)
            if first_write_idx is None:
                first_write_idx = i

    read_auth = any("tokens" in t[2] for t in tools if t[0] == "READ ")
    read_perms = any("permissions" in t[2] for t in tools if t[0] == "READ ")
    read_processor = any("processor" in t[2] for t in tools if t[0] == "READ ")

    print(f"\n  --- Analysis ---")
    print(f"  Total tool calls:            {len(tools)}")
    print(f"  Reads before first write:    {reads_before_write}")
    print(f"  Unique files read:           {sorted(files_read)}")
    print(f"  Unique files written:        {sorted(files_written)}")
    print(f"  Read auth/tokens.py:         {read_auth}  (thread-local pattern)")
    print(f"  Read auth/permissions.py:    {read_perms}")
    print(f"  Read payments/processor.py:  {read_processor}  (current_user usage)")
    print()
