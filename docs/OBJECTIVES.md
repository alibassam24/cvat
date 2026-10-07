# Objectives

## Machine

| | |
|---|---|
| CPU | Intel Core Ultra 5 135U |
| RAM | 15 GB (Docker Desktop 29.8.0 on WSL2, 7.5 GiB and 14 CPUs given to the VM) |
| OS | Windows 11 Pro, build 26200 |
| CVAT commit | `28f5bffaf1b66b81c1e908d3ae626047a54279b0` |
| Data | COCO 2017 val, first 1,000 images by file name: 7,204 COCO annotations, which CVAT stores as 8,109 shapes (task #4). Load task: the same images with every shape copied 10 times, 81,090 shapes (task #5). |

## MO-1: endpoint response time

| Field | Entry |
|---|---|
| What is measured | Time for `GET /api/test/tasks/{id}/label-counts` to return a full response, measured from the client. |
| How | `utils/annotation_counts/bench_label_counts.py`, committed with the code. One run is 5 warm-up requests followed by 50 timed requests, one after another, logged in as admin. I record the median and p95 for each run. I do 5 runs. |
| Target | Median of the 5 run medians at or below 50 ms, on a task with about 10x the imported data (81,090 shapes). |
| Conditions | Local Docker stack, nothing else heavy running, laptop plugged in. Requests go through Traefik on localhost:8080, the same way the UI makes them. |
| Not included | The first request after a server restart, and browser render time. |

Why this number: with 1,000 images the query will probably return in a few milliseconds whatever I do, so a target on that data alone wouldn't prove anything. The 10x task is there to make the query work hard enough that indexes and query shape actually matter. 50 ms is roughly where a chart refresh still feels instant after a live update. I'll measure the baseline first and write it down before changing anything.

### Results

**Target missed: 51.5 ms against 50 ms.** It came down from 135.0 ms, but the last few milliseconds aren't in my code.

Baseline on the 10x task (task #5), before any optimisation:

    GET /api/test/tasks/5/label-counts  session cookie  runs=5 warmup=5 requests=50
    run 1: median 135.8 ms  p95 183.7 ms  min 120.1 ms  max 203.4 ms
    run 2: median 138.1 ms  p95 155.2 ms  min 122.9 ms  max 228.0 ms
    run 3: median 135.0 ms  p95 150.7 ms  min 112.1 ms  max 174.2 ms
    run 4: median 102.2 ms  p95 141.8 ms  min 85.7 ms  max 162.2 ms
    run 5: median 103.1 ms  p95 125.1 ms  min 84.5 ms  max 125.4 ms
    median of run medians: 135.0 ms  spread: 102.2-138.1 ms

After caching:

    GET /api/test/tasks/5/label-counts  session cookie  runs=5 warmup=5 requests=50
    run 1: median 50.3 ms  p95 60.0 ms  min 42.6 ms  max 73.8 ms
    run 2: median 51.5 ms  p95 58.7 ms  min 42.9 ms  max 234.6 ms
    run 3: median 51.9 ms  p95 58.5 ms  min 42.7 ms  max 93.8 ms
    run 4: median 49.8 ms  p95 60.5 ms  min 42.5 ms  max 66.7 ms
    run 5: median 54.3 ms  p95 63.7 ms  min 43.6 ms  max 66.0 ms
    median of run medians: 51.5 ms  spread: 49.8-54.3 ms

| | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Median | Spread |
|---|---|---|---|---|---|---|---|
| Baseline (10x) | 135.8 | 138.1 | 135.0 | 102.2 | 103.1 | 135.0 | 102.2-138.1 |
| After (10x) | 50.3 | 51.5 | 51.9 | 49.8 | 54.3 | 51.5 | 49.8-54.3 |
| After (1x, task #4) | 52.6 | 52.1 | 52.0 | 54.2 | 50.7 | 52.1 | 50.7-54.2 |

**What I got wrong first.** My first run used Basic auth and gave 421 ms on the *small* task. Django hashes the password on every Basic-auth request: one `check_password` took 351 ms in the container (PBKDF2), while `count_annotations_by_label` on the same task took 13 ms. The browser logs in once and sends a session cookie, so the script now does that too. `--basic-auth` is still there, because API clients using it really do pay that cost.

**Where the time went.** `EXPLAIN ANALYZE` on the 10x task showed the shapes query taking 63 ms. It found the rows through the `job_id` index but then read 4,358 heap pages for 81,090 rows, just to get `label_id` and `type`.

**What I changed.** The per-label counts are cached in CVAT's Redis cache, keyed on `task.updated_date`. Every annotation write ends with `task.touch()`, so the key changes whenever the counts can, whichever process made the change. Label names and colors are still read fresh, because editing a label doesn't touch the task.

**What I didn't do.** A covering index on `(job_id, label_id, type)` would have allowed an index-only scan. But it adds an index to CVAT's busiest write table, slowing every shape save in order to speed up a read that is now cached.

**Why it still misses.** The rest is per-request cost that every CVAT endpoint pays on this machine. Same method, same session, 5 runs of 50:

    /api/users/self                    run medians [40.3, 40.6, 41.7, 40.3, 40.6]  median 40.6 ms
    /api/tasks/5                       run medians [62.5, 61.6, 60.7, 61.3, 60.7]  median 61.3 ms
    /api/test/tasks/5/label-counts     run medians [56.9, 52.8, 53.9, 50.8, 54.8]  median 53.9 ms

`/api/users/self` does almost nothing and still takes 40 ms through Docker Desktop, Traefik, nginx and uvicorn. On top of that floor, the label counts endpoint adds about 11 ms: one OPA policy call, one cache read and the labels query. That's less than CVAT's own task detail endpoint. I set 50 ms before I knew the floor was 40 ms on this laptop. If I set it again, I would make the target relative to that floor (for example, no more than 15 ms above `/api/users/self`), so it measures my code and not the machine.

The "Why this number" paragraph above also guessed that the query would take a few milliseconds whatever I did. On the 1x task it was 13 ms, which is close. At 10x it was 63 ms, which is why the cache was worth adding.
