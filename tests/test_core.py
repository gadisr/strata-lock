"""Tests for core strata-lock functionality."""

import json
from pathlib import Path

import pytest

from strata_lock.core import (
    compute_content_hash,
    create_lockfile,
    gate_keep_decision,
    get_registered_strata,
    load_lockfile,
    verify_strata_usage,
)


def test_compute_content_hash():
    """Test that content hash is deterministic and changes with content."""
    data1 = {"a": 1, "b": 2}
    data2 = {"b": 2, "a": 1}
    data3 = {"a": 1, "b": 3}
    
    hash1 = compute_content_hash(data1)
    hash2 = compute_content_hash(data2)
    hash3 = compute_content_hash(data3)
    
    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64


def test_create_lockfile(tmp_path):
    """Test creating a valid lockfile."""
    strata = {
        "holdout_A": {"ids": ["ep1", "ep2"]},
        "holdout_B": {"globs": ["*.json"]}
    }
    
    lockfile_path = tmp_path / "test.lock"
    lockfile = create_lockfile(strata, lockfile_path, note="test experiment")
    
    assert lockfile_path.exists()
    assert lockfile["version"] == "1.0"
    assert "timestamp" in lockfile
    assert "content_hash" in lockfile
    assert lockfile["note"] == "test experiment"
    assert lockfile["sealed_payload"]["strata"] == strata
    
    expected_hash = compute_content_hash(lockfile["sealed_payload"])
    assert lockfile["content_hash"] == expected_hash


def test_load_lockfile_valid(tmp_path):
    """Test loading a valid lockfile."""
    strata = {"holdout_A": {"ids": ["ep1"]}}
    lockfile_path = tmp_path / "test.lock"
    original = create_lockfile(strata, lockfile_path)
    
    loaded = load_lockfile(lockfile_path)
    
    assert loaded["content_hash"] == original["content_hash"]
    assert loaded["sealed_payload"] == original["sealed_payload"]


def test_load_lockfile_missing(tmp_path):
    """Test loading a non-existent lockfile."""
    lockfile_path = tmp_path / "missing.lock"
    
    with pytest.raises(ValueError, match="not found"):
        load_lockfile(lockfile_path)


def test_load_lockfile_tampered(tmp_path):
    """Test detecting a tampered lockfile."""
    strata = {"holdout_A": {"ids": ["ep1"]}}
    lockfile_path = tmp_path / "test.lock"
    create_lockfile(strata, lockfile_path)
    
    lockfile = json.loads(lockfile_path.read_text())
    lockfile["sealed_payload"]["strata"]["holdout_B"] = {"ids": ["ep2"]}
    lockfile_path.write_text(json.dumps(lockfile))
    
    with pytest.raises(ValueError, match="hash mismatch"):
        load_lockfile(lockfile_path)


def test_load_lockfile_invalid_json(tmp_path):
    """Test loading malformed JSON."""
    lockfile_path = tmp_path / "bad.lock"
    lockfile_path.write_text("{not valid json")
    
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_lockfile(lockfile_path)


def test_get_registered_strata(tmp_path):
    """Test extracting registered stratum names."""
    strata = {
        "holdout_A": {"ids": ["ep1"]},
        "holdout_B": {"ids": ["ep2"]},
        "holdout_C": {"globs": ["*.json"]}
    }
    lockfile_path = tmp_path / "test.lock"
    lockfile = create_lockfile(strata, lockfile_path)
    
    registered = get_registered_strata(lockfile)
    
    assert registered == {"holdout_A", "holdout_B", "holdout_C"}


def test_verify_strata_usage_valid(tmp_path):
    """Test verifying that all used strata are registered."""
    strata = {
        "holdout_A": {"ids": ["ep1"]},
        "holdout_B": {"ids": ["ep2"]},
        "holdout_C": {"globs": ["*.json"]}
    }
    lockfile_path = tmp_path / "test.lock"
    create_lockfile(strata, lockfile_path)
    
    used_strata = ["holdout_A", "holdout_B"]
    is_valid, message = verify_strata_usage(used_strata, lockfile_path)
    
    assert is_valid
    assert "OK" in message
    assert "2 strata" in message


def test_verify_strata_usage_post_hoc(tmp_path):
    """Test detecting post-hoc strata."""
    strata = {
        "holdout_A": {"ids": ["ep1"]},
        "holdout_B": {"ids": ["ep2"]}
    }
    lockfile_path = tmp_path / "test.lock"
    create_lockfile(strata, lockfile_path)
    
    used_strata = ["holdout_A", "post_hoc_slice", "holdout_B"]
    is_valid, message = verify_strata_usage(used_strata, lockfile_path)
    
    assert not is_valid
    assert "ERROR" in message
    assert "Post-hoc" in message
    assert "post_hoc_slice" in message


def test_verify_strata_usage_missing_lockfile(tmp_path):
    """Test verification with missing lockfile."""
    lockfile_path = tmp_path / "missing.lock"
    used_strata = ["holdout_A"]
    
    is_valid, message = verify_strata_usage(used_strata, lockfile_path)
    
    assert not is_valid
    assert "ERROR" in message


def test_gate_keep_decision_allowed(tmp_path):
    """Test gating a valid keep decision."""
    strata = {
        "holdout_A": {"ids": ["ep1"]},
        "holdout_B": {"ids": ["ep2"]}
    }
    lockfile_path = tmp_path / "test.lock"
    create_lockfile(strata, lockfile_path)
    
    justifying_strata = ["holdout_A", "holdout_B"]
    allowed, message, exit_code = gate_keep_decision(
        justifying_strata,
        lockfile_path
    )
    
    assert allowed
    assert exit_code == 0
    assert "ALLOWED" in message
    assert "holdout_A" in message


def test_gate_keep_decision_refused_post_hoc(tmp_path):
    """Test refusing a keep decision based on post-hoc strata."""
    strata = {
        "holdout_A": {"ids": ["ep1"]},
        "holdout_B": {"ids": ["ep2"]}
    }
    lockfile_path = tmp_path / "test.lock"
    create_lockfile(strata, lockfile_path)
    
    justifying_strata = ["holdout_A", "post_hoc_slice"]
    allowed, message, exit_code = gate_keep_decision(
        justifying_strata,
        lockfile_path
    )
    
    assert not allowed
    assert exit_code == 2
    assert "REFUSED" in message
    assert "post-hoc" in message.lower()
    assert "post_hoc_slice" in message


def test_gate_keep_decision_no_strata(tmp_path):
    """Test gating with no justifying strata."""
    strata = {"holdout_A": {"ids": ["ep1"]}}
    lockfile_path = tmp_path / "test.lock"
    create_lockfile(strata, lockfile_path)
    
    justifying_strata = []
    allowed, message, exit_code = gate_keep_decision(
        justifying_strata,
        lockfile_path
    )
    
    assert not allowed
    assert exit_code == 1
    assert "ERROR" in message


def test_gate_keep_decision_missing_lockfile(tmp_path):
    """Test gating with missing lockfile."""
    lockfile_path = tmp_path / "missing.lock"
    justifying_strata = ["holdout_A"]
    
    allowed, message, exit_code = gate_keep_decision(
        justifying_strata,
        lockfile_path
    )
    
    assert not allowed
    assert exit_code == 1
    assert "ERROR" in message
