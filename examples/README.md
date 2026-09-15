# Examples

This directory contains example files demonstrating strata-lock usage.

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

## File descriptions

- **strata_definitions.json**: Example strata definitions with ids and globs
- **valid_results.json**: Results that only reference pre-registered strata
- **invalid_results.json**: Results that reference an unregistered stratum (holdout_D)
- **valid_decision.json**: Keep decision justified by pre-registered strata only
- **posthoc_decision.json**: Keep decision that incorrectly relies on a post-hoc slice

## Try it yourself

From this directory:

```bash
# Lock the strata
strata-lock lock strata_definitions.json -o demo.lock -n "demo"

# Verify valid results
strata-lock verify valid_results.json -l demo.lock
echo "Exit code: $?"  # Should be 0

# Try invalid results
strata-lock verify invalid_results.json -l demo.lock
echo "Exit code: $?"  # Should be 1

# Allow valid decision
strata-lock gate-keep valid_decision.json -l demo.lock
echo "Exit code: $?"  # Should be 0

# Refuse post-hoc decision
strata-lock gate-keep posthoc_decision.json -l demo.lock
echo "Exit code: $?"  # Should be 2
```
