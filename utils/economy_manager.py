"""
Economy Management System for FunniGuy Discord Bot
Handles all financial operations, transactions, and currency management
"""
import asyncio
import logging
import random
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

from .database_manager import DatabaseManager, DatabaseError
from .schemas import EconomyData, SchemaValidator

logger = logging.getLogger(__name__)


class TransactionType(Enum):
    """Types of transactions"""
    EARN_WORK = "earn_work"
    EARN_DAILY = "earn_daily"
    EARN_WEEKLY = "earn_weekly"
    EARN_GAMBLING = "earn_gambling"
    EARN_ACHIEVEMENT = "earn_achievement"
    EARN_LEVEL_UP = "earn_level_up"
    EARN_GIFT = "earn_gift"
    SPEND_SHOP = "spend_shop"
    SPEND_GAMBLING = "spend_gambling"
    SPEND_GIFT = "spend_gift"
    TRANSFER_SEND = "transfer_send"
    TRANSFER_RECEIVE = "transfer_receive"
    BANK_DEPOSIT = "bank_deposit"
    BANK_WITHDRAW = "bank_withdraw"
    ADMIN_ADD = "admin_add"
    ADMIN_REMOVE = "admin_remove"


class InsufficientFundsError(Exception):
    """Exception raised when user has insufficient funds"""
    pass


class InvalidAmountError(Exception):
    """Exception raised for invalid transaction amounts"""
    pass


class EconomyManager:
    """
    Comprehensive economy management system
    Handles all financial operations and currency management
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize the economy manager
        
        Args:
            database_manager: Instance of DatabaseManager
        """
        self.db = database_manager
        self.validator = SchemaValidator()
        
        # Economy settings
        self.max_transaction_history = 100
        self.daily_bonus_amount = 100
        self.weekly_bonus_amount = 500
        self.work_min_amount = 50
        self.work_max_amount = 200
        self.work_cooldown_hours = 4
        
        # Bank settings
        self.initial_bank_capacity = 1000
        self.bank_upgrade_cost_multiplier = 2
        self.max_bank_capacity = 1000000
        
        # Gambling settings
        self.min_bet = 10
        self.max_bet = 10000
        self.gambling_win_multiplier = 1.8
        self.gambling_win_chance = 0.45  # 45% chance to win
    
    async def get_user_economy(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's economy data
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Economy data or None if not found
        """
        try:
            economy_data = await self.db.get_user_data(user_id, 'economy')
            
            # Reset daily/weekly flags if needed
            if economy_data:
                economy_data = await self._check_and_reset_daily_weekly(user_id, economy_data)
            
            return economy_data
            
        except Exception as e:
            logger.error(f"Error getting user economy {user_id}: {e}")
            return None
    
    async def _check_and_reset_daily_weekly(self, user_id: int, economy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check and reset daily/weekly flags if a new day/week has started
        
        Args:
            user_id: Discord user ID
            economy_data: Current economy data
            
        Returns:
            Updated economy data
        """
        now = datetime.utcnow()
        current_date = now.date()
        
        # Check daily reset
        last_daily = economy_data.get('last_daily_time')
        if last_daily:
            last_daily_date = datetime.fromisoformat(last_daily).date()
            if last_daily_date != current_date:
                economy_data['daily_work_used'] = False
                economy_data['daily_bonus_claimed'] = False
        
        # Check weekly reset (Monday = 0)
        last_weekly = economy_data.get('last_weekly_time')
        if last_weekly:
            last_weekly_date = datetime.fromisoformat(last_weekly).date()
            current_week = current_date.isocalendar()[1]
            last_week = last_weekly_date.isocalendar()[1]
            if current_week != last_week:
                economy_data['weekly_bonus_claimed'] = False
        
        # Check work cooldown
        last_work = economy_data.get('last_work_time')
        if last_work:
            last_work_time = datetime.fromisoformat(last_work)
            if (now - last_work_time).total_seconds() >= (self.work_cooldown_hours * 3600):
                economy_data['daily_work_used'] = False
        
        # Save updated data
        await self.db.save_user_data(user_id, 'economy', economy_data)
        return economy_data
    
    async def get_balance(self, user_id: int) -> Tuple[int, int]:
        """
        Get user's pocket and bank balance
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (pocket_balance, bank_balance)
        """
        economy_data = await self.get_user_economy(user_id)
        if not economy_data:
            return 0, 0
        
        return economy_data.get('pocket_balance', 0), economy_data.get('bank_balance', 0)
    
    async def add_money(self, user_id: int, amount: int, location: str = 'pocket', 
                       transaction_type: TransactionType = TransactionType.ADMIN_ADD,
                       description: str = "Money added") -> bool:
        """
        Add money to user's account
        
        Args:
            user_id: Discord user ID
            amount: Amount to add
            location: 'pocket' or 'bank'
            transaction_type: Type of transaction
            description: Transaction description
            
        Returns:
            True if money was added successfully
        """
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            if location == 'pocket':
                economy_data['pocket_balance'] += amount
            elif location == 'bank':
                economy_data['bank_balance'] += amount
            else:
                raise InvalidAmountError("Invalid location. Must be 'pocket' or 'bank'")
            
            economy_data['total_earned'] += amount
            
            # Add transaction to history
            await self._add_transaction(economy_data, transaction_type, amount, description)
            
            # Save updated data
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.debug(f"Added {amount} coins to {location} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding money for user {user_id}: {e}")
            return False
    
    async def remove_money(self, user_id: int, amount: int, location: str = 'pocket',
                          transaction_type: TransactionType = TransactionType.ADMIN_REMOVE,
                          description: str = "Money removed") -> bool:
        """
        Remove money from user's account
        
        Args:
            user_id: Discord user ID
            amount: Amount to remove
            location: 'pocket' or 'bank'
            transaction_type: Type of transaction
            description: Transaction description
            
        Returns:
            True if money was removed successfully
        """
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            current_balance = economy_data.get(f'{location}_balance', 0)
            if current_balance < amount:
                raise InsufficientFundsError(f"Insufficient funds in {location}")
            
            economy_data[f'{location}_balance'] -= amount
            economy_data['total_spent'] += amount
            
            # Add transaction to history
            await self._add_transaction(economy_data, transaction_type, -amount, description)
            
            # Save updated data
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.debug(f"Removed {amount} coins from {location} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing money for user {user_id}: {e}")
            return False
    
    async def transfer_money(self, sender_id: int, receiver_id: int, amount: int) -> bool:
        """
        Transfer money between users
        
        Args:
            sender_id: Discord user ID of sender
            receiver_id: Discord user ID of receiver
            amount: Amount to transfer
            
        Returns:
            True if transfer was successful
        """
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        
        if sender_id == receiver_id:
            raise InvalidAmountError("Cannot transfer to yourself")
        
        try:
            # Check sender has enough money
            sender_economy = await self.get_user_economy(sender_id)
            if not sender_economy:
                raise DatabaseError(f"Sender {sender_id} economy data not found")
            
            if sender_economy.get('pocket_balance', 0) < amount:
                raise InsufficientFundsError("Insufficient funds for transfer")
            
            # Check receiver exists
            receiver_economy = await self.get_user_economy(receiver_id)
            if not receiver_economy:
                raise DatabaseError(f"Receiver {receiver_id} economy data not found")
            
            # Perform transfer
            sender_economy['pocket_balance'] -= amount
            sender_economy['total_spent'] += amount
            await self._add_transaction(sender_economy, TransactionType.TRANSFER_SEND, 
                                      -amount, f"Transfer to user {receiver_id}")
            
            receiver_economy['pocket_balance'] += amount
            receiver_economy['total_earned'] += amount
            await self._add_transaction(receiver_economy, TransactionType.TRANSFER_RECEIVE, 
                                      amount, f"Transfer from user {sender_id}")
            
            # Save both users' data
            await self.db.save_user_data(sender_id, 'economy', sender_economy)
            await self.db.save_user_data(receiver_id, 'economy', receiver_economy)
            
            logger.info(f"Transferred {amount} coins from {sender_id} to {receiver_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error transferring money: {e}")
            return False
    
    async def deposit_to_bank(self, user_id: int, amount: int) -> bool:
        """
        Deposit money from pocket to bank
        
        Args:
            user_id: Discord user ID
            amount: Amount to deposit
            
        Returns:
            True if deposit was successful
        """
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            pocket_balance = economy_data.get('pocket_balance', 0)
            bank_balance = economy_data.get('bank_balance', 0)
            bank_capacity = economy_data.get('bank_capacity', self.initial_bank_capacity)
            
            if pocket_balance < amount:
                raise InsufficientFundsError("Insufficient funds in pocket")
            
            if bank_balance + amount > bank_capacity:
                raise InvalidAmountError("Bank capacity exceeded")
            
            # Perform deposit
            economy_data['pocket_balance'] -= amount
            economy_data['bank_balance'] += amount
            
            await self._add_transaction(economy_data, TransactionType.BANK_DEPOSIT,
                                      amount, f"Deposited to bank")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.debug(f"Deposited {amount} coins to bank for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error depositing to bank for user {user_id}: {e}")
            return False
    
    async def withdraw_from_bank(self, user_id: int, amount: int) -> bool:
        """
        Withdraw money from bank to pocket
        
        Args:
            user_id: Discord user ID
            amount: Amount to withdraw
            
        Returns:
            True if withdrawal was successful
        """
        if amount <= 0:
            raise InvalidAmountError("Amount must be positive")
        
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            bank_balance = economy_data.get('bank_balance', 0)
            
            if bank_balance < amount:
                raise InsufficientFundsError("Insufficient funds in bank")
            
            # Perform withdrawal
            economy_data['bank_balance'] -= amount
            economy_data['pocket_balance'] += amount
            
            await self._add_transaction(economy_data, TransactionType.BANK_WITHDRAW,
                                      amount, f"Withdrew from bank")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.debug(f"Withdrew {amount} coins from bank for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error withdrawing from bank for user {user_id}: {e}")
            return False
    
    async def claim_daily_bonus(self, user_id: int) -> Tuple[bool, int]:
        """
        Claim daily bonus
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (success, amount_earned)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            if economy_data.get('daily_bonus_claimed', False):
                return False, 0
            
            # Award daily bonus
            bonus_amount = self.daily_bonus_amount
            economy_data['pocket_balance'] += bonus_amount
            economy_data['total_earned'] += bonus_amount
            economy_data['daily_bonus_claimed'] = True
            economy_data['last_daily_time'] = datetime.utcnow().isoformat()
            
            await self._add_transaction(economy_data, TransactionType.EARN_DAILY,
                                      bonus_amount, "Daily bonus")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.info(f"User {user_id} claimed daily bonus: {bonus_amount}")
            return True, bonus_amount
            
        except Exception as e:
            logger.error(f"Error claiming daily bonus for user {user_id}: {e}")
            return False, 0
    
    async def claim_weekly_bonus(self, user_id: int) -> Tuple[bool, int]:
        """
        Claim weekly bonus
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (success, amount_earned)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            if economy_data.get('weekly_bonus_claimed', False):
                return False, 0
            
            # Award weekly bonus
            bonus_amount = self.weekly_bonus_amount
            economy_data['pocket_balance'] += bonus_amount
            economy_data['total_earned'] += bonus_amount
            economy_data['weekly_bonus_claimed'] = True
            economy_data['last_weekly_time'] = datetime.utcnow().isoformat()
            
            await self._add_transaction(economy_data, TransactionType.EARN_WEEKLY,
                                      bonus_amount, "Weekly bonus")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.info(f"User {user_id} claimed weekly bonus: {bonus_amount}")
            return True, bonus_amount
            
        except Exception as e:
            logger.error(f"Error claiming weekly bonus for user {user_id}: {e}")
            return False, 0
    
    async def work_for_money(self, user_id: int) -> Tuple[bool, int]:
        """
        Work to earn money
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (success, amount_earned)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            if economy_data.get('daily_work_used', False):
                return False, 0
            
            # Generate random work earnings
            earnings = random.randint(self.work_min_amount, self.work_max_amount)
            
            economy_data['pocket_balance'] += earnings
            economy_data['total_earned'] += earnings
            economy_data['daily_work_used'] = True
            economy_data['last_work_time'] = datetime.utcnow().isoformat()
            
            await self._add_transaction(economy_data, TransactionType.EARN_WORK,
                                      earnings, "Work earnings")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.info(f"User {user_id} worked and earned: {earnings}")
            return True, earnings
            
        except Exception as e:
            logger.error(f"Error processing work for user {user_id}: {e}")
            return False, 0
    
    async def gamble_money(self, user_id: int, bet_amount: int) -> Tuple[bool, int, bool]:
        """
        Gamble money
        
        Args:
            user_id: Discord user ID
            bet_amount: Amount to bet
            
        Returns:
            Tuple of (success, amount_won_or_lost, did_win)
        """
        if bet_amount < self.min_bet or bet_amount > self.max_bet:
            raise InvalidAmountError(f"Bet must be between {self.min_bet} and {self.max_bet}")
        
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            pocket_balance = economy_data.get('pocket_balance', 0)
            if pocket_balance < bet_amount:
                raise InsufficientFundsError("Insufficient funds to gamble")
            
            # Determine if user wins
            did_win = random.random() < self.gambling_win_chance
            
            if did_win:
                # User wins
                winnings = int(bet_amount * self.gambling_win_multiplier)
                net_gain = winnings - bet_amount
                
                economy_data['pocket_balance'] += net_gain
                economy_data['total_earned'] += winnings
                economy_data['total_won'] += winnings
                economy_data['gambling_streak'] = economy_data.get('gambling_streak', 0) + 1
                
                await self._add_transaction(economy_data, TransactionType.EARN_GAMBLING,
                                          net_gain, f"Gambling win (bet: {bet_amount})")
                
                logger.info(f"User {user_id} won gambling: bet {bet_amount}, won {winnings}")
                
                await self.db.save_user_data(user_id, 'economy', economy_data)
                return True, winnings, True
            else:
                # User loses
                economy_data['pocket_balance'] -= bet_amount
                economy_data['total_spent'] += bet_amount
                economy_data['total_gambled'] += bet_amount
                economy_data['gambling_streak'] = 0
                
                await self._add_transaction(economy_data, TransactionType.SPEND_GAMBLING,
                                          -bet_amount, f"Gambling loss")
                
                logger.info(f"User {user_id} lost gambling: bet {bet_amount}")
                
                await self.db.save_user_data(user_id, 'economy', economy_data)
                return True, bet_amount, False
                
        except Exception as e:
            logger.error(f"Error processing gambling for user {user_id}: {e}")
            return False, 0, False
    
    async def upgrade_bank(self, user_id: int) -> Tuple[bool, int, int]:
        """
        Upgrade user's bank capacity
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (success, upgrade_cost, new_capacity)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            current_capacity = economy_data.get('bank_capacity', self.initial_bank_capacity)
            
            if current_capacity >= self.max_bank_capacity:
                return False, 0, current_capacity  # Already at max capacity
            
            # Calculate upgrade cost
            upgrade_cost = int(current_capacity * self.bank_upgrade_cost_multiplier)
            new_capacity = current_capacity * 2
            
            if new_capacity > self.max_bank_capacity:
                new_capacity = self.max_bank_capacity
            
            pocket_balance = economy_data.get('pocket_balance', 0)
            if pocket_balance < upgrade_cost:
                raise InsufficientFundsError("Insufficient funds for bank upgrade")
            
            # Perform upgrade
            economy_data['pocket_balance'] -= upgrade_cost
            economy_data['bank_capacity'] = new_capacity
            economy_data['total_spent'] += upgrade_cost
            
            await self._add_transaction(economy_data, TransactionType.SPEND_SHOP,
                                      -upgrade_cost, f"Bank upgrade to {new_capacity}")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.info(f"User {user_id} upgraded bank: cost {upgrade_cost}, new capacity {new_capacity}")
            return True, upgrade_cost, new_capacity
            
        except Exception as e:
            logger.error(f"Error upgrading bank for user {user_id}: {e}")
            return False, 0, 0
    
    async def get_transaction_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user's transaction history
        
        Args:
            user_id: Discord user ID
            limit: Number of transactions to return
            
        Returns:
            List of transaction dictionaries
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                return []
            
            transactions = economy_data.get('transaction_history', [])
            
            # Return most recent transactions
            return transactions[-limit:] if len(transactions) > limit else transactions
            
        except Exception as e:
            logger.error(f"Error getting transaction history for user {user_id}: {e}")
            return []
    
    async def _add_transaction(self, economy_data: Dict[str, Any], transaction_type: TransactionType,
                              amount: int, description: str):
        """
        Add a transaction to user's history
        
        Args:
            economy_data: User's economy data
            transaction_type: Type of transaction
            amount: Transaction amount (positive for gains, negative for losses)
            description: Transaction description
        """
        transaction = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': transaction_type.value,
            'amount': amount,
            'description': description
        }
        
        if 'transaction_history' not in economy_data:
            economy_data['transaction_history'] = []
        
        economy_data['transaction_history'].append(transaction)
        
        # Keep only the most recent transactions
        if len(economy_data['transaction_history']) > self.max_transaction_history:
            economy_data['transaction_history'] = economy_data['transaction_history'][-self.max_transaction_history:]
    
    async def get_economy_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive economy statistics for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with economy statistics
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                return {}
            
            pocket_balance = economy_data.get('pocket_balance', 0)
            bank_balance = economy_data.get('bank_balance', 0)
            total_balance = pocket_balance + bank_balance
            
            return {
                'balances': {
                    'pocket': pocket_balance,
                    'bank': bank_balance,
                    'total': total_balance,
                    'bank_capacity': economy_data.get('bank_capacity', self.initial_bank_capacity)
                },
                'lifetime': {
                    'total_earned': economy_data.get('total_earned', 0),
                    'total_spent': economy_data.get('total_spent', 0),
                    'net_worth': economy_data.get('total_earned', 0) - economy_data.get('total_spent', 0)
                },
                'gambling': {
                    'total_gambled': economy_data.get('total_gambled', 0),
                    'total_won': economy_data.get('total_won', 0),
                    'gambling_streak': economy_data.get('gambling_streak', 0)
                },
                'bonuses': {
                    'daily_claimed': economy_data.get('daily_bonus_claimed', False),
                    'weekly_claimed': economy_data.get('weekly_bonus_claimed', False),
                    'work_used': economy_data.get('daily_work_used', False)
                },
                'transaction_count': len(economy_data.get('transaction_history', []))
            }
            
        except Exception as e:
            logger.error(f"Error getting economy stats for user {user_id}: {e}")
            return {}
    
    async def reset_daily_limits(self, user_id: int) -> bool:
        """
        Reset daily limits for a user (admin function)
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if reset was successful
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                return False
            
            economy_data['daily_bonus_claimed'] = False
            economy_data['daily_work_used'] = False
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.info(f"Reset daily limits for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting daily limits for user {user_id}: {e}")
            return False