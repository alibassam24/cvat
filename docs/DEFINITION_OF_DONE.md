# Definition of Done

Written before starting. Ticked at the end, each with the evidence next to it. Anything with no evidence stays unticked.

## Floor (items 1-4)

- [ ] The endpoint returns the right counts for a known task. They match my script's count of the COCO JSON, or every difference is explained.
  Evidence:
- [ ] Labels with no annotations come back with a count of 0 and aren't left out.
  Evidence:
- [ ] Ground truth jobs and skeleton child points aren't counted twice.
  Evidence:
- [ ] The page opens from the task page and shows the chart.
  Evidence:
- [ ] A task with no annotations shows an empty message, not a blank chart.
  Evidence:
- [ ] If the request fails (server stopped, or a 500), the page shows an error and Retry works once the server is back.
  Evidence:

## Access (item 5)

- [ ] No login gets a 401.
  Evidence:
- [ ] A logged-in user with no access to the task gets refused.
  Evidence:
- [ ] Unit tests cover both cases and pass.
  Evidence:

## Speed (item 6)

- [ ] Measured 5 times, raw output saved in the repo.
  Evidence:
- [ ] Target met, or missed with the reason written down.
  Evidence:

## Beyond the floor

- [ ] Grouping by shape type works and I've said why I picked it. (item 7)
  Evidence:
- [ ] Saving an annotation in a job updates the open chart without a page refresh. (item 8)
  Evidence:
- [ ] After stopping and restarting the server, the page reconnects by itself and shows current numbers. (item 9)
  Evidence:
- [ ] Decision record written in the Plan. (item 10)
  Evidence:

## Housekeeping

- [ ] No dead code, no commented-out blocks, no stray files in the diff.
  Evidence:
- [ ] Commits are small and each message says what changed and why.
  Evidence:
- [ ] Everything I didn't finish is listed below, with the reason.
  Evidence:
- [ ] PR opened from `dev-test01` into my own fork, not upstream CVAT.
  Evidence:

## Not finished

(filled in at the end)
