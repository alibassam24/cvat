# SPDX-License-Identifier: MIT

"""
Make a task N times heavier for load testing: every shape in every job is copied
N - 1 more times through the public annotations API. The copies are exact duplicates,
which is fine for timing the count query, but not for anything that looks at geometry.
"""

import argparse
import base64
import json
import urllib.request

SHAPE_SERVER_FIELDS = ("id", "elements")


def api(url: str, auth: str, method: str = "GET", body=None):
    request = urllib.request.Request(
        url,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("task_id", type=int)
    parser.add_argument("--factor", type=int, default=10)
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    auth = "Basic " + base64.b64encode(f"{args.user}:{args.password}".encode()).decode()
    jobs = api(f"{args.url}/api/jobs?task_id={args.task_id}&page_size=1000", auth)["results"]

    for job in jobs:
        annotations = api(f"{args.url}/api/jobs/{job['id']}/annotations", auth)
        shapes = [
            {key: value for key, value in shape.items() if key not in SHAPE_SERVER_FIELDS}
            for shape in annotations["shapes"]
        ]
        copies = shapes * (args.factor - 1)
        api(
            f"{args.url}/api/jobs/{job['id']}/annotations?action=create",
            auth,
            method="PATCH",
            body={"version": 0, "shapes": copies, "tracks": [], "tags": []},
        )
        print(f"job {job['id']}: {len(shapes)} shapes, added {len(copies)}")


if __name__ == "__main__":
    main()
