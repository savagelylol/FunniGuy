"""
Pet Management System for FunniGuy Discord Bot
Handles pet adoption, care, stats, breeding, and activities
"""
import asyncio
import logging
import uuid
import random
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from .database_manager import DatabaseManager, DatabaseError
from .schemas import (
    UserPets, Pet, PetType, SchemaValidator
)

logger = logging.getLogger(__name__)


class PetError(Exception):
    """Base exception for pet operations"""
    pass


class PetNotFoundError(PetError):
    """Exception raised when pet is not found"""
    pass


class MaxPetsReachedError(PetError):
    """Exception raised when user has reached max pets"""
    pass


class PetManager:
    """
    Comprehensive pet management system
    Handles pet adoption, care, activities, and breeding
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize the pet manager
        
        Args:
            database_manager: Instance of DatabaseManager
        """
        self.db = database_manager
        self.validator = SchemaValidator()
        
        # Pet settings
        self.adoption_cost = 500
        self.max_pets_default = 3
        self.max_pet_stat = 100
        
        # Pet care settings
        self.hunger_decay_rate = 5  # per hour
        self.happiness_decay_rate = 3  # per hour
        self.energy_decay_rate = 4  # per hour
        self.health_decay_rate = 1  # per hour when other stats are low
        
        # Activity costs and benefits
        self.activity_costs = {
            'feed': {'hunger': -30, 'happiness': 5, 'energy': 0, 'health': 2},
            'play': {'hunger': 10, 'happiness': 20, 'energy': -15, 'health': 5},
            'clean': {'hunger': 0, 'happiness': 10, 'energy': -5, 'health': 15},
            'train': {'hunger': 15, 'happiness': -5, 'energy': -20, 'health': 0, 'experience': 25},
            'rest': {'hunger': 5, 'happiness': 5, 'energy': 30, 'health': 10}
        }
        
        # Pet types and their characteristics
        self.pet_characteristics = {
            PetType.DOG: {
                'base_happiness': 80,
                'base_energy': 90,
                'hunger_rate': 6,
                'happiness_bonus': 1.2,
                'loyalty_bonus': 1.5
            },
            PetType.CAT: {
                'base_happiness': 70,
                'base_energy': 85,
                'hunger_rate': 4,
                'independence': 1.3,
                'cleanliness_bonus': 1.4
            },
            PetType.BIRD: {
                'base_happiness': 85,
                'base_energy': 95,
                'hunger_rate': 3,
                'intelligence_bonus': 1.3,
                'energy_bonus': 1.2
            },
            PetType.FISH: {
                'base_happiness': 60,
                'base_energy': 70,
                'hunger_rate': 2,
                'low_maintenance': 1.5,
                'health_bonus': 1.1
            },
            PetType.REPTILE: {
                'base_happiness': 50,
                'base_energy': 60,
                'hunger_rate': 1,
                'longevity_bonus': 1.8,
                'unique_bonus': 1.4
            },
            PetType.MYTHICAL: {
                'base_happiness': 95,
                'base_energy': 100,
                'hunger_rate': 2,
                'magic_bonus': 2.0,
                'special_abilities': True
            },
            PetType.ROBOT: {
                'base_happiness': 75,
                'base_energy': 100,
                'hunger_rate': 0,  # Doesn't eat
                'tech_bonus': 1.6,
                'efficiency_bonus': 1.3
            }
        }
        
        # Breeding settings
        self.breeding_cooldown_hours = 168  # 1 week
        self.breeding_success_rate = 0.7
        self.breeding_duration_hours = 72  # 3 days
    
    async def get_user_pets(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's pet data
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Pet data or None if not found
        """
        try:
            pet_data = await self.db.get_user_data(user_id, 'pets')
            
            if pet_data:
                # Update pet stats based on time passed
                pet_data = await self._update_pet_stats(user_id, pet_data)
            
            return pet_data
            
        except Exception as e:
            logger.error(f"Error getting user pets {user_id}: {e}")
            return None
    
    async def _update_pet_stats(self, user_id: int, pet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update pet stats based on time decay
        
        Args:
            user_id: Discord user ID
            pet_data: Current pet data
            
        Returns:
            Updated pet data
        """
        now = datetime.utcnow()
        pets = pet_data.get('pets', {})
        updated = False
        
        for pet_id, pet_info in pets.items():
            # Calculate time since last update
            last_update = pet_info.get('last_updated', now.isoformat())
            last_update_time = datetime.fromisoformat(last_update)
            hours_passed = (now - last_update_time).total_seconds() / 3600
            
            if hours_passed > 0.1:  # Only update if more than 6 minutes passed
                # Apply stat decay
                pet_type = PetType(pet_info.get('pet_type', 'dog'))
                characteristics = self.pet_characteristics.get(pet_type, {})
                
                # Hunger increases over time
                hunger_rate = characteristics.get('hunger_rate', self.hunger_decay_rate)
                pet_info['hunger'] = min(100, pet_info.get('hunger', 0) + (hunger_rate * hours_passed))
                
                # Happiness decreases over time
                happiness_decay = self.happiness_decay_rate * hours_passed
                pet_info['happiness'] = max(0, pet_info.get('happiness', 100) - happiness_decay)
                
                # Energy decreases over time
                energy_decay = self.energy_decay_rate * hours_passed
                pet_info['energy'] = max(0, pet_info.get('energy', 100) - energy_decay)
                
                # Health decreases if other stats are very low
                if (pet_info['hunger'] > 80 or pet_info['happiness'] < 20 or pet_info['energy'] < 20):
                    health_decay = self.health_decay_rate * hours_passed
                    pet_info['health'] = max(0, pet_info.get('health', 100) - health_decay)
                
                pet_info['last_updated'] = now.isoformat()
                updated = True
        
        if updated:
            await self.db.save_user_data(user_id, 'pets', pet_data)
        
        return pet_data
    
    async def adopt_pet(self, user_id: int, pet_type: str, pet_name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Adopt a new pet
        
        Args:
            user_id: Discord user ID
            pet_type: Type of pet to adopt
            pet_name: Name for the pet
            
        Returns:
            Tuple of (success, message, pet_id)
        """
        try:
            # Validate pet type
            try:
                pet_type_enum = PetType(pet_type.lower())
            except ValueError:
                return False, f"Invalid pet type: {pet_type}", None
            
            # Check if user has enough money
            economy_data = await self.db.get_user_data(user_id, 'economy')
            if not economy_data or economy_data.get('pocket_balance', 0) < self.adoption_cost:
                return False, f"You need {self.adoption_cost} coins to adopt a pet!", None
            
            # Get user's pet data
            pet_data = await self.get_user_pets(user_id)
            if not pet_data:
                raise DatabaseError(f"Pet data not found for user {user_id}")
            
            # Check pet limit
            current_pets = len(pet_data.get('pets', {}))
            max_pets = pet_data.get('max_pets', self.max_pets_default)
            
            if current_pets >= max_pets:
                return False, f"You can only have {max_pets} pets at once!", None
            
            # Create new pet
            pet_id = str(uuid.uuid4())[:8]  # Short ID
            characteristics = self.pet_characteristics.get(pet_type_enum, {})
            
            new_pet = {
                'pet_id': pet_id,
                'user_id': user_id,
                'name': self.validator.sanitize_user_input(pet_name, 50),
                'pet_type': pet_type_enum.value,
                'level': 1,
                'experience': 0,
                'happiness': characteristics.get('base_happiness', 80),
                'hunger': 20,  # Start slightly hungry
                'energy': characteristics.get('base_energy', 80),
                'health': 100,
                'last_fed': None,
                'last_played': None,
                'last_cleaned': None,
                'color': random.choice(['brown', 'black', 'white', 'gray', 'golden', 'spotted']),
                'accessories': [],
                'special_traits': [],
                'is_breeding': False,
                'breeding_partner': None,
                'breeding_end_time': None,
                'created_at': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat()
            }
            
            # Add pet to user's collection
            pets = pet_data.setdefault('pets', {})
            pets[pet_id] = new_pet
            pet_data['total_pets'] = pet_data.get('total_pets', 0) + 1
            
            # Set as active pet if it's their first
            if pet_data.get('active_pet') is None:
                pet_data['active_pet'] = pet_id
            
            # Charge adoption cost
            economy_data['pocket_balance'] -= self.adoption_cost
            economy_data['total_spent'] += self.adoption_cost
            
            # Save data
            await self.db.save_user_data(user_id, 'pets', pet_data)
            await self.db.save_user_data(user_id, 'economy', economy_data)
            
            logger.info(f"User {user_id} adopted pet {pet_id} ({pet_name}, {pet_type})")
            return True, f"Successfully adopted {pet_name} the {pet_type}! 🐾", pet_id
            
        except Exception as e:
            logger.error(f"Error adopting pet for user {user_id}: {e}")
            return False, f"Failed to adopt pet: {str(e)}", None
    
    async def care_for_pet(self, user_id: int, pet_id: str, activity: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Perform a care activity for a pet
        
        Args:
            user_id: Discord user ID
            pet_id: Pet ID
            activity: Care activity (feed, play, clean, train, rest)
            
        Returns:
            Tuple of (success, message, stat_changes)
        """
        try:
            if activity not in self.activity_costs:
                return False, f"Invalid activity: {activity}", {}
            
            pet_data = await self.get_user_pets(user_id)
            if not pet_data:
                return False, "Pet data not found!", {}
            
            pets = pet_data.get('pets', {})
            if pet_id not in pets:
                return False, "Pet not found!", {}
            
            pet = pets[pet_id]
            
            # Check if pet needs this activity (prevent spam)
            now = datetime.utcnow()
            last_activity_key = f'last_{activity.replace("_", "")}'
            
            if last_activity_key in pet:
                last_activity = datetime.fromisoformat(pet[last_activity_key])
                cooldown_minutes = 30  # 30 minute cooldown between same activities
                if (now - last_activity).total_seconds() < (cooldown_minutes * 60):
                    return False, f"You can only {activity} your pet every {cooldown_minutes} minutes!", {}
            
            # Apply activity effects
            stat_changes = self.activity_costs[activity].copy()
            message_parts = []
            
            for stat, change in stat_changes.items():
                if stat == 'experience':
                    # Handle experience separately
                    old_exp = pet.get('experience', 0)
                    new_exp = old_exp + change
                    pet['experience'] = new_exp
                    
                    # Check for level up
                    old_level = pet.get('level', 1)
                    new_level = self._calculate_pet_level(new_exp)
                    if new_level > old_level:
                        pet['level'] = new_level
                        message_parts.append(f"🎉 {pet['name']} leveled up to level {new_level}!")
                    
                    message_parts.append(f"📈 +{change} experience")
                else:
                    # Handle stat changes
                    old_value = pet.get(stat, 100 if stat == 'health' else 50)
                    new_value = max(0, min(100, old_value + change))
                    pet[stat] = new_value
                    
                    if change > 0:
                        message_parts.append(f"📈 +{change} {stat}")
                    elif change < 0:
                        message_parts.append(f"📉 {change} {stat}")
            
            # Update last activity time
            if last_activity_key.replace('last_', '') in ['fed', 'played', 'cleaned']:
                pet[last_activity_key] = now.isoformat()
            
            pet['last_updated'] = now.isoformat()
            
            # Save updated pet data
            await self.db.save_user_data(user_id, 'pets', pet_data)
            
            # Create success message
            activity_messages = {
                'feed': f"🍽️ You fed {pet['name']}! They look satisfied.",
                'play': f"🎾 You played with {pet['name']}! They had a great time.",
                'clean': f"🛁 You cleaned {pet['name']}! They feel much better.",
                'train': f"🎯 You trained {pet['name']}! They learned something new.",
                'rest': f"😴 {pet['name']} took a nice rest and feels refreshed."
            }
            
            main_message = activity_messages.get(activity, f"You performed {activity} on {pet['name']}!")
            full_message = main_message + " " + " ".join(message_parts)
            
            logger.debug(f"Pet care activity: user {user_id}, pet {pet_id}, activity {activity}")
            return True, full_message, stat_changes
            
        except Exception as e:
            logger.error(f"Error caring for pet: {e}")
            return False, f"Failed to care for pet: {str(e)}", {}
    
    def _calculate_pet_level(self, experience: int) -> int:
        """
        Calculate pet level from experience
        
        Args:
            experience: Total experience points
            
        Returns:
            Pet level
        """
        # Level formula: level = floor(sqrt(experience / 100)) + 1
        import math
        return math.floor(math.sqrt(experience / 100)) + 1
    
    async def set_active_pet(self, user_id: int, pet_id: str) -> Tuple[bool, str]:
        """
        Set the active pet for a user
        
        Args:
            user_id: Discord user ID
            pet_id: Pet ID to set as active
            
        Returns:
            Tuple of (success, message)
        """
        try:
            pet_data = await self.get_user_pets(user_id)
            if not pet_data:
                return False, "Pet data not found!"
            
            pets = pet_data.get('pets', {})
            if pet_id not in pets:
                return False, "Pet not found!"
            
            pet_data['active_pet'] = pet_id
            await self.db.save_user_data(user_id, 'pets', pet_data)
            
            pet_name = pets[pet_id].get('name', 'Unknown')
            return True, f"{pet_name} is now your active pet! 🐾"
            
        except Exception as e:
            logger.error(f"Error setting active pet: {e}")
            return False, f"Failed to set active pet: {str(e)}"
    
    async def get_pet_info(self, user_id: int, pet_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific pet
        
        Args:
            user_id: Discord user ID
            pet_id: Pet ID
            
        Returns:
            Pet information or None if not found
        """
        try:
            pet_data = await self.get_user_pets(user_id)
            if not pet_data:
                return None
            
            pets = pet_data.get('pets', {})
            if pet_id not in pets:
                return None
            
            pet = pets[pet_id]
            
            # Calculate additional info
            created_at = datetime.fromisoformat(pet['created_at'])
            age_days = (datetime.utcnow() - created_at).days
            
            # Pet condition based on stats
            avg_condition = (pet['happiness'] + pet['energy'] + pet['health'] + (100 - pet['hunger'])) / 4
            
            if avg_condition >= 80:
                condition = "Excellent 😊"
            elif avg_condition >= 60:
                condition = "Good 🙂"
            elif avg_condition >= 40:
                condition = "Fair 😐"
            elif avg_condition >= 20:
                condition = "Poor 😟"
            else:
                condition = "Critical 😰"
            
            return {
                **pet,
                'age_days': age_days,
                'condition': condition,
                'avg_condition': round(avg_condition, 1),
                'next_level_exp': ((pet['level'] ** 2) * 100) - pet['experience'],
                'is_active': pet_data.get('active_pet') == pet_id
            }
            
        except Exception as e:
            logger.error(f"Error getting pet info: {e}")
            return None
    
    async def get_pet_leaderboard(self, category: str = 'level', limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pet leaderboard
        
        Args:
            category: Leaderboard category ('level', 'experience', 'happiness')
            limit: Number of pets to return
            
        Returns:
            List of pet data sorted by category
        """
        try:
            # This would require scanning all user pet files
            # For now, return empty list as this is a complex operation
            logger.info(f"Pet leaderboard requested for category: {category}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting pet leaderboard: {e}")
            return []
    
    async def breed_pets(self, user_id: int, pet1_id: str, partner_user_id: int, pet2_id: str) -> Tuple[bool, str]:
        """
        Start breeding between two pets
        
        Args:
            user_id: Owner of first pet
            pet1_id: First pet ID
            partner_user_id: Owner of second pet
            pet2_id: Second pet ID
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get both pets' data
            user1_pets = await self.get_user_pets(user_id)
            user2_pets = await self.get_user_pets(partner_user_id)
            
            if not user1_pets or not user2_pets:
                return False, "Pet data not found for one or both users!"
            
            pet1 = user1_pets.get('pets', {}).get(pet1_id)
            pet2 = user2_pets.get('pets', {}).get(pet2_id)
            
            if not pet1 or not pet2:
                return False, "One or both pets not found!"
            
            # Check if pets are already breeding
            if pet1.get('is_breeding') or pet2.get('is_breeding'):
                return False, "One or both pets are already breeding!"
            
            # Check if pets are compatible (same type for now)
            if pet1['pet_type'] != pet2['pet_type']:
                return False, "Pets must be the same type to breed!"
            
            # Check if pets are healthy enough
            if (pet1['health'] < 70 or pet2['health'] < 70 or 
                pet1['happiness'] < 50 or pet2['happiness'] < 50):
                return False, "Pets must be healthy and happy to breed!"
            
            # Start breeding process
            breeding_end = datetime.utcnow() + timedelta(hours=self.breeding_duration_hours)
            
            pet1.update({
                'is_breeding': True,
                'breeding_partner': pet2_id,
                'breeding_end_time': breeding_end.isoformat()
            })
            
            pet2.update({
                'is_breeding': True,
                'breeding_partner': pet1_id,
                'breeding_end_time': breeding_end.isoformat()
            })
            
            # Save both pets' data
            await self.db.save_user_data(user_id, 'pets', user1_pets)
            await self.db.save_user_data(partner_user_id, 'pets', user2_pets)
            
            hours = self.breeding_duration_hours
            return True, f"Breeding started! Check back in {hours} hours to see if there's a baby! 🥚"
            
        except Exception as e:
            logger.error(f"Error starting breeding: {e}")
            return False, f"Failed to start breeding: {str(e)}"
    
    async def check_breeding_complete(self, user_id: int, pet_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if breeding is complete and handle baby creation
        
        Args:
            user_id: Discord user ID
            pet_id: Pet ID to check
            
        Returns:
            Tuple of (breeding_complete, baby_pet_data)
        """
        try:
            pet_data = await self.get_user_pets(user_id)
            if not pet_data:
                return False, None
            
            pet = pet_data.get('pets', {}).get(pet_id)
            if not pet or not pet.get('is_breeding'):
                return False, None
            
            breeding_end = datetime.fromisoformat(pet['breeding_end_time'])
            if datetime.utcnow() < breeding_end:
                return False, None  # Still breeding
            
            # Breeding is complete
            pet['is_breeding'] = False
            pet['breeding_partner'] = None
            pet['breeding_end_time'] = None
            
            # Check if breeding was successful
            if random.random() < self.breeding_success_rate:
                # Create baby pet
                baby_id = str(uuid.uuid4())[:8]
                baby_name = f"Baby {pet['name']}"
                
                baby_pet = {
                    'pet_id': baby_id,
                    'user_id': user_id,
                    'name': baby_name,
                    'pet_type': pet['pet_type'],
                    'level': 1,
                    'experience': 0,
                    'happiness': 90,  # Babies start very happy
                    'hunger': 40,     # But hungry
                    'energy': 80,
                    'health': 100,
                    'last_fed': None,
                    'last_played': None,
                    'last_cleaned': None,
                    'color': random.choice(['brown', 'black', 'white', 'gray', 'golden', 'spotted']),
                    'accessories': [],
                    'special_traits': ['baby'],  # Special baby trait
                    'is_breeding': False,
                    'breeding_partner': None,
                    'breeding_end_time': None,
                    'created_at': datetime.utcnow().isoformat(),
                    'last_updated': datetime.utcnow().isoformat()
                }
                
                # Add baby to user's pets
                pet_data['pets'][baby_id] = baby_pet
                pet_data['total_pets'] = pet_data.get('total_pets', 0) + 1
                
                await self.db.save_user_data(user_id, 'pets', pet_data)
                
                logger.info(f"Breeding successful: user {user_id} got baby pet {baby_id}")
                return True, baby_pet
            else:
                # Breeding failed
                await self.db.save_user_data(user_id, 'pets', pet_data)
                logger.info(f"Breeding failed for user {user_id}, pet {pet_id}")
                return True, None
            
        except Exception as e:
            logger.error(f"Error checking breeding completion: {e}")
            return False, None