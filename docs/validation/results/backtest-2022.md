# Top-25 discovery backtest

- Frozen at **2022-12-31**; outcomes observed through **2024-12-31**; k = 25.
- Candidates: non-excluded NJ companies with a public record in the 730 days before the cutoff.
- Outcome: a new Form D of at least $1,000,000 or an SBIR/STTR Phase II award after the cutoff, tied to the candidate by exact SEC company ID or exact name + postal code.

## All candidates

520 candidates; 93 had the outcome (base rate 18% (95% CI 15%-21%, n=520)).

| ranking | hits in top k | precision@k |
|---|---:|---:|
| **Gauge** | 3/25 | 12% (95% CI 4%-30%, n=25) |
| Largest Form D raise in the 2 years before cutoff | 2/25 | 8% (95% CI 2%-25%, n=25) |
| Most recent public record | 7/25 | 28% (95% CI 14%-48%, n=25) |
| Number of SBIR/STTR awards | 6/25 | 24% (95% CI 11%-43%, n=25) |

Headline: Gauge 3/25 vs. strongest baseline (Most recent public record) 7/25.
The 95% intervals overlap, so this difference is not conclusive.
Warning: 76 candidates share Gauge's score at rank 25, so which of them make the top k is arbitrary. The classifier scores how startup-like a company is; it saturates and is not a follow-on predictor.

## Cold start (first public record in the prior year)

168 candidates; 31 had the outcome (base rate 18% (95% CI 13%-25%, n=168)).

| ranking | hits in top k | precision@k |
|---|---:|---:|
| **Gauge** | 5/25 | 20% (95% CI 9%-39%, n=25) |
| Largest Form D raise in the 2 years before cutoff | 4/25 | 16% (95% CI 6%-35%, n=25) |
| Most recent public record | 4/25 | 16% (95% CI 6%-35%, n=25) |
| Number of SBIR/STTR awards | 4/25 | 16% (95% CI 6%-35%, n=25) |

Headline: Gauge 5/25 vs. strongest baseline (Number of SBIR/STTR awards) 4/25.
The 95% intervals overlap, so this difference is not conclusive.
Warning: 30 candidates share Gauge's score at rank 25, so which of them make the top k is arbitrary. The classifier scores how startup-like a company is; it saturates and is not a follow-on predictor.

## What this does and does not show

- **Does:** whether Gauge's ranking, using only records available at the cutoff, puts more companies with later follow-on activity in its top k than simple rankings built from the same records. The headline uses the best baseline on this data, which favors the baseline.
- **Does not:** measure investment returns or company quality. The outcome is a proxy that only counts activity visible in public filings; companies that raise without a Form D, or whose later records use another name or address, count as misses.
- The classifier's prior weights were written in 2026, not fit on this data, but their authors knew how startups generally behave; treat the result as supportive, not a controlled experiment.
- With k = 25 the intervals are wide; one or two hits can change the comparison.
