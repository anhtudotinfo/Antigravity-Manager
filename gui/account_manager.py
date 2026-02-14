# -*- coding: utf-8 -*-
import json
import os
import time
import uuid
from pathlib import Path
from datetime import datetime

# Use relative imports
from utils import info, error, warning, get_accounts_file_path, get_app_data_dir
from db_manager import backup_account, restore_account, get_current_account_info
from process_manager import close_antigravity, start_antigravity

def load_accounts():
    """Load account list"""
    file_path = get_accounts_file_path()
    if not file_path.exists():
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        error(f"Failed to load account list: {e}")
        return {}

def save_accounts(accounts):
    """Save account list"""
    file_path = get_accounts_file_path()
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        error(f"Failed to save account list: {e}")
        return False

def add_account_snapshot(name=None, email=None):
    """Add current state as a new account; overwrite if email already exists"""
    # 0. Auto-detect info
    if not email:
        info("Attempting to read account info from database...")
        account_info = get_current_account_info()
        if account_info and "email" in account_info:
            email = account_info["email"]
            info(f"Auto-detected email: {email}")
        else:
            warning("Unable to auto-detect email from database, using 'Unknown'")
            email = "Unknown"

    if not name:
        # If no name provided, use email prefix or default name
        if email and email != "Unknown":
            name = email.split("@")[0]
        else:
            name = f"Account_{int(time.time())}"
        info(f"Using auto-generated name: {name}")

    # 1. Check if an account with the same email already exists
    accounts = load_accounts()
    existing_account = None
    existing_id = None

    for acc_id, acc_data in accounts.items():
        if acc_data.get("email") == email:
            existing_account = acc_data
            existing_id = acc_id
            break

    if existing_account:
        info(f"Detected existing snapshot for {email}, will overwrite")
        # Use existing ID and backup path
        account_id = existing_id
        backup_path = Path(existing_account["backup_file"])
        created_at = existing_account.get("created_at", datetime.now().isoformat())

        # If no new name provided, keep the original name
        if not name or name == email.split("@")[0]:
            name = existing_account.get("name", name)
    else:
        info(f"Creating new account snapshot: {email}")
        # Generate new ID and backup path
        account_id = str(uuid.uuid4())
        backup_filename = f"{account_id}.json"
        backup_dir = get_app_data_dir() / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / backup_filename
        created_at = datetime.now().isoformat()

    # 2. Perform backup
    info(f"Backing up current state as account: {name}")
    if not backup_account(email, str(backup_path)):
        error("Backup failed, aborting account creation")
        return False

    # 3. Update account list
    accounts[account_id] = {
        "id": account_id,
        "name": name,
        "email": email,
        "backup_file": str(backup_path),
        "created_at": created_at,
        "last_used": datetime.now().isoformat()
    }

    if save_accounts(accounts):
        if existing_account:
            info(f"Account {name} ({email}) snapshot updated")
        else:
            info(f"Account {name} ({email}) added successfully")
        return True
    return False

def delete_account(account_id):
    """Delete an account"""
    accounts = load_accounts()
    if account_id not in accounts:
        error("Account not found")
        return False

    account = accounts[account_id]
    name = account.get("name", "Unknown")
    backup_file = account.get("backup_file")

    # Delete backup file
    if backup_file and os.path.exists(backup_file):
        try:
            os.remove(backup_file)
            info(f"Backup file deleted: {backup_file}")
        except Exception as e:
            warning(f"Failed to delete backup file: {e}")

    # Remove from list
    del accounts[account_id]
    if save_accounts(accounts):
        info(f"Account {name} deleted")
        return True
    return False

def switch_account(account_id):
    """Switch to specified account"""
    accounts = load_accounts()
    if account_id not in accounts:
        error("Account not found")
        return False

    account = accounts[account_id]
    name = account.get("name", "Unknown")
    backup_file = account.get("backup_file")

    if not backup_file or not os.path.exists(backup_file):
        error(f"Backup file missing: {backup_file}")
        return False

    info(f"Preparing to switch to account: {name}")

    # 1. Close process
    if not close_antigravity():
        # Try to continue, but warn
        warning("Unable to close Antigravity, attempting forced restore...")

    # 2. Restore data
    if restore_account(backup_file):
        # Update last used time
        accounts[account_id]["last_used"] = datetime.now().isoformat()
        save_accounts(accounts)

        # 3. Start process
        start_antigravity()
        info(f"Switched to account {name} successfully")
        return True
    else:
        error("Data restore failed")
        return False

def list_accounts_data():
    """Get account list data (for display)"""
    accounts = load_accounts()
    data = list(accounts.values())
    # Sort by last used time in descending order
    data.sort(key=lambda x: x.get("last_used", ""), reverse=True)
    return data
