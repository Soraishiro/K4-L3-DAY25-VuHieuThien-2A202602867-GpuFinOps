# NimbusAI — GPU FinOps (Synthetic Scenario)

**Status:** Conditional projection, not verified savings
**Period:** monthly  
**Baseline spend:** $18,005  
**Optimized spend (conditional):** $10,756  
**Projected savings (conditional):** $7,249 (**40%**)

## Savings by lever

| Lever | Conditional monthly saving (USD) |
|---|---:|
| Inference (routing/cache/batch) | $1,212 |
| Purchasing (spot/covered reserved) | $4,633 |
| GPU replacement candidates (unverified) | $804 |
| Idle-hours opportunity | $600 |

## Inference unit economics
- Before: $6.488/1M-token
- After: $1.126/1M-token
- Simulated improvement: 82.6%
- Routing, cache and batch are evaluated jointly, not independently.

## Sustainability
- Energy per simulated query: 0.24 Wh
- Carbon per query (us-east-1): 0.091 gCO2e
- Lowest carbon-intensity assumption: europe-north1
- Lowest electricity-price assumption: us-east-wa
- Neither region comparison includes GPU prices, latency or capacity.

## Scope and validation requirements

- All source data are synthetic. No real provider savings have occurred.
- Combined scenario assumes external token billing, GPU job costs and telemetry fleet do not overlap; their independence has NOT been proven.
- No linkage connects the 11 telemetry GPUs to the eight purchasing jobs; exclude cross-ledger savings until billing can be reconciled.
- Right-sizing is capacity screening, not a performance-validated replacement. Remove idle hours before estimating right-size savings.
- Reserved pricing assumes existing unused committed capacity; 30-day jobs alone cannot justify new one-year commitments.
- Purchasing-only scenario: USD 16,539 to USD 11,906 (28.0% saving).

_Synthetic June 2026 snapshot: re-baseline with invoices, measured throughput, latency and model quality._