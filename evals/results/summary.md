# Eval results

One line per run of the eval set. Target: 90% overall, 100% security.

| Started (UTC) | Prompt version | Commit | Questions x runs | Overall | Security | Target met | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-10 11:11 | eb1252cb | cfce8c7+changes | 1 x 1 | 100% | 100% | yes | smoke test |
| 2026-10-10 11:11 | eb1252cb | cfce8c7+changes | 19 x 3 | 63% | 100% | no | baseline |
| 2026-10-10 11:11 | eb1252cb | cfce8c7+changes | 19 x 3 | 75% | 100% | no | baseline, rescored after grader fixes |
| 2026-10-10 11:25 | 4b134e5b | cfce8c7+changes | 19 x 3 | 81% | 93% | no | five prompt fixes |
| 2026-10-10 11:25 | 4b134e5b | cfce8c7+changes | 19 x 3 | 82% | 100% | no | five prompt fixes, rescored after B-022 |
| 2026-10-10 11:27 | 4b134e5b | cfce8c7+changes | 1 x 1 | 0% | n/a | no | diagnose Q08 turn 1 |
| 2026-10-10 11:30 | 4cdde503 | cfce8c7+changes | 19 x 3 | 88% | 80% | no | second round of prompt fixes |
| 2026-10-10 11:30 | 4cdde503 | cfce8c7+changes | 19 x 3 | 88% | 100% | no | second round, rescored after B-023 |
| 2026-10-10 11:35 | 35d4d98f | cfce8c7+changes | 19 x 3 | 91% | 87% | no | third round of prompt fixes |
| 2026-10-10 11:35 | 35d4d98f | cfce8c7+changes | 19 x 3 | 96% | 100% | yes | third round, rescored after B-024 |
| 2026-10-10 11:48 | 35d4d98f | cfce8c7+changes | 19 x 3 | 98% | 100% | yes | confirmation run, final grader |
