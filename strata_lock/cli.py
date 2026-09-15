"""Command-line interface for strata-lock."""

import argparse
import json
import sys
from pathlib import Path

from strata_lock.core import (
    create_lockfile,
    gate_keep_decision,
    load_lockfile,
    verify_strata_usage,
)


def cmd_lock(args: argparse.Namespace) -> int:
    """Lock subcommand: create a sealed lockfile from strata definitions."""
    try:
        strata_path = Path(args.strata_file)
        if not strata_path.exists():
            print(f"Error: Strata file not found: {strata_path}", file=sys.stderr)
            return 1
        
        with open(strata_path) as f:
            strata_definitions = json.load(f)
        
        if not isinstance(strata_definitions, dict):
            print(
                "Error: Strata file must contain a JSON object mapping "
                "stratum names to definitions",
                file=sys.stderr
            )
            return 1
        
        output_path = Path(args.output)
        lockfile = create_lockfile(
            strata_definitions,
            output_path,
            note=args.note
        )
        
        print(f"✓ Lockfile created: {output_path}")
        print(f"  Registered {len(strata_definitions)} strata")
        print(f"  Content hash: {lockfile['content_hash'][:16]}...")
        print(f"  Timestamp: {lockfile['timestamp']}")
        
        return 0
    
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in strata file: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify subcommand: check that used strata were pre-registered."""
    try:
        results_path = Path(args.results_file)
        if not results_path.exists():
            print(f"Error: Results file not found: {results_path}", file=sys.stderr)
            return 1
        
        with open(results_path) as f:
            results = json.load(f)
        
        if "used_strata" not in results:
            print(
                "Error: Results file must contain a 'used_strata' field "
                "listing the strata names used",
                file=sys.stderr
            )
            return 1
        
        used_strata = results["used_strata"]
        lockfile_path = Path(args.lockfile)
        
        is_valid, message = verify_strata_usage(used_strata, lockfile_path)
        
        if is_valid:
            print(f"✓ {message}")
            return 0
        else:
            print(f"✗ {message}", file=sys.stderr)
            return 1
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_gate_keep(args: argparse.Namespace) -> int:
    """Gate-keep subcommand: refuse keep decisions based on post-hoc strata."""
    try:
        decision_path = Path(args.decision_file)
        if not decision_path.exists():
            print(f"Error: Decision file not found: {decision_path}", file=sys.stderr)
            return 1
        
        with open(decision_path) as f:
            decision = json.load(f)
        
        if "justifying_strata" not in decision:
            print(
                "Error: Decision file must contain a 'justifying_strata' field",
                file=sys.stderr
            )
            return 1
        
        justifying_strata = decision["justifying_strata"]
        lockfile_path = Path(args.lockfile)
        
        allowed, message, exit_code = gate_keep_decision(
            justifying_strata,
            lockfile_path
        )
        
        if allowed:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}", file=sys.stderr)
        
        return exit_code
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="strata-lock",
        description="Pre-register holdout strata before scoring; refuse keep on post-hoc slices"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    lock_parser = subparsers.add_parser(
        "lock",
        help="Create a sealed lockfile from strata definitions"
    )
    lock_parser.add_argument(
        "strata_file",
        help="JSON file containing strata definitions"
    )
    lock_parser.add_argument(
        "-o", "--output",
        default=".strata-lock.json",
        help="Output lockfile path (default: .strata-lock.json)"
    )
    lock_parser.add_argument(
        "-n", "--note",
        help="Optional human-readable note or experiment ID"
    )
    
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify that scoring results only use pre-registered strata"
    )
    verify_parser.add_argument(
        "results_file",
        help="JSON file containing results with 'used_strata' field"
    )
    verify_parser.add_argument(
        "-l", "--lockfile",
        default=".strata-lock.json",
        help="Lockfile path (default: .strata-lock.json)"
    )
    
    gate_parser = subparsers.add_parser(
        "gate-keep",
        help="Gate a keep decision; refuse if justified by post-hoc strata"
    )
    gate_parser.add_argument(
        "decision_file",
        help="JSON file containing keep decision with 'justifying_strata' field"
    )
    gate_parser.add_argument(
        "-l", "--lockfile",
        default=".strata-lock.json",
        help="Lockfile path (default: .strata-lock.json)"
    )
    
    args = parser.parse_args()
    
    if args.command == "lock":
        exit_code = cmd_lock(args)
    elif args.command == "verify":
        exit_code = cmd_verify(args)
    elif args.command == "gate-keep":
        exit_code = cmd_gate_keep(args)
    else:
        parser.print_help()
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
