"""
Deployment Manager - Configuration
App definitions, shared constants, and helper functions.
"""

import glob
import os
import sys

# Server settings
SERVER_USER = "ec2-user"
SERVER_IP = "100.50.222.238"
SSH_OPTIONS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", "ConnectTimeout=10",
]

# Base paths
DEPLOYMENT_MANAGER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.dirname(DEPLOYMENT_MANAGER_DIR)  # C:\claude_projects


def find_ssh_key():
    """Find SSH key, checking deployment-manager dir first, then taskschedule dir."""
    # Check deployment-manager directory
    pem_files = glob.glob(os.path.join(DEPLOYMENT_MANAGER_DIR, "*.pem"))
    if pem_files:
        return pem_files[0]

    # Fallback to taskschedule directory
    pem_files = glob.glob(os.path.join(PROJECTS_DIR, "taskschedule", "*.pem"))
    if pem_files:
        return pem_files[0]

    return None


# App configurations
APPS = {
    "taskschedule": {
        "local_path": os.path.join(PROJECTS_DIR, "taskschedule"),
        "remote_path": "/home/ec2-user/taskschedule",
        "service_name": "taskschedule",
        "port": 5000,
        "url": "http://taskschedule.mebbert.com:5000",
        "stack": "python",
        "db_remote_path": "/home/ec2-user/taskschedule/data/database.db",
        "exclude_patterns": [
            "venv/", "data/", ".git/", "__pycache__/", "*.pyc",
            "*.db", "*.db-journal", "*.db.bak*", "*.sqlite", "*.sqlite3",
            "app.log", ".DS_Store",
        ],
        "pre_sync_commands": [],
        "ensure_dirs": ["data"],
        "dep_install": "python3 -m pip install -r requirements.txt",
    },
    "sevenhabitslist": {
        "local_path": os.path.join(PROJECTS_DIR, "sevenhabitslist"),
        "remote_path": "/home/ec2-user/sevenhabitslist",
        "service_name": "sevenhabitslist",
        "port": 3002,
        "url": "https://sevenhabitslist.mebbert.com",
        "stack": "python",
        "db_remote_path": "/home/ec2-user/sevenhabitslist/data/sevenhabits.db",
        "exclude_patterns": [
            "venv/", "data/", ".git/", "__pycache__/", "*.pyc",
            "*.db", "*.db-journal", "*.sqlite", "*.sqlite3", ".DS_Store",
        ],
        "pre_sync_commands": [],

        "dep_install": "source venv/bin/activate && pip install -r requirements.txt",
    },
    "recipeshoppinglist": {
        "local_path": os.path.join(PROJECTS_DIR, "recipeshoppinglist"),
        "remote_path": "/home/ec2-user/recipeshoppinglist",
        "service_name": "recipeshoppinglist",
        "port": 3003,
        "url": "https://recipeshoppinglist.mebbert.com",
        "stack": "python",
        "db_remote_path": "/home/ec2-user/recipeshoppinglist/data/recipes.db",
        "exclude_patterns": [
            "venv/", "data/", ".git/", "__pycache__/", "*.pyc",
            "*.db", "*.db-journal", "*.sqlite", "*.sqlite3", ".DS_Store",
        ],
        "pre_sync_commands": [],
        "dep_install": "python3 -m pip install -r requirements.txt",
    },
    "tifootball": {
        "local_path": os.path.join(PROJECTS_DIR, "tifootball"),
        "remote_path": "/home/ec2-user/tifootball",
        "service_name": "tifootball",
        "port": 3001,
        "url": "https://tifootball.mebbert.com",
        "stack": "node",
        "db_remote_path": "/home/ec2-user/tifootball/data/tifootball.db",
        "exclude_patterns": [
            "node_modules/", ".git/", "client/src/",
            "*.db", "*.db-journal", "*.sqlite", "*.sqlite3", ".DS_Store",
        ],
        "pre_sync_commands": [
            {
                "cmd": "npm run build",
                "cwd_suffix": "client",
                "description": "Building React frontend",
            }
        ],
        "ensure_dirs": ["data"],
        "dep_install": "cd server && npm install",
    },
    "rjbingo": {
        "local_path": os.path.join(PROJECTS_DIR, "rjbingo"),
        "remote_path": "/home/ec2-user/rjbingo",
        "service_name": "rjbingo",
        "port": 5001,
        "url": "https://rjbingo.mebbert.com",
        "stack": "python",
        "db_remote_path": "/home/ec2-user/rjbingo/data/bingo.db",
        "exclude_patterns": [
            "venv/", "data/", ".git/", "__pycache__/", "*.pyc",
            "*.db", "*.db-journal", "*.sqlite", "*.sqlite3", ".DS_Store",
        ],
        "pre_sync_commands": [],
        "ensure_dirs": ["data"],
        "dep_install": "python3 -m pip install -r requirements.txt",
    },
}

# Backup settings
BACKUPS_DIR = os.path.join(DEPLOYMENT_MANAGER_DIR, "backups")


def get_app_config(name):
    """Get config for a single app by name."""
    name = name.lower().strip()
    if name not in APPS:
        print(f"Error: Unknown app '{name}'")
        print(f"Available apps: {', '.join(APPS.keys())}")
        sys.exit(1)
    return APPS[name]


def get_app_names(arg):
    """Parse app argument - 'all' returns all app names, otherwise returns list with single app."""
    arg = arg.lower().strip()
    if arg == "all":
        return list(APPS.keys())
    if arg not in APPS:
        print(f"Error: Unknown app '{arg}'")
        print(f"Available: {', '.join(APPS.keys())} | all")
        sys.exit(1)
    return [arg]
