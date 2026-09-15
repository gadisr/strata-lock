# strata-lock

Pre-register holdout evaluation strata *before* scoring. Refuse any "keep" / promotion decision that relies on post-hoc slices (strata chosen after seeing results).

## Why?

Post-hoc slice selection invalidates statistical guarantees from holdout evaluation. By locking strata definitions before scoring, you ensure that:

- All evaluation slices are defined independently of results
- Keep/promotion decisions rely only on pre-registered holdout strata
- Cherry-picking favorable subsets after seeing scores is prevented

## Installation

```bash
pip install -e .

# For development
pip install -e ".[dev]"
```

## Quick Start

### 1. Lock strata definitions

Create a JSON file with your strata definitions:

```json
{
  "holdout_A": {
    "ids": ["episode_001", "episode_002", "episode_003"],
    "description": "First holdout stratum"
  },
  "holdout_B": {
    "ids": ["episode_010", "episode_011"],
    "globs": ["results/task_b_*.json"],
    "description": "Second holdout stratum"
  }
}
```

Lock it before scoring:

```bash
strata-lock lock strata_definitions.json -o .strata-lock.json -n "experiment_001"
```

Output:
```
✓ Lockfile created: .strata-lock.json
  Registered 2 strata
  Content hash: a3f2c8e91b...
  Timestamp: 2026-09-15T07:13:42.123456+00:00
```

### 2. Verify scoring results

After scoring, verify that only pre-registered strata were used:

```bash
strata-lock verify results.json -l .strata-lock.json
```

Where `results.json` contains:
```json
{
  "experiment_id": "exp_20260915_001",
  "used_strata": ["holdout_A", "holdout_B"]
}
```

Output:
```
✓ OK: All 2 strata were pre-registered
```

### 3. Gate keep decisions

When making a keep/promotion decision, verify it's justified by pre-registered strata:

```bash
strata-lock gate-keep decision.json -l .strata-lock.json
```

Where `decision.json` contains:
```json
{
  "decision": "keep",
  "justifying_strata": ["holdout_A", "holdout_B"],
  "metrics": {
    "holdout_A_score": 0.85,
    "holdout_B_score": 0.82
  }
}
```

Output:
```
✓ ALLOWED: Keep decision justified by pre-registered strata: ['holdout_A', 'holdout_B']
```

### Post-hoc slice detection

If a decision relies on unregistered strata:

```bash
strata-lock gate-keep bad_decision.json -l .strata-lock.json
```

Where `bad_decision.json` contains:
```json
{
  "decision": "keep",
  "justifying_strata": ["holdout_A", "post_hoc_slice"]
}
```

Output (exits with code 2):
```
✗ REFUSED: Keep decision relies on post-hoc strata. Unregistered strata: ['post_hoc_slice']. Only pre-registered strata may justify keep decisions.
```

## CLI Reference

### `strata-lock lock`

Create a sealed lockfile from strata definitions.

```bash
strata-lock lock <strata_file> [-o OUTPUT] [-n NOTE]
```

**Arguments:**
- `strata_file`: JSON file containing strata definitions
- `-o, --output`: Output lockfile path (default: `.strata-lock.json`)
- `-n, --note`: Optional human-readable note or experiment ID

**Lockfile format:**
The lockfile includes:
- Strata definitions (sealed payload)
- SHA256 content hash for tamper detection
- ISO timestamp of registration
- Optional note/experiment ID

### `strata-lock verify`

Verify that scoring results only use pre-registered strata.

```bash
strata-lock verify <results_file> [-l LOCKFILE]
```

**Arguments:**
- `results_file`: JSON file with `used_strata` field listing strata names
- `-l, --lockfile`: Lockfile path (default: `.strata-lock.json`)

**Exit codes:**
- 0: All strata are pre-registered
- 1: Post-hoc strata detected or error

### `strata-lock gate-keep`

Gate a keep decision; refuse if justified by post-hoc strata.

```bash
strata-lock gate-keep <decision_file> [-l LOCKFILE]
```

**Arguments:**
- `decision_file`: JSON file with `justifying_strata` field
- `-l, --lockfile`: Lockfile path (default: `.strata-lock.json`)

**Exit codes:**
- 0: Decision allowed (all justifying strata are pre-registered)
- 2: Decision refused (post-hoc strata detected)
- 1: Other error (missing file, invalid lockfile, etc.)

## Alternative invocation

You can also run as a module:

```bash
python -m strata_lock lock strata.json
python -m strata_lock verify results.json
python -m strata_lock gate-keep decision.json
```

## Examples

See `tests/fixtures/` for example input files:
- `strata_definitions.json` - Sample strata definitions
- `valid_results.json` - Results using pre-registered strata
- `invalid_results.json` - Results with post-hoc strata
- `valid_decision.json` - Valid keep decision
- `posthoc_decision.json` - Invalid keep decision with post-hoc slices

## Development

Run tests:
```bash
pytest -v tests/
```

Run tests with coverage:
```bash
pytest --cov=strata_lock --cov-report=term-missing tests/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Design Principles

1. **Minimal dependencies**: Uses Python stdlib only (no external runtime deps)
2. **Tamper detection**: Content hashing ensures lockfiles can't be silently modified
3. **Clear exit codes**: Different codes for different failure modes enable automation
4. **Machine-readable**: All output is parseable for CI/CD integration
5. **Explicit**: No implicit strata registration or automatic approval
