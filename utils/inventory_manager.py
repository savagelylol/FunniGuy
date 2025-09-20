"""
Inventory Management System for FunniGuy Discord Bot
Handles all item operations, trading, and collections
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import uuid

from .database_manager import DatabaseManager, DatabaseError
from .schemas import (
    UserInventory, InventoryItem, ItemCategory,
    DEFAULT_ITEMS, SchemaValidator
)

logger = logging.getLogger(__name__)


class InsufficientItemsError(Exception):
    """Exception raised when user has insufficient items"""
    pass


class ItemNotFoundError(Exception):
    """Exception raised when item is not found"""
    pass


class InventoryFullError(Exception):
    """Exception raised when inventory is at capacity"""
    pass


class InventoryManager:
    """
    Comprehensive inventory management system
    Handles all item operations, trading, and collections
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize the inventory manager
        
        Args:
            database_manager: Instance of DatabaseManager
        """
        self.db = database_manager
        self.validator = SchemaValidator()
        
        # Inventory settings
        self.initial_capacity = 50
        self.max_capacity = 1000
        self.capacity_upgrade_cost = 100
        self.capacity_upgrade_multiplier = 1.5
        
        # Trading settings
        self.trade_tax_rate = 0.05  # 5% tax on trades
        self.min_trade_value = 10
        self.max_trade_items = 10
    
    async def get_user_inventory(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's inventory data
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Inventory data or None if not found
        """
        try:
            inventory_data = await self.db.get_user_data(user_id, 'inventory')
            
            if inventory_data:
                # Update total value calculation
                inventory_data = await self._update_inventory_value(inventory_data)
                await self.db.save_user_data(user_id, 'inventory', inventory_data)
            
            return inventory_data
            
        except Exception as e:
            logger.error(f"Error getting user inventory {user_id}: {e}")
            return None
    
    async def _update_inventory_value(self, inventory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update total inventory value based on current items
        
        Args:
            inventory_data: Current inventory data
            
        Returns:
            Updated inventory data
        """
        total_value = 0
        items = inventory_data.get('items', {})
        
        for item_id, item_data in items.items():
            item_value = item_data.get('value', 0)
            quantity = item_data.get('quantity', 1)
            total_value += item_value * quantity
        
        inventory_data['total_value'] = total_value
        return inventory_data
    
    async def add_item(self, user_id: int, item_id: str, quantity: int = 1, 
                      custom_item_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add an item to user's inventory
        
        Args:
            user_id: Discord user ID
            item_id: ID of the item to add
            quantity: Quantity to add
            custom_item_data: Custom item data if not in default items
            
        Returns:
            True if item was added successfully
        """
        if quantity <= 0:
            return False
        
        try:
            inventory_data = await self.get_user_inventory(user_id)
            if not inventory_data:
                raise DatabaseError(f"Inventory data not found for user {user_id}")
            
            # Check inventory capacity
            current_items = len(inventory_data.get('items', {}))
            capacity = inventory_data.get('capacity', self.initial_capacity)
            
            items = inventory_data.setdefault('items', {})
            
            if item_id in items:
                # Item already exists, just add quantity
                items[item_id]['quantity'] += quantity
            else:
                # New item, check capacity
                if current_items >= capacity:
                    raise InventoryFullError("Inventory is at full capacity")
                
                # Get item data from defaults or use custom data
                if custom_item_data:
                    item_data = custom_item_data.copy()
                elif item_id in DEFAULT_ITEMS:
                    item_data = DEFAULT_ITEMS[item_id].copy()
                else:
                    raise ItemNotFoundError(f"Item {item_id} not found in defaults")
                
                item_data['quantity'] = quantity
                item_data['obtained_at'] = datetime.utcnow().isoformat()
                items[item_id] = item_data
            
            # Update inventory
            inventory_data = await self._update_inventory_value(inventory_data)
            await self.db.save_user_data(user_id, 'inventory', inventory_data)
            
            logger.debug(f"Added {quantity}x {item_id} to user {user_id} inventory")
            return True
            
        except Exception as e:
            logger.error(f"Error adding item to inventory for user {user_id}: {e}")
            return False
    
    async def remove_item(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        """
        Remove an item from user's inventory
        
        Args:
            user_id: Discord user ID
            item_id: ID of the item to remove
            quantity: Quantity to remove
            
        Returns:
            True if item was removed successfully
        """
        if quantity <= 0:
            return False
        
        try:
            inventory_data = await self.get_user_inventory(user_id)
            if not inventory_data:
                raise DatabaseError(f"Inventory data not found for user {user_id}")
            
            items = inventory_data.get('items', {})
            
            if item_id not in items:
                raise ItemNotFoundError(f"Item {item_id} not found in inventory")
            
            current_quantity = items[item_id].get('quantity', 0)
            if current_quantity < quantity:
                raise InsufficientItemsError(f"Insufficient quantity of {item_id}")
            
            # Remove quantity
            if current_quantity == quantity:
                # Remove item completely
                del items[item_id]
            else:
                # Reduce quantity
                items[item_id]['quantity'] -= quantity
            
            # Update inventory
            inventory_data = await self._update_inventory_value(inventory_data)
            await self.db.save_user_data(user_id, 'inventory', inventory_data)
            
            logger.debug(f"Removed {quantity}x {item_id} from user {user_id} inventory")
            return True
            
        except Exception as e:
            logger.error(f"Error removing item from inventory for user {user_id}: {e}")
            return False
    
    async def use_item(self, user_id: int, item_id: str, quantity: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """
        Use a consumable item
        
        Args:
            user_id: Discord user ID
            item_id: ID of the item to use
            quantity: Quantity to use
            
        Returns:
            Tuple of (success, item_effects)
        """
        try:
            inventory_data = await self.get_user_inventory(user_id)
            if not inventory_data:
                raise DatabaseError(f"Inventory data not found for user {user_id}")
            
            items = inventory_data.get('items', {})
            
            if item_id not in items:
                raise ItemNotFoundError(f"Item {item_id} not found in inventory")
            
            item_data = items[item_id]
            
            # Check if item is consumable
            if not item_data.get('consumable', False):
                return False, {'error': 'Item is not consumable'}
            
            current_quantity = item_data.get('quantity', 0)
            if current_quantity < quantity:
                raise InsufficientItemsError(f"Insufficient quantity of {item_id}")
            
            # Remove used items
            await self.remove_item(user_id, item_id, quantity)
            
            # Calculate item effects based on item type
            effects = await self._calculate_item_effects(user_id, item_id, quantity)
            
            logger.info(f"User {user_id} used {quantity}x {item_id}")
            return True, effects
            
        except Exception as e:
            logger.error(f"Error using item for user {user_id}: {e}")
            return False, {'error': str(e)}
    
    async def _calculate_item_effects(self, user_id: int, item_id: str, quantity: int) -> Dict[str, Any]:
        """
        Calculate effects of using an item
        
        Args:
            user_id: Discord user ID
            item_id: ID of the item used
            quantity: Quantity used
            
        Returns:
            Dictionary with item effects
        """
        effects = {
            'health_restored': 0,
            'happiness_gained': 0,
            'coins_gained': 0,
            'experience_gained': 0,
            'special_effects': []
        }
        
        # Define item effects based on item ID
        item_effects_map = {
            'apple': {
                'health_restored': 10 * quantity,
                'happiness_gained': 5 * quantity
            },
            'pet_toy': {
                'happiness_gained': 15 * quantity,
                'special_effects': ['pet_happiness_boost']
            },
            'gold_coin': {
                'coins_gained': 100 * quantity
            }
        }
        
        if item_id in item_effects_map:
            item_effects = item_effects_map[item_id]
            for effect, value in item_effects.items():
                if effect in effects:
                    effects[effect] = value
                elif effect == 'special_effects':
                    effects['special_effects'].extend(value)
        
        return effects
    
    async def get_inventory_by_category(self, user_id: int, category: str) -> List[Dict[str, Any]]:
        """
        Get inventory items filtered by category
        
        Args:
            user_id: Discord user ID
            category: Item category to filter by
            
        Returns:
            List of items in the specified category
        """
        try:
            inventory_data = await self.get_user_inventory(user_id)
            if not inventory_data:
                return []
            
            items = inventory_data.get('items', {})
            category_items = []
            
            for item_id, item_data in items.items():
                if item_data.get('category') == category:
                    category_items.append({
                        'item_id': item_id,
                        **item_data
                    })
            
            # Sort by rarity and value
            rarity_order = {'common': 1, 'uncommon': 2, 'rare': 3, 'epic': 4, 'legendary': 5}
            category_items.sort(key=lambda x: (rarity_order.get(x.get('rarity', 'common'), 1), 
                                             x.get('value', 0)), reverse=True)
            
            return category_items
            
        except Exception as e:
            logger.error(f"Error getting inventory by category for user {user_id}: {e}")
            return []
    
    async def get_item_count(self, user_id: int, item_id: str) -> int:
        """
        Get the quantity of a specific item in user's inventory
        
        Args:
            user_id: Discord user ID
            item_id: ID of the item
            
        Returns:
            Quantity of the item (0 if not found)
        """
        try:
            inventory_data = await self.get_user_inventory(user_id)
            if not inventory_data:
                return 0
            
            items = inventory_data.get('items', {})
            return items.get(item_id, {}).get('quantity', 0)
            
        except Exception as e:
            logger.error(f"Error getting item count for user {user_id}: {e}")
            return 0
    
    async def upgrade_inventory_capacity(self, user_id: int) -> Tuple[bool, int, int]:
        """
        Upgrade user's inventory capacity
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (success, upgrade_cost, new_capacity)
        """
        try:
            inventory_data = await self.get_user_inventory(user_id)
            if not inventory_data:
                raise DatabaseError(f"Inventory data not found for user {user_id}")
            
            current_capacity = inventory_data.get('capacity', self.initial_capacity)
            
            if current_capacity >= self.max_capacity:
                return False, 0, current_capacity  # Already at max capacity
            
            # Calculate upgrade cost
            upgrade_cost = int(self.capacity_upgrade_cost * (self.capacity_upgrade_multiplier ** 
                              ((current_capacity - self.initial_capacity) // 10)))
            new_capacity = min(current_capacity + 10, self.max_capacity)
            
            # Check if user has enough money (this would integrate with economy system)
            # For now, assume they can afford it
            
            inventory_data['capacity'] = new_capacity
            await self.db.save_user_data(user_id, 'inventory', inventory_data)
            
            logger.info(f"User {user_id} upgraded inventory capacity to {new_capacity}")
            return True, upgrade_cost, new_capacity
            
        except Exception as e:
            logger.error(f"Error upgrading inventory capacity for user {user_id}: {e}")
            return False, 0, 0
    
    async def transfer_item(self, sender_id: int, receiver_id: int, item_id: str, quantity: int) -> bool:
        """
        Transfer an item between users
        
        Args:
            sender_id: Discord user ID of sender
            receiver_id: Discord user ID of receiver
            item_id: ID of the item to transfer
            quantity: Quantity to transfer
            
        Returns:
            True if transfer was successful
        """
        if quantity <= 0:
            return False
        
        if sender_id == receiver_id:
            return False  # Can't transfer to yourself
        
        try:
            # Check sender has the item
            sender_inventory = await self.get_user_inventory(sender_id)
            if not sender_inventory:
                raise DatabaseError(f"Sender inventory not found")
            
            sender_items = sender_inventory.get('items', {})
            if item_id not in sender_items:
                raise ItemNotFoundError(f"Item {item_id} not found in sender's inventory")
            
            sender_quantity = sender_items[item_id].get('quantity', 0)
            if sender_quantity < quantity:
                raise InsufficientItemsError(f"Insufficient quantity of {item_id}")
            
            # Check if item is tradeable
            if not sender_items[item_id].get('tradeable', True):
                return False  # Item is not tradeable
            
            # Check receiver inventory capacity
            receiver_inventory = await self.get_user_inventory(receiver_id)
            if not receiver_inventory:
                raise DatabaseError(f"Receiver inventory not found")
            
            receiver_items = receiver_inventory.get('items', {})
            receiver_capacity = receiver_inventory.get('capacity', self.initial_capacity)
            
            if item_id not in receiver_items and len(receiver_items) >= receiver_capacity:
                raise InventoryFullError("Receiver's inventory is full")
            
            # Get item data for transfer
            item_data = sender_items[item_id].copy()
            
            # Perform transfer
            success_remove = await self.remove_item(sender_id, item_id, quantity)
            if not success_remove:
                return False
            
            success_add = await self.add_item(receiver_id, item_id, quantity, item_data)
            if not success_add:
                # Rollback - add item back to sender
                await self.add_item(sender_id, item_id, quantity, item_data)
                return False
            
            logger.info(f"Transferred {quantity}x {item_id} from {sender_id} to {receiver_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error transferring item: {e}")
            return False
    
    async def create_trade_request(self, sender_id: int, receiver_id: int, 
                                  sender_items: List[Dict[str, Any]], 
                                  receiver_items: List[Dict[str, Any]]) -> Optional[str]:
        """
        Create a trade request between users
        
        Args:
            sender_id: Discord user ID of trade initiator
            receiver_id: Discord user ID of trade recipient
            sender_items: List of items sender is offering
            receiver_items: List of items sender wants from receiver
            
        Returns:
            Trade ID if successful, None otherwise
        """
        if sender_id == receiver_id:
            return None
        
        if len(sender_items) > self.max_trade_items or len(receiver_items) > self.max_trade_items:
            return None
        
        try:
            # Validate sender has all offered items
            for item_offer in sender_items:
                item_id = item_offer['item_id']
                quantity = item_offer['quantity']
                
                current_quantity = await self.get_item_count(sender_id, item_id)
                if current_quantity < quantity:
                    return None  # Insufficient items
            
            # Validate receiver has all requested items
            for item_request in receiver_items:
                item_id = item_request['item_id']
                quantity = item_request['quantity']
                
                current_quantity = await self.get_item_count(receiver_id, item_id)
                if current_quantity < quantity:
                    return None  # Insufficient items
            
            # Calculate trade values
            sender_value = await self._calculate_items_value(sender_items)
            receiver_value = await self._calculate_items_value(receiver_items)
            
            if min(sender_value, receiver_value) < self.min_trade_value:
                return None  # Trade value too low
            
            # Create trade record
            trade_id = str(uuid.uuid4())
            trade_data = {
                'trade_id': trade_id,
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'sender_items': sender_items,
                'receiver_items': receiver_items,
                'sender_value': sender_value,
                'receiver_value': receiver_value,
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
            
            # Store trade data (this would go in a separate trades collection)
            trades_file = self.db.global_dir / "active_trades.json"
            
            async with self.db._file_lock(trades_file):
                try:
                    trades_data = await self.db._read_json_file(trades_file)
                    if trades_data is None:
                        trades_data = {}
                    
                    trades_data[trade_id] = trade_data
                    await self.db._write_json_file(trades_file, trades_data)
                    
                    logger.info(f"Created trade request {trade_id} from {sender_id} to {receiver_id}")
                    return trade_id
                    
                except Exception as e:
                    logger.error(f"Error storing trade data: {e}")
                    return None
            
        except Exception as e:
            logger.error(f"Error creating trade request: {e}")
            return None
    
    async def _calculate_items_value(self, items: List[Dict[str, Any]]) -> int:
        """
        Calculate total value of a list of items
        
        Args:
            items: List of item dictionaries with item_id and quantity
            
        Returns:
            Total value of items
        """
        total_value = 0
        
        for item in items:
            item_id = item['item_id']
            quantity = item['quantity']
            
            # Get item value from defaults
            if item_id in DEFAULT_ITEMS:
                item_value = DEFAULT_ITEMS[item_id].get('value', 0)
                total_value += item_value * quantity
        
        return total_value
    
    async def get_inventory_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive inventory statistics
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with inventory statistics
        """
        try:
            inventory_data = await self.get_user_inventory(user_id)
            if not inventory_data:
                return {}
            
            items = inventory_data.get('items', {})
            
            # Count items by category
            category_counts = {}
            rarity_counts = {}
            total_items = 0
            
            for item_data in items.values():
                category = item_data.get('category', 'unknown')
                rarity = item_data.get('rarity', 'common')
                quantity = item_data.get('quantity', 1)
                
                category_counts[category] = category_counts.get(category, 0) + quantity
                rarity_counts[rarity] = rarity_counts.get(rarity, 0) + quantity
                total_items += quantity
            
            return {
                'total_items': total_items,
                'unique_items': len(items),
                'total_value': inventory_data.get('total_value', 0),
                'capacity': {
                    'current': len(items),
                    'maximum': inventory_data.get('capacity', self.initial_capacity),
                    'usage_percentage': round((len(items) / inventory_data.get('capacity', self.initial_capacity)) * 100, 1)
                },
                'categories': category_counts,
                'rarities': rarity_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting inventory statistics for user {user_id}: {e}")
            return {}
    
    async def get_all_available_items(self) -> Dict[str, Any]:
        """
        Get all available items in the game
        
        Returns:
            Dictionary of all available items
        """
        try:
            # Get items from global data
            items_file = self.db.global_dir / "items.json"
            items_data = await self.db._read_json_file(items_file)
            
            if items_data is None:
                return DEFAULT_ITEMS
            
            return items_data
            
        except Exception as e:
            logger.error(f"Error getting all available items: {e}")
            return DEFAULT_ITEMS
    
    async def search_inventory(self, user_id: int, search_term: str) -> List[Dict[str, Any]]:
        """
        Search user's inventory for items matching a term
        
        Args:
            user_id: Discord user ID
            search_term: Term to search for
            
        Returns:
            List of matching items
        """
        try:
            inventory_data = await self.get_user_inventory(user_id)
            if not inventory_data:
                return []
            
            items = inventory_data.get('items', {})
            matching_items = []
            
            search_term = search_term.lower()
            
            for item_id, item_data in items.items():
                item_name = item_data.get('name', '').lower()
                item_description = item_data.get('description', '').lower()
                
                if (search_term in item_name or 
                    search_term in item_description or 
                    search_term in item_id.lower()):
                    matching_items.append({
                        'item_id': item_id,
                        **item_data
                    })
            
            return matching_items
            
        except Exception as e:
            logger.error(f"Error searching inventory for user {user_id}: {e}")
            return []