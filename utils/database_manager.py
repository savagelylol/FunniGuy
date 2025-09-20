"""
Database Manager for FunniGuy Discord Bot
Handles JSON-based data persistence with async operations, file locking, and data safety
"""
import os
import json
import asyncio
import aiofiles
import aiofiles.os
from typing import Dict, List, Optional, Any, Union, Type
from datetime import datetime, timedelta
import logging
from pathlib import Path
import shutil
import fcntl
from contextlib import asynccontextmanager
import time

from .schemas import (
    UserProfile, EconomyData, UserInventory, UserAchievements, 
    UserPets, UserRelationships, UserCooldowns, ServerSettings,
    Marriage, Pet, InventoryItem, Achievement, Cooldown,
    SchemaValidator, create_default_user_data,
    DEFAULT_ITEMS, DEFAULT_ACHIEVEMENTS
)

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class DataCorruptionError(DatabaseError):
    """Exception for corrupted data files"""
    pass


class ConcurrentAccessError(DatabaseError):
    """Exception for concurrent access conflicts"""
    pass


class DatabaseManager:
    """
    Comprehensive database manager for FunniGuy bot
    Handles JSON persistence with async operations and data safety
    """
    
    def __init__(self, data_directory: str = "data"):
        """
        Initialize the database manager
        
        Args:
            data_directory: Base directory for all data files
        """
        self.data_dir = Path(data_directory)
        self.backup_dir = self.data_dir / "backups"
        self.temp_dir = self.data_dir / "temp"
        
        # Data subdirectories
        self.users_dir = self.data_dir / "users"
        self.guilds_dir = self.data_dir / "guilds"
        self.global_dir = self.data_dir / "global"
        self.marriages_dir = self.data_dir / "marriages"
        
        # Lock files for concurrent access
        self.locks = {}
        self.lock_timeout = 30.0
        
        # Cache for frequently accessed data
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_timestamps = {}
        
        # Data validation
        self.validator = SchemaValidator()
        
        # Initialize directories
        asyncio.create_task(self._initialize_directories())
    
    async def _initialize_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.data_dir, self.backup_dir, self.temp_dir,
            self.users_dir, self.guilds_dir, self.global_dir, self.marriages_dir
        ]
        
        for directory in directories:
            try:
                await aiofiles.os.makedirs(directory, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                raise DatabaseError(f"Failed to initialize directories: {e}")
        
        # Initialize global data files
        await self._initialize_global_data()
    
    async def _initialize_global_data(self):
        """Initialize global data files with default values"""
        global_files = {
            'items.json': DEFAULT_ITEMS,
            'achievements.json': DEFAULT_ACHIEVEMENTS,
            'bot_stats.json': {
                'total_users': 0,
                'total_commands': 0,
                'startup_time': datetime.utcnow().isoformat(),
                'version': '1.0.0'
            }
        }
        
        for filename, default_data in global_files.items():
            file_path = self.global_dir / filename
            if not await aiofiles.os.path.exists(file_path):
                await self._write_json_file(file_path, default_data)
    
    @asynccontextmanager
    async def _file_lock(self, file_path: Union[str, Path]):
        """
        Async context manager for file locking to prevent concurrent access
        
        Args:
            file_path: Path to the file to lock
        """
        file_path = str(file_path)
        lock_key = f"{file_path}.lock"
        
        # Check if lock already exists
        if lock_key in self.locks:
            # Wait for existing lock to be released
            start_time = time.time()
            while lock_key in self.locks:
                if time.time() - start_time > self.lock_timeout:
                    raise ConcurrentAccessError(f"Lock timeout for {file_path}")
                await asyncio.sleep(0.1)
        
        # Acquire lock
        self.locks[lock_key] = True
        
        try:
            yield
        finally:
            # Release lock
            self.locks.pop(lock_key, None)
    
    async def _read_json_file(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Safely read a JSON file with error handling
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Parsed JSON data or None if file doesn't exist
        """
        file_path = Path(file_path)
        
        if not await aiofiles.os.path.exists(file_path):
            return None
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
                if not content.strip():
                    logger.warning(f"Empty file found: {file_path}")
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            # Try to restore from backup
            backup_data = await self._restore_from_backup(file_path)
            if backup_data is not None:
                return backup_data
            raise DataCorruptionError(f"Corrupted JSON file: {file_path}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise DatabaseError(f"Failed to read file: {e}")
    
    async def _write_json_file(self, file_path: Union[str, Path], data: Dict[str, Any]):
        """
        Safely write data to a JSON file with atomic operations
        
        Args:
            file_path: Path to the JSON file
            data: Data to write
        """
        file_path = Path(file_path)
        temp_path = self.temp_dir / f"{file_path.name}.tmp"
        
        try:
            # Write to temporary file first
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Create backup before replacing
            if await aiofiles.os.path.exists(file_path):
                await self._create_backup(file_path)
            
            # Atomic move (replace original with temp file)
            await aiofiles.os.replace(temp_path, file_path)
            
        except Exception as e:
            # Clean up temp file if it exists
            if await aiofiles.os.path.exists(temp_path):
                await aiofiles.os.remove(temp_path)
            logger.error(f"Error writing file {file_path}: {e}")
            raise DatabaseError(f"Failed to write file: {e}")
    
    async def _create_backup(self, file_path: Union[str, Path]):
        """
        Create a backup of a file
        
        Args:
            file_path: Path to the file to backup
        """
        file_path = Path(file_path)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}.json"
        backup_path = self.backup_dir / backup_name
        
        try:
            if await aiofiles.os.path.exists(file_path):
                shutil.copy2(file_path, backup_path)
                logger.debug(f"Created backup: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup for {file_path}: {e}")
    
    async def _restore_from_backup(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Attempt to restore data from the most recent backup
        
        Args:
            file_path: Path to the corrupted file
            
        Returns:
            Restored data or None if no valid backup found
        """
        file_path = Path(file_path)
        backup_pattern = f"{file_path.stem}_*.json"
        
        try:
            backup_files = list(self.backup_dir.glob(backup_pattern))
            if not backup_files:
                return None
            
            # Sort by modification time (most recent first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup_file in backup_files:
                try:
                    data = await self._read_json_file(backup_file)
                    if data is not None:
                        logger.info(f"Restored data from backup: {backup_file}")
                        # Copy backup to original location
                        await self._write_json_file(file_path, data)
                        return data
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error during backup restoration: {e}")
            return None
    
    def _get_user_file_path(self, user_id: int, data_type: str) -> Path:
        """
        Get the file path for user data
        
        Args:
            user_id: Discord user ID
            data_type: Type of data (profile, economy, inventory, etc.)
            
        Returns:
            Path to the user data file
        """
        user_dir = self.users_dir / str(user_id)
        return user_dir / f"{data_type}.json"
    
    def _get_guild_file_path(self, guild_id: int) -> Path:
        """
        Get the file path for guild settings
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Path to the guild settings file
        """
        return self.guilds_dir / f"{guild_id}.json"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Check if cached data is still valid
        
        Args:
            cache_key: Key for the cached data
            
        Returns:
            True if cache is valid, False otherwise
        """
        if cache_key not in self.cache_timestamps:
            return False
        
        timestamp = self.cache_timestamps[cache_key]
        return (datetime.utcnow() - timestamp).total_seconds() < self.cache_ttl
    
    def _set_cache(self, cache_key: str, data: Any):
        """
        Set data in cache with timestamp
        
        Args:
            cache_key: Key for caching
            data: Data to cache
        """
        self.cache[cache_key] = data
        self.cache_timestamps[cache_key] = datetime.utcnow()
    
    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """
        Get data from cache if valid
        
        Args:
            cache_key: Key for cached data
            
        Returns:
            Cached data or None if not found/expired
        """
        if self._is_cache_valid(cache_key):
            return self.cache.get(cache_key)
        else:
            # Clean up expired cache
            self.cache.pop(cache_key, None)
            self.cache_timestamps.pop(cache_key, None)
            return None
    
    async def create_user(self, user_id: int, username: str, display_name: str) -> bool:
        """
        Create a new user with default data
        
        Args:
            user_id: Discord user ID
            username: User's username
            display_name: User's display name
            
        Returns:
            True if user was created, False if already exists
        """
        user_dir = self.users_dir / str(user_id)
        
        # Check if user already exists
        if await aiofiles.os.path.exists(user_dir):
            return False
        
        try:
            # Create user directory
            await aiofiles.os.makedirs(user_dir, exist_ok=True)
            
            # Create default user data
            default_data = create_default_user_data(user_id, username, display_name)
            
            # Save each data type to separate files
            for data_type, data_content in default_data.items():
                file_path = self._get_user_file_path(user_id, data_type)
                async with self._file_lock(file_path):
                    await self._write_json_file(file_path, data_content)
            
            logger.info(f"Created new user: {user_id} ({username})")
            
            # Update bot stats
            await self._increment_user_count()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            raise DatabaseError(f"Failed to create user: {e}")
    
    async def user_exists(self, user_id: int) -> bool:
        """
        Check if a user exists in the database
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if user exists, False otherwise
        """
        user_dir = self.users_dir / str(user_id)
        return await aiofiles.os.path.exists(user_dir)
    
    async def get_user_data(self, user_id: int, data_type: str) -> Optional[Dict[str, Any]]:
        """
        Get specific user data by type
        
        Args:
            user_id: Discord user ID
            data_type: Type of data to retrieve
            
        Returns:
            User data dictionary or None if not found
        """
        cache_key = f"user_{user_id}_{data_type}"
        
        # Check cache first
        cached_data = self._get_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        file_path = self._get_user_file_path(user_id, data_type)
        
        async with self._file_lock(file_path):
            data = await self._read_json_file(file_path)
            
            if data is not None:
                # Cache the data
                self._set_cache(cache_key, data)
            
            return data
    
    async def save_user_data(self, user_id: int, data_type: str, data: Dict[str, Any]):
        """
        Save user data of specific type
        
        Args:
            user_id: Discord user ID
            data_type: Type of data to save
            data: Data to save
        """
        # Validate data before saving
        if data_type == 'profile' and not self.validator.validate_user_profile(data):
            raise DatabaseError("Invalid user profile data structure")
        elif data_type == 'economy' and not self.validator.validate_economy_data(data):
            raise DatabaseError("Invalid economy data structure")
        elif data_type == 'inventory' and not self.validator.validate_inventory_data(data):
            raise DatabaseError("Invalid inventory data structure")
        
        file_path = self._get_user_file_path(user_id, data_type)
        
        # Ensure user directory exists
        user_dir = file_path.parent
        await aiofiles.os.makedirs(user_dir, exist_ok=True)
        
        async with self._file_lock(file_path):
            await self._write_json_file(file_path, data)
        
        # Update cache
        cache_key = f"user_{user_id}_{data_type}"
        self._set_cache(cache_key, data)
        
        logger.debug(f"Saved {data_type} data for user {user_id}")
    
    async def update_user_data(self, user_id: int, data_type: str, updates: Dict[str, Any]):
        """
        Update specific fields in user data
        
        Args:
            user_id: Discord user ID
            data_type: Type of data to update
            updates: Dictionary of fields to update
        """
        current_data = await self.get_user_data(user_id, data_type)
        if current_data is None:
            raise DatabaseError(f"User {user_id} {data_type} data not found")
        
        # Apply updates
        current_data.update(updates)
        
        # Save updated data
        await self.save_user_data(user_id, data_type, current_data)
    
    async def delete_user(self, user_id: int) -> bool:
        """
        Delete all user data (with backup)
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if user was deleted, False if not found
        """
        user_dir = self.users_dir / str(user_id)
        
        if not await aiofiles.os.path.exists(user_dir):
            return False
        
        try:
            # Create backups of all user files before deletion
            for file_path in user_dir.glob("*.json"):
                await self._create_backup(file_path)
            
            # Remove user directory
            shutil.rmtree(user_dir)
            
            # Clear cache
            for key in list(self.cache.keys()):
                if key.startswith(f"user_{user_id}_"):
                    self.cache.pop(key, None)
                    self.cache_timestamps.pop(key, None)
            
            logger.info(f"Deleted user data for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise DatabaseError(f"Failed to delete user: {e}")
    
    async def get_guild_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """
        Get guild settings
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Guild settings or None if not found
        """
        file_path = self._get_guild_file_path(guild_id)
        return await self._read_json_file(file_path)
    
    async def save_guild_settings(self, guild_id: int, settings: Dict[str, Any]):
        """
        Save guild settings
        
        Args:
            guild_id: Discord guild ID
            settings: Guild settings to save
        """
        file_path = self._get_guild_file_path(guild_id)
        
        async with self._file_lock(file_path):
            await self._write_json_file(file_path, settings)
    
    async def get_all_marriages(self) -> Dict[str, Any]:
        """
        Get all marriage data
        
        Returns:
            Dictionary of all marriages
        """
        marriages_file = self.marriages_dir / "marriages.json"
        data = await self._read_json_file(marriages_file)
        return data if data is not None else {}
    
    async def save_marriage(self, marriage_id: str, marriage_data: Dict[str, Any]):
        """
        Save marriage data
        
        Args:
            marriage_id: Unique marriage ID
            marriage_data: Marriage data to save
        """
        marriages_file = self.marriages_dir / "marriages.json"
        
        async with self._file_lock(marriages_file):
            all_marriages = await self.get_all_marriages()
            all_marriages[marriage_id] = marriage_data
            await self._write_json_file(marriages_file, all_marriages)
    
    async def _increment_user_count(self):
        """Increment the total user count in bot stats"""
        stats_file = self.global_dir / "bot_stats.json"
        
        async with self._file_lock(stats_file):
            stats = await self._read_json_file(stats_file)
            if stats is None:
                stats = {'total_users': 0, 'total_commands': 0}
            
            stats['total_users'] = stats.get('total_users', 0) + 1
            await self._write_json_file(stats_file, stats)
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """
        Get bot statistics
        
        Returns:
            Bot statistics dictionary
        """
        stats_file = self.global_dir / "bot_stats.json"
        data = await self._read_json_file(stats_file)
        return data if data is not None else {}
    
    async def cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, timestamp in self.cache_timestamps.items():
            if (current_time - timestamp).total_seconds() >= self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def create_full_backup(self) -> str:
        """
        Create a full backup of all data
        
        Returns:
            Path to the backup archive
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"full_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        try:
            # Create backup directory
            await aiofiles.os.makedirs(backup_path, exist_ok=True)
            
            # Copy all data directories
            for source_dir in [self.users_dir, self.guilds_dir, self.global_dir, self.marriages_dir]:
                if await aiofiles.os.path.exists(source_dir):
                    dest_dir = backup_path / source_dir.name
                    shutil.copytree(source_dir, dest_dir)
            
            # Create archive
            archive_path = f"{backup_path}.tar.gz"
            shutil.make_archive(str(backup_path), 'gztar', str(backup_path))
            
            # Remove uncompressed backup directory
            shutil.rmtree(backup_path)
            
            logger.info(f"Created full backup: {archive_path}")
            return archive_path
            
        except Exception as e:
            logger.error(f"Error creating full backup: {e}")
            raise DatabaseError(f"Failed to create backup: {e}")
    
    async def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information and statistics
        
        Returns:
            Database information dictionary
        """
        try:
            user_count = len([d for d in self.users_dir.iterdir() if d.is_dir()])
            guild_count = len(list(self.guilds_dir.glob("*.json")))
            cache_size = len(self.cache)
            
            total_size = 0
            for root, dirs, files in os.walk(self.data_dir):
                for file in files:
                    total_size += os.path.getsize(os.path.join(root, file))
            
            return {
                'total_users': user_count,
                'total_guilds': guild_count,
                'cache_entries': cache_size,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'data_directory': str(self.data_dir),
                'backup_directory': str(self.backup_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {'error': str(e)}