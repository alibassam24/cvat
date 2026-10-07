# Objectives

## Machine

| | |
|---|---|
| CPU | Intel Core Ultra 5 135U |
| RAM | 15 GB (Docker Desktop on WSL2, `<N>` GB given to the VM) |
| OS | Windows 11 Pro |
| CVAT commit | `28f5bffaf1b66b81c1e908d3ae626047a54279b0` |
| Data | COCO 2017 val, `<N>` images, `<N>` annotations after import |

## MO-1: endpoint response time

| Field | Entry |
|---|---|
| What is measured | Time for `GET /api/test/tasks/{id}/label-counts` to return a full response, measured from the client. |
| How | `scripts/bench_label_counts.py`, committed with the code. One run is 5 warm-up requests followed by 50 timed requests, one after another, logged in as admin. I record the median and p95 for each run. I do 5 runs. |
| Target | Median of the 5 run medians at or below 50 ms, on a task with about 10x the imported data (roughly `<N>` shapes). |
| Conditions | Local Docker stack, nothing else heavy running, laptop plugged in. Requests go through Traefik on localhost:8080, the same way the UI makes them. |
| Not included | The first request after a server restart, and browser render time. |

Why this number: with 1,000 images the query will probably return in a few milliseconds whatever I do, so a target on that data alone wouldn't prove anything. The 10x task is there to make the query work hard enough that indexes and query shape actually matter. 50 ms is roughly where a chart refresh still feels instant after a live update. I'll measure the baseline first and write it down before changing anything.

### Results

Baseline, before any optimisation:

    (raw output)

After:

    (raw output)

| | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Median | Spread |
|---|---|---|---|---|---|---|---|
| Baseline | | | | | | | |
| After | | | | | | | |

What I changed and why it helped (or didn't):
