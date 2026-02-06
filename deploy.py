"""
Deployment Manager - Full Deployment
Sync files, install dependencies, restart services, and verify.

Usage:
    python deploy.py <app|all>        Deploy specified app(s)
    python deploy.py <app> --yes      Skip confirmation prompt
"""

import os
import sys
import time

from config import get_app_names, get_app_config
from ssh_utils import (
    check_prerequisites, test_ssh_connection, run_local,
    run_ssh, run_ssh_quiet, sync_files,
)


def deploy_app(app_name):
    """Deploy a single application."""
    config = get_app_config(app_name)
    print(f"\n{'='*60}")
    print(f"  Deploying: {app_name}")
    print(f"  {config['local_path']} -> {config['remote_path']}")
    print(f"{'='*60}")

    # Pre-sync commands (e.g., npm build for tifootball)
    for cmd_info in config.get("pre_sync_commands", []):
        cwd = os.path.join(config["local_path"], cmd_info.get("cwd_suffix", ""))
        result = run_local(
            cmd_info["cmd"],
            description=cmd_info.get("description", cmd_info["cmd"]),
            check=True,
            cwd=cwd,
        )
        if result.returncode != 0:
            return False

    # Sync files
    print("\n  [Syncing files]")
    sync_files(
        config["local_path"],
        config["remote_path"],
        config["exclude_patterns"],
    )

    # Install dependencies
    print("\n  [Installing dependencies]")
    dep_cmd = f"cd {config['remote_path']} && {config['dep_install']}"
    result = run_ssh(dep_cmd, description="Installing dependencies", check=False)
    if result.returncode != 0:
        print(f"  WARNING: Dependency install had issues (exit code {result.returncode})")

    # Restart service
    print("\n  [Restarting service]")
    run_ssh(
        f"sudo systemctl restart {config['service_name']}",
        description=f"Restarting {config['service_name']}",
        check=False,
    )

    # Wait and verify
    print("  Waiting for service to start...")
    time.sleep(2)

    stdout, _, rc = run_ssh_quiet(
        f"systemctl is-active {config['service_name']}"
    )
    if stdout == "active":
        print(f"  Service {config['service_name']}: ACTIVE")
        return True
    else:
        print(f"  Service {config['service_name']}: {stdout or 'FAILED'}")
        print("\n  Recent logs:")
        run_ssh(
            f"sudo journalctl -u {config['service_name']} -n 20 --no-pager",
            check=False,
        )
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python deploy.py <app|all> [--yes]")
        print(f"Apps: taskschedule, sevenhabitslist, recipeshoppinglist, tifootball, all")
        sys.exit(1)

    app_names = get_app_names(sys.argv[1])
    skip_confirm = "--yes" in sys.argv

    print("Deployment Manager - Full Deploy")
    print("=" * 40)

    # Prerequisites
    print("\n[Prerequisites]")
    if not check_prerequisites():
        sys.exit(1)
    if not test_ssh_connection():
        sys.exit(1)

    # Confirmation
    print(f"\nApps to deploy: {', '.join(app_names)}")
    if not skip_confirm:
        response = input("\nProceed with deployment? [y/N] ").strip().lower()
        if response != "y":
            print("Deployment cancelled.")
            sys.exit(0)

    # Deploy each app
    results = {}
    for name in app_names:
        try:
            results[name] = deploy_app(name)
        except Exception as e:
            print(f"\n  ERROR deploying {name}: {e}")
            results[name] = False

    # Summary
    print(f"\n{'='*60}")
    print("  DEPLOYMENT SUMMARY")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "OK" if success else "FAILED"
        config = get_app_config(name)
        print(f"  [{status:>6}] {name:<25} {config['url']}")
    print()

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
