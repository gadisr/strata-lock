"""Tests for strata-lock CLI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(*args):
    """Run the CLI and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "strata_lock"] + list(args),
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def test_cli_lock_basic(tmp_path):
    """Test basic lock command."""
    strata_file = tmp_path / "strata.json"
    strata_file.write_text(json.dumps({
        "holdout_A": {"ids": ["ep1", "ep2"]},
        "holdout_B": {"globs": ["*.json"]}
    }))
    
    lockfile = tmp_path / "test.lock"
    exit_code, stdout, stderr = run_cli(
        "lock",
        str(strata_file),
        "-o", str(lockfile)
    )
    
    assert exit_code == 0
    assert lockfile.exists()
    assert "Lockfile created" in stdout
    assert "Registered 2 strata" in stdout
    
    lockfile_data = json.loads(lockfile.read_text())
    assert lockfile_data["version"] == "1.0"
    assert "content_hash" in lockfile_data


def test_cli_lock_with_note(tmp_path):
    """Test lock command with note."""
    strata_file = tmp_path / "strata.json"
    strata_file.write_text(json.dumps({
        "holdout_A": {"ids": ["ep1"]}
    }))
    
    lockfile = tmp_path / "test.lock"
    exit_code, stdout, stderr = run_cli(
        "lock",
        str(strata_file),
        "-o", str(lockfile),
        "-n", "experiment_xyz"
    )
    
    assert exit_code == 0
    lockfile_data = json.loads(lockfile.read_text())
    assert lockfile_data["note"] == "experiment_xyz"


def test_cli_lock_missing_file(tmp_path):
    """Test lock command with missing input file."""
    strata_file = tmp_path / "missing.json"
    lockfile = tmp_path / "test.lock"
    
    exit_code, stdout, stderr = run_cli(
        "lock",
        str(strata_file),
        "-o", str(lockfile)
    )
    
    assert exit_code == 1
    assert "not found" in stderr.lower()


def test_cli_verify_valid(tmp_path):
    """Test verify command with valid results."""
    strata_file = tmp_path / "strata.json"
    strata_file.write_text(json.dumps({
        "holdout_A": {"ids": ["ep1"]},
        "holdout_B": {"ids": ["ep2"]}
    }))
    
    lockfile = tmp_path / "test.lock"
    run_cli("lock", str(strata_file), "-o", str(lockfile))
    
    results_file = tmp_path / "results.json"
    results_file.write_text(json.dumps({
        "used_strata": ["holdout_A", "holdout_B"]
    }))
    
    exit_code, stdout, stderr = run_cli(
        "verify",
        str(results_file),
        "-l", str(lockfile)
    )
    
    assert exit_code == 0
    assert "OK" in stdout
    assert "2 strata" in stdout


def test_cli_verify_post_hoc(tmp_path):
    """Test verify command detecting post-hoc strata."""
    strata_file = tmp_path / "strata.json"
    strata_file.write_text(json.dumps({
        "holdout_A": {"ids": ["ep1"]}
    }))
    
    lockfile = tmp_path / "test.lock"
    run_cli("lock", str(strata_file), "-o", str(lockfile))
    
    results_file = tmp_path / "results.json"
    results_file.write_text(json.dumps({
        "used_strata": ["holdout_A", "post_hoc_slice"]
    }))
    
    exit_code, stdout, stderr = run_cli(
        "verify",
        str(results_file),
        "-l", str(lockfile)
    )
    
    assert exit_code == 1
    assert "Post-hoc" in stderr
    assert "post_hoc_slice" in stderr


def test_cli_gate_keep_allowed(tmp_path):
    """Test gate-keep command allowing a valid decision."""
    strata_file = tmp_path / "strata.json"
    strata_file.write_text(json.dumps({
        "holdout_A": {"ids": ["ep1"]},
        "holdout_B": {"ids": ["ep2"]}
    }))
    
    lockfile = tmp_path / "test.lock"
    run_cli("lock", str(strata_file), "-o", str(lockfile))
    
    decision_file = tmp_path / "decision.json"
    decision_file.write_text(json.dumps({
        "justifying_strata": ["holdout_A", "holdout_B"]
    }))
    
    exit_code, stdout, stderr = run_cli(
        "gate-keep",
        str(decision_file),
        "-l", str(lockfile)
    )
    
    assert exit_code == 0
    assert "ALLOWED" in stdout


def test_cli_gate_keep_refused(tmp_path):
    """Test gate-keep command refusing a post-hoc decision."""
    strata_file = tmp_path / "strata.json"
    strata_file.write_text(json.dumps({
        "holdout_A": {"ids": ["ep1"]}
    }))
    
    lockfile = tmp_path / "test.lock"
    run_cli("lock", str(strata_file), "-o", str(lockfile))
    
    decision_file = tmp_path / "decision.json"
    decision_file.write_text(json.dumps({
        "justifying_strata": ["holdout_A", "post_hoc_slice"]
    }))
    
    exit_code, stdout, stderr = run_cli(
        "gate-keep",
        str(decision_file),
        "-l", str(lockfile)
    )
    
    assert exit_code == 2
    assert "REFUSED" in stderr
    assert "post-hoc" in stderr.lower()


def test_cli_help():
    """Test that help is displayed."""
    exit_code, stdout, stderr = run_cli("--help")
    
    assert exit_code == 0
    assert "strata-lock" in stdout
    assert "lock" in stdout
    assert "verify" in stdout
    assert "gate-keep" in stdout


def test_cli_lock_default_output(tmp_path, monkeypatch):
    """Test lock command with default output path."""
    monkeypatch.chdir(tmp_path)
    
    strata_file = tmp_path / "strata.json"
    strata_file.write_text(json.dumps({
        "holdout_A": {"ids": ["ep1"]}
    }))
    
    exit_code, stdout, stderr = run_cli("lock", str(strata_file))
    
    assert exit_code == 0
    default_lock = tmp_path / ".strata-lock.json"
    assert default_lock.exists()
