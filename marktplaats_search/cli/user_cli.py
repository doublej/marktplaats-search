"""CLI interface for user management operations."""

from typing import Any

from ..services.user_management_service import UserManagementService


class UserCLI:
    """Command-line interface for user management operations."""

    def __init__(self) -> None:
        """Initialize CLI with user management service."""
        self.service = UserManagementService()

    async def create_user(self, username: str | None = None) -> dict[str, Any]:
        """Create a new user.

        Args:
            username: Optional username (auto-generated if None)

        Returns:
            Dictionary with creation results
        """
        try:
            username, token = await self.service.create_user(username)
            return {
                "success": True,
                "username": username,
                "token": token,
                "message": "User created successfully",
            }
        except ValueError as e:
            return {
                "success": False,
                "message": str(e),
            }

    async def list_users(self, include_inactive: bool = True) -> dict[str, Any]:
        """List all users.

        Args:
            include_inactive: Whether to include inactive users

        Returns:
            Dictionary with user list
        """
        users = await self.service.get_all_users(include_inactive)
        return {
            "success": True,
            "users": users,
            "count": len(users),
        }

    async def activate_user(self, username: str, activate: bool = True) -> dict[str, Any]:
        """Activate or deactivate a user.

        Args:
            username: Username to modify
            activate: True to activate, False to deactivate

        Returns:
            Dictionary with operation results
        """
        success = await self.service.activate_user(username, activate)

        if success:
            action = "activated" if activate else "deactivated"
            return {
                "success": True,
                "message": f"User '{username}' has been {action}",
            }
        else:
            return {
                "success": False,
                "message": f"User '{username}' not found",
            }

    async def reset_user_token(self, username: str) -> dict[str, Any]:
        """Reset a user's API token.

        Args:
            username: Username whose token to reset

        Returns:
            Dictionary with reset results
        """
        new_token = await self.service.reset_user_token(username)

        if new_token:
            return {
                "success": True,
                "username": username,
                "new_token": new_token,
                "message": "Token reset successfully",
            }
        else:
            return {
                "success": False,
                "message": f"User '{username}' not found",
            }

    async def delete_user(self, username: str) -> dict[str, Any]:
        """Delete a user and all their data.

        Args:
            username: Username to delete

        Returns:
            Dictionary with deletion results
        """
        success = await self.service.delete_user(username)

        if success:
            return {
                "success": True,
                "message": f"User '{username}' and all associated data have been deleted",
            }
        else:
            return {
                "success": False,
                "message": f"User '{username}' not found",
            }

    async def show_statistics(self, recent_days: int = 7) -> dict[str, Any]:
        """Show user statistics.

        Args:
            recent_days: Number of days for recent activity calculation

        Returns:
            Dictionary with user statistics
        """
        stats = await self.service.get_user_statistics(recent_days)
        return {
            "success": True,
            **stats,
        }

    def format_user_list(self, users_data: dict[str, Any]) -> str:
        """Format user list for console output.

        Args:
            users_data: Dictionary from list_users method

        Returns:
            Formatted string for console output
        """
        users = users_data["users"]

        if not users:
            return "No users found."

        lines = []
        lines.append(
            f"{'ID':<5} {'Username':<20} {'Active':<8} {'Created':<20} {'Last Activity':<20}"
        )
        lines.append("-" * 80)

        for user in users:
            created = user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "N/A"
            last_activity = (
                user.last_activity.strftime("%Y-%m-%d %H:%M:%S") if user.last_activity else "Never"
            )
            active = "Yes" if user.is_active else "No"

            lines.append(
                f"{user.id:<5} {user.user_identifier:<20} {active:<8} {created:<20} {last_activity:<20}"
            )

        return "\n".join(lines)

    def format_statistics(self, stats_data: dict[str, Any]) -> str:
        """Format user statistics for console output.

        Args:
            stats_data: Dictionary from show_statistics method

        Returns:
            Formatted string for console output
        """
        lines = []
        lines.append("=" * 40)
        lines.append("USER STATISTICS")
        lines.append("=" * 40)
        lines.append(f"Total Users:        {stats_data['total_users']}")
        lines.append(f"Active Users:       {stats_data['active_users']}")
        lines.append(f"Inactive Users:     {stats_data['inactive_users']}")
        lines.append(
            f"Recent Activity:    {stats_data['recent_users']} (last {stats_data['recent_days']} days)"
        )
        lines.append("=" * 40)
        return "\n".join(lines)
