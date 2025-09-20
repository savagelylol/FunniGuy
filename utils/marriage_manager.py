"""
Marriage and Relationship Management System for FunniGuy Discord Bot
Handles proposals, partnerships, marriages, and relationship benefits
"""
import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from .database_manager import DatabaseManager, DatabaseError
from .schemas import (
    UserRelationships, Marriage, MarriageStatus, SchemaValidator
)

logger = logging.getLogger(__name__)


class RelationshipError(Exception):
    """Base exception for relationship operations"""
    pass


class AlreadyMarriedError(RelationshipError):
    """Exception raised when user is already married"""
    pass


class MarriageManager:
    """
    Comprehensive marriage and relationship management system
    Handles proposals, marriages, benefits, and relationship tracking
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize the marriage manager
        
        Args:
            database_manager: Instance of DatabaseManager
        """
        self.db = database_manager
        self.validator = SchemaValidator()
        
        # Marriage settings
        self.proposal_expiry_hours = 72  # 3 days
        self.divorce_cooldown_days = 7
        self.marriage_cost = 1000  # Cost to get married
        
        # Relationship benefits
        self.marriage_benefits = {
            'experience_bonus': 1.1,  # 10% bonus experience
            'daily_bonus_multiplier': 1.2,  # 20% bonus daily rewards
            'shared_bank_access': True,
            'love_point_daily_max': 10
        }
        
        # Anniversary rewards
        self.anniversary_rewards = {
            1: {'coins': 5000, 'experience': 100},   # 1 month
            6: {'coins': 15000, 'experience': 300},  # 6 months
            12: {'coins': 50000, 'experience': 1000} # 1 year
        }
    
    async def get_user_relationships(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's relationship data
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Relationship data or None if not found
        """
        try:
            return await self.db.get_user_data(user_id, 'relationships')
        except Exception as e:
            logger.error(f"Error getting user relationships {user_id}: {e}")
            return None
    
    async def send_proposal(self, proposer_id: int, proposed_to_id: int) -> Tuple[bool, str]:
        """
        Send a marriage proposal
        
        Args:
            proposer_id: User ID of the person proposing
            proposed_to_id: User ID of the person being proposed to
            
        Returns:
            Tuple of (success, message/error)
        """
        if proposer_id == proposed_to_id:
            return False, "You cannot propose to yourself!"
        
        try:
            # Check if proposer is already married or in a relationship
            proposer_rel = await self.get_user_relationships(proposer_id)
            if not proposer_rel:
                raise DatabaseError(f"Relationship data not found for user {proposer_id}")
            
            if proposer_rel.get('current_relationship'):
                return False, "You are already in a relationship!"
            
            # Check if proposed-to user is already married or in a relationship
            proposed_rel = await self.get_user_relationships(proposed_to_id)
            if not proposed_rel:
                raise DatabaseError(f"Relationship data not found for user {proposed_to_id}")
            
            if proposed_rel.get('current_relationship'):
                return False, "This person is already in a relationship!"
            
            # Check if there's already a pending proposal between these users
            proposals_sent = proposer_rel.get('proposals_sent', [])
            if proposed_to_id in proposals_sent:
                return False, "You already have a pending proposal to this person!"
            
            proposals_received = proposed_rel.get('proposals_received', [])
            if proposer_id in proposals_received:
                return False, "This person already has a pending proposal from you!"
            
            # Check if user has enough money for marriage (if they accept)
            economy_data = await self.db.get_user_data(proposer_id, 'economy')
            if not economy_data or economy_data.get('pocket_balance', 0) < self.marriage_cost:
                return False, f"You need at least {self.marriage_cost} coins to propose!"
            
            # Add proposal to both users' data
            proposals_sent.append(proposed_to_id)
            proposals_received.append(proposer_id)
            
            proposer_rel['proposals_sent'] = proposals_sent
            proposed_rel['proposals_received'] = proposals_received
            
            # Save updated relationship data
            await self.db.save_user_data(proposer_id, 'relationships', proposer_rel)
            await self.db.save_user_data(proposed_to_id, 'relationships', proposed_rel)
            
            logger.info(f"Marriage proposal sent from {proposer_id} to {proposed_to_id}")
            return True, "Proposal sent successfully! 💍"
            
        except Exception as e:
            logger.error(f"Error sending proposal: {e}")
            return False, f"Failed to send proposal: {str(e)}"
    
    async def accept_proposal(self, accepter_id: int, proposer_id: int) -> Tuple[bool, str]:
        """
        Accept a marriage proposal
        
        Args:
            accepter_id: User ID of person accepting
            proposer_id: User ID of person who proposed
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            # Verify proposal exists
            accepter_rel = await self.get_user_relationships(accepter_id)
            proposer_rel = await self.get_user_relationships(proposer_id)
            
            if not accepter_rel or not proposer_rel:
                return False, "Relationship data not found!"
            
            proposals_received = accepter_rel.get('proposals_received', [])
            if proposer_id not in proposals_received:
                return False, "No proposal found from this person!"
            
            # Check if both users are still single
            if accepter_rel.get('current_relationship') or proposer_rel.get('current_relationship'):
                return False, "One of you is already in a relationship!"
            
            # Check if proposer still has enough money
            proposer_economy = await self.db.get_user_data(proposer_id, 'economy')
            if not proposer_economy or proposer_economy.get('pocket_balance', 0) < self.marriage_cost:
                return False, f"The proposer needs {self.marriage_cost} coins to complete the marriage!"
            
            # Create marriage
            marriage_id = str(uuid.uuid4())
            marriage_data = {
                'relationship_id': marriage_id,
                'user1_id': proposer_id,
                'user2_id': accepter_id,
                'status': MarriageStatus.MARRIED.value,
                'started_at': datetime.utcnow().isoformat(),
                'married_at': datetime.utcnow().isoformat(),
                'anniversary': datetime.utcnow().replace(day=1).isoformat(),  # Monthly anniversary
                'love_points': 10,  # Starting love points
                'shared_activities': 0,
                'gifts_exchanged': 0,
                'shared_bank_access': True,
                'experience_bonus': self.marriage_benefits['experience_bonus'],
                'daily_bonus_multiplier': self.marriage_benefits['daily_bonus_multiplier']
            }
            
            # Save marriage data
            await self.db.save_marriage(marriage_id, marriage_data)
            
            # Update both users' relationship status
            accepter_rel['current_relationship'] = marriage_id
            proposer_rel['current_relationship'] = marriage_id
            
            # Clear proposals
            accepter_rel['proposals_received'] = [p for p in proposals_received if p != proposer_id]
            proposer_rel['proposals_sent'] = [p for p in proposer_rel.get('proposals_sent', []) if p != accepter_id]
            
            # Add to relationship history
            accepter_rel.setdefault('relationship_history', []).append(marriage_id)
            proposer_rel.setdefault('relationship_history', []).append(marriage_id)
            
            # Save relationship data
            await self.db.save_user_data(accepter_id, 'relationships', accepter_rel)
            await self.db.save_user_data(proposer_id, 'relationships', proposer_rel)
            
            # Charge marriage cost
            proposer_economy['pocket_balance'] -= self.marriage_cost
            proposer_economy['total_spent'] += self.marriage_cost
            await self.db.save_user_data(proposer_id, 'economy', proposer_economy)
            
            logger.info(f"Marriage completed between {proposer_id} and {accepter_id}")
            return True, f"Congratulations! You are now married! 💕 (Marriage cost: {self.marriage_cost} coins)"
            
        except Exception as e:
            logger.error(f"Error accepting proposal: {e}")
            return False, f"Failed to accept proposal: {str(e)}"
    
    async def reject_proposal(self, rejecter_id: int, proposer_id: int) -> Tuple[bool, str]:
        """
        Reject a marriage proposal
        
        Args:
            rejecter_id: User ID of person rejecting
            proposer_id: User ID of person who proposed
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            rejecter_rel = await self.get_user_relationships(rejecter_id)
            proposer_rel = await self.get_user_relationships(proposer_id)
            
            if not rejecter_rel or not proposer_rel:
                return False, "Relationship data not found!"
            
            # Remove proposal from both users
            proposals_received = rejecter_rel.get('proposals_received', [])
            if proposer_id in proposals_received:
                proposals_received.remove(proposer_id)
                rejecter_rel['proposals_received'] = proposals_received
            
            proposals_sent = proposer_rel.get('proposals_sent', [])
            if rejecter_id in proposals_sent:
                proposals_sent.remove(rejecter_id)
                proposer_rel['proposals_sent'] = proposals_sent
            
            # Save updated data
            await self.db.save_user_data(rejecter_id, 'relationships', rejecter_rel)
            await self.db.save_user_data(proposer_id, 'relationships', proposer_rel)
            
            logger.info(f"Proposal rejected: {proposer_id} -> {rejecter_id}")
            return True, "Proposal rejected."
            
        except Exception as e:
            logger.error(f"Error rejecting proposal: {e}")
            return False, f"Failed to reject proposal: {str(e)}"
    
    async def divorce(self, user_id: int) -> Tuple[bool, str]:
        """
        Initiate divorce proceedings
        
        Args:
            user_id: User ID initiating divorce
            
        Returns:
            Tuple of (success, message/error)
        """
        try:
            user_rel = await self.get_user_relationships(user_id)
            if not user_rel:
                return False, "Relationship data not found!"
            
            marriage_id = user_rel.get('current_relationship')
            if not marriage_id:
                return False, "You are not currently married!"
            
            # Get marriage data
            all_marriages = await self.db.get_all_marriages()
            if marriage_id not in all_marriages:
                return False, "Marriage data not found!"
            
            marriage_data = all_marriages[marriage_id]
            
            # Get partner ID
            partner_id = marriage_data['user1_id'] if marriage_data['user2_id'] == user_id else marriage_data['user2_id']
            
            # Update marriage status
            marriage_data['status'] = MarriageStatus.DIVORCED.value
            marriage_data['divorced_at'] = datetime.utcnow().isoformat()
            
            # Save updated marriage data
            await self.db.save_marriage(marriage_id, marriage_data)
            
            # Update both users' relationship status
            user_rel['current_relationship'] = None
            partner_rel = await self.get_user_relationships(partner_id)
            if partner_rel:
                partner_rel['current_relationship'] = None
                await self.db.save_user_data(partner_id, 'relationships', partner_rel)
            
            await self.db.save_user_data(user_id, 'relationships', user_rel)
            
            logger.info(f"Divorce completed: marriage {marriage_id}")
            return True, "Divorce completed. You are now single. 💔"
            
        except Exception as e:
            logger.error(f"Error processing divorce: {e}")
            return False, f"Failed to process divorce: {str(e)}"
    
    async def add_love_points(self, user_id: int, points: int = 1) -> bool:
        """
        Add love points to a marriage
        
        Args:
            user_id: User ID
            points: Points to add
            
        Returns:
            True if points were added successfully
        """
        try:
            user_rel = await self.get_user_relationships(user_id)
            if not user_rel or not user_rel.get('current_relationship'):
                return False
            
            marriage_id = user_rel['current_relationship']
            all_marriages = await self.db.get_all_marriages()
            
            if marriage_id not in all_marriages:
                return False
            
            marriage_data = all_marriages[marriage_id]
            current_points = marriage_data.get('love_points', 0)
            max_daily = self.marriage_benefits['love_point_daily_max']
            
            # Check daily limit (this would need proper daily tracking)
            new_points = min(current_points + points, current_points + max_daily)
            marriage_data['love_points'] = new_points
            
            await self.db.save_marriage(marriage_id, marriage_data)
            return True
            
        except Exception as e:
            logger.error(f"Error adding love points: {e}")
            return False
    
    async def get_marriage_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get marriage information for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Marriage information or None if not married
        """
        try:
            user_rel = await self.get_user_relationships(user_id)
            if not user_rel or not user_rel.get('current_relationship'):
                return None
            
            marriage_id = user_rel['current_relationship']
            all_marriages = await self.db.get_all_marriages()
            
            if marriage_id not in all_marriages:
                return None
            
            marriage_data = all_marriages[marriage_id]
            
            # Calculate relationship duration
            married_at = datetime.fromisoformat(marriage_data['married_at'])
            duration = datetime.utcnow() - married_at
            
            # Get partner info
            partner_id = marriage_data['user1_id'] if marriage_data['user2_id'] == user_id else marriage_data['user2_id']
            partner_profile = await self.db.get_user_data(partner_id, 'profile')
            
            return {
                'marriage_id': marriage_id,
                'partner_id': partner_id,
                'partner_name': partner_profile.get('display_name', 'Unknown') if partner_profile else 'Unknown',
                'married_at': marriage_data['married_at'],
                'duration_days': duration.days,
                'love_points': marriage_data.get('love_points', 0),
                'shared_activities': marriage_data.get('shared_activities', 0),
                'gifts_exchanged': marriage_data.get('gifts_exchanged', 0),
                'experience_bonus': marriage_data.get('experience_bonus', 1.0),
                'daily_bonus_multiplier': marriage_data.get('daily_bonus_multiplier', 1.0),
                'shared_bank_access': marriage_data.get('shared_bank_access', False)
            }
            
        except Exception as e:
            logger.error(f"Error getting marriage info for user {user_id}: {e}")
            return None
    
    async def check_anniversary(self, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if it's the user's anniversary and award rewards
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (is_anniversary, reward_info)
        """
        try:
            marriage_info = await self.get_marriage_info(user_id)
            if not marriage_info:
                return False, {}
            
            married_at = datetime.fromisoformat(marriage_info['married_at'])
            now = datetime.utcnow()
            
            # Calculate months married
            months_married = (now.year - married_at.year) * 12 + (now.month - married_at.month)
            
            # Check if it's anniversary day and hasn't been claimed
            if (now.day == married_at.day and 
                months_married in self.anniversary_rewards):
                
                # Award anniversary rewards
                rewards = self.anniversary_rewards[months_married]
                
                # Add coins
                if rewards.get('coins', 0) > 0:
                    economy_data = await self.db.get_user_data(user_id, 'economy')
                    if economy_data:
                        economy_data['pocket_balance'] += rewards['coins']
                        economy_data['total_earned'] += rewards['coins']
                        await self.db.save_user_data(user_id, 'economy', economy_data)
                
                # Add experience
                if rewards.get('experience', 0) > 0:
                    profile_data = await self.db.get_user_data(user_id, 'profile')
                    if profile_data:
                        profile_data['experience'] += rewards['experience']
                        await self.db.save_user_data(user_id, 'profile', profile_data)
                
                logger.info(f"Anniversary rewards given to user {user_id}: {months_married} months")
                return True, {
                    'months': months_married,
                    'rewards': rewards
                }
            
            return False, {}
            
        except Exception as e:
            logger.error(f"Error checking anniversary for user {user_id}: {e}")
            return False, {}
    
    async def get_relationship_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get relationship statistics for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with relationship statistics
        """
        try:
            user_rel = await self.get_user_relationships(user_id)
            if not user_rel:
                return {}
            
            marriage_info = await self.get_marriage_info(user_id)
            
            stats = {
                'current_status': 'married' if marriage_info else 'single',
                'proposals_sent': len(user_rel.get('proposals_sent', [])),
                'proposals_received': len(user_rel.get('proposals_received', [])),
                'relationship_history_count': len(user_rel.get('relationship_history', []))
            }
            
            if marriage_info:
                stats.update({
                    'marriage_duration_days': marriage_info['duration_days'],
                    'love_points': marriage_info['love_points'],
                    'shared_activities': marriage_info['shared_activities'],
                    'gifts_exchanged': marriage_info['gifts_exchanged'],
                    'partner_id': marriage_info['partner_id']
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting relationship statistics for user {user_id}: {e}")
            return {}