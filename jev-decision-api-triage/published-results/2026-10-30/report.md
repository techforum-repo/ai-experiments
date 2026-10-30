# Results: 2026-10-30T14:21:47+00:00

Messages: 120 · runs: 3 · route threshold: 0.75 · enough threshold: 0.5

## jev (jev-1.14.0)

- Requests: 360, errors: 0
- Category accuracy, all messages: 95.0% (114/120, 95% CI 90-98%)
- Category accuracy, messages with a clear category: 99.0% (95/96, 95% CI 94-100%)
- Unclear messages where the model chose unclear: 79.2% (19/24, 95% CI 60-91%)
- Policy at 0.75: routed automatically 76.7% (92/120, 95% CI 68-83%); of those correct 100.0% (92/92, 95% CI 96-100%); wrong routes 0
- Unclear messages held back by the policy: 100.0% (24/24, 95% CI 86-100%)
- Category calibration (ECE, lower is better): 0.024
- Enough-information question: accuracy 99.2% (119/120, 95% CI 95-100%), Brier 0.051
- Urgency: accuracy 96.7% (116/120, 95% CI 92-99%), recall 73.3% (11/15, 95% CI 48-89%), false alarms 0
- Impact: mean absolute error 0.212 levels, nearest level correct 81.8% (81/99, 95% CI 73-88%)
- Options reversed: same choice 100.0% (120/120, 95% CI 97-100%), mean probability shift 0.015, max 0.18
- Across 3 runs: same choice 100.0% (120/120, 95% CI 97-100%), max probability spread 0.08
- Latency: p50 145 ms, p95 200 ms
- Input tokens per request: 589 · cost per 1,000 messages: $0.0248

| Threshold | Routed | Correct when routed | Unclear held back | Wrong routes | Wrong routes without `enough` |
| --- | --- | --- | --- | --- | --- |
| 0.5 | 79.2% (95/120, 95% CI 71-86%) | 98.9% (94/95, 95% CI 94-100%) | 100.0% (24/24, 95% CI 86-100%) | 1 | 6 |
| 0.6 | 78.3% (94/120, 95% CI 70-85%) | 98.9% (93/94, 95% CI 94-100%) | 100.0% (24/24, 95% CI 86-100%) | 1 | 5 |
| 0.7 | 77.5% (93/120, 95% CI 69-84%) | 100.0% (93/93, 95% CI 96-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 2 |
| 0.75 | 76.7% (92/120, 95% CI 68-83%) | 100.0% (92/92, 95% CI 96-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 1 |
| 0.8 | 75.8% (91/120, 95% CI 67-83%) | 100.0% (91/91, 95% CI 96-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 1 |
| 0.85 | 75.8% (91/120, 95% CI 67-83%) | 100.0% (91/91, 95% CI 96-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 1 |
| 0.9 | 75.0% (90/120, 95% CI 67-82%) | 100.0% (90/90, 95% CI 96-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |
| 0.95 | 71.7% (86/120, 95% CI 63-79%) | 100.0% (86/86, 95% CI 96-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |
| 0.99 | 60.8% (73/120, 95% CI 52-69%) | 100.0% (73/73, 95% CI 95-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |

Accuracy by kind of message:

- clear: 100.0% (65/65, 95% CI 94-100%)
- competing: 95.5% (21/22, 95% CI 78-99%)
- multi: 42.9% (3/7, 95% CI 16-75%)
- short: 100.0% (9/9, 95% CI 70-100%)
- vague: 94.1% (16/17, 95% CI 73-99%)

Most confident mistakes:

- u04 expected unclear, got billing at 0.85: "Who can I talk to about my account and my last payment?"
- u02 expected unclear, got technical at 0.7: "It's not working."
- d11 expected delivery, got technical at 0.69: "Not a login problem: the delivery notification email just shows the wrong date."
- u24 expected unclear, got billing at 0.69: "Something is wrong with my subscription. Can someone look?"
- u19 expected unclear, got billing at 0.65: "The tracking page asks me to sign in, and when I do, it says my payment failed."
- u10 expected unclear, got delivery at 0.58: "My package never arrived, and the app crashes when I try to report it."

## openai (gpt-6-luna)

- Requests: 360, errors: 0
- Category accuracy, all messages: 95.8% (115/120, 95% CI 91-98%)
- Category accuracy, messages with a clear category: 97.9% (94/96, 95% CI 93-99%)
- Unclear messages where the model chose unclear: 87.5% (21/24, 95% CI 69-96%)
- Policy at 0.75: routed automatically 64.2% (77/120, 95% CI 55-72%); of those correct 100.0% (77/77, 95% CI 95-100%); wrong routes 0
- Unclear messages held back by the policy: 100.0% (24/24, 95% CI 86-100%)
- Category calibration (ECE, lower is better): 0.103
- Enough-information question: accuracy 93.3% (112/120, 95% CI 87-97%), Brier 0.047
- Urgency: accuracy 97.5% (117/120, 95% CI 93-99%), recall 80.0% (12/15, 95% CI 55-93%), false alarms 0
- Impact: mean absolute error 0.238 levels, nearest level correct 80.8% (80/99, 95% CI 72-87%)
- Options reversed: same choice 96.7% (116/120, 95% CI 92-99%), mean probability shift 0.073, max 0.37
- Across 3 runs: same choice 100.0% (120/120, 95% CI 97-100%), max probability spread 0.0
- Latency: p50 276 ms, p95 647 ms
- Input tokens per request: 709 · cost per 1,000 messages: $0.0709

| Threshold | Routed | Correct when routed | Unclear held back | Wrong routes | Wrong routes without `enough` |
| --- | --- | --- | --- | --- | --- |
| 0.5 | 76.7% (92/120, 95% CI 68-83%) | 98.9% (91/92, 95% CI 94-100%) | 95.8% (23/24, 95% CI 80-99%) | 1 | 1 |
| 0.6 | 73.3% (88/120, 95% CI 65-80%) | 98.9% (87/88, 95% CI 94-100%) | 95.8% (23/24, 95% CI 80-99%) | 1 | 1 |
| 0.7 | 68.3% (82/120, 95% CI 60-76%) | 100.0% (82/82, 95% CI 96-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |
| 0.75 | 64.2% (77/120, 95% CI 55-72%) | 100.0% (77/77, 95% CI 95-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |
| 0.8 | 59.2% (71/120, 95% CI 50-68%) | 100.0% (71/71, 95% CI 95-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |
| 0.85 | 54.2% (65/120, 95% CI 45-63%) | 100.0% (65/65, 95% CI 94-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |
| 0.9 | 50.0% (60/120, 95% CI 41-59%) | 100.0% (60/60, 95% CI 94-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |
| 0.95 | 38.3% (46/120, 95% CI 30-47%) | 100.0% (46/46, 95% CI 92-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |
| 0.99 | 13.3% (16/120, 95% CI 8-21%) | 100.0% (16/16, 95% CI 81-100%) | 100.0% (24/24, 95% CI 86-100%) | 0 | 0 |

Accuracy by kind of message:

- clear: 96.9% (63/65, 95% CI 90-99%)
- competing: 100.0% (22/22, 95% CI 85-100%)
- multi: 57.1% (4/7, 95% CI 25-84%)
- short: 100.0% (9/9, 95% CI 70-100%)
- vague: 100.0% (17/17, 95% CI 82-100%)

Most confident mistakes:

- d14 expected delivery, got unclear at 0.83: "My medication refill hasn't arrived and I run out tomorrow."
- u04 expected unclear, got billing at 0.65: "Who can I talk to about my account and my last payment?"
- d04 expected delivery, got unclear at 0.53: "The parcel arrived with the box crushed and the lamp inside broken."
- u10 expected unclear, got technical at 0.41: "My package never arrived, and the app crashes when I try to report it."
- u19 expected unclear, got delivery at 0.3: "The tracking page asks me to sign in, and when I do, it says my payment failed."
