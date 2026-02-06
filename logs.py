"""
Deployment Manager - View Service Logs
View or follow logs for a single application.

Usage:
    python logs.py <app>                    Last 50 lines
    python logs.py <app> -n 100             Last 100 lines
    python logs.py <app> -f                 Follow real-time
    python logs.py <app> --since "1 hour ago"
"""

import sys

from config import get_app_config, APPS
from ssh_utils import check_prerequisites, test_ssh_connection, run_ssh, run_ssh_stream


def main():
    if len(sys.argv) < 2:
        print("Usage: python logs.py <app> [-f] [-n LINES] [--since TIME]")
        print(f"Apps: {', '.join(APPS.keys())}")
        print("\nNote: Only single app supported (no 'all')")
        sys.exit(1)

    app_name = sys.argv[1].lower().strip()
    if app_name == "all":
        print("Error: logs.py supports single app only, not 'all'")
        print(f"Apps: {', '.join(APPS.keys())}")
        sys.exit(1)

    config = get_app_config(app_name)
    service = config["service_name"]

    # Parse flags
    follow = "-f" in sys.argv or "--follow" in sys.argv
    lines = 50
    since = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] in ("-n", "--lines") and i + 1 < len(args):
            lines = int(args[i + 1])
            i += 2
        elif args[i] == "--since" and i + 1 < len(args):
            since = args[i + 1]
            i += 2
        else:
            i += 1

    print(f"Deployment Manager - Logs: {app_name}")
    print("=" * 40)

    print("\n[Prerequisites]")
    if not check_prerequisites():
        sys.exit(1)
    if not test_ssh_connection():
        sys.exit(1)

    # Build journalctl command
    cmd = f"sudo journalctl -u {service}"

    if since:
        cmd += f' --since "{since}"'

    if follow:
        cmd += f" -n {lines} -f"
        print(f"\n  Following logs for {app_name} (Ctrl+C to stop)...\n")
        run_ssh_stream(cmd)
    else:
        cmd += f" -n {lines} --no-pager"
        print(f"\n  Last {lines} lines for {app_name}:\n")
        run_ssh(cmd, check=False)


if __name__ == "__main__":
    main()
