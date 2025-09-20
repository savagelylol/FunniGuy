"""
FunniGuy Discord Bot - Main Bot File
"""
import os
import asyncio
import logging
from typing import Optional, List

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.embeds import create_success_embed, create_error_embed, create_info_embed
from utils.data_manager import DataManager
from datetime import datetime

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class FunniGuyBot(commands.Bot):
    """Main FunniGuy Bot class"""
    
    # Type hints for dynamically added attributes
    data_manager: DataManager
    initial_extensions: List[str]
    
    def __init__(self):
        # Define intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Enable if you need member events
        
        # Initialize bot
        super().__init__(
            command_prefix=os.getenv('BOT_PREFIX', '!'),
            intents=intents,
            help_command=None  # We'll create custom help
        )
        
        # Initialize data manager
        self.data_manager = DataManager('data')
        
        self.initial_extensions = [
            'cogs.core',
        ]
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Setting up FunniGuy Bot...")
        
        # Initialize data manager
        data_init_success = await self.data_manager.initialize()
        if not data_init_success:
            logger.error("Failed to initialize data manager!")
            return
        
        logger.info("Data manager initialized successfully!")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        
        # Load extensions
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guilds")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Game(name="Making people laugh! 😄"),
            status=discord.Status.online
        )
        
        # Log system status
        system_status = await self.data_manager.get_system_status()
        logger.info(f"Data system status: {system_status.get('initialized', False)}")
    
    async def close(self):
        """Called when the bot is shutting down"""
        logger.info("Shutting down FunniGuy Bot...")
        await self.data_manager.shutdown()
        await super().close()
    
    async def on_error(self, event_method: str, *args, **kwargs):
        """Global error handler"""
        logger.error(f"An error occurred in {event_method}", exc_info=True)
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            embed = create_error_embed("Command not found! Use `/help` to see available commands.")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = create_error_embed(f"Missing required argument: {error.param.name}")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = create_error_embed("You don't have permission to use this command!")
            await ctx.send(embed=embed)
        else:
            logger.error(f"Unhandled command error: {error}", exc_info=True)
            embed = create_error_embed("An unexpected error occurred. Please try again later.")
            await ctx.send(embed=embed)


# Create bot instance
bot = FunniGuyBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle slash command errors"""
    if isinstance(error, discord.app_commands.CommandNotFound):
        embed = create_error_embed("Command not found! This command may have been removed or renamed.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, discord.app_commands.MissingPermissions):
        embed = create_error_embed("You don't have permission to use this command!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        embed = create_error_embed(f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, discord.app_commands.MissingAnyRole):
        embed = create_error_embed("You don't have any of the required roles to use this command!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        embed = create_error_embed("I don't have the required permissions to execute this command!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        logger.error(f"Unhandled slash command error: {error}", exc_info=True)
        embed = create_error_embed("An unexpected error occurred. Please try again later.")
        
        # Check if we can still respond
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


# Commands are now handled by cogs - see cogs/core.py


def main():
    """Main function to run the bot"""
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        logger.error("Please create a .env file with your Discord bot token.")
        logger.error("See .env.example for the required format.")
        return
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord token provided!")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")


if __name__ == "__main__":
    main()