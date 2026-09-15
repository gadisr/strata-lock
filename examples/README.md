# Examples

This directory contains example files demonstrating strata-lock usage across different scenarios.

## Use case examples

### SWE-bench agent keep gate
- `swebench_strata.json` - Holdout task categories from SWE-bench Verified
- `swebench_keep_decision.json` - Valid keep decision using pre-registered strata
- `swebench_bad_decision.json` - Invalid decision relying on post-hoc "easy_tasks_only" slice

**Try it:**
```bash
strata-lock lock swebench_strata.json -o swebench.lock -n "agent_v2.3_eval"
strata-lock gate-keep swebench_keep_decision.json -l swebench.lock  # ALLOWED
strata-lock gate-keep swebench_bad_decision.json -l swebench.lock   # REFUSED (exit 2)
```

### Meta-harness / policy evolution
- `harness_holdout.json` - Holdout episodes for comparing harness variants
- `harness_results.json` - Results using only pre-registered holdout

**Try it:**
```bash
strata-lock lock harness_holdout.json -o harness.lock -n "harness_v3_vs_v2"
strata-lock verify harness_results.json -l harness.lock  # OK
```

### CI leaderboard
- `leaderboard_strata.json` - Official leaderboard holdout set
- `leaderboard_results.json` - Published leaderboard results

**Try it:**
```bash
strata-lock lock leaderboard_strata.json -o leaderboard.lock -n "2026-Q3-leaderboard"
strata-lock verify leaderboard_results.json -l leaderboard.lock  # OK
```

## Legacy/generic examples

The following files demonstrate the basic mechanics without specific use cases:

- `strata_definitions.json` - Generic strata definitions with ids and globs
- `valid_results.json` - Results that only reference pre-registered strata
- `invalid_results.json` - Results that reference an unregistered stratum (holdout_D)
- `valid_decision.json` - Keep decision justified by pre-registered strata only
- `posthoc_decision.json` - Keep decision that incorrectly relies on a post-hoc slice

## Quick walkthrough

1. **Lock your strata definitions before scoring:**

```bash
strata-lock lock strata_definitions.json -o experiment.lock -n "my_experiment_001"
```

2. **After scoring, verify that only pre-registered strata were used:**

```bash
# This will pass - both strata are registered
strata-lock verify valid_results.json -l experiment.lock

# This will fail - holdout_D was not pre-registered
strata-lock verify invalid_results.json -l experiment.lock
```

3. **Gate keep/promotion decisions:**

```bash
# This will be allowed - uses only pre-registered strata
strata-lock gate-keep valid_decision.json -l experiment.lock

# This will be refused (exit code 2) - uses post-hoc slice
strata-lock gate-keep posthoc_decision.json -l experiment.lock
```
