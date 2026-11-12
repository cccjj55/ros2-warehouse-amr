"""Splice a benchmark summary into the README benchmark block.

    python3 scripts/render_bench_table.py docs/benchmarks/latest.json

Rewrites the text between ``<!-- BENCH:START -->`` and ``<!-- BENCH:END -->`` in
README.md so that every number in the table comes from a committed artifact
rather than from memory.
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'warehouse_amr_mission'))

from warehouse_amr_mission.metrics import render_readme_block  # noqa: E402

START, END = '<!-- BENCH:START -->', '<!-- BENCH:END -->'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('summary_json', help='output of bench_goals / write_summary')
    parser.add_argument('--readme', default=os.path.join(ROOT, 'README.md'))
    args = parser.parse_args()

    import json

    with open(args.summary_json, encoding='utf-8') as fh:
        payload = json.load(fh)
    block = render_readme_block(payload['summary'], payload.get('meta'))

    with open(args.readme, encoding='utf-8') as fh:
        text = fh.read()
    if START not in text or END not in text:
        print(f'error: {START} / {END} markers missing from {args.readme}', file=sys.stderr)
        return 2

    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    with open(args.readme, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(head + block + tail)

    print(f'updated {args.readme} from {args.summary_json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
