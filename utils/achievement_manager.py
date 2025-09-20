"""
Achievement Management System for FunniGuy Discord Bot
Handles achievement tracking, progress, rewards, and unlocks
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .database_manager import DatabaseManager, DatabaseError
from .schemas import (
    UserAchievements, Achievement, AchievementType,
    DEFAULT_ACHIEVEMENTS, SchemaValidator
)

logger = logging.getLogger(__name__)


class AchievementManager:
    """
    Comprehensive achievement management system
    Handles achievement tracking, progress, and rewards
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize the achievement manager
        
        Args:
            database_manager: Instance of DatabaseManager
        """
        self.db = database_manager
        self.validator = SchemaValidator()
        
        # Achievement categories and their progress tracking
        self.achievement_progress_handlers = {
            AchievementType.COMMAND_USAGE: self._track_command_usage,
            AchievementType.ECONOMY: self._track_economy,
            AchievementType.SOCIAL: self._track_social,
            AchievementType.GAMING: self._track_gaming,
            AchievementType.COLLECTION: self._track_collection,
            AchievementType.TIME_BASED: self._track_time_based,
            AchievementType.SPECIAL: self._track_special
        }
    
    async def get_user_achievements(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's achievement data
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Achievement data or None if not found
        """
        try:
            achievement_data = await self.db.get_user_data(user_id, 'achievements')
            return achievement_data
            
        except Exception as e:
            logger.error(f"Error getting user achievements {user_id}: {e}")
            return None
    
    async def get_all_achievements(self) -> Dict[str, Any]:
        """
        Get all available achievements in the game
        
        Returns:
            Dictionary of all achievements
        """
        try:
            achievements_file = self.db.global_dir / "achievements.json"
            achievements_data = await self.db._read_json_file(achievements_file)
            
            if achievements_data is None:
                return DEFAULT_ACHIEVEMENTS
            
            return achievements_data
            
        except Exception as e:
            logger.error(f"Error getting all achievements: {e}")
            return DEFAULT_ACHIEVEMENTS
    
    async def check_achievement_progress(self, user_id: int, achievement_id: str, 
                                       current_value: int) -> Tuple[bool, bool, Dict[str, Any]]:
        """
        Check and update achievement progress
        
        Args:
            user_id: Discord user ID
            achievement_id: ID of the achievement to check
            current_value: Current progress value
            
        Returns:
            Tuple of (progress_updated, achievement_unlocked, achievement_data)
        """
        try:
            # Get achievement definition
            all_achievements = await self.get_all_achievements()
            if achievement_id not in all_achievements:
                return False, False, {}
            
            achievement_def = all_achievements[achievement_id]
            requirement = achievement_def.get('requirement', 1)
            
            # Get user's current achievement data
            user_achievements = await self.get_user_achievements(user_id)
            if not user_achievements:
                raise DatabaseError(f"Achievement data not found for user {user_id}")
            
            # Check if already unlocked
            if achievement_id in user_achievements.get('unlocked', {}):
                return False, False, achievement_def
            
            # Update progress
            progress = user_achievements.setdefault('progress', {})
            old_progress = progress.get(achievement_id, 0)
            
            if current_value > old_progress:
                progress[achievement_id] = current_value
                
                # Check if achievement is complete
                if current_value >= requirement:
                    await self._unlock_achievement(user_id, achievement_id, user_achievements, achievement_def)
                    return True, True, achievement_def
                else:
                    # Just progress update
                    await self.db.save_user_data(user_id, 'achievements', user_achievements)
                    return True, False, achievement_def
            
            return False, False, achievement_def
            
        except Exception as e:
            logger.error(f"Error checking achievement progress for user {user_id}: {e}")
            return False, False, {}
    
    async def _unlock_achievement(self, user_id: int, achievement_id: str, 
                                 user_achievements: Dict[str, Any], 
                                 achievement_def: Dict[str, Any]):
        """
        Unlock an achievement and award rewards
        
        Args:
            user_id: Discord user ID
            achievement_id: ID of the achievement to unlock
            user_achievements: User's achievement data
            achievement_def: Achievement definition
        """
        try:
            # Mark as unlocked
            user_achievements.setdefault('unlocked', {})[achievement_id] = datetime.utcnow().isoformat()
            user_achievements['total_unlocked'] = user_achievements.get('total_unlocked', 0) + 1
            
            # Calculate achievement points (based on rarity/difficulty)
            points = self._calculate_achievement_points(achievement_def)
            user_achievements['achievement_points'] = user_achievements.get('achievement_points', 0) + points
            
            # Save achievement data
            await self.db.save_user_data(user_id, 'achievements', user_achievements)
            
            # Award rewards
            await self._award_achievement_rewards(user_id, achievement_def)
            
            logger.info(f"User {user_id} unlocked achievement: {achievement_id}")
            
        except Exception as e:
            logger.error(f"Error unlocking achievement for user {user_id}: {e}")
    
    async def _award_achievement_rewards(self, user_id: int, achievement_def: Dict[str, Any]):
        """
        Award rewards for unlocking an achievement
        
        Args:
            user_id: Discord user ID
            achievement_def: Achievement definition with rewards
        """
        try:
            # Award coins
            coin_reward = achievement_def.get('reward_coins', 0)
            if coin_reward > 0:
                economy_data = await self.db.get_user_data(user_id, 'economy')
                if economy_data:
                    economy_data['pocket_balance'] += coin_reward
                    economy_data['total_earned'] += coin_reward
                    await self.db.save_user_data(user_id, 'economy', economy_data)
            
            # Award experience
            exp_reward = achievement_def.get('reward_experience', 0)
            if exp_reward > 0:
                profile_data = await self.db.get_user_data(user_id, 'profile')
                if profile_data:
                    profile_data['experience'] += exp_reward
                    await self.db.save_user_data(user_id, 'profile', profile_data)
            
            # Award items
            item_rewards = achievement_def.get('reward_items', [])
            if item_rewards:
                inventory_data = await self.db.get_user_data(user_id, 'inventory')
                if inventory_data:
                    for item_id in item_rewards:
                        # This would integrate with inventory manager
                        # For now, just log the reward
                        logger.info(f"User {user_id} earned item reward: {item_id}")
            
        except Exception as e:
            logger.error(f"Error awarding achievement rewards for user {user_id}: {e}")
    
    def _calculate_achievement_points(self, achievement_def: Dict[str, Any]) -> int:
        """
        Calculate points awarded for an achievement
        
        Args:
            achievement_def: Achievement definition
            
        Returns:
            Points to award
        """
        base_points = 10
        
        # Bonus points based on category
        category = achievement_def.get('category', 'special')
        category_multipliers = {
            'command_usage': 1.0,
            'economy': 1.2,
            'social': 1.5,
            'gaming': 1.3,
            'collection': 1.4,
            'time_based': 2.0,
            'special': 3.0
        }
        
        multiplier = category_multipliers.get(category, 1.0)
        
        # Bonus for hidden achievements
        if achievement_def.get('hidden', False):
            multiplier *= 1.5
        
        return int(base_points * multiplier)
    
    async def track_command_usage(self, user_id: int, total_commands: int) -> List[str]:
        """
        Track command usage achievements
        
        Args:
            user_id: Discord user ID
            total_commands: Total commands used by user
            
        Returns:
            List of newly unlocked achievement IDs
        """
        unlocked_achievements = []
        
        try:
            # Define command usage milestones
            command_achievements = {
                'first_command': 1,
                'command_novice': 10,
                'command_user': 50,
                'command_enthusiast': 100,
                'command_expert': 500,
                'command_master': 1000,
                'command_legend': 5000,
                'command_god': 10000
            }
            
            for achievement_id, requirement in command_achievements.items():
                if total_commands >= requirement:
                    _, unlocked, _ = await self.check_achievement_progress(user_id, achievement_id, total_commands)
                    if unlocked:
                        unlocked_achievements.append(achievement_id)
            
        except Exception as e:
            logger.error(f"Error tracking command usage achievements for user {user_id}: {e}")
        
        return unlocked_achievements
    
    async def track_economy_achievement(self, user_id: int, achievement_type: str, value: int) -> List[str]:
        """
        Track economy-related achievements
        
        Args:
            user_id: Discord user ID
            achievement_type: Type of economy achievement
            value: Current value for the achievement
            
        Returns:
            List of newly unlocked achievement IDs
        """
        unlocked_achievements = []
        
        try:
            economy_achievements = {
                'first_coin': {'type': 'total_earned', 'requirement': 1},
                'hundred_coins': {'type': 'total_earned', 'requirement': 100},
                'thousand_coins': {'type': 'total_earned', 'requirement': 1000},
                'ten_thousand_coins': {'type': 'total_earned', 'requirement': 10000},
                'millionaire': {'type': 'total_balance', 'requirement': 1000000},
                'big_spender': {'type': 'total_spent', 'requirement': 50000},
                'gambling_winner': {'type': 'gambling_wins', 'requirement': 100}
            }
            
            for achievement_id, data in economy_achievements.items():
                if data['type'] == achievement_type and value >= data['requirement']:
                    _, unlocked, _ = await self.check_achievement_progress(user_id, achievement_id, value)
                    if unlocked:
                        unlocked_achievements.append(achievement_id)
            
        except Exception as e:
            logger.error(f"Error tracking economy achievements for user {user_id}: {e}")
        
        return unlocked_achievements
    
    async def track_collection_achievement(self, user_id: int, collection_type: str, count: int) -> List[str]:
        """
        Track collection-related achievements
        
        Args:
            user_id: Discord user ID
            collection_type: Type of collection (items, pets, etc.)
            count: Current count
            
        Returns:
            List of newly unlocked achievement IDs
        """
        unlocked_achievements = []
        
        try:
            collection_achievements = {
                'first_item': {'type': 'items', 'requirement': 1},
                'item_collector': {'type': 'items', 'requirement': 10},
                'item_hoarder': {'type': 'items', 'requirement': 50},
                'first_pet': {'type': 'pets', 'requirement': 1},
                'pet_lover': {'type': 'pets', 'requirement': 5},
                'achievement_hunter': {'type': 'achievements', 'requirement': 10}
            }
            
            for achievement_id, data in collection_achievements.items():
                if data['type'] == collection_type and count >= data['requirement']:
                    _, unlocked, _ = await self.check_achievement_progress(user_id, achievement_id, count)
                    if unlocked:
                        unlocked_achievements.append(achievement_id)
            
        except Exception as e:
            logger.error(f"Error tracking collection achievements for user {user_id}: {e}")
        
        return unlocked_achievements
    
    async def track_social_achievement(self, user_id: int, social_type: str, count: int) -> List[str]:
        """
        Track social-related achievements
        
        Args:
            user_id: Discord user ID
            social_type: Type of social achievement
            count: Current count
            
        Returns:
            List of newly unlocked achievement IDs
        """
        unlocked_achievements = []
        
        try:
            social_achievements = {
                'first_friend': {'type': 'friends', 'requirement': 1},
                'social_butterfly': {'type': 'friends', 'requirement': 10},
                'popular': {'type': 'friends', 'requirement': 25},
                'married': {'type': 'marriage', 'requirement': 1},
                'gift_giver': {'type': 'gifts_sent', 'requirement': 10}
            }
            
            for achievement_id, data in social_achievements.items():
                if data['type'] == social_type and count >= data['requirement']:
                    _, unlocked, _ = await self.check_achievement_progress(user_id, achievement_id, count)
                    if unlocked:
                        unlocked_achievements.append(achievement_id)
            
        except Exception as e:
            logger.error(f"Error tracking social achievements for user {user_id}: {e}")
        
        return unlocked_achievements
    
    async def get_user_achievement_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive achievement statistics for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with achievement statistics
        """
        try:
            user_achievements = await self.get_user_achievements(user_id)
            if not user_achievements:
                return {}
            
            all_achievements = await self.get_all_achievements()
            
            unlocked = user_achievements.get('unlocked', {})
            progress = user_achievements.get('progress', {})
            
            # Calculate completion percentage
            total_achievements = len(all_achievements)
            unlocked_count = len(unlocked)
            completion_percentage = (unlocked_count / total_achievements) * 100 if total_achievements > 0 else 0
            
            # Group by category
            category_stats = {}
            for achievement_id, achievement_data in all_achievements.items():
                category = achievement_data.get('category', 'special')
                
                if category not in category_stats:
                    category_stats[category] = {
                        'total': 0,
                        'unlocked': 0,
                        'in_progress': 0
                    }
                
                category_stats[category]['total'] += 1
                
                if achievement_id in unlocked:
                    category_stats[category]['unlocked'] += 1
                elif achievement_id in progress:
                    category_stats[category]['in_progress'] += 1
            
            # Recent unlocks (last 10)
            recent_unlocks = []
            for achievement_id, unlock_date in unlocked.items():
                recent_unlocks.append({
                    'achievement_id': achievement_id,
                    'name': all_achievements.get(achievement_id, {}).get('name', achievement_id),
                    'unlocked_at': unlock_date
                })
            
            # Sort by unlock date (most recent first)
            recent_unlocks.sort(key=lambda x: x['unlocked_at'], reverse=True)
            recent_unlocks = recent_unlocks[:10]
            
            return {
                'total_achievements': total_achievements,
                'unlocked_count': unlocked_count,
                'completion_percentage': round(completion_percentage, 1),
                'achievement_points': user_achievements.get('achievement_points', 0),
                'category_stats': category_stats,
                'recent_unlocks': recent_unlocks,
                'achievements_in_progress': len(progress)
            }
            
        except Exception as e:
            logger.error(f"Error getting achievement stats for user {user_id}: {e}")
            return {}
    
    async def get_achievement_leaderboard(self, category: str = 'total', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get achievement leaderboard
        
        Args:
            category: Leaderboard category ('total', 'points', etc.)
            limit: Number of users to return
            
        Returns:
            List of user achievement data sorted by category
        """
        try:
            # This would require scanning all user achievement files
            # For now, return empty list as this is a complex operation
            # In a real implementation, you might want to maintain a separate leaderboard cache
            logger.info(f"Achievement leaderboard requested for category: {category}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting achievement leaderboard: {e}")
            return []
    
    # Progress tracking handlers for different achievement types
    async def _track_command_usage(self, user_id: int, data: Dict[str, Any]) -> List[str]:
        """Track command usage achievements"""
        total_commands = data.get('total_commands', 0)
        return await self.track_command_usage(user_id, total_commands)
    
    async def _track_economy(self, user_id: int, data: Dict[str, Any]) -> List[str]:
        """Track economy achievements"""
        unlocked = []
        
        for achievement_type, value in data.items():
            unlocked.extend(await self.track_economy_achievement(user_id, achievement_type, value))
        
        return unlocked
    
    async def _track_social(self, user_id: int, data: Dict[str, Any]) -> List[str]:
        """Track social achievements"""
        unlocked = []
        
        for social_type, count in data.items():
            unlocked.extend(await self.track_social_achievement(user_id, social_type, count))
        
        return unlocked
    
    async def _track_gaming(self, user_id: int, data: Dict[str, Any]) -> List[str]:
        """Track gaming achievements"""
        # Placeholder for gaming-specific achievements
        return []
    
    async def _track_collection(self, user_id: int, data: Dict[str, Any]) -> List[str]:
        """Track collection achievements"""
        unlocked = []
        
        for collection_type, count in data.items():
            unlocked.extend(await self.track_collection_achievement(user_id, collection_type, count))
        
        return unlocked
    
    async def _track_time_based(self, user_id: int, data: Dict[str, Any]) -> List[str]:
        """Track time-based achievements"""
        # Placeholder for time-based achievements (daily streaks, etc.)
        return []
    
    async def _track_special(self, user_id: int, data: Dict[str, Any]) -> List[str]:
        """Track special achievements"""
        # Placeholder for special/event achievements
        return []