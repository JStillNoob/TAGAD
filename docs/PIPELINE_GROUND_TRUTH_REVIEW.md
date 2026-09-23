# TAGAD Pilot Ground-Truth Review

This worksheet is the remaining human-validation step for the three short
camera-angle clips. The training handoff explicitly states that there is no
validated combined end-to-end five-state accuracy yet; software output alone
cannot establish it.

## Review rules

- Watch the complete time window, not one still frame.
- Count only students whose behavior can be judged from that camera.
- Use `Uncertain` instead of forcing a state when the evidence is unclear.
- Do not identify or name students.
- Do not add counts from different cameras; the same student may appear in more
  than one view.
- If possible, have two people complete separate copies before comparing notes.

## Labels

- Engaged
- Attentive
- Confused
- Bored
- Disengaged
- Uncertain / not visible enough to label

## Reviewer 1

Reviewer: ____________________  Date: ____________________

| Camera | Window | Engaged | Attentive | Confused | Bored | Disengaged | Uncertain | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Center | 0–5 s |  |  |  |  |  |  |  |
| Center | 5–10 s |  |  |  |  |  |  |  |
| Center | 10–15 s |  |  |  |  |  |  |  |
| Center | 15–15.7 s |  |  |  |  |  |  |  |
| Left | 0–5 s |  |  |  |  |  |  |  |
| Left | 5–8.7 s |  |  |  |  |  |  |  |
| Right | 0–5 s |  |  |  |  |  |  |  |
| Right | 5–7.7 s |  |  |  |  |  |  |  |

## Reviewer 2

Reviewer: ____________________  Date: ____________________

| Camera | Window | Engaged | Attentive | Confused | Bored | Disengaged | Uncertain | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Center | 0–5 s |  |  |  |  |  |  |  |
| Center | 5–10 s |  |  |  |  |  |  |  |
| Center | 10–15 s |  |  |  |  |  |  |  |
| Center | 15–15.7 s |  |  |  |  |  |  |  |
| Left | 0–5 s |  |  |  |  |  |  |  |
| Left | 5–8.7 s |  |  |  |  |  |  |  |
| Right | 0–5 s |  |  |  |  |  |  |  |
| Right | 5–7.7 s |  |  |  |  |  |  |  |

## Agreement and comparison

- [ ] Resolve or retain reviewer disagreements explicitly.
- [ ] Compare agreed labels with the aggregate pipeline segments in
      `pipeline/benchmark_results/three_angle_benchmark.json`.
- [ ] Record distribution agreement and obvious disagreements without calling
      them precision, recall, or F1. Aggregate counts cannot produce paired
      per-student classification metrics.
- [ ] Record limitations caused by blur, side profiles, distance, and occlusion.
- [ ] Do not publish an accuracy claim from these short clips alone.

Per-state precision, recall, and F1 require a separate ethically reviewed pilot
whose ground-truth labels are paired with individual anonymized samples. They
cannot be calculated honestly from these aggregate-only benchmark results.
