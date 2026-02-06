"""
Deployment Manager - Database Backup
Download database files from the EC2 instance for local backup.

Rotation strategy:
- Only backup if newest backup is > 7 days old
- Keep last 4 weekly backups
- Keep 1 monthly backup for 12 months
- ~15-16 backups per app total

Usage:
    python backup.py <app|all>          Backup specified app(s)
    python backup.py <app|all> --force  Backup even if recent backup exists
    python backup.py --list             List existing backups
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from collections import defaultdict

from config import get_app_names, get_app_config, APPS, BACKUPS_DIR, SERVER_USER, SERVER_IP, SSH_OPTIONS
from ssh_utils import check_prerequisites, test_ssh_connection, run_ssh_quiet, _ssh_key


def parse_backup_date(filename):
    """Extract date from backup filename like 'database.db.2026-02-05'."""
    match = re.search(r'\.(\d{4}-\d{2}-\d{2})$', filename)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    return None


def get_existing_backups(app_name):
    """Get list of existing backups for an app, sorted newest first."""
    app_dir = os.path.join(BACKUPS_DIR, app_name)
    if not os.path.exists(app_dir):
        return []

    backups = []
    for f in os.listdir(app_dir):
        date = parse_backup_date(f)
        if date:
            path = os.path.join(app_dir, f)
            backups.append((f, date, path))

    # Sort by date, newest first
    backups.sort(key=lambda x: x[1], reverse=True)
    return backups


def should_backup(app_name, force=False):
    """Check if we should backup (newest backup > 7 days old)."""
    if force:
        return True

    backups = get_existing_backups(app_name)
    if not backups:
        return True

    newest_date = backups[0][1]
    days_old = (datetime.now().date() - newest_date).days

    if days_old <= 7:
        print(f"  Skipping: latest backup is {days_old} days old (threshold: 7)")
        return False

    return True


def rotate_backups(app_name):
    """
    Apply rotation policy:
    - Keep last 4 backups (weekly)
    - Keep 1 per month for 12 months
    """
    backups = get_existing_backups(app_name)
    if len(backups) <= 4:
        return  # Nothing to rotate yet

    to_keep = set()
    to_delete = []

    # Keep the 4 most recent
    for f, date, path in backups[:4]:
        to_keep.add(path)

    # Group remaining by month
    monthly = defaultdict(list)
    for f, date, path in backups[4:]:
        month_key = (date.year, date.month)
        monthly[month_key].append((f, date, path))

    # Keep oldest backup from each month (up to 12 months)
    cutoff = datetime.now().date() - timedelta(days=365)
    months_kept = 0

    for month_key in sorted(monthly.keys(), reverse=True):
        if months_kept >= 12:
            break

        # Get oldest from this month
        month_backups = sorted(monthly[month_key], key=lambda x: x[1])
        oldest = month_backups[0]

        if oldest[1] >= cutoff:
            to_keep.add(oldest[2])
            months_kept += 1

    # Delete anything not in to_keep
    for f, date, path in backups:
        if path not in to_keep:
            to_delete.append((f, path))

    if to_delete:
        print(f"  Rotating out {len(to_delete)} old backup(s):")
        for f, path in to_delete:
            print(f"    Removing: {f}")
            os.remove(path)


def list_backups():
    """List all existing backups."""
    if not os.path.exists(BACKUPS_DIR):
        print("No backups directory found.")
        return

    print(f"\nBackups in: {BACKUPS_DIR}\n")

    for app_name in APPS.keys():
        backups = get_existing_backups(app_name)
        if backups:
            print(f"  {app_name}: ({len(backups)} backups)")
            for f, date, path in backups[:5]:
                size_kb = os.path.getsize(path) / 1024
                days_ago = (datetime.now().date() - date).days
                print(f"    {f} ({size_kb:.1f} KB, {days_ago}d ago)")
            if len(backups) > 5:
                print(f"    ... and {len(backups) - 5} more")
            print()


def backup_app(app_name, force=False):
    """Backup database for a single application."""
    config = get_app_config(app_name)
    db_path = config.get("db_remote_path")

    if not db_path:
        print(f"  {app_name}: No database path configured, skipping")
        return None

    print(f"\n  {app_name}")
    print(f"  {'-'*40}")

    # Check if backup needed
    if not should_backup(app_name, force):
        return None

    # Check if remote db exists
    stdout, stderr, rc = run_ssh_quiet(f"test -f {db_path} && echo exists")
    if stdout != "exists":
        print(f"  WARNING: Database file not found on server")
        return False

    # Get remote file size
    stdout, _, _ = run_ssh_quiet(f"stat -c%s {db_path} 2>/dev/null || stat -f%z {db_path} 2>/dev/null")
    remote_size = int(stdout) if stdout.isdigit() else 0
    print(f"  Remote: {db_path} ({remote_size / 1024:.1f} KB)")

    # Create backup directory
    app_backup_dir = os.path.join(BACKUPS_DIR, app_name)
    os.makedirs(app_backup_dir, exist_ok=True)

    # Generate backup filename: name.db.yyyy-mm-dd
    today = datetime.now().strftime("%Y-%m-%d")
    db_filename = os.path.basename(db_path)
    backup_filename = f"{db_filename}.{today}"
    local_path = os.path.join(app_backup_dir, backup_filename)

    # Check if today's backup already exists
    if os.path.exists(local_path):
        print(f"  Backup for today already exists: {backup_filename}")
        return None

    # Download via SCP
    print(f"  Downloading...")
    scp_cmd = [
        "scp", "-i", _ssh_key(),
    ] + SSH_OPTIONS + [
        f"{SERVER_USER}@{SERVER_IP}:{db_path}",
        local_path,
    ]

    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        print(f"  FAILED: {result.stderr.strip()}")
        return False

    # Verify local file
    if os.path.exists(local_path):
        local_size = os.path.getsize(local_path)
        print(f"  Saved: {backup_filename} ({local_size / 1024:.1f} KB)")

        # Apply rotation
        rotate_backups(app_name)
        return True
    else:
        print(f"  FAILED: File not created")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python backup.py <app|all> [--force]")
        print("       python backup.py --list")
        print(f"Apps: {', '.join(APPS.keys())}, all")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_backups()
        sys.exit(0)

    app_names = get_app_names(sys.argv[1])
    force = "--force" in sys.argv

    print("Deployment Manager - Database Backup")
    print("=" * 40)

    if force:
        print("(--force: ignoring 7-day threshold)")

    print("\n[Prerequisites]")
    if not check_prerequisites():
        sys.exit(1)
    if not test_ssh_connection():
        sys.exit(1)

    results = {}
    for name in app_names:
        try:
            results[name] = backup_app(name, force)
        except Exception as e:
            print(f"\n  ERROR backing up {name}: {e}")
            results[name] = False

    # Summary
    print(f"\n{'='*40}")
    print("  BACKUP SUMMARY")
    print(f"{'='*40}")
    for name, success in results.items():
        if success is None:
            status = "SKIP"
        elif success:
            status = "OK"
        else:
            status = "FAIL"
        print(f"  [{status:>4}] {name}")
    print(f"\n  Backups: {BACKUPS_DIR}")
    print()

    if any(r is False for r in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
