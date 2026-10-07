# SPDX-License-Identifier: MIT

"""
Compare GET /api/test/tasks/{id}/label-counts with the per-class shape counts in
expected_counts.json written by prepare_coco_subset.py. Prints every class that differs
and the totals.
"""

import argparse
import base64
import json
import urllib.request
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("task_id", type=int)
    parser.add_argument("expected", type=Path, help="expected_counts.json")
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    token = base64.b64encode(f"{args.user}:{args.password}".encode()).decode()
    request = urllib.request.Request(
        f"{args.url}/api/test/tasks/{args.task_id}/label-counts",
        headers={"Authorization": f"Basic {token}"},
    )
    with urllib.request.urlopen(request) as response:
        actual = json.load(response)

    expected_counts = json.loads(args.expected.read_text())
    expected = expected_counts["per_class_shapes"]
    by_name = {label["name"]: label for label in actual["labels"]}

    mismatches = 0
    for name in sorted(set(expected) | set(by_name)):
        want = expected.get(name, 0)
        got = by_name[name]["count"] if name in by_name else None
        if got != want:
            mismatches += 1
            breakdown = by_name[name]["by_type"] if name in by_name else {}
            print(f"{name:<16} expected {want:>5}  endpoint {got}  by type {breakdown}")

    print(f"classes compared: {len(set(expected) | set(by_name))}, differing: {mismatches}")
    print(f"total expected {sum(expected.values())}, endpoint {actual['total']}")
    print(f"(COCO objects in the JSON: {expected_counts['annotations']})")


if __name__ == "__main__":
    main()
