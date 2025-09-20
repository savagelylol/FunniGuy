"""
FunniGuy Discord Bot - Main Bot File
"""
import os
import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.embeds import create_success_embed, create_error_embed, create_info_embed

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
        
        self.initial_extensions = [
            # Add cog files here when created
        ]
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Setting up FunniGuy Bot...")
        
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
    
    async def on_error(self, event_method: str, *args, **kwargs):
        """Global error handler"""
        logger.error(f"An error occurred in {event_method}", exc_info=True)
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            embed = create_error_embed("Command not found! Use `/help` to see available commands.")
            await ctx.send(embed=embed, ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = create_error_embed(f"Missing required argument: {error.param.name}")
            await ctx.send(embed=embed, ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            embed = create_error_embed("You don't have permission to use this command!")
            await ctx.send(embed=embed, ephemeral=True)
        else:
            logger.error(f"Unhandled command error: {error}", exc_info=True)
            embed = create_error_embed("An unexpected error occurred. Please try again later.")
            await ctx.send(embed=embed, ephemeral=True)


# Create bot instance
bot = FunniGuyBot()


# Test slash command
@bot.tree.command(name="ping", description="Test command to check if the bot is working")
async def ping_command(interaction: discord.Interaction):
    """Simple ping command to test bot functionality"""
    latency = round(bot.latency * 1000)
    embed = create_success_embed(
        f"Pong! 🏓\nLatency: {latency}ms",
        title="Bot Status"
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="hello", description="Get a friendly greeting from FunniGuy!")
async def hello_command(interaction: discord.Interaction):
    """Friendly greeting command"""
    embed = create_info_embed(
        f"Hello there, {interaction.user.mention}! 👋\n"
        f"I'm FunniGuy, your friendly Discord bot! 😄\n"
        f"I'm here to make your server more fun and entertaining!",
        title="Hello!"
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="info", description="Get information about FunniGuy bot")
async def info_command(interaction: discord.Interaction):
    """Bot information command"""
    embed = discord.Embed(
        title="🤖 FunniGuy Bot Info",
        description="A fun and entertaining Discord bot!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📊 Stats",
        value=f"Servers: {len(bot.guilds)}\nLatency: {round(bot.latency * 1000)}ms",
        inline=True
    )
    
    embed.add_field(
        name="🛠️ Built with",
        value="discord.py\nPython 3.11",
        inline=True
    )
    
    embed.add_field(
        name="🎯 Purpose",
        value="To bring fun and entertainment to your Discord server!",
        inline=False
    )
    
    embed.set_footer(text="FunniGuy Bot", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
    
    await interaction.response.send_message(embed=embed)


# Regular prefix command for testing
@bot.command(name="test")
async def test_command(ctx: commands.Context):
    """Test prefix command"""
    embed = create_success_embed(
        "Prefix commands are working! ✅",
        title="Test Command"
    )
    await ctx.send(embed=embed)


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