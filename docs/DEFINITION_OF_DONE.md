# Definition of Done

Written before starting. Ticked at the end, each with the evidence next to it. Anything with no evidence stays unticked.

## Floor (items 1-4)

- [x] The endpoint returns the right counts for a known task. They match my script's count of the COCO JSON, or every difference is explained.
  Evidence: task #4 (first 1,000 val2017 images). The endpoint returns 8,109 against 7,204 COCO annotations. That's because CVAT imports every part of a COCO polygon as its own shape (8,022 parts) and every crowd region as one mask (87): 8,022 + 87 = 8,109. With that rule, all 80 classes match exactly:

      $ python utils/annotation_counts/compare_counts.py 4 expected_counts.json --password ***
      classes compared: 80, differing: 0
      total expected 8109, endpoint 8109
      (COCO objects in the JSON: 7204)

  My first guess (that the extra shapes shared a `group` id) was wrong: counting groups once gave 6,614, not 7,204. Counting polygon parts is what matched.
- [x] Labels with no annotations come back with a count of 0 and aren't left out.
  Evidence: `test_counts_shapes_per_label_and_keeps_empty_labels`. On task #4, `hair drier` is in the COCO categories but not in the first 1,000 images, and the endpoint returns it with 0 (80 labels returned, 79 used).
- [x] Ground truth jobs and skeleton child points aren't counted twice.
  Evidence: `test_ignores_ground_truth_jobs`, `test_counts_a_skeleton_once_not_per_point`.
- [ ] The page opens from the task page and shows the chart.
  Evidence: not yet checked in a browser. Route `/tasks/:tid/label-counts`, linked from Actions > Label counts. The UI passes `yarn type-check` and ESLint, and the image builds.
- [ ] A task with no annotations shows an empty message, not a blank chart.
  Evidence: not yet checked in a browser. The code path is the `total === 0` branch in `label-counts-page.tsx`.
- [ ] If the request fails (server stopped, or a 500), the page shows an error and Retry works once the server is back.
  Evidence: not yet checked in a browser.

## Access (item 5)

- [x] No login gets a 401.
  Evidence:

      $ curl http://localhost:8080/api/test/tasks/4/label-counts
      {"detail":"Authentication credentials were not provided."} [HTTP 401]

- [x] A logged-in user with no access to the task gets refused.
  Evidence:

      $ curl -u outsider:*** http://localhost:8080/api/test/tasks/4/label-counts
      {"detail":"You do not have permission to perform this action."} [HTTP 403]

  The WebSocket refuses the same way: no login closes with 4401, outsider with 4403, and a cross-origin page with 4403.
- [x] Unit tests cover both cases and pass.
  Evidence: `cvat/apps/test/tests/test_label_counts.py`, 9 tests, `Ran 9 tests in 3.404s OK`. Run inside `cvat_server` with OPA reachable.

## Speed (item 6)

- [x] Measured 5 times, raw output saved in the repo.
  Evidence: [OBJECTIVES.md](OBJECTIVES.md), baseline and after, 5 runs of 50 requests each.
- [x] Target met, or missed with the reason written down.
  Evidence: missed, 51.5 ms against 50 ms (down from 135.0 ms). The reason is in [OBJECTIVES.md](OBJECTIVES.md): a 40 ms floor that every CVAT endpoint has on this machine.

## Beyond the floor

- [x] Grouping by shape type works and I've said why I picked it. (item 7)
  Evidence: `test_breaks_counts_down_by_shape_type`. On task #4, `person` comes back as `{"polygon": 2447, "mask": 52}`. Why: a COCO import mixes polygons and crowd masks, and a single number per class hides that (commit "Break each label's count down by shape type").
- [ ] Saving an annotation in a job updates the open chart without a page refresh. (item 8)
  Evidence: the server side is verified with a socket client. A snapshot arrives on connect, and after saving a box through `PATCH /api/jobs/{id}/annotations` a new snapshot arrives within about 1.2 s with `car: 1`. Not yet checked in a browser with the chart open.
- [ ] After stopping and restarting the server, the page reconnects by itself and shows current numbers. (item 9)
  Evidence: not yet checked. The backoff, `online` handling and close codes are in `use-live-label-counts.ts`.
- [x] Decision record written in the Plan. (item 10)
  Evidence: [PLAN.md](PLAN.md), "Decision record".

## Housekeeping

- [x] No dead code, no commented-out blocks, no stray files in the diff.
  Evidence: searched the changed files for TODO, print and console.log and for commented-out code: nothing. The local compose override and the data stay outside the repo. Python passes the repo's black and isort settings; the UI passes ESLint and `type-check`.
- [x] Commits are small and each message says what changed and why.
  Evidence: `git log 28f5bffaf..dev-test01`. The plan was committed first and contains no code.
- [x] Everything I didn't finish is listed below, with the reason.
  Evidence: see "Not finished".
- [ ] PR opened from `dev-test01` into my own fork, not upstream CVAT.
  Evidence:

## Not finished

- **Browser checks for the page, empty state, error and Retry, live chart and reconnect.** These are written and the backend for them is verified, but I haven't watched them work in the browser yet. They stay unticked until I have.
- **No automated test for the WebSocket.** Django's test client can't open sockets. I checked it with a socket client script against the running stack instead, so a regression there would only show up by hand.
- **The 50 ms target.** Missed by 1.5 ms. See Objectives for why, and what I would measure instead.
- **No Cypress tests**, as planned. The UI is covered by type-check, lint and manual checks only.
- **`cvat/schema.yml` not regenerated.** The endpoint is described with `extend_schema`, but CVAT's checked-in OpenAPI schema doesn't include it yet.
