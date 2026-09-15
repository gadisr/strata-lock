# strata-lock

**strata-lock** is a pre-registration lock for holdout evaluation strata. Lock your evaluation slices *before* scoring to prevent post-hoc cherry-picking of favorable subsets. Any keep/promotion decision that relies on strata chosen after seeing results is refused. This protects the statistical validity of holdout evaluation in model benchmarking, CI gating, leaderboards, and research pipelines.

## Public use cases

### 1. SWE-bench keep gate: refuse promotion on post-hoc task slices

You're evaluating an agent on SWE-bench Verified. Lock the holdout task categories before running:

**Lock holdout strata** (`swebench_strata.json`):
```json
{
  "verified_django": {
    "ids": ["django__django-11001", "django__django-11179", "django__django-11283"],
    "description": "Django tasks from SWE-bench Verified"
  },
  "verified_requests": {
    "ids": ["psf__requests-1963", "psf__requests-2148"],
    "description": "Requests library tasks"
  }
}
```

```bash
strata-lock lock swebench_strata.json -n "agent_v2.3_eval"
```

After scoring, decide whether to promote the agent based on registered strata:

**Valid keep decision** (`keep_decision.json`):
```json
{
  "agent_version": "v2.3",
  "decision": "keep",
  "justifying_strata": ["verified_django", "verified_requests"],
  "metrics": {
    "verified_django_pass_rate": 0.82,
    "verified_requests_pass_rate": 0.76
  }
}
```

```bash
strata-lock gate-keep keep_decision.json
# ✓ ALLOWED: Keep decision justified by pre-registered strata
```

**Invalid keep decision** (post-hoc slice):
```json
{
  "agent_version": "v2.3",
  "decision": "keep",
  "justifying_strata": ["verified_django", "easy_tasks_only"],
  "metrics": {
    "verified_django_pass_rate": 0.82,
    "easy_tasks_only_pass_rate": 0.95
  }
}
```

```bash
strata-lock gate-keep bad_decision.json
# ✗ REFUSED: Keep decision relies on post-hoc strata. Unregistered strata: ['easy_tasks_only']
# Exit code: 2
```

### 2. Meta-harness policy evolution: lock holdout before comparing harness variants

You're A/B testing changes to your evaluation harness. Lock holdout episodes before running both variants to ensure fair comparison:

**Lock holdout strata** (`harness_holdout.json`):
```json
{
  "holdout_standard": {
    "ids": ["episode_h001", "episode_h002", "episode_h003"],
    "description": "Standard difficulty holdout"
  },
  "holdout_adversarial": {
    "ids": ["episode_h101", "episode_h102"],
    "description": "Adversarial cases"
  }
}
```

```bash
strata-lock lock harness_holdout.json -n "harness_v3_vs_v2"
```

After running both harness versions, verify that scoring only used the pre-registered holdout:

**Results file** (`harness_results.json`):
```json
{
  "experiment": "v3_vs_v2_comparison",
  "used_strata": ["holdout_standard", "holdout_adversarial"]
}
```

```bash
strata-lock verify harness_results.json
# ✓ OK: All 2 strata were pre-registered
```

### 3. CI scoreboard: verify published leaderboard slices match a sealed lockfile

Your CI publishes a leaderboard. Commit the lockfile to the repo so reviewers can verify that leaderboard slices weren't cherry-picked:

**Leaderboard strata** (`leaderboard_strata.json`):
```json
{
  "official_holdout": {
    "ids": ["task_001", "task_002", "task_003", "task_004", "task_005"],
    "description": "Official leaderboard holdout set"
  }
}
```

```bash
# In CI, before scoring:
strata-lock lock leaderboard_strata.json -o leaderboard.lock -n "2026-Q3-leaderboard"
git add leaderboard.lock
git commit -m "lock: Q3 leaderboard holdout"

# After scoring, verify leaderboard results:
strata-lock verify leaderboard_results.json -l leaderboard.lock
```

Reviewers can inspect `leaderboard.lock` to confirm the holdout definition and timestamp, and verify the content hash hasn't been tampered with.

## Installation

```bash
pip install -e .

# For development
pip install -e ".[dev]"
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

See `examples/` for complete end-to-end examples with sample JSON files for each use case.

## Development

Run tests:
```bash
pytest -v tests/
```

Run tests with coverage:
```bash
pytest --cov=strata_lock --cov-report=term-missing tests/
```

## With failstrata

If you're using [failstrata](https://github.com/anysphere/failstrata) for agent evaluation, strata-lock complements its audit cycle by providing tamper-evident pre-registration of holdout slices. Lock your failstrata holdout definitions before running the eval loop, then gate keep decisions in CI.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Design Principles

1. **Minimal dependencies**: Uses Python stdlib only (no external runtime deps)
2. **Tamper detection**: Content hashing ensures lockfiles can't be silently modified
3. **Clear exit codes**: Different codes for different failure modes enable automation
4. **Machine-readable**: All output is parseable for CI/CD integration
5. **Explicit**: No implicit strata registration or automatic approval
