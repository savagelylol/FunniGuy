"""
User Profile Management System for FunniGuy Discord Bot
Handles all user profile operations, statistics, and social features
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import math

from .database_manager import DatabaseManager, DatabaseError
from .schemas import (
    UserProfile, EconomyData, UserInventory, UserAchievements,
    UserPets, UserRelationships, UserCooldowns,
    create_default_user_data, SchemaValidator
)

logger = logging.getLogger(__name__)


class UserNotFoundError(Exception):
    """Exception raised when user is not found"""
    pass


class UserManager:
    """
    Comprehensive user profile management system
    Handles user creation, profile updates, statistics, and social features
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize the user manager
        
        Args:
            database_manager: Instance of DatabaseManager
        """
        self.db = database_manager
        self.validator = SchemaValidator()
        
        # Level calculation constants
        self.base_experience = 100
        self.experience_multiplier = 1.5
        
        # Daily limits
        self.max_daily_commands = 100
        self.command_experience = 5
    
    async def create_user_if_not_exists(self, user_id: int, username: str, display_name: str) -> bool:
        """
        Create a new user if they don't exist
        
        Args:
            user_id: Discord user ID
            username: User's username
            display_name: User's display name
            
        Returns:
            True if user was created, False if already existed
        """
        try:
            if await self.db.user_exists(user_id):
                # Update username and display name if they changed
                await self.update_user_info(user_id, username, display_name)
                return False
            
            success = await self.db.create_user(user_id, username, display_name)
            if success:
                logger.info(f"Created new user profile for {username} ({user_id})")
                
                # Initialize user with first command achievement
                await self.track_command_usage(user_id)
                
            return success
            
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            raise DatabaseError(f"Failed to create user: {e}")
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user profile data
        
        Args:
            user_id: Discord user ID
            
        Returns:
            User profile data or None if not found
        """
        try:
            profile_data = await self.db.get_user_data(user_id, 'profile')
            if profile_data is None:
                return None
            
            # Update last active timestamp
            profile_data['last_active'] = datetime.utcnow().isoformat()
            await self.db.save_user_data(user_id, 'profile', profile_data)
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting user profile {user_id}: {e}")
            return None
    
    async def update_user_info(self, user_id: int, username: str, display_name: str):
        """
        Update user's basic information
        
        Args:
            user_id: Discord user ID
            username: New username
            display_name: New display name
        """
        try:
            updates = {
                'username': username,
                'display_name': display_name,
                'last_active': datetime.utcnow().isoformat()
            }
            
            await self.db.update_user_data(user_id, 'profile', updates)
            logger.debug(f"Updated user info for {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating user info {user_id}: {e}")
            raise DatabaseError(f"Failed to update user info: {e}")
    
    async def get_user_level_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's level and experience information
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with level, experience, and progress information
        """
        profile = await self.get_user_profile(user_id)
        if not profile:
            raise UserNotFoundError(f"User {user_id} not found")
        
        current_level = profile.get('level', 1)
        current_exp = profile.get('experience', 0)
        
        # Calculate experience required for current and next level
        current_level_exp = self._calculate_level_experience(current_level)
        next_level_exp = self._calculate_level_experience(current_level + 1)
        
        # Calculate progress within current level
        exp_for_current_level = current_exp - current_level_exp
        exp_needed_for_next = next_level_exp - current_level_exp
        progress_percentage = (exp_for_current_level / exp_needed_for_next) * 100
        
        return {
            'level': current_level,
            'experience': current_exp,
            'experience_for_current_level': exp_for_current_level,
            'experience_needed_for_next': next_level_exp - current_exp,
            'progress_percentage': round(progress_percentage, 1),
            'total_experience_for_next_level': next_level_exp
        }
    
    def _calculate_level_experience(self, level: int) -> int:
        """
        Calculate total experience required to reach a specific level
        
        Args:
            level: Target level
            
        Returns:
            Total experience required
        """
        if level <= 1:
            return 0
        
        total_exp = 0
        for i in range(1, level):
            level_exp = int(self.base_experience * (self.experience_multiplier ** (i - 1)))
            total_exp += level_exp
        
        return total_exp
    
    def _calculate_level_from_experience(self, experience: int) -> int:
        """
        Calculate level from total experience
        
        Args:
            experience: Total experience
            
        Returns:
            Current level
        """
        level = 1
        while self._calculate_level_experience(level + 1) <= experience:
            level += 1
        return level
    
    async def add_experience(self, user_id: int, amount: int) -> Dict[str, Any]:
        """
        Add experience to user and handle level ups
        
        Args:
            user_id: Discord user ID
            amount: Amount of experience to add
            
        Returns:
            Dictionary with level up information
        """
        profile = await self.get_user_profile(user_id)
        if not profile:
            raise UserNotFoundError(f"User {user_id} not found")
        
        old_level = profile.get('level', 1)
        old_experience = profile.get('experience', 0)
        
        new_experience = old_experience + amount
        new_level = self._calculate_level_from_experience(new_experience)
        
        # Update profile
        updates = {
            'experience': new_experience,
            'level': new_level
        }
        
        await self.db.update_user_data(user_id, 'profile', updates)
        
        level_up_info = {
            'experience_gained': amount,
            'old_level': old_level,
            'new_level': new_level,
            'leveled_up': new_level > old_level,
            'levels_gained': new_level - old_level
        }
        
        if level_up_info['leveled_up']:
            logger.info(f"User {user_id} leveled up from {old_level} to {new_level}")
            
            # Award level up rewards (could be coins, items, etc.)
            await self._handle_level_up_rewards(user_id, old_level, new_level)
        
        return level_up_info
    
    async def _handle_level_up_rewards(self, user_id: int, old_level: int, new_level: int):
        """
        Handle rewards for leveling up
        
        Args:
            user_id: Discord user ID
            old_level: Previous level
            new_level: New level
        """
        try:
            # Award coins based on level difference
            levels_gained = new_level - old_level
            coin_reward = levels_gained * 100  # 100 coins per level
            
            # Get user's economy data
            economy_data = await self.db.get_user_data(user_id, 'economy')
            if economy_data:
                economy_data['pocket_balance'] += coin_reward
                economy_data['total_earned'] += coin_reward
                await self.db.save_user_data(user_id, 'economy', economy_data)
                
                logger.info(f"Awarded {coin_reward} coins to user {user_id} for level up")
        
        except Exception as e:
            logger.error(f"Error handling level up rewards for {user_id}: {e}")
    
    async def track_command_usage(self, user_id: int, command_name: Optional[str] = None) -> bool:
        """
        Track command usage and award experience
        
        Args:
            user_id: Discord user ID
            command_name: Name of the command used (optional)
            
        Returns:
            True if command was tracked, False if daily limit reached
        """
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                # Auto-create user if they don't exist
                await self.create_user_if_not_exists(user_id, f"User{user_id}", f"User{user_id}")
                profile = await self.get_user_profile(user_id)
            
            current_date = datetime.utcnow().date().isoformat()
            
            # Reset daily counters if it's a new day
            if profile.get('daily_reset_date') != current_date:
                profile['daily_commands_used'] = 0
                profile['daily_reset_date'] = current_date
            
            # Check daily limit
            daily_used = profile.get('daily_commands_used', 0)
            if daily_used >= self.max_daily_commands:
                return False
            
            # Update command usage statistics
            updates = {
                'total_commands_used': profile.get('total_commands_used', 0) + 1,
                'daily_commands_used': daily_used + 1,
                'daily_reset_date': current_date,
                'last_active': datetime.utcnow().isoformat()
            }
            
            await self.db.update_user_data(user_id, 'profile', updates)
            
            # Award experience for command usage
            await self.add_experience(user_id, self.command_experience)
            
            # Track achievement progress
            await self._track_command_achievement(user_id, updates['total_commands_used'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking command usage for {user_id}: {e}")
            return False
    
    async def _track_command_achievement(self, user_id: int, total_commands: int):
        """
        Track command usage achievements
        
        Args:
            user_id: Discord user ID
            total_commands: Total commands used by user
        """
        try:
            # Achievement milestones
            milestones = [1, 10, 50, 100, 500, 1000, 5000, 10000]
            
            for milestone in milestones:
                if total_commands >= milestone:
                    achievement_id = f"commands_{milestone}"
                    # This would integrate with the achievement system
                    logger.debug(f"User {user_id} reached command milestone: {milestone}")
        
        except Exception as e:
            logger.error(f"Error tracking command achievement for {user_id}: {e}")
    
    async def update_user_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """
        Update user settings
        
        Args:
            user_id: Discord user ID
            settings: Dictionary of settings to update
            
        Returns:
            True if settings were updated successfully
        """
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                raise UserNotFoundError(f"User {user_id} not found")
            
            # Validate and sanitize settings
            allowed_settings = {
                'timezone', 'language', 'notifications_enabled', 
                'privacy_mode', 'bio', 'favorite_color', 'status_message'
            }
            
            valid_settings = {}
            for key, value in settings.items():
                if key in allowed_settings:
                    if key in ['bio', 'status_message']:
                        # Sanitize text inputs
                        valid_settings[key] = self.validator.sanitize_user_input(str(value), 500)
                    elif key == 'favorite_color':
                        # Validate color format (hex color)
                        if isinstance(value, str) and (value.startswith('#') or value.lower() in ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink']):
                            valid_settings[key] = value
                    elif key in ['notifications_enabled', 'privacy_mode']:
                        # Boolean settings
                        valid_settings[key] = bool(value)
                    else:
                        valid_settings[key] = value
            
            if not valid_settings:
                return False
            
            await self.db.update_user_data(user_id, 'profile', valid_settings)
            logger.debug(f"Updated settings for user {user_id}: {list(valid_settings.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user settings {user_id}: {e}")
            return False
    
    async def add_friend(self, user_id: int, friend_id: int) -> bool:
        """
        Add a friend to user's friend list
        
        Args:
            user_id: Discord user ID
            friend_id: Friend's Discord user ID
            
        Returns:
            True if friend was added successfully
        """
        try:
            if user_id == friend_id:
                return False  # Can't add yourself as friend
            
            profile = await self.get_user_profile(user_id)
            if not profile:
                raise UserNotFoundError(f"User {user_id} not found")
            
            friends = profile.get('friends', [])
            if friend_id not in friends:
                friends.append(friend_id)
                await self.db.update_user_data(user_id, 'profile', {'friends': friends})
                logger.debug(f"Added friend {friend_id} to user {user_id}")
                return True
            
            return False  # Already friends
            
        except Exception as e:
            logger.error(f"Error adding friend for user {user_id}: {e}")
            return False
    
    async def remove_friend(self, user_id: int, friend_id: int) -> bool:
        """
        Remove a friend from user's friend list
        
        Args:
            user_id: Discord user ID
            friend_id: Friend's Discord user ID to remove
            
        Returns:
            True if friend was removed successfully
        """
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                raise UserNotFoundError(f"User {user_id} not found")
            
            friends = profile.get('friends', [])
            if friend_id in friends:
                friends.remove(friend_id)
                await self.db.update_user_data(user_id, 'profile', {'friends': friends})
                logger.debug(f"Removed friend {friend_id} from user {user_id}")
                return True
            
            return False  # Not in friend list
            
        except Exception as e:
            logger.error(f"Error removing friend for user {user_id}: {e}")
            return False
    
    async def get_user_friends(self, user_id: int) -> List[int]:
        """
        Get user's friend list
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of friend user IDs
        """
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return []
            
            return profile.get('friends', [])
            
        except Exception as e:
            logger.error(f"Error getting friends for user {user_id}: {e}")
            return []
    
    async def block_user(self, user_id: int, blocked_user_id: int) -> bool:
        """
        Block a user
        
        Args:
            user_id: Discord user ID
            blocked_user_id: User ID to block
            
        Returns:
            True if user was blocked successfully
        """
        try:
            if user_id == blocked_user_id:
                return False  # Can't block yourself
            
            profile = await self.get_user_profile(user_id)
            if not profile:
                raise UserNotFoundError(f"User {user_id} not found")
            
            blocked_users = profile.get('blocked_users', [])
            if blocked_user_id not in blocked_users:
                blocked_users.append(blocked_user_id)
                
                # Also remove from friends if they were friends
                friends = profile.get('friends', [])
                if blocked_user_id in friends:
                    friends.remove(blocked_user_id)
                
                updates = {
                    'blocked_users': blocked_users,
                    'friends': friends
                }
                
                await self.db.update_user_data(user_id, 'profile', updates)
                logger.debug(f"Blocked user {blocked_user_id} for user {user_id}")
                return True
            
            return False  # Already blocked
            
        except Exception as e:
            logger.error(f"Error blocking user for {user_id}: {e}")
            return False
    
    async def unblock_user(self, user_id: int, blocked_user_id: int) -> bool:
        """
        Unblock a user
        
        Args:
            user_id: Discord user ID
            blocked_user_id: User ID to unblock
            
        Returns:
            True if user was unblocked successfully
        """
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                raise UserNotFoundError(f"User {user_id} not found")
            
            blocked_users = profile.get('blocked_users', [])
            if blocked_user_id in blocked_users:
                blocked_users.remove(blocked_user_id)
                await self.db.update_user_data(user_id, 'profile', {'blocked_users': blocked_users})
                logger.debug(f"Unblocked user {blocked_user_id} for user {user_id}")
                return True
            
            return False  # Not in blocked list
            
        except Exception as e:
            logger.error(f"Error unblocking user for {user_id}: {e}")
            return False
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive user statistics
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with user statistics
        """
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                raise UserNotFoundError(f"User {user_id} not found")
            
            # Get level information
            level_info = await self.get_user_level_info(user_id)
            
            # Calculate account age
            created_at = datetime.fromisoformat(profile['created_at'])
            account_age = datetime.utcnow() - created_at
            
            # Get additional data from other systems
            economy_data = await self.db.get_user_data(user_id, 'economy')
            inventory_data = await self.db.get_user_data(user_id, 'inventory')
            achievements_data = await self.db.get_user_data(user_id, 'achievements')
            pets_data = await self.db.get_user_data(user_id, 'pets')
            
            statistics = {
                'basic_info': {
                    'username': profile['username'],
                    'display_name': profile['display_name'],
                    'created_at': profile['created_at'],
                    'account_age_days': account_age.days,
                    'last_active': profile['last_active']
                },
                'level_info': level_info,
                'activity': {
                    'total_commands_used': profile.get('total_commands_used', 0),
                    'daily_commands_used': profile.get('daily_commands_used', 0),
                    'commands_remaining_today': self.max_daily_commands - profile.get('daily_commands_used', 0)
                },
                'social': {
                    'friends_count': len(profile.get('friends', [])),
                    'blocked_users_count': len(profile.get('blocked_users', []))
                },
                'economy': {
                    'total_balance': (economy_data.get('pocket_balance', 0) + economy_data.get('bank_balance', 0)) if economy_data else 0,
                    'total_earned': economy_data.get('total_earned', 0) if economy_data else 0
                } if economy_data else {},
                'collection': {
                    'total_items': len(inventory_data.get('items', {})) if inventory_data else 0,
                    'achievements_unlocked': achievements_data.get('total_unlocked', 0) if achievements_data else 0,
                    'pets_owned': pets_data.get('total_pets', 0) if pets_data else 0
                }
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error getting user statistics {user_id}: {e}")
            raise DatabaseError(f"Failed to get user statistics: {e}")
    
    async def delete_user_profile(self, user_id: int) -> bool:
        """
        Delete a user's complete profile
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if profile was deleted successfully
        """
        try:
            return await self.db.delete_user(user_id)
            
        except Exception as e:
            logger.error(f"Error deleting user profile {user_id}: {e}")
            return False
    
    async def get_leaderboard(self, category: str = 'level', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get leaderboard data for users
        
        Args:
            category: Leaderboard category ('level', 'experience', 'commands')
            limit: Number of users to return
            
        Returns:
            List of user data sorted by category
        """
        try:
            # This would need to be implemented based on how you want to handle leaderboards
            # For now, return empty list as this requires scanning all user files
            # In a real implementation, you might want to maintain a separate leaderboard cache
            logger.info(f"Leaderboard requested for category: {category}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []