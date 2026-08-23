#!/usr/bin/env python
"""Extract per-agent read metrics from subagent transcript JSONL.

THE INSTRUMENT for the task-tool trial (docs/tasktool-trial-protocol.md section 4). It
answers "how much did this agent read, and what did it open" from the RECORD of what the
agent did, never from the agent's account of it.

WHY NOT ASK THE AGENT. During the tool's build, nine of ten verifier agents reported
success over report files that were never written to disk, and a separate pass silently
checked 90 of 98 files while reading green. A model's report of its own behaviour is
generated text with the same confidence whether or not it is true; a `tool_use` block is
a record of a call that actually happened. Only the second is evidence.

WHAT IT DELIBERATELY DOES NOT PRINT: any transcript CONTENT. The caller is an agent with
a context window, the transcripts run to hundreds of KB, and an instrument that overflows
the analyst is not an instrument. Aggregates and short path lists only.

M3 IS THE METRIC THE TRIAL TURNS ON -- did a TREE-arm agent open `HANDOFF.md` anyway. It
is matched against the ROOT board specifically: `formal/HANDOFF.md` is a different file
with a different job (the proof frontier), every formal item is SUPPOSED to point at it,
and counting it as a board read would report the treatment arm as having fallen back to
the control when it did the correct thing. The negative lookbehind is that distinction.

Usage:
    python scripts/trial_metrics.py <dir> --map <agentid>=<arm>:<model> [...]
    python scripts/trial_metrics.py <dir>            # no map: report every transcript
"""
from __future__ import print_function

import argparse
import collections
import json
import os
import re
import sys

# Root HANDOFF.md only. `(?<!formal/)` and `(?<!formal\\)` cover both path separators,
# because these transcripts are written on Windows and carry both forms.
ROOT_BOARD = re.compile(r'(?<!formal/)(?<!formal\\)\bHANDOFF\.md\b')
TASK_PY = re.compile(r'task\.py\b')
STUB = re.compile(r'tasktool-trial-stub\.md\b')


def _text_of(inp):
    """Every string a tool call was given, joined -- path, command, pattern alike.

    Flattened rather than read per-tool by name: a new read-ish tool (or a rename) would
    otherwise silently stop being counted, and a metric that quietly stops observing is
    the failure mode this whole project is organised around.
    """
    if not isinstance(inp, dict):
        return ''
    out = []
    for v in inp.values():
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, (list, tuple)):
            out.extend(x for x in v if isinstance(x, str))
    return '\n'.join(out)


def scan(path):
    tools = collections.Counter()
    result_bytes = 0
    n_results = 0
    opened_board = 0
    ran_task_py = 0
    opened_stub = 0
    files = set()
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            msg = ev.get('message') or {}
            content = msg.get('content')
            if not isinstance(content, list):
                continue
            for blk in content:
                if not isinstance(blk, dict):
                    continue
                if blk.get('type') == 'tool_use':
                    tools[blk.get('name')] += 1
                    t = _text_of(blk.get('input'))
                    if ROOT_BOARD.search(t):
                        opened_board += 1
                    if TASK_PY.search(t):
                        ran_task_py += 1
                    if STUB.search(t):
                        opened_stub += 1
                    fp = (blk.get('input') or {}).get('file_path')
                    if isinstance(fp, str):
                        files.add(os.path.basename(fp))
                elif blk.get('type') == 'tool_result':
                    n_results += 1
                    c = blk.get('content')
                    result_bytes += len(c) if isinstance(c, str) else len(json.dumps(c))
    return {
        'M1_result_bytes': result_bytes,
        'M2_tool_calls': sum(tools.values()),
        'M3_board_opens': opened_board,
        'M4_task_py_calls': ran_task_py,
        'stub_opens': opened_stub,
        'n_results': n_results,
        'tools': dict(tools),
        'files_read': sorted(files),
    }


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dir', help='directory holding <agentid>.output transcripts')
    ap.add_argument('--map', nargs='*', default=[],
                    help='agentid=ARM:MODEL, repeatable')
    args = ap.parse_args(argv)

    label = {}
    for item in args.map:
        aid, _, rest = item.partition('=')
        label[aid] = rest or '?:?'

    rows = []
    empty = []
    for name in sorted(os.listdir(args.dir)):
        if not name.endswith('.output'):
            continue
        aid = name[:-len('.output')]
        if label and aid not in label:
            continue
        path = os.path.join(args.dir, name)
        m = scan(path)
        m['agent'] = aid[:8]
        m['label'] = label.get(aid, '?:?')
        # AN UNREADABLE SUBJECT IS AN INSTRUMENT FAILURE, NOT A MEASUREMENT OF ZERO.
        # Observed 2026-08-23, first run of this script: all four pilot transcripts were
        # 0 bytes on disk while a fifth from the same directory held 416 KB, and the
        # script printed `0 bytes, 0 calls, 0 board-opens` for each and exited 0. Every
        # number was false and the table looked like a result -- a clean-reading report
        # over subjects that were never observed, which is this repo's house failure mode
        # committed by the measuring device itself. Refuse instead: a trial arm that
        # cannot be measured has to be visibly missing from the table, because a zero is
        # indistinguishable from "read nothing at all", which is a real and interesting
        # outcome that this would silently forge.
        if os.path.getsize(path) == 0 or m['M2_tool_calls'] == 0:
            empty.append((m['label'], aid[:8], os.path.getsize(path)))
            continue
        rows.append(m)

    if empty:
        print('REFUSED: %d transcript(s) yielded no observations -- NOT measured as zero:'
              % len(empty))
        for lab, aid, size in empty:
            print('  %-14s %-8s %d bytes on disk, 0 tool_use blocks parsed' % (lab, aid, size))
        print('  A transcript that was never written is an instrument failure. Use the '
              'harness-reported usage (tokens / tool_uses / duration) for these agents, '
              'or re-run them; do not report them as low-read.')
        print('')

    if not rows:
        print('no measurable transcripts matched')
        return 1

    print('%-14s %-8s %10s %6s %6s %7s  %s'
          % ('label', 'agent', 'bytes', 'calls', 'board', 'task.py', 'files read'))
    for r in sorted(rows, key=lambda r: r['label']):
        print('%-14s %-8s %10d %6d %6d %7d  %s'
              % (r['label'], r['agent'], r['M1_result_bytes'], r['M2_tool_calls'],
                 r['M3_board_opens'], r['M4_task_py_calls'],
                 ','.join(r['files_read'][:6]) or '-'))

    by_arm = collections.defaultdict(list)
    for r in rows:
        by_arm[r['label']].append(r)
    print('')
    for lab in sorted(by_arm):
        g = by_arm[lab]
        b = sorted(x['M1_result_bytes'] for x in g)
        med = b[len(b) // 2] if len(b) % 2 else (b[len(b) // 2 - 1] + b[len(b) // 2]) / 2.0
        print('%-14s n=%d  median bytes %9.0f  range %d..%d  board-opens %s'
              % (lab, len(g), med, b[0], b[-1],
                 sum(1 for x in g if x['M3_board_opens'])))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
