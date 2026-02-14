# -*- coding: utf-8 -*-
import argparse
import sys
import os

# Add the gui directory to sys.path so internal modules can import each other (e.g. account_manager imports utils)
sys.path.append(os.path.join(os.path.dirname(__file__), "gui"))

# Support both direct execution and module import
try:
    from gui.utils import info, error, warning
    from gui.account_manager import (
        list_accounts_data,
        add_account_snapshot,
        switch_account,
        delete_account
    )
    from gui.process_manager import start_antigravity, close_antigravity
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def show_menu():
    """Display the main menu"""
    print("\n" + "="*50)
    print("🚀 Antigravity Account Manager")
    print("="*50)
    print("\nSelect an action:")
    print("  1. 📋 List all snapshots")
    print("  2. ➕ Add/Update snapshot")
    print("  3. 🔄 Switch/Restore snapshot")
    print("  4. 🗑️  Delete snapshot")
    print("  5. ▶️  Start Antigravity")
    print("  6. ⏹️  Stop Antigravity")
    print("  0. 🚪 Exit")
    print("-"*50)

def list_accounts():
    """List all accounts"""
    accounts = list_accounts_data()
    if not accounts:
        info("No snapshots found")
        return []
    else:
        print("\n" + "="*50)
        info(f"Total {len(accounts)} snapshot(s):")
        print("="*50)
        for idx, acc in enumerate(accounts, 1):
            print(f"\n{idx}. {acc['name']}")
            print(f"   📧 Email: {acc['email']}")
            print(f"   🆔 ID: {acc['id']}")
            print(f"   ⏰ Last used: {acc['last_used']}")
            print("-" * 50)
        return accounts

def add_account():
    """Add account snapshot"""
    print("\n" + "="*50)
    print("➕ Add/Update Account Snapshot")
    print("="*50)

    name = input("\nEnter account name (leave empty to auto-generate): ").strip()
    email = input("Enter email (leave empty to auto-detect): ").strip()

    name = name if name else None
    email = email if email else None

    print()
    if add_account_snapshot(name, email):
        info("✅ Operation successful!")
    else:
        error("❌ Operation failed!")

def switch_account_interactive():
    """Interactive account switch"""
    accounts = list_accounts()
    if not accounts:
        return

    print("\n" + "="*50)
    print("🔄 Switch/Restore Account")
    print("="*50)

    choice = input("\nEnter the account number to switch to: ").strip()

    if not choice:
        warning("Operation cancelled")
        return

    real_id = resolve_id(choice)
    if not real_id:
        error(f"❌ Invalid number: {choice}")
        return

    print()
    if switch_account(real_id):
        info("✅ Switch successful!")
    else:
        error("❌ Switch failed!")

def delete_account_interactive():
    """Interactive account deletion"""
    accounts = list_accounts()
    if not accounts:
        return

    print("\n" + "="*50)
    print("🗑️  Delete Account Snapshot")
    print("="*50)

    choice = input("\nEnter the account number to delete: ").strip()

    if not choice:
        warning("Operation cancelled")
        return

    real_id = resolve_id(choice)
    if not real_id:
        error(f"❌ Invalid number: {choice}")
        return

    # Confirm deletion
    confirm = input(f"\n⚠️  Are you sure you want to delete this account? (y/N): ").strip().lower()
    if confirm != 'y':
        warning("Deletion cancelled")
        return

    print()
    if delete_account(real_id):
        info("✅ Deletion successful!")
    else:
        error("❌ Deletion failed!")

def interactive_mode():
    """Interactive menu mode"""
    while True:
        show_menu()
        choice = input("Enter option (0-6): ").strip()

        if choice == "1":
            list_accounts()
            input("\nPress Enter to continue...")

        elif choice == "2":
            add_account()
            input("\nPress Enter to continue...")

        elif choice == "3":
            switch_account_interactive()
            input("\nPress Enter to continue...")

        elif choice == "4":
            delete_account_interactive()
            input("\nPress Enter to continue...")

        elif choice == "5":
            print()
            start_antigravity()
            input("\nPress Enter to continue...")

        elif choice == "6":
            print()
            close_antigravity()
            input("\nPress Enter to continue...")

        elif choice == "0":
            print("\n👋 Goodbye!")
            sys.exit(0)

        else:
            error("❌ Invalid option, please try again")
            input("\nPress Enter to continue...")

def cli_mode():
    """Command-line mode"""
    parser = argparse.ArgumentParser(description="Antigravity Account Manager (Pure Python)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List
    subparsers.add_parser("list", help="List all snapshots")

    # Add
    add_parser = subparsers.add_parser("add", help="Save current state as a new snapshot")
    add_parser.add_argument("--name", "-n", help="Snapshot name (optional, auto-generated by default)")
    add_parser.add_argument("--email", "-e", help="Associated email (optional, read from database by default)")

    # Switch
    switch_parser = subparsers.add_parser("switch", help="Switch to a specified snapshot")
    switch_parser.add_argument("--id", "-i", required=True, help="Snapshot ID")

    # Delete
    del_parser = subparsers.add_parser("delete", help="Delete a snapshot")
    del_parser.add_argument("--id", "-i", required=True, help="Snapshot ID")

    # Process Control
    subparsers.add_parser("start", help="Start Antigravity")
    subparsers.add_parser("stop", help="Stop Antigravity")

    args = parser.parse_args()

    if args.command == "list":
        list_accounts()

    elif args.command == "add":
        if add_account_snapshot(args.name, args.email):
            info("Snapshot added successfully")
        else:
            sys.exit(1)

    elif args.command == "switch":
        real_id = resolve_id(args.id)
        if not real_id:
            error(f"Invalid ID or number: {args.id}")
            sys.exit(1)

        if switch_account(real_id):
            info("Switch successful")
        else:
            sys.exit(1)

    elif args.command == "delete":
        real_id = resolve_id(args.id)
        if not real_id:
            error(f"Invalid ID or number: {args.id}")
            sys.exit(1)

        if delete_account(real_id):
            info("Deletion successful")
        else:
            sys.exit(1)

    elif args.command == "start":
        start_antigravity()

    elif args.command == "stop":
        close_antigravity()

    else:
        # No arguments provided, enter interactive mode
        interactive_mode()

def main():
    """Main entry point"""
    # If no command-line arguments, enter interactive mode
    if len(sys.argv) == 1:
        interactive_mode()
    else:
        cli_mode()

def resolve_id(input_id):
    """Resolve ID, supports UUID or index number"""
    accounts = list_accounts_data()

    # 1. Try as index number
    if input_id.isdigit():
        idx = int(input_id)
        if 1 <= idx <= len(accounts):
            return accounts[idx-1]['id']

    # 2. Try as UUID match
    for acc in accounts:
        if acc['id'] == input_id:
            return input_id

    return None

if __name__ == "__main__":
    main()
