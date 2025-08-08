#!/usr/bin/env python3
"""
User management CLI for MarktplaatsSearch API.
Provides commands for creating, listing, and managing users.
"""

import argparse
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marktplaats_search.cli.user_cli import UserCLI


def main():
    parser = argparse.ArgumentParser(description="User management for MarktplaatsSearch API")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create user
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("--username", "-u", help="Username (auto-generated if not provided)")

    # List users
    list_parser = subparsers.add_parser("list", help="List all users")
    list_parser.add_argument(
        "--include-inactive", action="store_true", help="Include inactive users"
    )

    # Activate/deactivate user
    activate_parser = subparsers.add_parser("activate", help="Activate a user")
    activate_parser.add_argument("username", help="Username to activate")

    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a user")
    deactivate_parser.add_argument("username", help="Username to deactivate")

    # Reset token
    reset_parser = subparsers.add_parser("reset-token", help="Reset a user's API token")
    reset_parser.add_argument("username", help="Username whose token to reset")

    # Delete user
    delete_parser = subparsers.add_parser(
        "delete", help="Delete a user (WARNING: deletes all data)"
    )
    delete_parser.add_argument("username", help="Username to delete")
    delete_parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")

    # Show stats
    subparsers.add_parser("stats", help="Show user statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        cli = UserCLI()

        if args.command == "create":
            result = asyncio.run(cli.create_user(args.username))
            if result["success"]:
                print("\nUser created successfully!")
                print(f"Username: {result['username']}")
                print(f"API Token: {result['token']}")
                print("\nIMPORTANT: Save this token securely. It cannot be retrieved again.")
            else:
                print(f"Error: {result['message']}")
                sys.exit(1)

        elif args.command == "list":
            result = asyncio.run(cli.list_users(args.include_inactive))
            if result["success"]:
                print(cli.format_user_list(result))
            else:
                print(f"Error: {result['message']}")
                sys.exit(1)

        elif args.command == "activate":
            result = asyncio.run(cli.activate_user(args.username, True))
            print(result["message"])
            if not result["success"]:
                sys.exit(1)

        elif args.command == "deactivate":
            result = asyncio.run(cli.activate_user(args.username, False))
            print(result["message"])
            if not result["success"]:
                sys.exit(1)

        elif args.command == "reset-token":
            result = asyncio.run(cli.reset_user_token(args.username))
            if result["success"]:
                print("\nToken reset successfully!")
                print(f"New API Token: {result['new_token']}")
                print("\nIMPORTANT: Save this token securely. The old token is now invalid.")
            else:
                print(f"Error: {result['message']}")
                sys.exit(1)

        elif args.command == "delete":
            if not args.confirm:
                response = input(
                    f"Are you sure you want to delete user '{args.username}' and ALL their data? (yes/no): "
                )
                if response.lower() != "yes":
                    print("Operation cancelled.")
                    sys.exit(0)

            result = asyncio.run(cli.delete_user(args.username))
            print(result["message"])
            if not result["success"]:
                sys.exit(1)

        elif args.command == "stats":
            result = asyncio.run(cli.show_statistics())
            if result["success"]:
                print(cli.format_statistics(result))
            else:
                print(f"Error: {result['message']}")
                sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
