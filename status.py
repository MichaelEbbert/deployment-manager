"""
Deployment Manager - Status Checks
Check service status, ports, processes, and HTTP health for all apps.

Usage:
    python status.py <app|all>
"""

import sys

from config import get_app_names, get_app_config
from ssh_utils import check_prerequisites, test_ssh_connection, run_ssh_quiet


def check_app_status(app_name):
    """Run all health checks for a single app. Returns True if all pass."""
    config = get_app_config(app_name)
    service = config["service_name"]
    port = config["port"]

    print(f"\n  {app_name} (port {port})")
    print(f"  {'-'*40}")

    all_ok = True

    # 1. Service status
    stdout, _, rc = run_ssh_quiet(f"systemctl is-active {service}")
    ok = stdout == "active"
    print(f"  {'[OK]' if ok else '[FAIL]':>8}  Service: {stdout or 'unknown'}")
    if not ok:
        all_ok = False

    # 2. Port listening
    stdout, _, rc = run_ssh_quiet(f"sudo netstat -tlnp 2>/dev/null | grep ':{port} ' || true")
    ok = bool(stdout.strip())
    print(f"  {'[OK]' if ok else '[FAIL]':>8}  Port {port}: {'listening' if ok else 'not listening'}")
    if not ok:
        all_ok = False

    # 3. Process check (via systemd MainPID)
    stdout, _, rc = run_ssh_quiet(
        f"systemctl show {service} --property=MainPID"
    )
    pid = stdout.replace("MainPID=", "").strip()
    ok = pid and pid != "0"
    if ok:
        # Get process command for display
        cmd_out, _, _ = run_ssh_quiet(f"ps -p {pid} -o args= 2>/dev/null || true")
        display = cmd_out.strip() if cmd_out.strip() else f"PID {pid}"
        print(f"  {'[OK]':>8}  Process: {display}")
    else:
        print(f"  {'[FAIL]':>8}  Process: not running")
        all_ok = False

    # 4. HTTP check
    stdout, _, rc = run_ssh_quiet(
        f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}/ --max-time 5"
    )
    http_code = stdout.strip().strip("'")
    ok = http_code.startswith(("2", "3"))
    print(f"  {'[OK]' if ok else '[FAIL]':>8}  HTTP: {http_code or 'no response'}")
    if not ok:
        all_ok = False

    # 5. Last 3 log lines
    stdout, _, rc = run_ssh_quiet(
        f"sudo journalctl -u {service} -n 3 --no-pager 2>/dev/null"
    )
    if stdout.strip():
        print(f"  {'':>8}  Recent logs:")
        for line in stdout.strip().split("\n"):
            print(f"  {'':>8}    {line.strip()}")

    return all_ok


def main():
    if len(sys.argv) < 2:
        print("Usage: python status.py <app|all>")
        print(f"Apps: taskschedule, sevenhabitslist, recipeshoppinglist, tifootball, all")
        sys.exit(1)

    app_names = get_app_names(sys.argv[1])

    print("Deployment Manager - Status Check")
    print("=" * 40)

    print("\n[Prerequisites]")
    if not check_prerequisites():
        sys.exit(1)
    if not test_ssh_connection():
        sys.exit(1)

    results = {}
    for name in app_names:
        try:
            results[name] = check_app_status(name)
        except Exception as e:
            print(f"\n  ERROR checking {name}: {e}")
            results[name] = False

    # Summary
    print(f"\n{'='*40}")
    print("  SUMMARY")
    print(f"{'='*40}")
    for name, ok in results.items():
        print(f"  {'[OK]' if ok else '[FAIL]':>8}  {name}")
    print()

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
