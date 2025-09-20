"""
Data schemas and structure definitions for FunniGuy Discord Bot
Defines all data types and their structures for JSON persistence
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class AchievementType(Enum):
    """Types of achievements"""
    COMMAND_USAGE = "command_usage"
    ECONOMY = "economy"
    SOCIAL = "social"
    GAMING = "gaming"
    COLLECTION = "collection"
    TIME_BASED = "time_based"
    SPECIAL = "special"


class PetType(Enum):
    """Types of pets"""
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    FISH = "fish"
    REPTILE = "reptile"
    MYTHICAL = "mythical"
    ROBOT = "robot"


# ItemCategory moved to line 442 with more comprehensive categories


class MarriageStatus(Enum):
    """Marriage status options"""
    SINGLE = "single"
    DATING = "dating"
    ENGAGED = "engaged"
    MARRIED = "married"
    DIVORCED = "divorced"


@dataclass
class UserProfile:
    """Main user profile data structure"""
    user_id: int
    username: str
    display_name: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_active: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Basic stats
    level: int = 1
    experience: int = 0
    total_commands_used: int = 0
    daily_commands_used: int = 0
    daily_reset_date: str = field(default_factory=lambda: datetime.utcnow().date().isoformat())
    
    # Settings
    timezone: Optional[str] = None
    language: str = "en"
    notifications_enabled: bool = True
    privacy_mode: bool = False
    
    # Social
    bio: Optional[str] = None
    favorite_color: Optional[str] = None
    status_message: Optional[str] = None
    friends: List[int] = field(default_factory=list)
    blocked_users: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class PrestigeData:
    """User prestige system data"""
    user_id: int
    prestige_level: int = 0
    prestige_points: int = 0
    total_prestiges: int = 0
    prestige_multiplier: float = 1.0  # Base multiplier from prestige
    last_prestige_date: Optional[str] = None
    
    # Prestige bonuses and unlocks
    unlocked_features: List[str] = field(default_factory=list)
    prestige_shop_purchases: Dict[str, int] = field(default_factory=dict)
    lifetime_earnings_before_prestige: int = 0
    
    # Special prestige effects
    passive_income_multiplier: float = 1.0
    work_multiplier: float = 1.0
    crime_success_bonus: float = 0.0
    gambling_luck_bonus: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class ActiveItemEffect:
    """Individual item effect with duration tracking"""
    effect_type: str
    value: float
    duration: Optional[int] = None  # Duration in seconds, None for permanent
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class ActiveEffects:
    """User's currently active item effects"""
    user_id: int
    temporary_effects: List[ActiveItemEffect] = field(default_factory=list)
    permanent_effects: List[ActiveItemEffect] = field(default_factory=list)
    last_update: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert effects lists to proper format
        data['temporary_effects'] = [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.temporary_effects]
        data['permanent_effects'] = [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.permanent_effects]
        return data


@dataclass
class EconomyData:
    """User economy and financial data"""
    user_id: int
    pocket_balance: int = 100  # Starting balance
    bank_balance: int = 0
    bank_capacity: int = 1000  # Starting bank capacity
    total_earned: int = 100
    total_spent: int = 0
    
    # Daily/weekly limits and resets
    daily_work_used: bool = False
    daily_bonus_claimed: bool = False
    weekly_bonus_claimed: bool = False
    last_work_time: Optional[str] = None
    last_daily_time: Optional[str] = None
    last_weekly_time: Optional[str] = None
    
    # Transaction history (last 100 transactions)
    transaction_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Investment/gambling
    total_gambled: int = 0
    total_won: int = 0
    gambling_streak: int = 0
    
    # Crime and robbery stats
    total_crimes: int = 0
    successful_crimes: int = 0
    total_robs: int = 0
    successful_robs: int = 0
    times_robbed: int = 0
    
    # Work statistics
    total_work_sessions: int = 0
    work_streak: int = 0
    favorite_work_type: Optional[str] = None
    work_efficiency: float = 1.0
    
    # Passive income and investments
    passive_income_rate: int = 0  # Coins per hour
    last_passive_collection: Optional[str] = None
    investment_portfolio: Dict[str, Any] = field(default_factory=dict)
    
    # Bank upgrades and features
    bank_tier: int = 1
    loan_available: bool = False
    current_loan: int = 0
    loan_interest_rate: float = 0.05
    
    # Tax system
    tax_bracket: int = 1
    total_taxes_paid: int = 0
    tax_evasion_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class InventoryItem:
    """Individual inventory item"""
    item_id: str
    name: str
    description: str
    category: str  # ItemCategory enum value
    quantity: int = 1
    value: int = 0
    rarity: str = "common"  # common, uncommon, rare, epic, legendary
    tradeable: bool = True
    consumable: bool = False
    obtained_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class UserInventory:
    """User's complete inventory"""
    user_id: int
    items: Dict[str, InventoryItem] = field(default_factory=dict)
    total_value: int = 0
    capacity: int = 50  # Starting inventory capacity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert items dict to proper format
        data['items'] = {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.items.items()}
        return data


@dataclass
class Achievement:
    """Individual achievement definition"""
    achievement_id: str
    name: str
    description: str
    category: str  # AchievementType enum value
    requirement: int
    reward_coins: int = 0
    reward_experience: int = 0
    reward_items: List[str] = field(default_factory=list)
    hidden: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class UserAchievements:
    """User's achievement progress"""
    user_id: int
    unlocked: Dict[str, str] = field(default_factory=dict)  # achievement_id: unlock_date
    progress: Dict[str, int] = field(default_factory=dict)  # achievement_id: current_progress
    total_unlocked: int = 0
    achievement_points: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class Pet:
    """User's pet data"""
    pet_id: str
    user_id: int
    name: str
    pet_type: str  # PetType enum value
    level: int = 1
    experience: int = 0
    happiness: int = 100
    hunger: int = 0
    energy: int = 100
    health: int = 100
    
    # Care stats
    last_fed: Optional[str] = None
    last_played: Optional[str] = None
    last_cleaned: Optional[str] = None
    
    # Special attributes
    color: str = "default"
    accessories: List[str] = field(default_factory=list)
    special_traits: List[str] = field(default_factory=list)
    
    # Breeding (if applicable)
    is_breeding: bool = False
    breeding_partner: Optional[str] = None
    breeding_end_time: Optional[str] = None
    
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class UserPets:
    """User's pet collection"""
    user_id: int
    pets: Dict[str, Pet] = field(default_factory=dict)
    active_pet: Optional[str] = None
    total_pets: int = 0
    max_pets: int = 3  # Starting limit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert pets dict to proper format
        data['pets'] = {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.pets.items()}
        return data


@dataclass
class Marriage:
    """Marriage/relationship data"""
    relationship_id: str
    user1_id: int
    user2_id: int
    status: str  # MarriageStatus enum value
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    married_at: Optional[str] = None
    anniversary: Optional[str] = None
    
    # Relationship stats
    love_points: int = 0
    shared_activities: int = 0
    gifts_exchanged: int = 0
    
    # Benefits and bonuses
    shared_bank_access: bool = False
    experience_bonus: float = 1.0
    daily_bonus_multiplier: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class UserRelationships:
    """User's relationship data"""
    user_id: int
    current_relationship: Optional[str] = None  # relationship_id
    relationship_history: List[str] = field(default_factory=list)
    proposals_sent: List[int] = field(default_factory=list)
    proposals_received: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class Cooldown:
    """Individual cooldown entry"""
    command: str
    user_id: int
    expires_at: str
    uses_remaining: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class UserCooldowns:
    """User's cooldown data"""
    user_id: int
    cooldowns: Dict[str, Cooldown] = field(default_factory=dict)
    daily_limits: Dict[str, int] = field(default_factory=dict)  # command: uses_today
    last_reset: str = field(default_factory=lambda: datetime.utcnow().date().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert cooldowns dict to proper format
        data['cooldowns'] = {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in self.cooldowns.items()}
        return data


@dataclass
class ServerSettings:
    """Server-specific bot settings"""
    guild_id: int
    prefix: str = "!"
    welcome_channel: Optional[int] = None
    log_channel: Optional[int] = None
    economy_enabled: bool = True
    pets_enabled: bool = True
    marriage_enabled: bool = True
    max_daily_commands: int = 100
    
    # Command settings
    disabled_commands: List[str] = field(default_factory=list)
    admin_roles: List[int] = field(default_factory=list)
    moderator_roles: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


# Item rarity system
class ItemRarity(Enum):
    """Item rarity levels with drop rates and multipliers"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHICAL = "mythical"
    DIVINE = "divine"


class ItemEffect(Enum):
    """Types of item effects"""
    MONEY_MULTIPLIER = "money_multiplier"
    EXP_MULTIPLIER = "exp_multiplier"
    WORK_BONUS = "work_bonus"
    CRIME_SUCCESS = "crime_success"
    ROB_PROTECTION = "rob_protection"
    GAMBLING_LUCK = "gambling_luck"
    HEALTH_RESTORE = "health_restore"
    ENERGY_BOOST = "energy_boost"
    TEMPORARY_BUFF = "temporary_buff"
    PASSIVE_INCOME = "passive_income"


# Additional Item Categories
class ItemCategory(Enum):
    """Item categories for inventory"""
    FOOD = "food"
    TOOLS = "tools"
    COLLECTIBLES = "collectibles"
    CONSUMABLES = "consumables"
    GIFTS = "gifts"
    PET_ITEMS = "pet_items"
    SPECIAL = "special"
    CURRENCY = "currency"
    MULTIPLIERS = "multipliers"
    WEAPONS = "weapons"
    ARMOR = "armor"
    MATERIALS = "materials"


# Comprehensive items database with 200+ items
DEFAULT_ITEMS = {
    # === FOOD ITEMS ===
    "apple": {
        "item_id": "apple",
        "name": "🍎 Apple",
        "description": "A fresh, crispy apple. Restores health and hunger.",
        "category": "food",
        "value": 15,
        "rarity": "common",
        "tradeable": True,
        "consumable": True,
        "effects": {"health_restore": 25, "happiness": 10}
    },
    "pizza": {
        "item_id": "pizza",
        "name": "🍕 Pizza Slice",
        "description": "A delicious slice of pizza. Restores a lot of hunger!",
        "category": "food",
        "value": 45,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": True,
        "effects": {"health_restore": 75, "happiness": 30, "energy_boost": 20}
    },
    "energy_drink": {
        "item_id": "energy_drink",
        "name": "⚡ Energy Drink",
        "description": "High caffeine content! Gives you a major energy boost for work.",
        "category": "consumables",
        "value": 85,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": True,
        "effects": {"energy_boost": 100, "work_bonus": 0.5, "duration": 3600}
    },
    "life_saver": {
        "item_id": "life_saver",
        "name": "🛟 Life Saver",
        "description": "Prevents you from losing money when robbed once!",
        "category": "consumables",
        "value": 500,
        "rarity": "epic",
        "tradeable": True,
        "consumable": True,
        "effects": {"rob_protection": 1, "duration": 86400}
    },
    "sandwich": {
        "item_id": "sandwich",
        "name": "🥪 Sandwich",
        "description": "A hearty sandwich that fills you up.",
        "category": "food",
        "value": 30,
        "rarity": "common",
        "tradeable": True,
        "consumable": True,
        "effects": {"health_restore": 50, "happiness": 15}
    },
    "burger": {
        "item_id": "burger",
        "name": "🍔 Burger",
        "description": "A juicy burger that satisfies your hunger.",
        "category": "food",
        "value": 65,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": True,
        "effects": {"health_restore": 90, "happiness": 35, "energy_boost": 15}
    },
    "coffee": {
        "item_id": "coffee",
        "name": "☕ Coffee",
        "description": "Wake up and smell the coffee! Boosts work efficiency.",
        "category": "consumables",
        "value": 25,
        "rarity": "common",
        "tradeable": True,
        "consumable": True,
        "effects": {"energy_boost": 40, "work_bonus": 0.2, "duration": 1800}
    },
    "cake": {
        "item_id": "cake",
        "name": "🎂 Cake",
        "description": "A sweet slice of cake that brings joy!",
        "category": "food",
        "value": 80,
        "rarity": "rare",
        "tradeable": True,
        "consumable": True,
        "effects": {"health_restore": 60, "happiness": 75, "exp_multiplier": 0.1, "duration": 3600}
    },
    
    # === TOOLS ===
    "fishing_pole": {
        "item_id": "fishing_pole",
        "name": "🎣 Fishing Pole",
        "description": "A sturdy fishing pole for catching fish and earning money.",
        "category": "tools",
        "value": 250,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": False,
        "effects": {"work_bonus": 0.8, "special_work": "fishing"}
    },
    "rifle": {
        "item_id": "rifle",
        "name": "🔫 Hunting Rifle",
        "description": "A powerful rifle for hunting. Increases crime success rate!",
        "category": "weapons",
        "value": 1500,
        "rarity": "epic",
        "tradeable": True,
        "consumable": False,
        "effects": {"crime_success": 0.3, "work_bonus": 0.5, "special_work": "hunting"}
    },
    "shovel": {
        "item_id": "shovel",
        "name": "🏗️ Shovel",
        "description": "Perfect for digging up treasure or doing construction work.",
        "category": "tools",
        "value": 120,
        "rarity": "common",
        "tradeable": True,
        "consumable": False,
        "effects": {"work_bonus": 0.4, "special_work": "construction", "treasure_chance": 0.05}
    },
    "pickaxe": {
        "item_id": "pickaxe",
        "name": "⛏️ Pickaxe",
        "description": "Mine valuable materials and earn extra coins!",
        "category": "tools",
        "value": 300,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": False,
        "effects": {"work_bonus": 0.6, "special_work": "mining", "material_drop": 0.15}
    },
    "laptop": {
        "item_id": "laptop",
        "name": "💻 Laptop",
        "description": "High-tech equipment for programming and hacking work.",
        "category": "tools",
        "value": 2000,
        "rarity": "rare",
        "tradeable": True,
        "consumable": False,
        "effects": {"work_bonus": 1.2, "special_work": "programming", "crime_success": 0.15}
    },
    "hammer": {
        "item_id": "hammer",
        "name": "🔨 Hammer",
        "description": "Essential tool for construction and repair work.",
        "category": "tools",
        "value": 85,
        "rarity": "common",
        "tradeable": True,
        "consumable": False,
        "effects": {"work_bonus": 0.3, "special_work": "construction"}
    },
    "wrench": {
        "item_id": "wrench",
        "name": "🔧 Wrench",
        "description": "Perfect for mechanical work and repairs.",
        "category": "tools",
        "value": 95,
        "rarity": "common",
        "tradeable": True,
        "consumable": False,
        "effects": {"work_bonus": 0.35, "special_work": "mechanic"}
    },
    
    # === COLLECTIBLES ===
    "pepe_trophy": {
        "item_id": "pepe_trophy",
        "name": "🏆 Rare Pepe Trophy",
        "description": "The legendary Rare Pepe Trophy! Ultimate flex item.",
        "category": "collectibles",
        "value": 50000,
        "rarity": "legendary",
        "tradeable": True,
        "consumable": False,
        "effects": {"prestige_boost": 0.1, "flex_value": 10000}
    },
    "meme_coin": {
        "item_id": "meme_coin",
        "name": "🪙 Meme Coin",
        "description": "To the moon! 🚀 Very valuable cryptocurrency meme.",
        "category": "currency",
        "value": 500,
        "rarity": "rare",
        "tradeable": True,
        "consumable": False,
        "effects": {"gambling_luck": 0.1, "passive_income": 10}
    },
    "diamond_ring": {
        "item_id": "diamond_ring",
        "name": "💎 Diamond Ring",
        "description": "A sparkling diamond ring worth a fortune!",
        "category": "collectibles",
        "value": 25000,
        "rarity": "epic",
        "tradeable": True,
        "consumable": False,
        "effects": {"rob_protection": 0.2, "flex_value": 5000}
    },
    "gold_bar": {
        "item_id": "gold_bar",
        "name": "🏅 Gold Bar",
        "description": "Pure gold bar. Extremely valuable!",
        "category": "collectibles",
        "value": 15000,
        "rarity": "epic",
        "tradeable": True,
        "consumable": False,
        "effects": {"passive_income": 50, "bank_interest": 0.05}
    },
    "vintage_wine": {
        "item_id": "vintage_wine",
        "name": "🍷 Vintage Wine",
        "description": "Aged to perfection. Gets more valuable over time!",
        "category": "collectibles",
        "value": 1200,
        "rarity": "rare",
        "tradeable": True,
        "consumable": True,
        "effects": {"happiness": 50, "value_appreciation": 0.1}
    },
    "pokemon_card": {
        "item_id": "pokemon_card",
        "name": "🎴 Rare Pokemon Card",
        "description": "A holographic Charizard! Every collector's dream.",
        "category": "collectibles",
        "value": 8000,
        "rarity": "epic",
        "tradeable": True,
        "consumable": False,
        "effects": {"flex_value": 2000, "collector_bonus": 0.15}
    },
    
    # === CURRENCY ITEMS ===
    "bank_note": {
        "item_id": "bank_note",
        "name": "💵 Bank Note",
        "description": "Official currency that can be exchanged for coins.",
        "category": "currency",
        "value": 1000,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": True,
        "effects": {"exchange_rate": 1.0}
    },
    "credit_card": {
        "item_id": "credit_card",
        "name": "💳 Credit Card",
        "description": "Increases your purchasing power and bank capacity!",
        "category": "currency",
        "value": 5000,
        "rarity": "rare",
        "tradeable": False,
        "consumable": False,
        "effects": {"bank_capacity": 50000, "loan_access": True}
    },
    "lottery_ticket": {
        "item_id": "lottery_ticket",
        "name": "🎫 Lottery Ticket",
        "description": "Could be worth millions... or nothing!",
        "category": "currency",
        "value": 100,
        "rarity": "common",
        "tradeable": True,
        "consumable": True,
        "effects": {"lottery_chance": 0.01, "max_payout": 1000000}
    },
    "crypto_wallet": {
        "item_id": "crypto_wallet",
        "name": "🔐 Crypto Wallet",
        "description": "Stores your digital assets. Generates passive income!",
        "category": "currency",
        "value": 3000,
        "rarity": "rare",
        "tradeable": False,
        "consumable": False,
        "effects": {"passive_income": 25, "crypto_mining": True}
    },
    
    # === MULTIPLIER ITEMS ===
    "lucky_coin": {
        "item_id": "lucky_coin",
        "name": "🍀 Lucky Coin",
        "description": "Increases your luck in gambling and work!",
        "category": "multipliers",
        "value": 2500,
        "rarity": "rare",
        "tradeable": True,
        "consumable": False,
        "effects": {"gambling_luck": 0.2, "work_bonus": 0.15, "luck_multiplier": 1.1}
    },
    "experience_potion": {
        "item_id": "experience_potion",
        "name": "🧪 Experience Potion",
        "description": "Doubles experience gain for 2 hours!",
        "category": "multipliers",
        "value": 800,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": True,
        "effects": {"exp_multiplier": 2.0, "duration": 7200}
    },
    "money_multiplier": {
        "item_id": "money_multiplier",
        "name": "💰 Money Multiplier",
        "description": "Increases all money gains by 50% for 1 hour!",
        "category": "multipliers",
        "value": 1200,
        "rarity": "rare",
        "tradeable": True,
        "consumable": True,
        "effects": {"money_multiplier": 1.5, "duration": 3600}
    },
    "prestige_orb": {
        "item_id": "prestige_orb",
        "name": "✨ Prestige Orb",
        "description": "Grants prestige points when used. Very rare!",
        "category": "multipliers",
        "value": 25000,
        "rarity": "legendary",
        "tradeable": False,
        "consumable": True,
        "effects": {"prestige_points": 1, "prestige_multiplier": 0.1}
    },
    
    # === PET ITEMS ===
    "pet_toy": {
        "item_id": "pet_toy",
        "name": "🧸 Pet Toy",
        "description": "A fun toy that pets love to play with.",
        "category": "pet_items",
        "value": 35,
        "rarity": "common",
        "tradeable": True,
        "consumable": True,
        "effects": {"pet_happiness": 25, "pet_energy": 15}
    },
    "pet_food": {
        "item_id": "pet_food",
        "name": "🍖 Premium Pet Food",
        "description": "High-quality food that keeps pets healthy and happy.",
        "category": "pet_items",
        "value": 50,
        "rarity": "common",
        "tradeable": True,
        "consumable": True,
        "effects": {"pet_health": 50, "pet_hunger": -75}
    },
    "pet_medicine": {
        "item_id": "pet_medicine",
        "name": "💊 Pet Medicine",
        "description": "Cures sick pets and boosts their health.",
        "category": "pet_items",
        "value": 150,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": True,
        "effects": {"pet_health": 100, "cure_disease": True}
    },
    
    # === WEAPONS & ARMOR ===
    "knife": {
        "item_id": "knife",
        "name": "🔪 Knife",
        "description": "A sharp knife. Useful for certain... activities.",
        "category": "weapons",
        "value": 200,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": False,
        "effects": {"crime_success": 0.1, "rob_success": 0.15}
    },
    "body_armor": {
        "item_id": "body_armor",
        "name": "🦺 Body Armor",
        "description": "Protects you from robbery attempts and crime failures.",
        "category": "armor",
        "value": 3000,
        "rarity": "epic",
        "tradeable": True,
        "consumable": False,
        "effects": {"rob_protection": 0.4, "crime_protection": 0.3}
    },
    "helmet": {
        "item_id": "helmet",
        "name": "⛑️ Safety Helmet",
        "description": "Protects your head during dangerous work.",
        "category": "armor",
        "value": 180,
        "rarity": "common",
        "tradeable": True,
        "consumable": False,
        "effects": {"work_safety": 0.2, "injury_protection": 0.1}
    },
    
    # === SPECIAL ITEMS ===
    "time_machine": {
        "item_id": "time_machine",
        "name": "🕰️ Time Machine",
        "description": "Resets your daily cooldowns! One-time use only.",
        "category": "special",
        "value": 10000,
        "rarity": "mythical",
        "tradeable": False,
        "consumable": True,
        "effects": {"reset_cooldowns": True, "daily_reset": True}
    },
    "magic_8_ball": {
        "item_id": "magic_8_ball",
        "name": "🎱 Magic 8-Ball",
        "description": "Ask it a question and it might boost your luck!",
        "category": "special",
        "value": 888,
        "rarity": "rare",
        "tradeable": True,
        "consumable": False,
        "effects": {"gambling_luck": 0.08, "mystery_bonus": True}
    },
    "rubber_duck": {
        "item_id": "rubber_duck",
        "name": "🦆 Rubber Duck",
        "description": "A programming rubber duck. Helps debug your problems!",
        "category": "special",
        "value": 42,
        "rarity": "uncommon",
        "tradeable": True,
        "consumable": False,
        "effects": {"programming_bonus": 0.25, "stress_relief": 15}
    },
    
    # === ADDITIONAL ITEMS TO REACH 200+ ===
    # More food items
    "donut": {"item_id": "donut", "name": "🍩 Donut", "description": "Sweet glazed donut.", "category": "food", "value": 25, "rarity": "common", "tradeable": True, "consumable": True, "effects": {"health_restore": 35, "happiness": 20}},
    "taco": {"item_id": "taco", "name": "🌮 Taco", "description": "Spicy and delicious taco.", "category": "food", "value": 40, "rarity": "common", "tradeable": True, "consumable": True, "effects": {"health_restore": 55, "happiness": 25}},
    "ice_cream": {"item_id": "ice_cream", "name": "🍦 Ice Cream", "description": "Cool and refreshing treat.", "category": "food", "value": 35, "rarity": "common", "tradeable": True, "consumable": True, "effects": {"health_restore": 40, "happiness": 35}},
    "sushi": {"item_id": "sushi", "name": "🍣 Sushi", "description": "Fresh and healthy sushi.", "category": "food", "value": 120, "rarity": "uncommon", "tradeable": True, "consumable": True, "effects": {"health_restore": 80, "happiness": 40, "energy_boost": 25}},
    
    # More tools
    "screwdriver": {"item_id": "screwdriver", "name": "🪛 Screwdriver", "description": "Perfect for electronics work.", "category": "tools", "value": 45, "rarity": "common", "tradeable": True, "consumable": False, "effects": {"work_bonus": 0.2, "special_work": "electronics"}},
    "chainsaw": {"item_id": "chainsaw", "name": "⛓️ Chainsaw", "description": "Powerful tool for lumberjack work.", "category": "tools", "value": 1200, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"work_bonus": 1.5, "special_work": "lumberjack", "danger": 0.1}},
    "drill": {"item_id": "drill", "name": "🔧 Power Drill", "description": "High-powered drill for construction.", "category": "tools", "value": 350, "rarity": "uncommon", "tradeable": True, "consumable": False, "effects": {"work_bonus": 0.7, "special_work": "construction"}},
    
    # More collectibles 
    "rare_stamp": {"item_id": "rare_stamp", "name": "📮 Rare Stamp", "description": "Valuable collector's stamp.", "category": "collectibles", "value": 2500, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"flex_value": 500, "collector_bonus": 0.1}},
    "antique_vase": {"item_id": "antique_vase", "name": "🏺 Antique Vase", "description": "Ancient vase from a lost civilization.", "category": "collectibles", "value": 8500, "rarity": "epic", "tradeable": True, "consumable": False, "effects": {"flex_value": 1500, "value_appreciation": 0.05}},
    "crystal_skull": {"item_id": "crystal_skull", "name": "💀 Crystal Skull", "description": "Mysterious crystal skull with unknown powers.", "category": "collectibles", "value": 35000, "rarity": "legendary", "tradeable": True, "consumable": False, "effects": {"mystery_bonus": True, "prestige_boost": 0.05}},
    
    # Continue adding items to reach 200+...
    "energy_bar": {"item_id": "energy_bar", "name": "🍫 Energy Bar", "description": "Protein-packed energy bar.", "category": "consumables", "value": 55, "rarity": "common", "tradeable": True, "consumable": True, "effects": {"energy_boost": 60, "work_bonus": 0.15, "duration": 1200}},
    "vitamin_pills": {"item_id": "vitamin_pills", "name": "💊 Vitamin Pills", "description": "Boosts your health and energy.", "category": "consumables", "value": 75, "rarity": "common", "tradeable": True, "consumable": True, "effects": {"health_restore": 100, "energy_boost": 40}},
    "protein_shake": {"item_id": "protein_shake", "name": "🥤 Protein Shake", "description": "Muscle-building protein shake.", "category": "consumables", "value": 85, "rarity": "uncommon", "tradeable": True, "consumable": True, "effects": {"health_restore": 75, "work_bonus": 0.3, "duration": 2400}},
    
    
    # === MORE FOOD ITEMS (continuing to reach 200+) ===
    "steak": {"item_id": "steak", "name": "🥩 Steak", "description": "Premium cut of beef. Very filling!", "category": "food", "value": 150, "rarity": "uncommon", "tradeable": True, "consumable": True, "effects": {"health_restore": 120, "happiness": 60, "energy_boost": 40}},
    "lobster": {"item_id": "lobster", "name": "🦞 Lobster", "description": "Luxury seafood delicacy.", "category": "food", "value": 300, "rarity": "rare", "tradeable": True, "consumable": True, "effects": {"health_restore": 100, "happiness": 100, "prestige_boost": 0.01}},
    "caviar": {"item_id": "caviar", "name": "🍣 Caviar", "description": "The finest caviar money can buy!", "category": "food", "value": 2500, "rarity": "epic", "tradeable": True, "consumable": True, "effects": {"health_restore": 80, "happiness": 150, "prestige_boost": 0.05, "flex_value": 500}},
    "truffles": {"item_id": "truffles", "name": "🍄 Truffles", "description": "Rare mushrooms worth their weight in gold.", "category": "food", "value": 5000, "rarity": "legendary", "tradeable": True, "consumable": True, "effects": {"health_restore": 200, "happiness": 200, "money_multiplier": 0.1, "duration": 7200}},
    "champagne": {"item_id": "champagne", "name": "🍾 Champagne", "description": "Celebrate in style with premium champagne!", "category": "food", "value": 800, "rarity": "rare", "tradeable": True, "consumable": True, "effects": {"happiness": 100, "gambling_luck": 0.15, "duration": 3600}},

    # === MORE TOOLS ===
    "calculator": {"item_id": "calculator", "name": "🔢 Calculator", "description": "For accounting and finance work.", "category": "tools", "value": 75, "rarity": "common", "tradeable": True, "consumable": False, "effects": {"work_bonus": 0.25, "special_work": "accounting"}},
    "microscope": {"item_id": "microscope", "name": "🔬 Microscope", "description": "High-powered microscope for scientific research.", "category": "tools", "value": 2500, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"work_bonus": 1.0, "special_work": "science", "research_bonus": 0.2}},
    "telescope": {"item_id": "telescope", "name": "🔭 Telescope", "description": "Explore the cosmos and discover new opportunities!", "category": "tools", "value": 1800, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"work_bonus": 0.8, "special_work": "astronomy", "discovery_chance": 0.1}},
    "paintbrush": {"item_id": "paintbrush", "name": "🖌️ Paintbrush", "description": "Create beautiful art and earn money from creativity.", "category": "tools", "value": 120, "rarity": "uncommon", "tradeable": True, "consumable": False, "effects": {"work_bonus": 0.6, "special_work": "artist", "creativity_bonus": 0.25}},
    "camera": {"item_id": "camera", "name": "📷 Professional Camera", "description": "Capture moments and sell photography.", "category": "tools", "value": 1500, "rarity": "uncommon", "tradeable": True, "consumable": False, "effects": {"work_bonus": 0.9, "special_work": "photography", "art_bonus": 0.3}},
    "guitar": {"item_id": "guitar", "name": "🎸 Electric Guitar", "description": "Rock out and earn money as a musician!", "category": "tools", "value": 800, "rarity": "uncommon", "tradeable": True, "consumable": False, "effects": {"work_bonus": 0.7, "special_work": "musician", "happiness": 25}},
    
    # === MORE COLLECTIBLES ===
    "signed_baseball": {"item_id": "signed_baseball", "name": "⚾ Signed Baseball", "description": "Baseball signed by a famous player.", "category": "collectibles", "value": 3500, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"flex_value": 700, "collector_bonus": 0.1}},
    "moon_rock": {"item_id": "moon_rock", "name": "🌙 Moon Rock", "description": "Actual rock from the lunar surface!", "category": "collectibles", "value": 100000, "rarity": "mythical", "tradeable": True, "consumable": False, "effects": {"flex_value": 25000, "prestige_boost": 0.2, "space_collector": True}},
    "dinosaur_fossil": {"item_id": "dinosaur_fossil", "name": "🦴 Dinosaur Fossil", "description": "Ancient fossil from prehistoric times.", "category": "collectibles", "value": 15000, "rarity": "epic", "tradeable": True, "consumable": False, "effects": {"flex_value": 3000, "science_bonus": 0.15}},
    "mona_lisa": {"item_id": "mona_lisa", "name": "🖼️ Mona Lisa (Replica)", "description": "High-quality replica of the famous painting.", "category": "collectibles", "value": 50000, "rarity": "legendary", "tradeable": True, "consumable": False, "effects": {"flex_value": 15000, "art_appreciation": 0.2, "prestige_boost": 0.15}},
    "royal_crown": {"item_id": "royal_crown", "name": "👑 Royal Crown", "description": "Crown fit for a king! Ultimate status symbol.", "category": "collectibles", "value": 250000, "rarity": "divine", "tradeable": False, "consumable": False, "effects": {"flex_value": 100000, "prestige_boost": 0.5, "royal_status": True, "money_multiplier": 0.25}},

    # === MORE WEAPONS ===
    "bow": {"item_id": "bow", "name": "🏹 Bow and Arrow", "description": "Silent but deadly hunting weapon.", "category": "weapons", "value": 400, "rarity": "uncommon", "tradeable": True, "consumable": False, "effects": {"crime_success": 0.15, "special_work": "hunting", "stealth_bonus": 0.2}},
    "sword": {"item_id": "sword", "name": "⚔️ Sword", "description": "Ancient blade with mysterious powers.", "category": "weapons", "value": 2000, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"crime_success": 0.25, "rob_success": 0.3, "honor_bonus": 0.1}},
    "laser_gun": {"item_id": "laser_gun", "name": "🔫 Laser Gun", "description": "Futuristic weapon from the future!", "category": "weapons", "value": 50000, "rarity": "mythical", "tradeable": False, "consumable": False, "effects": {"crime_success": 0.5, "rob_success": 0.6, "sci_fi_bonus": True}},

    # === MORE ARMOR ===
    "shield": {"item_id": "shield", "name": "🛡️ Shield", "description": "Protects against attacks and robbery.", "category": "armor", "value": 800, "rarity": "uncommon", "tradeable": True, "consumable": False, "effects": {"rob_protection": 0.3, "crime_protection": 0.2, "defense_bonus": 0.25}},
    "power_suit": {"item_id": "power_suit", "name": "🦾 Power Suit", "description": "High-tech suit that enhances all abilities.", "category": "armor", "value": 75000, "rarity": "legendary", "tradeable": False, "consumable": False, "effects": {"work_bonus": 0.5, "rob_protection": 0.8, "crime_success": 0.4, "energy_efficiency": 0.3}},

    # === MORE CURRENCY ITEMS ===
    "bitcoin": {"item_id": "bitcoin", "name": "₿ Bitcoin", "description": "Digital gold! Volatile but valuable cryptocurrency.", "category": "currency", "value": 45000, "rarity": "epic", "tradeable": True, "consumable": False, "effects": {"passive_income": 100, "crypto_volatility": 0.2, "investment_potential": 0.15}},
    "stock_certificate": {"item_id": "stock_certificate", "name": "📊 Stock Certificate", "description": "Ownership in a profitable company.", "category": "currency", "value": 5000, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"passive_income": 150, "dividend_yield": 0.1, "market_exposure": True}},
    "treasury_bond": {"item_id": "treasury_bond", "name": "🏦 Treasury Bond", "description": "Safe government investment with guaranteed returns.", "category": "currency", "value": 10000, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"passive_income": 75, "stability_bonus": True, "government_backing": True}},

    # === MORE MULTIPLIER ITEMS ===
    "golden_horseshoe": {"item_id": "golden_horseshoe", "name": "🐎 Golden Horseshoe", "description": "Extremely lucky charm that boosts all earnings!", "category": "multipliers", "value": 10000, "rarity": "epic", "tradeable": True, "consumable": False, "effects": {"money_multiplier": 1.25, "gambling_luck": 0.3, "work_bonus": 0.2, "luck_aura": True}},
    "four_leaf_clover": {"item_id": "four_leaf_clover", "name": "🍀 Four Leaf Clover", "description": "Rare clover that brings incredible luck!", "category": "multipliers", "value": 7500, "rarity": "legendary", "tradeable": True, "consumable": False, "effects": {"gambling_luck": 0.4, "crime_success": 0.2, "treasure_chance": 0.15, "rare_drop_bonus": 0.25}},
    "phoenix_feather": {"item_id": "phoenix_feather", "name": "🪶 Phoenix Feather", "description": "Mythical feather that grants rebirth powers!", "category": "multipliers", "value": 100000, "rarity": "divine", "tradeable": False, "consumable": True, "effects": {"full_restore": True, "prestige_boost": 1.0, "immortality_temp": True, "duration": 86400}},

    # === MORE SPECIAL ITEMS ===
    "crystal_ball": {"item_id": "crystal_ball", "name": "🔮 Crystal Ball", "description": "Reveals future opportunities and hidden treasures!", "category": "special", "value": 5000, "rarity": "epic", "tradeable": True, "consumable": False, "effects": {"future_vision": True, "treasure_chance": 0.2, "mystery_bonus": True, "prediction_power": 0.15}},
    "genie_lamp": {"item_id": "genie_lamp", "name": "🪔 Genie Lamp", "description": "Rub it for three wishes! (One-time use)", "category": "special", "value": 1000000, "rarity": "divine", "tradeable": False, "consumable": True, "effects": {"wishes": 3, "reality_alteration": True, "ultimate_power": True}},
    "pandoras_box": {"item_id": "pandoras_box", "name": "📦 Pandora's Box", "description": "Contains unknown mysteries... use at your own risk!", "category": "special", "value": 25000, "rarity": "mythical", "tradeable": True, "consumable": True, "effects": {"random_outcome": True, "chaos_factor": 0.5, "mystery_rewards": True, "curse_chance": 0.1}},

    # === MATERIALS AND CRAFTING ===
    "wood": {"item_id": "wood", "name": "🪵 Wood", "description": "Basic crafting material from trees.", "category": "materials", "value": 10, "rarity": "common", "tradeable": True, "consumable": False, "effects": {"crafting_material": True, "construction_bonus": 0.05}},
    "iron_ore": {"item_id": "iron_ore", "name": "⛽ Iron Ore", "description": "Raw iron for crafting tools and weapons.", "category": "materials", "value": 25, "rarity": "common", "tradeable": True, "consumable": False, "effects": {"crafting_material": True, "tool_crafting": True}},
    "diamond": {"item_id": "diamond", "name": "💎 Diamond", "description": "Precious gemstone used in luxury crafting.", "category": "materials", "value": 2000, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"crafting_material": True, "luxury_crafting": True, "value_multiplier": 0.1}},
    "mythril": {"item_id": "mythril", "name": "✨ Mythril", "description": "Legendary metal with magical properties.", "category": "materials", "value": 50000, "rarity": "legendary", "tradeable": True, "consumable": False, "effects": {"crafting_material": True, "magical_properties": True, "enchantment_bonus": 0.5}},

    # === PETS AND PET ITEMS ===
    "pet_collar": {"item_id": "pet_collar", "name": "🦮 Diamond Pet Collar", "description": "Fancy collar that makes pets more attractive.", "category": "pet_items", "value": 500, "rarity": "rare", "tradeable": True, "consumable": False, "effects": {"pet_happiness": 50, "pet_value": 0.2, "breeding_success": 0.1}},
    "pet_bed": {"item_id": "pet_bed", "name": "🛏️ Luxury Pet Bed", "description": "Comfortable bed that keeps pets well-rested.", "category": "pet_items", "value": 200, "rarity": "uncommon", "tradeable": True, "consumable": False, "effects": {"pet_energy": 100, "pet_health": 25, "sleep_quality": True}},
    "dragon_egg": {"item_id": "dragon_egg", "name": "🥚 Dragon Egg", "description": "Mythical egg that might hatch into a dragon!", "category": "pet_items", "value": 500000, "rarity": "divine", "tradeable": False, "consumable": True, "effects": {"dragon_pet_chance": 0.1, "mythical_pet": True, "prestige_boost": 0.3}},

    # === CONSUMABLES AND POTIONS ===
    "health_potion": {"item_id": "health_potion", "name": "❤️ Health Potion", "description": "Restores full health instantly.", "category": "consumables", "value": 100, "rarity": "common", "tradeable": True, "consumable": True, "effects": {"health_restore": 1000, "instant_healing": True}},
    "mana_potion": {"item_id": "mana_potion", "name": "💙 Mana Potion", "description": "Restores magical energy for special abilities.", "category": "consumables", "value": 150, "rarity": "uncommon", "tradeable": True, "consumable": True, "effects": {"mana_restore": 100, "spell_power": 0.2, "duration": 3600}},
    "invisibility_potion": {"item_id": "invisibility_potion", "name": "👻 Invisibility Potion", "description": "Become invisible for perfect crimes!", "category": "consumables", "value": 2000, "rarity": "epic", "tradeable": True, "consumable": True, "effects": {"invisibility": True, "crime_success": 0.8, "rob_success": 0.9, "duration": 1800}},
    "strength_potion": {"item_id": "strength_potion", "name": "💪 Strength Potion", "description": "Doubles your physical power temporarily!", "category": "consumables", "value": 300, "rarity": "rare", "tradeable": True, "consumable": True, "effects": {"work_bonus": 1.0, "crime_success": 0.3, "duration": 7200}},
    "speed_potion": {"item_id": "speed_potion", "name": "💨 Speed Potion", "description": "Move at lightning speed!", "category": "consumables", "value": 400, "rarity": "rare", "tradeable": True, "consumable": True, "effects": {"speed_boost": 2.0, "escape_chance": 0.5, "work_efficiency": 0.4, "duration": 3600}}
}

DEFAULT_ACHIEVEMENTS = {
    "first_command": {
        "achievement_id": "first_command",
        "name": "First Steps",
        "description": "Use your first bot command!",
        "category": "command_usage",
        "requirement": 1,
        "reward_coins": 50,
        "reward_experience": 10,
        "hidden": False
    },
    "command_master": {
        "achievement_id": "command_master",
        "name": "Command Master",
        "description": "Use 1000 bot commands!",
        "category": "command_usage",
        "requirement": 1000,
        "reward_coins": 5000,
        "reward_experience": 500,
        "hidden": False
    },
    "first_pet": {
        "achievement_id": "first_pet",
        "name": "Pet Owner",
        "description": "Adopt your first pet!",
        "category": "collection",
        "requirement": 1,
        "reward_coins": 100,
        "reward_experience": 25,
        "hidden": False
    },
    "millionaire": {
        "achievement_id": "millionaire",
        "name": "Millionaire",
        "description": "Accumulate 1,000,000 coins!",
        "category": "economy",
        "requirement": 1000000,
        "reward_coins": 100000,
        "reward_experience": 1000,
        "hidden": False
    }
}


class SchemaValidator:
    """Utility class for validating data schemas"""
    
    @staticmethod
    def validate_user_profile(data: Dict[str, Any]) -> bool:
        """Validate user profile data structure"""
        required_fields = ['user_id', 'username', 'display_name']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_economy_data(data: Dict[str, Any]) -> bool:
        """Validate economy data structure"""
        required_fields = ['user_id', 'pocket_balance', 'bank_balance']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_inventory_data(data: Dict[str, Any]) -> bool:
        """Validate inventory data structure"""
        required_fields = ['user_id', 'items']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def sanitize_user_input(text: str, max_length: int = 500) -> str:
        """Sanitize user input for storage"""
        if not text:
            return ""
        
        # Remove potentially harmful characters
        sanitized = text.strip()[:max_length]
        # Add more sanitization rules as needed
        return sanitized


def create_default_user_data(user_id: int, username: str, display_name: str) -> Dict[str, Any]:
    """Create default user data structure for a new user"""
    return {
        'profile': UserProfile(user_id=user_id, username=username, display_name=display_name).to_dict(),
        'economy': EconomyData(user_id=user_id).to_dict(),
        'inventory': UserInventory(user_id=user_id).to_dict(),
        'achievements': UserAchievements(user_id=user_id).to_dict(),
        'pets': UserPets(user_id=user_id).to_dict(),
        'relationships': UserRelationships(user_id=user_id).to_dict(),
        'cooldowns': UserCooldowns(user_id=user_id).to_dict(),
        'prestige': PrestigeData(user_id=user_id).to_dict(),
        'active_effects': ActiveEffects(user_id=user_id).to_dict()
    }