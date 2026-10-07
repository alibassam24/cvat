# Plan

Annotation counts per class for a CVAT task: an API, a page with a chart, and live updates if I get that far.

Branch `dev-test01`, forked from CVAT at commit `28f5bffaf1b66b81c1e908d3ae626047a54279b0`.

## What I'm building

A new Django app, `cvat/apps/test`, with one endpoint:

    GET /api/test/tasks/{id}/label-counts

It returns every label in the task with the number of annotations it has, labels with zero included. On the UI side, a new page reached from the task page that calls the endpoint and draws a horizontal bar chart, sorted by count. COCO has 80 classes, so vertical bars would be unreadable.

## Order and rough timing (8h)

| # | What | Time |
|---|------|------|
| 0 | Plan and DoD committed. Docker build and COCO import started in the background | 0:30 |
| 1 | Read the engine models and the annotation save path. Write the count query and the endpoint, with a unit test | 1:30 |
| 5 | Permissions: reuse CVAT's existing task "view" check rather than writing new policy rules. Check with curl as admin, as a user with no access, and with no login | 0:30 |
| 2-4 | UI page, chart, empty state, error state with a retry button | 1:30 |
| 6 | Measure the endpoint, try to improve it, write Objectives | 1:00 |
| 7 | Group by shape type (rectangle / polygon / mask) as a stacked bar | 0:30 |
| 8-9 | WebSocket push and reconnect | 1:45 |
| 10 | Decision record, finish docs, open the PR on my fork | 0:45 |

Items 1 to 4 come first and have to work before I touch anything else. If I'm behind at the 5-hour mark, I drop 8-9 and spend the time on tests and docs instead.

## Things I need to confirm in the code before relying on them

- How a task gets to its annotations. My guess is Task -> Segment -> Job -> LabeledShape -> Label, but I want to read `engine/models.py` before writing the query.
- Whether ground truth jobs need to be excluded from the count. I think they do, otherwise QA copies get counted twice.
- Whether skeleton points are stored as child shapes. If they are, I only count the parent.
- Whether the server runs under ASGI. If it doesn't, WebSockets need more setup than I've planned for.
- Annotations seem to be saved with `bulk_create`, which doesn't fire Django signals. So the live-update hook probably has to sit in the save code itself, not in a signal handler.

## Data

COCO 2017 val. My laptop has 15 GB of RAM and Docker needs about half of that, so I'll start with 1,000 images and only go higher if the stack stays responsive. I'll write the real number in Objectives.

To check the counts are right, I'll count the same images straight from `instances_val2017.json` with a small script and compare. I expect some differences, because a COCO object made of several polygons may come in as several shapes. If that happens I'll explain it rather than hide it.

## Not doing

- New permission rules. Reusing the existing task view check is safer and less code.
- Video tracks in any depth. The COCO data has none. A track counts as one annotation and I'll note that.
- Cypress end-to-end tests. Backend unit tests plus manual checks with saved output.
- Translations, mobile layout, export of the chart.

## Decision record

**Live updates: push a full snapshot, produced by the REST endpoint itself.**

What I did: every annotation save already ends with `task.touch()`, so a `post_save` receiver on Task publishes the task id to Redis after commit. The socket is a small ASGI wrapper in front of Django. When it hears about a change it runs `GET .../label-counts` in-process with the client's own cookies and sends the response body as is.

What I rejected: Django Channels, with the server computing what changed and pushing deltas.

Why: Channels isn't in the image, so it meant a new dependency, a server image rebuild (on a 15 GB laptop that was already running out of memory building the UI), and a second login and permission path to keep in step with the REST one. Deltas also need the client to have seen every message. With snapshots, a client that was offline is correct again after the first message, so reconnecting (item 9) is just opening the socket again.

What it cost: every change makes every open page run the count query once, instead of the server sending a few bytes. Ten people watching a task during an import means ten queries per change. The 300 ms debounce helps, because an import touches the task once per job, but it doesn't remove the cost. If that ever mattered I would cache the counts per task and clear the cache from the same signal.

Smaller decisions:
- Permissions reuse the task "view" rule instead of a new rego file. Less to maintain, and it can't drift from what the task page allows.
- The page calls the API through `core.server.request` rather than a new typed method in cvat-core. That's one file instead of four, but the response type is declared by hand in the page.

## Changes to this plan

- I did items 7, 8 and 9 before item 6. Measuring needs the COCO task, and the dataset wasn't extracted yet, so I moved on to the work that didn't depend on it instead of waiting.
- Setup took longer than the 0:30 I planned. `yarn install` fails on Windows (it can't create workspace symlinks), so the UI is built in Docker with CVAT's own `Dockerfile.ui`. The webpack build ran Docker out of memory while the stack was up, so I stop the stack for each UI build. That's slow, so I batched UI changes together.
- The plan didn't mention linting. I ran the repo's ESLint, black and isort over my files. ESLint caught one indentation mistake in an earlier commit, which I fixed in its own commit.
