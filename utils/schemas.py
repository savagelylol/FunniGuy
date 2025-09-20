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


class ItemCategory(Enum):
    """Item categories for inventory"""
    FOOD = "food"
    TOOLS = "tools"
    COLLECTIBLES = "collectibles"
    CONSUMABLES = "consumables"
    GIFTS = "gifts"
    PET_ITEMS = "pet_items"
    SPECIAL = "special"


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


# Global configurations and item definitions
DEFAULT_ITEMS = {
    "apple": {
        "item_id": "apple",
        "name": "Apple",
        "description": "A fresh, crispy apple. Restores some pet hunger.",
        "category": "food",
        "value": 5,
        "rarity": "common",
        "tradeable": True,
        "consumable": True
    },
    "gold_coin": {
        "item_id": "gold_coin",
        "name": "Gold Coin",
        "description": "A shiny gold coin. Very valuable!",
        "category": "collectibles",
        "value": 100,
        "rarity": "rare",
        "tradeable": True,
        "consumable": False
    },
    "pet_toy": {
        "item_id": "pet_toy",
        "name": "Pet Toy",
        "description": "A fun toy that pets love to play with.",
        "category": "pet_items",
        "value": 15,
        "rarity": "common",
        "tradeable": True,
        "consumable": True
    }
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
        'cooldowns': UserCooldowns(user_id=user_id).to_dict()
    }