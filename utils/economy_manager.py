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
from .schemas import EconomyData, PrestigeData, ActiveEffects, ItemEffect, SchemaValidator, DEFAULT_ITEMS

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
        
        # Prestige system settings
        self.prestige_requirements = {
            1: 100000,   # 100k total earned
            2: 500000,   # 500k total earned
            3: 2000000,  # 2M total earned
            4: 10000000, # 10M total earned
            5: 50000000  # 50M total earned
        }
        self.prestige_multipliers = {
            0: 1.0,   # No prestige
            1: 1.1,   # +10% earnings
            2: 1.25,  # +25% earnings
            3: 1.5,   # +50% earnings
            4: 2.0,   # +100% earnings
            5: 3.0    # +200% earnings
        }
        
        # Crime and work settings
        self.crime_base_success_rate = 0.3
        self.crime_min_reward = 500
        self.crime_max_reward = 5000
        self.crime_failure_loss_rate = 0.2
        
        self.rob_base_success_rate = 0.25
        self.rob_min_amount = 100
        self.rob_max_percentage = 0.3
        
        # Tax system
        self.tax_brackets = {
            1: {'min': 0, 'max': 10000, 'rate': 0.0},      # No tax for poor
            2: {'min': 10001, 'max': 50000, 'rate': 0.05}, # 5% tax
            3: {'min': 50001, 'max': 200000, 'rate': 0.1}, # 10% tax
            4: {'min': 200001, 'max': 1000000, 'rate': 0.15}, # 15% tax
            5: {'min': 1000001, 'max': float('inf'), 'rate': 0.2} # 20% tax
        }
        
        # Bank tier system
        self.bank_tier_costs = [0, 5000, 25000, 100000, 500000]  # Cost to upgrade to each tier
        self.bank_tier_capacities = [1000, 10000, 50000, 200000, 1000000]  # Capacity at each tier
    
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
    
    async def upgrade_bank_tier(self, user_id: int) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Upgrade user's bank to the next tier with enhanced features
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (success, upgrade_cost, new_tier_info)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            current_tier = economy_data.get('bank_tier', 1)
            next_tier = current_tier + 1
            
            if next_tier > len(self.bank_tier_costs):
                return False, 0, {'error': 'Already at maximum bank tier'}
            
            upgrade_cost = self.bank_tier_costs[next_tier - 1]  # 0-indexed
            new_capacity = self.bank_tier_capacities[next_tier - 1]
            
            total_balance = economy_data.get('pocket_balance', 0) + economy_data.get('bank_balance', 0)
            if total_balance < upgrade_cost:
                raise InsufficientFundsError(f"Insufficient funds for tier {next_tier} upgrade")
            
            # Deduct from pocket first, then bank if needed
            remaining_cost = upgrade_cost
            pocket_balance = economy_data.get('pocket_balance', 0)
            
            if pocket_balance >= remaining_cost:
                economy_data['pocket_balance'] -= remaining_cost
            else:
                economy_data['pocket_balance'] = 0
                remaining_cost -= pocket_balance
                economy_data['bank_balance'] -= remaining_cost
            
            # Upgrade bank tier
            economy_data['bank_tier'] = next_tier
            economy_data['bank_capacity'] = new_capacity
            economy_data['total_spent'] += upgrade_cost
            
            # Unlock tier-specific features
            tier_features = self._get_bank_tier_features(next_tier)
            for feature, enabled in tier_features.items():
                economy_data[feature] = enabled
            
            await self._add_transaction(economy_data, TransactionType.SPEND_SHOP,
                                      -upgrade_cost, f"Bank tier {next_tier} upgrade")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            tier_info = {
                'tier': next_tier,
                'capacity': new_capacity,
                'features': tier_features,
                'cost': upgrade_cost
            }
            
            logger.info(f"User {user_id} upgraded to bank tier {next_tier}")
            return True, upgrade_cost, tier_info
            
        except Exception as e:
            logger.error(f"Error upgrading bank tier for user {user_id}: {e}")
            return False, 0, {'error': str(e)}
    
    def _get_bank_tier_features(self, tier: int) -> Dict[str, Any]:
        """
        Get features unlocked at each bank tier
        
        Args:
            tier: Bank tier level
            
        Returns:
            Dictionary of features and their values
        """
        tier_features = {
            1: {'loan_available': False, 'passive_income_rate': 0},
            2: {'loan_available': True, 'passive_income_rate': 5},
            3: {'loan_available': True, 'passive_income_rate': 15, 'investment_access': True},
            4: {'loan_available': True, 'passive_income_rate': 40, 'investment_access': True, 'premium_services': True},
            5: {'loan_available': True, 'passive_income_rate': 100, 'investment_access': True, 'premium_services': True, 'vip_status': True}
        }
        return tier_features.get(tier, tier_features[1])
    
    async def get_loan_eligibility(self, user_id: int) -> Tuple[bool, int, float]:
        """
        Check if user is eligible for a loan and calculate terms
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (eligible, max_loan_amount, interest_rate)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                return False, 0, 0.0
            
            bank_tier = economy_data.get('bank_tier', 1)
            if not economy_data.get('loan_available', False):
                return False, 0, 0.0
            
            current_loan = economy_data.get('current_loan', 0)
            if current_loan > 0:
                return False, 0, 0.0  # Already has a loan
            
            # Calculate max loan based on total earned and tier
            total_earned = economy_data.get('total_earned', 0)
            tier_multipliers = {1: 0, 2: 0.5, 3: 1.0, 4: 2.0, 5: 5.0}
            max_loan = int(total_earned * tier_multipliers.get(bank_tier, 0))
            
            # Interest rates by tier (lower tier = higher interest)
            tier_interest = {1: 0.15, 2: 0.10, 3: 0.08, 4: 0.05, 5: 0.03}
            interest_rate = tier_interest.get(bank_tier, 0.15)
            
            return max_loan > 1000, max_loan, interest_rate
            
        except Exception as e:
            logger.error(f"Error checking loan eligibility for user {user_id}: {e}")
            return False, 0, 0.0
    
    async def take_loan(self, user_id: int, amount: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Take out a loan
        
        Args:
            user_id: Discord user ID
            amount: Loan amount
            
        Returns:
            Tuple of (success, loan_info)
        """
        try:
            eligible, max_loan, interest_rate = await self.get_loan_eligibility(user_id)
            if not eligible:
                return False, {'error': 'Not eligible for loans'}
            
            if amount > max_loan:
                return False, {'error': f'Loan amount exceeds maximum ({max_loan})'}
            
            if amount < 1000:
                return False, {'error': 'Minimum loan amount is 1000 coins'}
            
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                return False, {'error': 'Economy data not found'}
            
            # Calculate total repayment amount
            total_repayment = int(amount * (1 + interest_rate))
            
            # Give loan money
            economy_data['pocket_balance'] += amount
            economy_data['current_loan'] = total_repayment
            economy_data['loan_interest_rate'] = interest_rate
            economy_data['total_earned'] += amount
            
            await self._add_transaction(economy_data, TransactionType.TRANSFER_RECEIVE,
                                      amount, f"Bank loan (interest rate: {interest_rate*100:.1f}%)")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            loan_info = {
                'amount': amount,
                'total_repayment': total_repayment,
                'interest_rate': interest_rate,
                'interest_amount': total_repayment - amount
            }
            
            logger.info(f"User {user_id} took loan: {amount} coins at {interest_rate*100:.1f}% interest")
            return True, loan_info
            
        except Exception as e:
            logger.error(f"Error processing loan for user {user_id}: {e}")
            return False, {'error': str(e)}
    
    async def repay_loan(self, user_id: int, amount: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Repay a loan (partial or full)
        
        Args:
            user_id: Discord user ID
            amount: Amount to repay (None for full repayment)
            
        Returns:
            Tuple of (success, repayment_info)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                return False, {'error': 'Economy data not found'}
            
            current_loan = economy_data.get('current_loan', 0)
            if current_loan <= 0:
                return False, {'error': 'No active loan to repay'}
            
            if amount is None:
                amount = current_loan  # Full repayment
            
            amount = min(amount, current_loan)  # Can't repay more than owed
            
            total_balance = economy_data.get('pocket_balance', 0) + economy_data.get('bank_balance', 0)
            if total_balance < amount:
                return False, {'error': 'Insufficient funds for repayment'}
            
            # Deduct repayment amount
            remaining_payment = amount
            pocket_balance = economy_data.get('pocket_balance', 0)
            
            if pocket_balance >= remaining_payment:
                economy_data['pocket_balance'] -= remaining_payment
            else:
                economy_data['pocket_balance'] = 0
                remaining_payment -= pocket_balance
                economy_data['bank_balance'] -= remaining_payment
            
            economy_data['current_loan'] -= amount
            economy_data['total_spent'] += amount
            
            if economy_data['current_loan'] <= 0:
                economy_data['current_loan'] = 0
                economy_data['loan_interest_rate'] = 0.0
            
            await self._add_transaction(economy_data, TransactionType.SPEND_SHOP,
                                      -amount, f"Loan repayment")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            repayment_info = {
                'amount_paid': amount,
                'remaining_loan': economy_data['current_loan'],
                'fully_paid': economy_data['current_loan'] <= 0
            }
            
            logger.info(f"User {user_id} repaid {amount} coins on loan")
            return True, repayment_info
            
        except Exception as e:
            logger.error(f"Error processing loan repayment for user {user_id}: {e}")
            return False, {'error': str(e)}
    
    async def collect_passive_income(self, user_id: int) -> Tuple[bool, int]:
        """
        Collect accumulated passive income
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (success, income_collected)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                return False, 0
            
            passive_rate = economy_data.get('passive_income_rate', 0)
            if passive_rate <= 0:
                return False, 0
            
            last_collection = economy_data.get('last_passive_collection')
            now = datetime.utcnow()
            
            if last_collection:
                last_time = datetime.fromisoformat(last_collection)
                hours_elapsed = (now - last_time).total_seconds() / 3600
            else:
                hours_elapsed = 1  # First collection gets 1 hour
            
            # Cap at 24 hours to prevent abuse
            hours_elapsed = min(hours_elapsed, 24)
            
            income = int(passive_rate * hours_elapsed)
            if income <= 0:
                return False, 0
            
            # Apply prestige bonus
            final_income = await self.calculate_prestige_bonus(user_id, income)
            
            economy_data['pocket_balance'] += final_income
            economy_data['total_earned'] += final_income
            economy_data['last_passive_collection'] = now.isoformat()
            
            await self._add_transaction(economy_data, TransactionType.EARN_ACHIEVEMENT,
                                      final_income, f"Passive income ({hours_elapsed:.1f}h)")
            
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.info(f"User {user_id} collected {final_income} passive income")
            return True, final_income
            
        except Exception as e:
            logger.error(f"Error collecting passive income for user {user_id}: {e}")
            return False, 0
    
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

    # === PRESTIGE SYSTEM ===
    
    async def get_user_prestige(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's prestige data
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Prestige data or None if not found
        """
        try:
            return await self.db.get_user_data(user_id, 'prestige')
        except Exception as e:
            logger.error(f"Error getting user prestige {user_id}: {e}")
            return None
    
    async def check_prestige_eligibility(self, user_id: int) -> Tuple[bool, int, int]:
        """
        Check if user is eligible for prestige
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (eligible, next_prestige_level, requirement)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            prestige_data = await self.get_user_prestige(user_id)
            
            if not economy_data or not prestige_data:
                return False, 1, self.prestige_requirements[1]
            
            current_prestige = prestige_data.get('prestige_level', 0)
            total_earned = economy_data.get('total_earned', 0)
            next_level = current_prestige + 1
            
            if next_level not in self.prestige_requirements:
                return False, next_level, 0  # Max prestige reached
            
            requirement = self.prestige_requirements[next_level]
            return total_earned >= requirement, next_level, requirement
            
        except Exception as e:
            logger.error(f"Error checking prestige eligibility for user {user_id}: {e}")
            return False, 1, self.prestige_requirements[1]
    
    async def prestige_user(self, user_id: int, confirm: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        Prestige a user (reset progress for bonuses)
        
        Args:
            user_id: Discord user ID
            confirm: Confirmation that user wants to prestige
            
        Returns:
            Tuple of (success, prestige_info)
        """
        if not confirm:
            return False, {'error': 'Prestige requires confirmation'}
        
        try:
            # Check eligibility
            eligible, next_level, requirement = await self.check_prestige_eligibility(user_id)
            if not eligible:
                return False, {'error': 'Not eligible for prestige', 'requirement': requirement}
            
            economy_data = await self.get_user_economy(user_id)
            prestige_data = await self.get_user_prestige(user_id)
            
            if not economy_data or not prestige_data:
                return False, {'error': 'User data not found'}
            
            # Store pre-prestige stats
            old_prestige_level = prestige_data.get('prestige_level', 0)
            total_earned_before = economy_data.get('total_earned', 0)
            
            # Update prestige data
            prestige_data['prestige_level'] = next_level
            prestige_data['prestige_points'] += 1
            prestige_data['total_prestiges'] += 1
            prestige_data['prestige_multiplier'] = self.prestige_multipliers.get(next_level, 1.0)
            prestige_data['last_prestige_date'] = datetime.utcnow().isoformat()
            prestige_data['lifetime_earnings_before_prestige'] = total_earned_before
            
            # Reset economy progress but keep some items
            economy_data['pocket_balance'] = 1000  # Start with bonus money
            economy_data['bank_balance'] = 0
            economy_data['total_earned'] = 1000
            economy_data['total_spent'] = 0
            economy_data['total_gambled'] = 0
            economy_data['total_won'] = 0
            economy_data['gambling_streak'] = 0
            economy_data['total_crimes'] = 0
            economy_data['successful_crimes'] = 0
            economy_data['total_robs'] = 0
            economy_data['successful_robs'] = 0
            economy_data['total_work_sessions'] = 0
            economy_data['work_streak'] = 0
            
            # Clear transaction history
            economy_data['transaction_history'] = []
            
            # Add prestige transaction
            await self._add_transaction(economy_data, TransactionType.ADMIN_ADD,
                                      0, f"Prestige Level {next_level} Achieved!")
            
            # Save both datasets
            await self.db.save_user_data(user_id, 'prestige', prestige_data)
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.info(f"User {user_id} prestiged to level {next_level}")
            
            return True, {
                'new_prestige_level': next_level,
                'old_prestige_level': old_prestige_level,
                'prestige_multiplier': self.prestige_multipliers.get(next_level, 1.0),
                'starting_balance': 1000,
                'lifetime_earnings': total_earned_before
            }
            
        except Exception as e:
            logger.error(f"Error prestiging user {user_id}: {e}")
            return False, {'error': str(e)}
    
    async def calculate_prestige_bonus(self, user_id: int, base_amount: int) -> int:
        """
        Calculate amount with prestige bonus applied
        
        Args:
            user_id: Discord user ID
            base_amount: Base amount to apply bonus to
            
        Returns:
            Amount with prestige bonus
        """
        try:
            prestige_data = await self.get_user_prestige(user_id)
            if not prestige_data:
                return base_amount
            
            multiplier = prestige_data.get('prestige_multiplier', 1.0)
            return int(base_amount * multiplier)
            
        except Exception as e:
            logger.error(f"Error calculating prestige bonus for user {user_id}: {e}")
            return base_amount
    
    # === CRIME AND ROB SYSTEMS ===
    
    async def commit_crime(self, user_id: int, crime_type: str = "petty_theft") -> Tuple[bool, int, str, bool]:
        """
        Commit a crime for money with risk/reward mechanics
        
        Args:
            user_id: Discord user ID
            crime_type: Type of crime to commit
            
        Returns:
            Tuple of (success, money_change, description, caught)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                raise DatabaseError(f"Economy data not found for user {user_id}")
            
            # Calculate success rate with bonuses
            multipliers = await self.calculate_total_multipliers(user_id)
            crime_bonus = multipliers.get('crime_success', 0.0)
            success_rate = min(self.crime_base_success_rate + crime_bonus, 0.95)
            
            # Different crime types have different risks/rewards
            crime_configs = {
                "petty_theft": {"min": 200, "max": 800, "risk": 0.3, "description": "shoplifting"},
                "pickpocket": {"min": 100, "max": 500, "risk": 0.4, "description": "pickpocketing"},
                "burglary": {"min": 1000, "max": 5000, "risk": 0.6, "description": "breaking into a house"},
                "bank_heist": {"min": 10000, "max": 50000, "risk": 0.8, "description": "robbing a bank"},
                "cyber_crime": {"min": 5000, "max": 25000, "risk": 0.5, "description": "hacking systems"}
            }
            
            config = crime_configs.get(crime_type, crime_configs["petty_theft"])
            success = random.random() < (success_rate * (1 - config["risk"] * 0.5))
            
            if success:
                # Crime succeeded
                reward = random.randint(config["min"], config["max"])
                final_reward = await self.calculate_prestige_bonus(user_id, reward)
                
                economy_data['pocket_balance'] += final_reward
                economy_data['total_earned'] += final_reward
                economy_data['total_crimes'] += 1
                economy_data['successful_crimes'] += 1
                
                await self._add_transaction(economy_data, TransactionType.EARN_ACHIEVEMENT,
                                          final_reward, f"Successful {crime_type}")
                
                description = f"🎭 You successfully committed {config['description']} and earned {final_reward} coins!"
                
                await self.db.save_user_data(user_id, 'economy', economy_data)
                logger.info(f"User {user_id} successful crime: {crime_type}, earned {final_reward}")
                
                return True, final_reward, description, False
            else:
                # Crime failed
                loss = int(economy_data.get('pocket_balance', 0) * self.crime_failure_loss_rate)
                loss = min(loss, config["max"])  # Cap the loss
                
                economy_data['pocket_balance'] -= loss
                economy_data['total_spent'] += loss
                economy_data['total_crimes'] += 1
                
                await self._add_transaction(economy_data, TransactionType.SPEND_SHOP,
                                          -loss, f"Failed {crime_type} - caught!")
                
                description = f"🚔 You were caught {config['description']} and fined {loss} coins!"
                
                await self.db.save_user_data(user_id, 'economy', economy_data)
                logger.info(f"User {user_id} failed crime: {crime_type}, lost {loss}")
                
                return False, loss, description, True
                
        except Exception as e:
            logger.error(f"Error processing crime for user {user_id}: {e}")
            return False, 0, "Crime attempt failed", False
    
    async def rob_user(self, robber_id: int, target_id: int) -> Tuple[bool, int, str]:
        """
        Rob another user
        
        Args:
            robber_id: Discord user ID of robber
            target_id: Discord user ID of target
            
        Returns:
            Tuple of (success, money_stolen, description)
        """
        if robber_id == target_id:
            return False, 0, "You can't rob yourself!"
        
        try:
            robber_economy = await self.get_user_economy(robber_id)
            target_economy = await self.get_user_economy(target_id)
            
            if not robber_economy or not target_economy:
                return False, 0, "User data not found"
            
            target_balance = target_economy.get('pocket_balance', 0)
            if target_balance < self.rob_min_amount:
                return False, 0, f"Target doesn't have enough money to rob (minimum {self.rob_min_amount} coins)"
            
            # Calculate success rates with bonuses
            robber_multipliers = await self.calculate_total_multipliers(robber_id)
            target_multipliers = await self.calculate_total_multipliers(target_id)
            
            rob_success_bonus = robber_multipliers.get('crime_success', 0.0)
            target_protection = target_multipliers.get('rob_protection', 0.0)
            
            final_success_rate = max(0.05, self.rob_base_success_rate + rob_success_bonus - target_protection)
            success = random.random() < final_success_rate
            
            if success:
                # Rob succeeded
                max_steal = int(target_balance * self.rob_max_percentage)
                stolen = random.randint(self.rob_min_amount, max_steal)
                
                # Transfer money
                target_economy['pocket_balance'] -= stolen
                target_economy['times_robbed'] += 1
                
                robber_economy['pocket_balance'] += stolen
                robber_economy['total_earned'] += stolen
                robber_economy['total_robs'] += 1
                robber_economy['successful_robs'] += 1
                
                # Add transactions
                await self._add_transaction(target_economy, TransactionType.ADMIN_REMOVE,
                                          -stolen, f"Robbed by user {robber_id}")
                await self._add_transaction(robber_economy, TransactionType.TRANSFER_RECEIVE,
                                          stolen, f"Robbed user {target_id}")
                
                # Save both users
                await self.db.save_user_data(target_id, 'economy', target_economy)
                await self.db.save_user_data(robber_id, 'economy', robber_economy)
                
                description = f"💰 You successfully robbed {stolen} coins!"
                logger.info(f"User {robber_id} robbed {stolen} from user {target_id}")
                
                return True, stolen, description
            else:
                # Rob failed
                penalty = random.randint(100, 1000)
                penalty = min(penalty, robber_economy.get('pocket_balance', 0))
                
                robber_economy['pocket_balance'] -= penalty
                robber_economy['total_spent'] += penalty
                robber_economy['total_robs'] += 1
                
                await self._add_transaction(robber_economy, TransactionType.SPEND_SHOP,
                                          -penalty, f"Failed rob attempt on user {target_id}")
                
                await self.db.save_user_data(robber_id, 'economy', robber_economy)
                
                description = f"🚔 Your rob attempt failed and you were fined {penalty} coins!"
                logger.info(f"User {robber_id} failed to rob user {target_id}, lost {penalty}")
                
                return False, penalty, description
                
        except Exception as e:
            logger.error(f"Error processing rob: {e}")
            return False, 0, "Rob attempt failed"
    
    # === TAX SYSTEM ===
    
    async def calculate_tax_bracket(self, total_balance: int) -> Dict[str, Any]:
        """
        Calculate tax bracket and rate for a given balance
        
        Args:
            total_balance: Total user balance
            
        Returns:
            Tax bracket information
        """
        for bracket, info in self.tax_brackets.items():
            if info['min'] <= total_balance <= info['max']:
                return {
                    'bracket': bracket,
                    'rate': info['rate'],
                    'min': info['min'],
                    'max': info['max']
                }
        return self.tax_brackets[5]  # Highest bracket as default
    
    async def apply_tax(self, user_id: int, income: int) -> Tuple[int, int]:
        """
        Apply tax to income and deduct from user balance
        
        Args:
            user_id: Discord user ID
            income: Income to tax
            
        Returns:
            Tuple of (tax_amount, after_tax_income)
        """
        try:
            economy_data = await self.get_user_economy(user_id)
            if not economy_data:
                return 0, income
            
            total_balance = economy_data.get('pocket_balance', 0) + economy_data.get('bank_balance', 0)
            tax_info = await self.calculate_tax_bracket(total_balance)
            
            tax_rate = tax_info['rate']
            tax_amount = int(income * tax_rate)
            after_tax_income = income - tax_amount
            
            if tax_amount > 0:
                # Deduct tax from pocket balance
                economy_data['pocket_balance'] -= tax_amount
                economy_data['total_taxes_paid'] += tax_amount
                economy_data['tax_bracket'] = tax_info['bracket']
                
                await self._add_transaction(economy_data, TransactionType.ADMIN_REMOVE,
                                          -tax_amount, f"Tax payment ({tax_rate*100:.1f}%)")
                
                await self.db.save_user_data(user_id, 'economy', economy_data)
                
                logger.debug(f"Applied {tax_amount} tax to user {user_id} (rate: {tax_rate*100:.1f}%)")
            
            return tax_amount, after_tax_income
            
        except Exception as e:
            logger.error(f"Error applying tax for user {user_id}: {e}")
            return 0, income
    
    # === ITEM EFFECTS SYSTEM ===
    
    async def get_user_active_effects(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's currently active item effects
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Active effects data or None if not found
        """
        try:
            effects_data = await self.db.get_user_data(user_id, 'active_effects')
            
            if effects_data:
                # Clean up expired effects
                effects_data = await self._clean_expired_effects(user_id, effects_data)
            
            return effects_data
            
        except Exception as e:
            logger.error(f"Error getting user active effects {user_id}: {e}")
            return None
    
    async def _clean_expired_effects(self, user_id: int, effects_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove expired temporary effects
        
        Args:
            user_id: Discord user ID
            effects_data: Current effects data
            
        Returns:
            Updated effects data
        """
        now = datetime.utcnow()
        temp_effects = effects_data.get('temporary_effects', [])
        active_temp_effects = []
        
        for effect in temp_effects:
            if effect.get('duration') is None:
                active_temp_effects.append(effect)
                continue
            
            started_at = datetime.fromisoformat(effect.get('started_at', now.isoformat()))
            duration = effect.get('duration', 0)
            
            if (now - started_at).total_seconds() < duration:
                active_temp_effects.append(effect)
        
        effects_data['temporary_effects'] = active_temp_effects
        effects_data['last_update'] = now.isoformat()
        
        # Save cleaned data
        await self.db.save_user_data(user_id, 'active_effects', effects_data)
        return effects_data
    
    async def apply_item_effects(self, user_id: int, item_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Apply effects from using an item
        
        Args:
            user_id: Discord user ID
            item_id: ID of the item used
            
        Returns:
            Tuple of (success, effects_applied)
        """
        try:
            if item_id not in DEFAULT_ITEMS:
                return False, {'error': 'Item not found'}
            
            item_data = DEFAULT_ITEMS[item_id]
            effects = item_data.get('effects', {})
            
            if not effects:
                return True, {'message': 'Item has no effects'}
            
            # Get current effects
            active_effects = await self.get_user_active_effects(user_id)
            if not active_effects:
                active_effects = {
                    'user_id': user_id,
                    'temporary_effects': [],
                    'permanent_effects': [],
                    'last_update': datetime.utcnow().isoformat()
                }
            
            applied_effects = {}
            
            # Process each effect
            for effect_type, value in effects.items():
                if effect_type == 'duration':
                    continue  # Skip duration, it's handled per effect
                
                duration = effects.get('duration')
                
                # Create effect object
                effect_obj = {
                    'effect_type': effect_type,
                    'value': value,
                    'duration': duration,
                    'started_at': datetime.utcnow().isoformat()
                }
                
                if duration:
                    active_effects['temporary_effects'].append(effect_obj)
                else:
                    active_effects['permanent_effects'].append(effect_obj)
                
                applied_effects[effect_type] = value
            
            # Save updated effects
            await self.db.save_user_data(user_id, 'active_effects', active_effects)
            
            logger.info(f"Applied effects from {item_id} to user {user_id}: {applied_effects}")
            return True, applied_effects
            
        except Exception as e:
            logger.error(f"Error applying item effects for user {user_id}: {e}")
            return False, {'error': str(e)}
    
    async def calculate_total_multipliers(self, user_id: int) -> Dict[str, float]:
        """
        Calculate total multipliers from all sources (prestige + items + inventory)
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary of multiplier types and values
        """
        try:
            multipliers = {
                'money_multiplier': 1.0,
                'exp_multiplier': 1.0,
                'work_bonus': 0.0,
                'gambling_luck': 0.0,
                'crime_success': 0.0,
                'rob_protection': 0.0,
                'rob_success': 0.0
            }
            
            # Add prestige multipliers
            prestige_data = await self.get_user_prestige(user_id)
            if prestige_data:
                prestige_mult = prestige_data.get('prestige_multiplier', 1.0)
                multipliers['money_multiplier'] *= prestige_mult
                multipliers['exp_multiplier'] *= prestige_mult
            
            # Add item effect multipliers from active effects
            active_effects = await self.get_user_active_effects(user_id)
            if active_effects:
                all_effects = (active_effects.get('temporary_effects', []) + 
                             active_effects.get('permanent_effects', []))
                
                for effect in all_effects:
                    effect_type = effect.get('effect_type')
                    value = effect.get('value', 0)
                    
                    if effect_type in multipliers:
                        if effect_type.endswith('_multiplier'):
                            multipliers[effect_type] *= (1 + value)
                        else:
                            multipliers[effect_type] += value
            
            # Add equipped item bonuses from inventory (tools, weapons, armor)
            try:
                from .inventory_manager import InventoryManager
                inventory_manager = InventoryManager(self.db)
                inventory_data = await inventory_manager.get_user_inventory(user_id)
                
                if inventory_data:
                    items = inventory_data.get('items', {})
                    
                    for item_id, item_data in items.items():
                        # Only count non-consumable items as "equipped"
                        if not item_data.get('consumable', False):
                            if item_id in DEFAULT_ITEMS:
                                item_effects = DEFAULT_ITEMS[item_id].get('effects', {})
                                
                                for effect_type, value in item_effects.items():
                                    if effect_type in multipliers and effect_type != 'duration':
                                        if effect_type.endswith('_multiplier'):
                                            multipliers[effect_type] *= (1 + value)
                                        else:
                                            multipliers[effect_type] += value
                
            except ImportError:
                # Inventory manager not available, skip inventory bonuses
                pass
            
            return multipliers
            
        except Exception as e:
            logger.error(f"Error calculating multipliers for user {user_id}: {e}")
            return {'money_multiplier': 1.0, 'exp_multiplier': 1.0, 'work_bonus': 0.0,
                   'gambling_luck': 0.0, 'crime_success': 0.0, 'rob_protection': 0.0, 'rob_success': 0.0}