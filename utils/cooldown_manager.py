"""
Cooldown Management System for FunniGuy Discord Bot
Handles command cooldowns, daily limits, and timing restrictions
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from .database_manager import DatabaseManager, DatabaseError
from .schemas import UserCooldowns, Cooldown, SchemaValidator

logger = logging.getLogger(__name__)


class CooldownManager:
    """
    Comprehensive cooldown management system
    Handles command cooldowns, daily limits, and timing restrictions
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize the cooldown manager
        
        Args:
            database_manager: Instance of DatabaseManager
        """
        self.db = database_manager
        self.validator = SchemaValidator()
        
        # Default cooldown settings (in seconds)
        self.default_cooldowns = {
            'work': 14400,  # 4 hours
            'daily': 86400,  # 24 hours
            'weekly': 604800,  # 7 days
            'rob': 3600,  # 1 hour
            'gamble': 300,  # 5 minutes
            'hunt': 1800,  # 30 minutes
            'fish': 900,  # 15 minutes
            'crime': 7200,  # 2 hours
            'slut': 3600,  # 1 hour
            'pet_feed': 14400,  # 4 hours
            'pet_play': 7200,  # 2 hours
            'trade': 60,  # 1 minute
            'gift': 300,  # 5 minutes
        }
        
        # Daily usage limits
        self.daily_limits = {
            'work': 1,
            'daily': 1,
            'weekly': 1,
            'rob': 3,
            'hunt': 5,
            'fish': 10,
            'crime': 2,
            'slut': 3,
            'pet_feed': 3,
            'pet_play': 5,
            'trade': 20,
            'gift': 10,
        }
        
        # Commands that reset on daily basis
        self.daily_reset_commands = {
            'work', 'daily', 'rob', 'hunt', 'fish', 'crime', 'slut',
            'pet_feed', 'pet_play', 'trade', 'gift'
        }
    
    async def get_user_cooldowns(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's cooldown data
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Cooldown data or None if not found
        """
        try:
            cooldown_data = await self.db.get_user_data(user_id, 'cooldowns')
            
            if cooldown_data:
                # Clean up expired cooldowns and reset daily limits if needed
                cooldown_data = await self._cleanup_expired_cooldowns(user_id, cooldown_data)
            
            return cooldown_data
            
        except Exception as e:
            logger.error(f"Error getting user cooldowns {user_id}: {e}")
            return None
    
    async def _cleanup_expired_cooldowns(self, user_id: int, cooldown_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean up expired cooldowns and reset daily limits
        
        Args:
            user_id: Discord user ID
            cooldown_data: Current cooldown data
            
        Returns:
            Updated cooldown data
        """
        now = datetime.utcnow()
        current_date = now.date().isoformat()
        
        # Check if we need to reset daily limits
        last_reset = cooldown_data.get('last_reset')
        if last_reset != current_date:
            cooldown_data['daily_limits'] = {}
            cooldown_data['last_reset'] = current_date
        
        # Clean up expired cooldowns
        cooldowns = cooldown_data.get('cooldowns', {})
        expired_cooldowns = []
        
        for command, cooldown_info in cooldowns.items():
            expires_at = datetime.fromisoformat(cooldown_info['expires_at'])
            if now >= expires_at:
                expired_cooldowns.append(command)
        
        # Remove expired cooldowns
        for command in expired_cooldowns:
            del cooldowns[command]
        
        if expired_cooldowns:
            cooldown_data['cooldowns'] = cooldowns
            await self.db.save_user_data(user_id, 'cooldowns', cooldown_data)
            logger.debug(f"Cleaned up {len(expired_cooldowns)} expired cooldowns for user {user_id}")
        
        return cooldown_data
    
    async def check_cooldown(self, user_id: int, command: str) -> Tuple[bool, Optional[datetime], int]:
        """
        Check if a command is on cooldown for a user
        
        Args:
            user_id: Discord user ID
            command: Command name to check
            
        Returns:
            Tuple of (is_on_cooldown, expires_at, remaining_uses_today)
        """
        try:
            cooldown_data = await self.get_user_cooldowns(user_id)
            if not cooldown_data:
                return False, None, self.daily_limits.get(command, 999)
            
            cooldowns = cooldown_data.get('cooldowns', {})
            daily_limits = cooldown_data.get('daily_limits', {})
            
            # Check active cooldown
            if command in cooldowns:
                cooldown_info = cooldowns[command]
                expires_at = datetime.fromisoformat(cooldown_info['expires_at'])
                
                if datetime.utcnow() < expires_at:
                    return True, expires_at, cooldown_info.get('uses_remaining', 0)
            
            # Check daily limit
            if command in self.daily_limits:
                uses_today = daily_limits.get(command, 0)
                max_uses = self.daily_limits[command]
                remaining_uses = max(0, max_uses - uses_today)
                
                if remaining_uses <= 0:
                    # On daily limit cooldown until tomorrow
                    tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                    return True, tomorrow, 0
                
                return False, None, remaining_uses
            
            return False, None, 999  # No limit for this command
            
        except Exception as e:
            logger.error(f"Error checking cooldown for user {user_id}, command {command}: {e}")
            return False, None, 0
    
    async def set_cooldown(self, user_id: int, command: str, duration_seconds: Optional[int] = None) -> bool:
        """
        Set a cooldown for a command
        
        Args:
            user_id: Discord user ID
            command: Command name
            duration_seconds: Cooldown duration (uses default if None)
            
        Returns:
            True if cooldown was set successfully
        """
        try:
            cooldown_data = await self.get_user_cooldowns(user_id)
            if not cooldown_data:
                raise DatabaseError(f"Cooldown data not found for user {user_id}")
            
            # Get cooldown duration
            if duration_seconds is None:
                duration_seconds = self.default_cooldowns.get(command, 300)  # Default 5 minutes
            
            expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
            
            # Set cooldown
            cooldowns = cooldown_data.setdefault('cooldowns', {})
            cooldowns[command] = {
                'command': command,
                'user_id': user_id,
                'expires_at': expires_at.isoformat(),
                'uses_remaining': 0
            }
            
            # Update daily limit usage
            if command in self.daily_limits:
                daily_limits = cooldown_data.setdefault('daily_limits', {})
                daily_limits[command] = daily_limits.get(command, 0) + 1
            
            # Save updated data
            await self.db.save_user_data(user_id, 'cooldowns', cooldown_data)
            
            logger.debug(f"Set cooldown for user {user_id}, command {command}, duration {duration_seconds}s")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cooldown for user {user_id}, command {command}: {e}")
            return False
    
    async def reset_cooldown(self, user_id: int, command: str) -> bool:
        """
        Reset a specific command cooldown (admin function)
        
        Args:
            user_id: Discord user ID
            command: Command name to reset
            
        Returns:
            True if cooldown was reset successfully
        """
        try:
            cooldown_data = await self.get_user_cooldowns(user_id)
            if not cooldown_data:
                return False
            
            cooldowns = cooldown_data.get('cooldowns', {})
            
            if command in cooldowns:
                del cooldowns[command]
                await self.db.save_user_data(user_id, 'cooldowns', cooldown_data)
                logger.info(f"Reset cooldown for user {user_id}, command {command}")
                return True
            
            return False  # Cooldown not found
            
        except Exception as e:
            logger.error(f"Error resetting cooldown for user {user_id}, command {command}: {e}")
            return False
    
    async def reset_daily_limits(self, user_id: int) -> bool:
        """
        Reset all daily limits for a user (admin function)
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if limits were reset successfully
        """
        try:
            cooldown_data = await self.get_user_cooldowns(user_id)
            if not cooldown_data:
                return False
            
            cooldown_data['daily_limits'] = {}
            cooldown_data['last_reset'] = datetime.utcnow().date().isoformat()
            
            await self.db.save_user_data(user_id, 'cooldowns', cooldown_data)
            
            logger.info(f"Reset daily limits for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting daily limits for user {user_id}: {e}")
            return False
    
    async def get_cooldown_status(self, user_id: int, command: str) -> Dict[str, Any]:
        """
        Get detailed cooldown status for a command
        
        Args:
            user_id: Discord user ID
            command: Command name
            
        Returns:
            Dictionary with cooldown status information
        """
        try:
            is_on_cooldown, expires_at, remaining_uses = await self.check_cooldown(user_id, command)
            
            status = {
                'command': command,
                'is_on_cooldown': is_on_cooldown,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'remaining_uses_today': remaining_uses,
                'max_uses_per_day': self.daily_limits.get(command, 999),
                'default_cooldown_seconds': self.default_cooldowns.get(command, 300)
            }
            
            if is_on_cooldown and expires_at:
                time_remaining = expires_at - datetime.utcnow()
                status['time_remaining_seconds'] = max(0, int(time_remaining.total_seconds()))
                status['time_remaining_formatted'] = self._format_time_remaining(time_remaining)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting cooldown status for user {user_id}, command {command}: {e}")
            return {'error': str(e)}
    
    def _format_time_remaining(self, time_delta: timedelta) -> str:
        """
        Format time remaining in a human-readable way
        
        Args:
            time_delta: Time remaining as timedelta
            
        Returns:
            Formatted string
        """
        total_seconds = int(time_delta.total_seconds())
        
        if total_seconds <= 0:
            return "Ready now"
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    async def get_all_cooldowns(self, user_id: int) -> Dict[str, Any]:
        """
        Get all active cooldowns for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with all cooldown information
        """
        try:
            cooldown_data = await self.get_user_cooldowns(user_id)
            if not cooldown_data:
                return {}
            
            cooldowns = cooldown_data.get('cooldowns', {})
            daily_limits = cooldown_data.get('daily_limits', {})
            
            result = {
                'active_cooldowns': {},
                'daily_usage': {},
                'commands_available': []
            }
            
            now = datetime.utcnow()
            
            # Process active cooldowns
            for command, cooldown_info in cooldowns.items():
                expires_at = datetime.fromisoformat(cooldown_info['expires_at'])
                
                if now < expires_at:
                    time_remaining = expires_at - now
                    result['active_cooldowns'][command] = {
                        'expires_at': expires_at.isoformat(),
                        'time_remaining_seconds': int(time_remaining.total_seconds()),
                        'time_remaining_formatted': self._format_time_remaining(time_remaining)
                    }
            
            # Process daily usage
            for command, max_uses in self.daily_limits.items():
                uses_today = daily_limits.get(command, 0)
                result['daily_usage'][command] = {
                    'uses_today': uses_today,
                    'max_uses': max_uses,
                    'remaining_uses': max(0, max_uses - uses_today)
                }
                
                # Add to available commands if not on cooldown and has uses remaining
                if (command not in result['active_cooldowns'] and 
                    uses_today < max_uses):
                    result['commands_available'].append(command)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all cooldowns for user {user_id}: {e}")
            return {}
    
    async def bulk_reset_cooldowns(self, user_ids: List[int], command: Optional[str] = None) -> int:
        """
        Reset cooldowns for multiple users (admin function)
        
        Args:
            user_ids: List of Discord user IDs
            command: Specific command to reset (all if None)
            
        Returns:
            Number of users whose cooldowns were reset
        """
        reset_count = 0
        
        try:
            for user_id in user_ids:
                if command:
                    success = await self.reset_cooldown(user_id, command)
                else:
                    success = await self.reset_daily_limits(user_id)
                
                if success:
                    reset_count += 1
            
            logger.info(f"Bulk reset cooldowns for {reset_count}/{len(user_ids)} users")
            return reset_count
            
        except Exception as e:
            logger.error(f"Error in bulk reset cooldowns: {e}")
            return reset_count
    
    async def set_custom_cooldown(self, user_id: int, command: str, duration_seconds: int, 
                                 uses_remaining: int = 0) -> bool:
        """
        Set a custom cooldown with specific parameters
        
        Args:
            user_id: Discord user ID
            command: Command name
            duration_seconds: Custom cooldown duration
            uses_remaining: Number of uses remaining in this cooldown period
            
        Returns:
            True if cooldown was set successfully
        """
        try:
            cooldown_data = await self.get_user_cooldowns(user_id)
            if not cooldown_data:
                raise DatabaseError(f"Cooldown data not found for user {user_id}")
            
            expires_at = datetime.utcnow() + timedelta(seconds=duration_seconds)
            
            cooldowns = cooldown_data.setdefault('cooldowns', {})
            cooldowns[command] = {
                'command': command,
                'user_id': user_id,
                'expires_at': expires_at.isoformat(),
                'uses_remaining': uses_remaining
            }
            
            await self.db.save_user_data(user_id, 'cooldowns', cooldown_data)
            
            logger.info(f"Set custom cooldown for user {user_id}, command {command}, "
                       f"duration {duration_seconds}s, uses_remaining {uses_remaining}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting custom cooldown for user {user_id}, command {command}: {e}")
            return False
    
    async def get_cooldown_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get cooldown usage statistics for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with cooldown statistics
        """
        try:
            cooldown_data = await self.get_user_cooldowns(user_id)
            if not cooldown_data:
                return {}
            
            daily_limits = cooldown_data.get('daily_limits', {})
            
            stats = {
                'commands_used_today': sum(daily_limits.values()),
                'active_cooldowns_count': len(cooldown_data.get('cooldowns', {})),
                'daily_usage_by_command': daily_limits,
                'efficiency_score': 0.0
            }
            
            # Calculate efficiency score (percentage of available daily uses consumed)
            if self.daily_limits:
                total_possible_uses = sum(self.daily_limits.values())
                total_actual_uses = sum(daily_limits.values())
                stats['efficiency_score'] = round((total_actual_uses / total_possible_uses) * 100, 1)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cooldown statistics for user {user_id}: {e}")
            return {}