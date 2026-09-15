"""Core functionality for strata-lock."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def compute_content_hash(data: dict[str, Any]) -> str:
    """Compute SHA256 hash of normalized JSON data."""
    normalized = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def create_lockfile(
    strata_definitions: dict[str, Any],
    output_path: Path,
    note: str | None = None
) -> dict[str, Any]:
    """Create a sealed lockfile from strata definitions.
    
    Args:
        strata_definitions: Dictionary mapping stratum names to their definitions.
            Each definition should include 'ids' (list of episode/task ids) and/or
            'globs' (list of path patterns).
        output_path: Where to write the lockfile.
        note: Optional human-readable note or experiment ID.
    
    Returns:
        The complete lockfile data structure.
    """
    sealed_payload = {
        "strata": strata_definitions
    }
    
    lockfile = {
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sealed_payload": sealed_payload,
        "content_hash": compute_content_hash(sealed_payload),
    }
    
    if note:
        lockfile["note"] = note
    
    output_path.write_text(json.dumps(lockfile, indent=2) + '\n')
    return lockfile


def load_lockfile(lockfile_path: Path) -> dict[str, Any]:
    """Load and validate a lockfile.
    
    Args:
        lockfile_path: Path to the lockfile.
    
    Returns:
        The lockfile data structure.
    
    Raises:
        ValueError: If the lockfile is invalid or tampered.
    """
    if not lockfile_path.exists():
        raise ValueError(f"Lockfile not found: {lockfile_path}")
    
    try:
        lockfile = json.loads(lockfile_path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in lockfile: {e}")
    
    if "sealed_payload" not in lockfile or "content_hash" not in lockfile:
        raise ValueError("Lockfile missing required fields")
    
    expected_hash = compute_content_hash(lockfile["sealed_payload"])
    if expected_hash != lockfile["content_hash"]:
        raise ValueError(
            f"Lockfile hash mismatch. Expected {expected_hash}, "
            f"got {lockfile['content_hash']}. File may have been tampered."
        )
    
    return lockfile


def get_registered_strata(lockfile: dict[str, Any]) -> set[str]:
    """Extract the set of registered stratum names from a lockfile."""
    return set(lockfile["sealed_payload"]["strata"].keys())


def verify_strata_usage(
    used_strata: list[str],
    lockfile_path: Path
) -> tuple[bool, str]:
    """Verify that all used strata were pre-registered.
    
    Args:
        used_strata: List of stratum names that were used in scoring/results.
        lockfile_path: Path to the lockfile.
    
    Returns:
        Tuple of (is_valid, message).
        is_valid is True if all used strata are registered, False otherwise.
    """
    try:
        lockfile = load_lockfile(lockfile_path)
    except ValueError as e:
        return False, f"ERROR: {e}"
    
    registered = get_registered_strata(lockfile)
    used_set = set(used_strata)
    
    unregistered = used_set - registered
    
    if unregistered:
        return False, (
            f"ERROR: Post-hoc strata detected. The following strata were not "
            f"pre-registered: {sorted(unregistered)}"
        )
    
    return True, f"OK: All {len(used_set)} strata were pre-registered"


def gate_keep_decision(
    justifying_strata: list[str],
    lockfile_path: Path
) -> tuple[bool, str, int]:
    """Gate a keep decision by verifying justifying strata were pre-registered.
    
    Args:
        justifying_strata: List of stratum names used to justify the keep decision.
        lockfile_path: Path to the lockfile.
    
    Returns:
        Tuple of (allowed, message, exit_code).
        allowed is True if decision is allowed, False if refused.
        exit_code is 0 for allowed, 2 for refused, 1 for other errors.
    """
    if not justifying_strata:
        return False, "ERROR: No justifying strata provided", 1
    
    try:
        lockfile = load_lockfile(lockfile_path)
    except ValueError as e:
        return False, f"ERROR: {e}", 1
    
    registered = get_registered_strata(lockfile)
    justifying_set = set(justifying_strata)
    
    unregistered = justifying_set - registered
    
    if unregistered:
        return False, (
            f"REFUSED: Keep decision relies on post-hoc strata. "
            f"Unregistered strata: {sorted(unregistered)}. "
            f"Only pre-registered strata may justify keep decisions."
        ), 2
    
    return True, (
        f"ALLOWED: Keep decision justified by pre-registered strata: "
        f"{sorted(justifying_strata)}"
    ), 0
