"""
Deployment Manager - SSH/SCP/Tar Utilities
Shared functions for remote operations using scp/ssh (no rsync required).
"""

import fnmatch
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

from config import SERVER_USER, SERVER_IP, SSH_OPTIONS, find_ssh_key


def _ssh_key():
    """Get SSH key path or exit with error."""
    key = find_ssh_key()
    if not key:
        print("Error: No SSH key (.pem) found.")
        print("Place your .pem file in the deployment-manager directory.")
        sys.exit(1)
    return key


def _ssh_base():
    """Return base SSH command parts."""
    return ["ssh", "-i", _ssh_key()] + SSH_OPTIONS + [f"{SERVER_USER}@{SERVER_IP}"]


def _scp_base():
    """Return base SCP command parts."""
    return ["scp", "-i", _ssh_key()] + SSH_OPTIONS


def check_prerequisites():
    """Verify SSH key exists and ssh/scp are available."""
    key = find_ssh_key()
    if not key:
        print("FAIL: No SSH key (.pem) found")
        print("  Place your .pem file in the deployment-manager directory")
        return False

    for cmd in ["ssh", "scp"]:
        if not shutil.which(cmd):
            print(f"FAIL: '{cmd}' not found in PATH")
            return False

    print(f"  SSH key: {os.path.basename(key)}")
    return True


def test_ssh_connection():
    """Test SSH connectivity to the server."""
    print(f"  Testing SSH to {SERVER_IP}...")
    result = subprocess.run(
        _ssh_base() + ["echo ok"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0 and "ok" in result.stdout:
        print("  SSH connection OK")
        return True
    print(f"  SSH connection FAILED: {result.stderr.strip()}")
    return False


def run_local(cmd, description=None, check=True, cwd=None):
    """Run a local command with logging."""
    if description:
        print(f"  {description}...")

    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd,
    )

    if result.returncode != 0:
        if description:
            print(f"  FAILED: {description}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")
        if check:
            sys.exit(1)

    return result


def run_ssh(remote_cmd, description=None, check=True):
    """Run a command on the remote server via SSH."""
    if description:
        print(f"  {description}...")

    result = subprocess.run(
        _ssh_base() + [remote_cmd],
        capture_output=True, text=True, timeout=120,
    )

    if result.stdout.strip():
        print(result.stdout.strip())

    if result.returncode != 0:
        if description:
            print(f"  FAILED: {description}")
        if result.stderr.strip():
            print(f"  stderr: {result.stderr.strip()}")
        if check:
            sys.exit(1)

    return result


def run_ssh_quiet(remote_cmd):
    """Run SSH command and return (stdout, stderr, returncode) without printing."""
    try:
        result = subprocess.run(
            _ssh_base() + [remote_cmd],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "SSH command timed out", 1


def run_ssh_stream(remote_cmd):
    """Run SSH command with real-time output streaming (for logs -f)."""
    try:
        return subprocess.call(_ssh_base() + [remote_cmd])
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


def _should_exclude(path, exclude_patterns):
    """Check if a path should be excluded based on patterns."""
    # Normalize path separators to forward slashes
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")

    for pattern in exclude_patterns:
        # Directory pattern (ends with /)
        if pattern.endswith("/"):
            dir_name = pattern.rstrip("/")
            if dir_name in parts:
                return True
        # Wildcard pattern
        elif "*" in pattern:
            basename = os.path.basename(path)
            if fnmatch.fnmatch(basename, pattern):
                return True
        # Exact filename match
        else:
            basename = os.path.basename(path)
            if basename == pattern:
                return True

    return False


def sync_files(local_path, remote_path, exclude_patterns):
    """
    Sync local files to remote server using tarfile + scp + ssh extract.

    1. Create tar.gz archive locally (respecting exclusions)
    2. SCP archive to /tmp on server
    3. SSH to clean stale files (preserving data/venv/node_modules/db dirs)
    4. SSH to extract archive into target directory
    5. Clean up archive on both ends
    """
    archive_name = f"deploy_{os.path.basename(local_path)}.tar.gz"
    local_archive = os.path.join(tempfile.gettempdir(), archive_name)
    remote_archive = f"/tmp/{archive_name}"

    try:
        # Step 1: Create tar.gz archive
        print(f"  Creating archive from {local_path}...")
        file_count = 0

        with tarfile.open(local_archive, "w:gz") as tar:
            for root, dirs, files in os.walk(local_path):
                rel_root = os.path.relpath(root, local_path)
                if rel_root == ".":
                    rel_root = ""

                # Filter directories in-place to skip excluded ones
                dirs[:] = [
                    d for d in dirs
                    if not _should_exclude(
                        os.path.join(rel_root, d) if rel_root else d,
                        exclude_patterns,
                    )
                ]

                for f in files:
                    rel_path = os.path.join(rel_root, f) if rel_root else f
                    if _should_exclude(rel_path, exclude_patterns):
                        continue

                    full_path = os.path.join(root, f)
                    tar.add(full_path, arcname=rel_path)
                    file_count += 1

        archive_size_mb = os.path.getsize(local_archive) / (1024 * 1024)
        print(f"  Archive: {file_count} files, {archive_size_mb:.1f} MB")

        # Step 2: SCP archive to server
        print("  Uploading archive...")
        result = subprocess.run(
            _scp_base() + [local_archive, f"{SERVER_USER}@{SERVER_IP}:{remote_archive}"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            print(f"  SCP failed: {result.stderr.strip()}")
            sys.exit(1)

        # Step 3: Clean stale files on server (preserve data dirs)
        print("  Cleaning stale files on server...")
        preserve_dirs = "venv data node_modules db .db"
        clean_cmd = (
            f"cd {remote_path} && "
            f"find . -maxdepth 1 -mindepth 1 "
            + " ".join(f"! -name '{d}'" for d in preserve_dirs.split())
            + " -exec rm -rf {} + 2>/dev/null; true"
        )
        run_ssh_quiet(clean_cmd)

        # Step 4: Extract archive on server
        print("  Extracting on server...")
        extract_cmd = (
            f"mkdir -p {remote_path} && "
            f"tar -xzf {remote_archive} -C {remote_path} && "
            f"rm -f {remote_archive}"
        )
        stdout, stderr, rc = run_ssh_quiet(extract_cmd)
        if rc != 0:
            print(f"  Extract failed: {stderr}")
            sys.exit(1)

        print("  Sync complete")

    finally:
        # Clean up local archive
        if os.path.exists(local_archive):
            os.remove(local_archive)
