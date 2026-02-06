"""
Deployment Manager - Quick Service Restart
Restart services and verify they come back up.

Usage:
    python restart.py <app|all>
"""

import sys
import time

from config import get_app_names, get_app_config
from ssh_utils import check_prerequisites, test_ssh_connection, run_ssh, run_ssh_quiet


def restart_app(app_name):
    """Restart a single app's service and verify it comes back up."""
    config = get_app_config(app_name)
    service = config["service_name"]

    print(f"\n  Restarting {app_name} ({service})...")

    # Restart
    run_ssh(f"sudo systemctl restart {service}", check=False)

    # Wait and verify
    time.sleep(2)
    stdout, _, rc = run_ssh_quiet(f"systemctl is-active {service}")

    if stdout == "active":
        print(f"  [OK] {app_name}: active")
        return True
    else:
        print(f"  [FAIL] {app_name}: {stdout or 'failed'}")
        print("\n  Recent logs:")
        run_ssh(
            f"sudo journalctl -u {service} -n 15 --no-pager",
            check=False,
        )
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python restart.py <app|all>")
        print(f"Apps: taskschedule, sevenhabitslist, recipeshoppinglist, tifootball, all")
        sys.exit(1)

    app_names = get_app_names(sys.argv[1])

    print("Deployment Manager - Restart")
    print("=" * 40)

    print("\n[Prerequisites]")
    if not check_prerequisites():
        sys.exit(1)
    if not test_ssh_connection():
        sys.exit(1)

    results = {}
    for name in app_names:
        try:
            results[name] = restart_app(name)
        except Exception as e:
            print(f"\n  ERROR restarting {name}: {e}")
            results[name] = False

    # Summary
    print(f"\n{'='*40}")
    for name, ok in results.items():
        print(f"  {'[OK]' if ok else '[FAIL]':>8}  {name}")
    print()

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
