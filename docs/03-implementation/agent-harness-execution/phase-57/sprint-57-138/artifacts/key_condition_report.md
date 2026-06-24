# Key-Condition vs Generic Judge — A/B — 2026-06-24T10:15:51

- cases: **11**
- generic accuracy (all): **90.91%**
- key_condition accuracy (all): **90.91%**
- **key_condition gain** (key_cond − generic on instruction_violation): **+16.67%**
- **false_positive_rate** (acceptable wrongly failed by key_condition): **20.00%**
- generic tokens: 4090 · key_condition tokens: 7493
- thresholds: gain ≥ 30% AND fp ≤ 20% → **NOT recommended**

## Per class

| class | n | generic acc | key_condition acc |
|-------|---|-------------|-------------------|
| instruction_violation | 6 | 83.33% | 100.00% |
| acceptable | 5 | 100.00% | 80.00% |
