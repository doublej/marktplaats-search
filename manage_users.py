#!/usr/bin/env python3
"""
User management CLI for MarktplaatsSearch API.
Provides commands for creating, listing, and managing users.
"""

import asyncio
import argparse
import sys
from datetime import datetime, timezone
from typing import Optional
import getpass

from sqlalchemy.future import select
from sqlalchemy import func

from database import AsyncSessionLocal
from models import User
from auth import generate_secure_token, hash_token, generate_user_identifier
from config import settings


async def create_user(username: Optional[str] = None) -> tuple[str, str]:
    """Create a new user with secure token."""
    # Generate or use provided username
    if not username:
        username = generate_user_identifier()
    
    # Check if username exists
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.user_identifier == username)
        )
        if result.scalars().first():
            raise ValueError(f"User '{username}' already exists")
        
        # Generate secure token
        token = generate_secure_token()
        token_hash = hash_token(token)
        
        # Create user
        user = User(
            user_identifier=username,
            api_token_hash=token_hash,
            is_active=True,
            token_created_at=datetime.now(timezone.utc)
        )
        
        db.add(user)
        await db.commit()
        
        return username, token


async def list_users():
    """List all users in the system."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        
        if not users:
            print("No users found.")
            return
        
        print(f"\n{'ID':<5} {'Username':<20} {'Active':<8} {'Created':<20} {'Last Activity':<20}")
        print("-" * 80)
        
        for user in users:
            created = user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "N/A"
            last_activity = user.last_activity.strftime("%Y-%m-%d %H:%M:%S") if user.last_activity else "Never"
            active = "Yes" if user.is_active else "No"
            
            print(f"{user.id:<5} {user.user_identifier:<20} {active:<8} {created:<20} {last_activity:<20}")


async def activate_user(username: str, activate: bool = True):
    """Activate or deactivate a user."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.user_identifier == username)
        )
        user = result.scalars().first()
        
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        user.is_active = activate
        await db.commit()
        
        status = "activated" if activate else "deactivated"
        print(f"User '{username}' has been {status}.")


async def reset_token(username: str) -> str:
    """Reset a user's API token."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.user_identifier == username)
        )
        user = result.scalars().first()
        
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        # Generate new token
        new_token = generate_secure_token()
        new_token_hash = hash_token(new_token)
        
        user.api_token_hash = new_token_hash
        user.token_created_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return new_token


async def show_stats():
    """Show user statistics."""
    async with AsyncSessionLocal() as db:
        # Total users
        total_result = await db.execute(
            select(func.count(User.id))
        )
        total_users = total_result.scalar()
        
        # Active users
        active_result = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_result.scalar()
        
        # Users with recent activity (last 7 days)
        from datetime import timedelta
        recent_date = datetime.now(timezone.utc) - timedelta(days=7)
        recent_result = await db.execute(
            select(func.count(User.id)).where(User.last_activity > recent_date)
        )
        recent_users = recent_result.scalar()
        
        print("\n" + "=" * 40)
        print("USER STATISTICS")
        print("=" * 40)
        print(f"Total Users:        {total_users}")
        print(f"Active Users:       {active_users}")
        print(f"Inactive Users:     {total_users - active_users}")
        print(f"Recent Activity:    {recent_users} (last 7 days)")
        print("=" * 40)


async def delete_user(username: str):
    """Delete a user and all their data."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.user_identifier == username)
        )
        user = result.scalars().first()
        
        if not user:
            raise ValueError(f"User '{username}' not found")
        
        # This will cascade delete all searches and listings
        await db.delete(user)
        await db.commit()
        
        print(f"User '{username}' and all associated data have been deleted.")


def main():
    parser = argparse.ArgumentParser(description="User management for MarktplaatsSearch API")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create user
    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("--username", "-u", help="Username (auto-generated if not provided)")
    
    # List users
    subparsers.add_parser("list", help="List all users")
    
    # Activate/deactivate user
    activate_parser = subparsers.add_parser("activate", help="Activate a user")
    activate_parser.add_argument("username", help="Username to activate")
    
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a user")
    deactivate_parser.add_argument("username", help="Username to deactivate")
    
    # Reset token
    reset_parser = subparsers.add_parser("reset-token", help="Reset a user's API token")
    reset_parser.add_argument("username", help="Username whose token to reset")
    
    # Delete user
    delete_parser = subparsers.add_parser("delete", help="Delete a user (WARNING: deletes all data)")
    delete_parser.add_argument("username", help="Username to delete")
    delete_parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    
    # Show stats
    subparsers.add_parser("stats", help="Show user statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == "create":
            username, token = asyncio.run(create_user(args.username))
            print(f"\nUser created successfully!")
            print(f"Username: {username}")
            print(f"API Token: {token}")
            print("\nIMPORTANT: Save this token securely. It cannot be retrieved again.")
            
        elif args.command == "list":
            asyncio.run(list_users())
            
        elif args.command == "activate":
            asyncio.run(activate_user(args.username, True))
            
        elif args.command == "deactivate":
            asyncio.run(activate_user(args.username, False))
            
        elif args.command == "reset-token":
            new_token = asyncio.run(reset_token(args.username))
            print(f"\nToken reset successfully!")
            print(f"New API Token: {new_token}")
            print("\nIMPORTANT: Save this token securely. The old token is now invalid.")
            
        elif args.command == "delete":
            if not args.confirm:
                response = input(f"Are you sure you want to delete user '{args.username}' and ALL their data? (yes/no): ")
                if response.lower() != "yes":
                    print("Operation cancelled.")
                    sys.exit(0)
            asyncio.run(delete_user(args.username))
            
        elif args.command == "stats":
            asyncio.run(show_stats())
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()