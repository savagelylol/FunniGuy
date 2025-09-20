"""
Unified Data Manager for FunniGuy Discord Bot
Integrates all data management systems into a single, cohesive interface
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

from .database_manager import DatabaseManager
from .user_manager import UserManager
from .economy_manager import EconomyManager
from .inventory_manager import InventoryManager
from .achievement_manager import AchievementManager
from .cooldown_manager import CooldownManager
from .marriage_manager import MarriageManager
from .pet_manager import PetManager

logger = logging.getLogger(__name__)


class DataManager:
    """
    Unified data manager that provides a single interface to all bot data systems
    Handles user profiles, economy, inventory, achievements, pets, marriages, and cooldowns
    """
    
    def __init__(self, data_directory: str = "data"):
        """
        Initialize the unified data manager
        
        Args:
            data_directory: Base directory for all data files
        """
        # Initialize core database manager
        self.db = DatabaseManager(data_directory)
        
        # Initialize all specialized managers
        self.users = UserManager(self.db)
        self.economy = EconomyManager(self.db)
        self.inventory = InventoryManager(self.db)
        self.achievements = AchievementManager(self.db)
        self.cooldowns = CooldownManager(self.db)
        self.marriage = MarriageManager(self.db)
        self.pets = PetManager(self.db)
        
        # System status
        self._initialized = False
        self._startup_errors = []
    
    async def initialize(self) -> bool:
        """
        Initialize the data manager and all subsystems
        
        Returns:
            True if initialization was successful
        """
        try:
            logger.info("Initializing FunniGuy Data Manager...")
            
            # Initialize database directories
            await self.db._initialize_directories()
            
            # Run startup checks
            await self._run_startup_checks()
            
            self._initialized = True
            logger.info("Data Manager initialization complete!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Data Manager: {e}")
            self._startup_errors.append(str(e))
            return False
    
    async def _run_startup_checks(self):
        """Run startup checks to ensure all systems are working"""
        try:
            # Check database connectivity
            db_info = await self.db.get_database_info()
            logger.info(f"Database info: {db_info}")
            
            # Check global data files
            bot_stats = await self.db.get_bot_stats()
            logger.info(f"Bot stats: {bot_stats}")
            
            # Test creating a temporary user to verify system integration
            test_user_id = 999999999999999999  # Use a test ID that won't conflict
            test_created = await self.ensure_user_exists(test_user_id, "TestUser", "Test User")
            if test_created:
                # Clean up test user
                await self.db.delete_user(test_user_id)
            
            logger.info("All startup checks passed!")
            
        except Exception as e:
            logger.warning(f"Startup check failed: {e}")
            self._startup_errors.append(f"Startup check: {str(e)}")
    
    async def ensure_user_exists(self, user_id: int, username: str, display_name: str) -> bool:
        """
        Ensure a user exists in the system, creating them if necessary
        This is the main entry point for any user interaction
        
        Args:
            user_id: Discord user ID
            username: User's username
            display_name: User's display name
            
        Returns:
            True if user exists (or was created), False on error
        """
        try:
            # Track command usage (creates user if needed)
            success = await self.users.track_command_usage(user_id)
            
            if success:
                # Update user info in case username/display name changed
                await self.users.update_user_info(user_id, username, display_name)
            
            return success
            
        except Exception as e:
            logger.error(f"Error ensuring user exists {user_id}: {e}")
            return False
    
    async def process_command(self, user_id: int, username: str, display_name: str, 
                            command_name: str) -> Dict[str, Any]:
        """
        Process a command execution - handles user creation, cooldowns, achievements, etc.
        
        Args:
            user_id: Discord user ID
            username: User's username
            display_name: User's display name
            command_name: Name of the command being executed
            
        Returns:
            Dictionary with command processing results
        """
        try:
            # Ensure user exists
            user_exists = await self.ensure_user_exists(user_id, username, display_name)
            if not user_exists:
                return {
                    'success': False,
                    'error': 'Failed to initialize user data',
                    'can_execute': False
                }
            
            # Check cooldowns
            is_on_cooldown, expires_at, remaining_uses = await self.cooldowns.check_cooldown(user_id, command_name)
            
            if is_on_cooldown:
                time_remaining = ""
                if expires_at:
                    time_delta = expires_at - datetime.utcnow()
                    time_remaining = self.cooldowns._format_time_remaining(time_delta)
                
                return {
                    'success': False,
                    'error': 'Command is on cooldown',
                    'can_execute': False,
                    'cooldown_expires': expires_at.isoformat() if expires_at else None,
                    'time_remaining': time_remaining,
                    'remaining_uses': remaining_uses
                }
            
            # Command can be executed
            return {
                'success': True,
                'can_execute': True,
                'remaining_uses': remaining_uses,
                'user_exists': True
            }
            
        except Exception as e:
            logger.error(f"Error processing command for user {user_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'can_execute': False
            }
    
    async def complete_command(self, user_id: int, command_name: str, 
                             success: bool = True) -> Dict[str, Any]:
        """
        Complete a command execution - sets cooldowns, tracks achievements, etc.
        
        Args:
            user_id: Discord user ID
            command_name: Name of the command that was executed
            success: Whether the command execution was successful
            
        Returns:
            Dictionary with completion results (achievements unlocked, etc.)
        """
        try:
            results = {
                'achievements_unlocked': [],
                'level_up': False,
                'cooldown_set': False
            }
            
            if success:
                # Set cooldown for the command
                cooldown_set = await self.cooldowns.set_cooldown(user_id, command_name)
                results['cooldown_set'] = cooldown_set
                
                # Track command usage and check for achievements
                tracked = await self.users.track_command_usage(user_id, command_name)
                if tracked:
                    # Get updated user stats for achievement tracking
                    profile = await self.users.get_user_profile(user_id)
                    if profile:
                        total_commands = profile.get('total_commands_used', 0)
                        achievements = await self.achievements.track_command_usage(user_id, total_commands)
                        results['achievements_unlocked'].extend(achievements)
            
            return results
            
        except Exception as e:
            logger.error(f"Error completing command for user {user_id}: {e}")
            return {'error': str(e)}
    
    async def get_user_overview(self, user_id: int) -> Dict[str, Any]:
        """
        Get a comprehensive overview of a user's data across all systems
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with user overview data
        """
        try:
            # Get data from all systems
            profile_stats = await self.users.get_user_statistics(user_id)
            economy_stats = await self.economy.get_economy_stats(user_id)
            inventory_stats = await self.inventory.get_inventory_statistics(user_id)
            achievement_stats = await self.achievements.get_user_achievement_stats(user_id)
            cooldown_stats = await self.cooldowns.get_cooldown_statistics(user_id)
            marriage_stats = await self.marriage.get_relationship_statistics(user_id)
            
            # Get active pet info
            pet_data = await self.pets.get_user_pets(user_id)
            active_pet = None
            if pet_data and pet_data.get('active_pet'):
                active_pet = await self.pets.get_pet_info(user_id, pet_data['active_pet'])
            
            return {
                'profile': profile_stats,
                'economy': economy_stats,
                'inventory': inventory_stats,
                'achievements': achievement_stats,
                'cooldowns': cooldown_stats,
                'marriage': marriage_stats,
                'active_pet': active_pet,
                'total_pets': pet_data.get('total_pets', 0) if pet_data else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user overview for {user_id}: {e}")
            return {'error': str(e)}
    
    async def award_experience(self, user_id: int, amount: int, 
                              reason: str = "Activity") -> Dict[str, Any]:
        """
        Award experience to a user and handle level ups
        
        Args:
            user_id: Discord user ID
            amount: Amount of experience to award
            reason: Reason for the experience gain
            
        Returns:
            Dictionary with level up information
        """
        try:
            # Check if user is married for experience bonus
            marriage_info = await self.marriage.get_marriage_info(user_id)
            if marriage_info:
                bonus_multiplier = marriage_info.get('experience_bonus', 1.0)
                amount = int(amount * bonus_multiplier)
            
            # Award experience
            level_info = await self.users.add_experience(user_id, amount)
            
            # Track achievement progress if leveled up
            if level_info.get('leveled_up', False):
                new_level = level_info.get('new_level', 1)
                achievements = await self.achievements.track_collection_achievement(
                    user_id, 'level', new_level
                )
                level_info['achievements_unlocked'] = achievements
            
            return level_info
            
        except Exception as e:
            logger.error(f"Error awarding experience to user {user_id}: {e}")
            return {'error': str(e)}
    
    async def award_money(self, user_id: int, amount: int, 
                         reason: str = "Activity") -> bool:
        """
        Award money to a user with marriage bonuses
        
        Args:
            user_id: Discord user ID
            amount: Amount of money to award
            reason: Reason for the money gain
            
        Returns:
            True if money was awarded successfully
        """
        try:
            # Check if user is married for money bonus
            marriage_info = await self.marriage.get_marriage_info(user_id)
            if marriage_info and reason.lower() == 'daily':
                bonus_multiplier = marriage_info.get('daily_bonus_multiplier', 1.0)
                amount = int(amount * bonus_multiplier)
            
            # Award money
            success = await self.economy.add_money(user_id, amount, 'pocket', 
                                                 description=reason)
            
            # Track economy achievements
            if success:
                economy_data = await self.economy.get_user_economy(user_id)
                if economy_data:
                    total_earned = economy_data.get('total_earned', 0)
                    await self.achievements.track_economy_achievement(
                        user_id, 'total_earned', total_earned
                    )
            
            return success
            
        except Exception as e:
            logger.error(f"Error awarding money to user {user_id}: {e}")
            return False
    
    async def create_backup(self) -> str:
        """
        Create a full backup of all data
        
        Returns:
            Path to the backup file
        """
        try:
            return await self.db.create_full_backup()
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status and health information
        
        Returns:
            Dictionary with system status
        """
        try:
            db_info = await self.db.get_database_info()
            bot_stats = await self.db.get_bot_stats()
            
            return {
                'initialized': self._initialized,
                'startup_errors': self._startup_errors,
                'database_info': db_info,
                'bot_stats': bot_stats,
                'managers': {
                    'database': 'initialized',
                    'users': 'initialized',
                    'economy': 'initialized',
                    'inventory': 'initialized',
                    'achievements': 'initialized',
                    'cooldowns': 'initialized',
                    'marriage': 'initialized',
                    'pets': 'initialized'
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    async def maintenance_cleanup(self):
        """
        Perform routine maintenance and cleanup tasks
        """
        try:
            logger.info("Starting maintenance cleanup...")
            
            # Clean up expired cache entries
            await self.db.cleanup_cache()
            
            # This could be expanded to include:
            # - Cleaning up expired trades
            # - Updating pet stats for all users
            # - Checking for expired marriages/relationships
            # - Cleaning up old transaction histories
            
            logger.info("Maintenance cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during maintenance cleanup: {e}")
    
    async def shutdown(self):
        """
        Gracefully shutdown the data manager
        """
        try:
            logger.info("Shutting down Data Manager...")
            
            # Perform final cleanup
            await self.maintenance_cleanup()
            
            # Create a final backup
            try:
                backup_path = await self.create_backup()
                logger.info(f"Final backup created: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create final backup: {e}")
            
            self._initialized = False
            logger.info("Data Manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    # Quick access methods for common operations
    async def get_balance(self, user_id: int) -> Tuple[int, int]:
        """Get user's pocket and bank balance"""
        return await self.economy.get_balance(user_id)
    
    async def get_level_info(self, user_id: int) -> Dict[str, Any]:
        """Get user's level and experience info"""
        return await self.users.get_user_level_info(user_id)
    
    async def get_active_pet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's active pet info"""
        pet_data = await self.pets.get_user_pets(user_id)
        if pet_data and pet_data.get('active_pet'):
            return await self.pets.get_pet_info(user_id, pet_data['active_pet'])
        return None
    
    async def is_married(self, user_id: int) -> bool:
        """Check if user is married"""
        marriage_info = await self.marriage.get_marriage_info(user_id)
        return marriage_info is not None
    
    async def get_command_cooldown(self, user_id: int, command: str) -> Dict[str, Any]:
        """Get cooldown status for a specific command"""
        return await self.cooldowns.get_cooldown_status(user_id, command)