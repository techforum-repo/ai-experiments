# Gemini Decisions API: multimodal triage results

Model `gemini-decision-1`, endpoint `https://generativelanguage.googleapis.com/v1beta/decisions`. Started 2026-11-16T15:50:23+00:00. Prices at $0.1 per million input tokens.

273 requests, 1 errors, 345,270 input tokens, $0.0345 in total. Median latency 640 ms.

## Same message, six formats

Ten customer messages, each sent as text, a photographed letter, a voicemail, a PDF form, a scanned PDF and a video message. Counts are correct answers out of labelled answers.

| Format | Category | Urgent | Impact | Enough | Sensitive (should be no) | Route as expected | Mean top p | Input tokens | p50 ms | $ per 1,000 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Text | 29/29 (100%) | 29/29 (100%) | 24/27 (89%) | 29/29 (100%) | 29/29 (100%) | 29/29 (100%) | 0.974 | 532 | 400 | 0.0532 |
| Image (photo of a letter) | 30/30 (100%) | 30/30 (100%) | 27/27 (100%) | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) | 0.958 | 1,596 | 734 | 0.1596 |
| Audio (voicemail) | 30/30 (100%) | 24/30 (80%) | 27/27 (100%) | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) | 0.915 | 824 | 535 | 0.0824 |
| PDF (text layer) | 30/30 (100%) | 30/30 (100%) | 27/27 (100%) | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) | 0.957 | 1,136 | 574 | 0.1136 |
| PDF (scanned, image only) | 30/30 (100%) | 30/30 (100%) | 27/27 (100%) | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) | 0.953 | 1,086 | 680 | 0.1086 |
| Video (spoken message) | 30/30 (100%) | 27/30 (90%) | 27/27 (100%) | 30/30 (100%) | 30/30 (100%) | 30/30 (100%) | 0.906 | 1,509 | 679 | 0.1509 |

Did each message get the same category in every format?

- s01 (billing): same, P(billing) 0.984–0.998
- s02 (billing): same, P(billing) 0.951–0.999
- s03 (account): same, P(account) 0.925–0.976
- s04 (account): same, P(account) 0.946–0.993
- s05 (technical): same, P(technical) 0.918–0.991
- s06 (technical): same, P(technical) 0.961–0.99
- s07 (delivery): same, P(delivery) 0.959–0.993
- s08 (delivery): same, P(delivery) 0.968–0.994
- s09 (unclear): same, P(unclear) 0.888–0.986
- s10 (unclear): same, P(unclear) 0.456–0.832

## Messages with attachments

✓/✗ against the label; noul answers show P(yes). One row per case: run 1's answer, with the range in brackets when runs differed. Unlabelled answers are shown without a mark.

| Case | category | urgent | impact | enough | sensitive | conflict | Route (expected) | Tokens | ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| att-error-screenshot | ✓ technical | ✓ 0.03 | 1.70 | ✓ 0.84 | ✓ 0.07 | ✓ 0.05 | ✓ route:technical (route:technical) | 1,718 | 512 |
| att-voicemail-invoice-match | ✓ billing | ✓ 0.05 | ✓ 2 | ✓ 0.96 | ✓ 0.09 (0.05–0.09) | ✓ 0.04 | ✓ route:billing (route:billing) | 1,717 | 675 |
| att-voicemail-invoice-conflict | ✓ billing | ✓ 0.05 (0.04–0.05) | ✓ 2 | ✓ 0.94 | ✓ 0.06 (0.06–0.07) | ✓ 0.75 (0.66–0.75) | ✓ review (review) | 1,695 | 428 |
| att-damaged-tracking-delivered | ✓ delivery | ✓ 0.05 | 1.55 | ✓ 0.67 | ✓ 0.05 | ✓ 0.05 | ✓ route:delivery (route:delivery) | 1,733 | 670 |
| att-damaged-tracking-in-transit | ✓ delivery | ✓ 0.04 | 1.59 | ✓ 0.81 | ✓ 0.05 | ✓ 0.93 | ✓ review (review) | 1,733 | 685 |
| att-login-recording | ✓ account | ✓ 0.07 | ✓ 2 | ✓ 0.89 | ✓ 0.37 | ✓ 0.04 | ✓ route:account (route:account) | 1,496 | 707 |
| att-checkout-recording | ✓ billing | ✓ 0.05 | ✓ 2 | ✓ 0.87 | ✓ 0.06 | ✓ 0.15 | ✓ route:billing (route:billing) | 1,505 | 822 |
| att-export-recording-conflict | ✓ technical | ✓ 0.04 | ✗ 0 | ✗ 0.42 | ✓ 0.05 | ✓ 0.98 | ✓ review (review) | 1,279 | 810 |
| att-card-exposed | ✓ billing | ✓ 0.07 | ✓ 2 | ✓ 0.79 | ✓ 0.77 | ✓ 0.04 | ✓ redact (redact) | 1,717 | 622 |
| att-courier-card | ✓ delivery | ✓ 0.18 | 1.01 | ✓ 0.95 | ✓ 0.04 | ✓ 0.07 | ✓ route:delivery (route:delivery) | 1,215 | 820 |
| att-injection | ✓ account | ✓ 0.07 | ✓ 0 | ✓ 0.86 | ✓ 0.04 | ✓ 0.04 | ✓ route:account (route:account) | 1,726 | 800 |
| att-spanish-voicemail | ✓ account | ✓ 0.78 | ✓ 2 | ✓ 0.76 | ✓ 0.06 | ✓ 0.06 | ✓ route:account (route:account) | 1,002 | 731 |
| att-noisy-voicemail | ✓ delivery | ✓ 0.05 | ✓ 2 | ✓ 0.91 | ✓ 0.02 | ✓ 0.08 | ✓ route:delivery (route:delivery) | 1,047 | 485 |
| att-irrelevant-image | ✓ unclear | ✓ 0.07 | 0.78 | ✓ 0.12 | ✓ 0.06 | 0.17 | ✓ clarify (clarify) | 1,692 | 464 |

## All five formats in one request

✓/✗ against the label; noul answers show P(yes). One row per case: run 1's answer, with the range in brackets when runs differed. Unlabelled answers are shown without a mark.

| Case | category | urgent | impact | enough | sensitive | conflict | wrong_address | Route (expected) | Tokens | ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mix-all-formats-wrong-door | ✓ delivery | ✓ 0.03 | ✓ 2 | ✓ 0.94 (0.90–0.94) | ✓ 0.06 | ✓ 0.75 (0.75–0.81) | ✓ 0.95 | ✓ review (review) | 3,616 | 1039 |
| mix-all-formats-right-door | ✓ delivery | ✓ 0.04 | ✓ 2 | ✓ 0.93 | ✓ 0.06 | ✓ 0.97 | ✓ 0.08 | ✓ review (review) | 3,616 | 831 |

## Media resolution

| Case | Resolution | Answer | p | Media tokens | Total tokens | ms |
| --- | --- | --- | --- | --- | --- | --- |
| error_code | low | ✓ SYN-4127 | 0.980 | 264 | 408 | 747 |
| error_code | medium | ✓ SYN-4127 | 0.968 | 527 | 671 | 916 |
| error_code | high | ✓ SYN-4127 | 0.967 | 1,100 | 1,244 | 817 |
| error_code | ultra_high | ✓ SYN-4127 | 0.997 | 2,205 | 2,349 | 811 |
| receipt_total | low | ✓ 47.85 | 0.992 | 250 | 393 | 670 |
| receipt_total | medium | ✓ 47.85 | 0.961 | 540 | 683 | 951 |
| receipt_total | high | ✓ 47.85 | 0.984 | 1,071 | 1,214 | 811 |
| receipt_total | ultra_high | ✓ 47.85 | 0.959 | 2,190 | 2,333 | 767 |
| tracking_number | low | ✓ PR-7781-2290 | 0.988 | 260 | 426 | 745 |
| tracking_number | medium | ✓ PR-7781-2290 | 0.984 | 522 | 688 | 610 |
| tracking_number | high | ✓ PR-7781-2290 | 0.969 | 1,066 | 1,232 | 750 |
| tracking_number | ultra_high | ✓ PR-7781-2290 | 0.990 | 2,183 | 2,349 | 820 |
| lock_duration | low | ✓ 24_hours | 0.998 | 852 | 1,191 | 591 |
| lock_duration | medium | ✓ 24_hours | 0.998 | 852 | 1,191 | 462 |
| lock_duration | high | ✓ 24_hours | 0.999 | 3,228 | 3,567 | 1507 |

## Repeat runs

Category identical across runs for 91 of 91 cases.


## Errors

- fmt-s09-text: HTTP 403 {"error": {"message": "The caller does not have permission", "code": "permission_denied"}}

## Questions per request

Same shared input every time (text, image, audio, PDF, video); only the number of questions changes.

| Questions | Requests | p50 ms (min–max) | Input tokens | $ per request | $ per question | True facts found | False facts rejected | Near-miss false positives |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | 1016 (668–1032) | 3,154 | 0.000315 | 0.00031540 | – | – | – |
| 10 | 3 | 955 (754–1181) | 3,784 | 0.000378 | 0.00003784 | 3/3 (100%) | 6/6 (100%) | 0/3 (0%) |
| 100 | 3 | 609 (596–935) | 8,642 | 0.000864 | 0.00000864 | 33/33 (100%) | 246/246 (100%) | 0/84 (0%) |
| 1000 | 3 | 1170 (1115–1432) | 58,316 | 0.005832 | 0.00000583 | 33/33 (100%) | 2946/2946 (100%) | 0/138 (0%) |

Triage answers as questions are added (mean probability; change from the first size that asked it):

- 1: category 0.598 (+0.0)
- 10: category 0.598 (+0.0), urgent 0.034 (+0.0), enough 0.931 (+0.0), conflict 0.76 (+0.0), wrong_address 0.941 (+0.0)
- 100: category 0.526 (-0.072), urgent 0.027 (-0.007), enough 0.916 (-0.015), conflict 0.925 (+0.165), wrong_address 0.958 (+0.017)
- 1000: category 0.531 (-0.067), urgent 0.034 (+0.0), enough 0.924 (-0.007), conflict 0.883 (+0.123), wrong_address 0.949 (+0.008)
