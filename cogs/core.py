"""
Core Cog for FunniGuy Discord Bot
Contains basic commands and functionality
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import TYPE_CHECKING

from utils.embeds import create_success_embed, create_error_embed, create_info_embed

if TYPE_CHECKING:
    from bot import FunniGuyBot

logger = logging.getLogger(__name__)


class Core(commands.Cog):
    """Core commands and functionality"""
    
    def __init__(self, bot: "FunniGuyBot"):
        self.bot = bot

    @app_commands.command(name="ping", description="Test command to check if the bot is working")
    async def ping_command(self, interaction: discord.Interaction):
        """Simple ping command to test bot functionality"""
        # Process command through data manager
        cmd_result = await self.bot.data_manager.process_command(
            interaction.user.id, 
            interaction.user.name, 
            interaction.user.display_name,
            "ping"
        )
        
        if not cmd_result.get('can_execute', False):
            error_msg = cmd_result.get('error', 'Unknown error')
            embed = create_error_embed(f"Cannot execute command: {error_msg}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        latency = round(self.bot.latency * 1000)
        embed = create_success_embed(
            f"Pong! 🏓\nLatency: {latency}ms",
            title="Bot Status"
        )
        await interaction.response.send_message(embed=embed)
        
        # Complete command processing
        await self.bot.data_manager.complete_command(interaction.user.id, "ping")

    @commands.command(name="hello")
    async def hello_command(self, ctx: commands.Context):
        """Friendly greeting command"""
        embed = create_info_embed(
            f"Hello there, {ctx.author.mention}! 👋\n"
            f"I'm FunniGuy, your friendly Discord bot! 😄\n"
            f"I'm here to make your server more fun and entertaining!",
            title="Hello!"
        )
        await ctx.send(embed=embed)

    @commands.command(name="info")
    async def info_command(self, ctx: commands.Context):
        """Bot information command"""
        # Get system status from data manager
        system_status = await self.bot.data_manager.get_system_status()
        db_info = system_status.get('database_info', {})
        
        embed = discord.Embed(
            title="🤖 FunniGuy Bot Info",
            description="A complete Dank Memer clone with 80+ commands!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Stats",
            value=f"Servers: {len(self.bot.guilds)}\nLatency: {round(self.bot.latency * 1000)}ms\nUsers: {db_info.get('total_users', 0)}",
            inline=True
        )
        
        embed.add_field(
            name="🛠️ Built with",
            value="discord.py\nPython 3.11\nJSON Data Persistence",
            inline=True
        )
        
        embed.add_field(
            name="💾 Data System",
            value=f"Status: {'✅ Online' if system_status.get('initialized') else '❌ Offline'}\nData Size: {db_info.get('total_size_mb', 0)}MB",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Features",
            value="• 80+ Commands\n• Economy System\n• Gambling & Games\n• Fun & Meme Commands\n• Social Features\n• Pet System\n• Marriage System",
            inline=False
        )
        
        embed.set_footer(text="FunniGuy Bot - Dank Memer Clone", icon_url=self.bot.user.avatar.url if self.bot.user and self.bot.user.avatar else None)
        
        await ctx.send(embed=embed)

    @commands.command(name="profile")
    async def profile_command(self, ctx: commands.Context):
        """Display user profile with comprehensive statistics"""
        # Get comprehensive user overview
        user_overview = await self.bot.data_manager.get_user_overview(ctx.author.id)
        
        if 'error' in user_overview:
            embed = create_error_embed("Failed to retrieve profile data")
            await ctx.send(embed=embed)
            return
        
        profile = user_overview.get('profile', {})
        economy = user_overview.get('economy', {})
        achievements = user_overview.get('achievements', {})
        
        embed = discord.Embed(
            title=f"👤 {ctx.author.display_name}'s Profile",
            color=discord.Color.green()
        )
        
        # Basic info
        level_info = profile.get('level_info', {})
        embed.add_field(
            name="📊 Level & Experience",
            value=f"Level: {level_info.get('level', 1)}\nXP: {level_info.get('experience', 0)}\nProgress: {level_info.get('progress_percentage', 0)}%",
            inline=True
        )
        
        # Economy info
        balances = economy.get('balances', {})
        embed.add_field(
            name="💰 Economy",
            value=f"Pocket: {balances.get('pocket', 0)} coins\nBank: {balances.get('bank', 0)} coins\nTotal: {balances.get('total', 0)} coins",
            inline=True
        )
        
        # Achievement info
        embed.add_field(
            name="🏆 Achievements",
            value=f"Unlocked: {achievements.get('unlocked_count', 0)}\nCompletion: {achievements.get('completion_percentage', 0)}%\nPoints: {achievements.get('achievement_points', 0)}",
            inline=True
        )
        
        # Activity info
        activity = profile.get('activity', {})
        embed.add_field(
            name="⚡ Activity",
            value=f"Commands Used: {activity.get('total_commands_used', 0)}\nToday: {activity.get('daily_commands_used', 0)}\nRemaining: {activity.get('commands_remaining_today', 0)}",
            inline=True
        )
        
        # Additional info
        social = profile.get('social', {})
        marriage_status = "Single" if not user_overview.get('marriage') else "Married"
        active_pet = user_overview.get('active_pet')
        pet_name = active_pet.get('name', 'None') if active_pet else 'None'
        
        embed.add_field(
            name="👥 Social & Pets",
            value=f"Friends: {social.get('friends_count', 0)}\nStatus: {marriage_status}\nActive Pet: {pet_name}",
            inline=True
        )
        
        embed.add_field(
            name="📦 Collection",
            value=f"Items: {user_overview.get('inventory', {}).get('total_items', 0)}\nPets: {user_overview.get('total_pets', 0)}\nAchievements: {achievements.get('unlocked_count', 0)}",
            inline=True
        )
        
        # Account info
        basic_info = profile.get('basic_info', {})
        embed.set_footer(text=f"Account created {basic_info.get('account_age_days', 0)} days ago")
        
        await ctx.send(embed=embed)

    @commands.command(name="balance", aliases=["bal"])
    async def balance_command(self, ctx: commands.Context):
        """Display user's current balance"""
        # Get user balance
        pocket, bank = await self.bot.data_manager.get_balance(ctx.author.id)
        total = pocket + bank
        
        embed = discord.Embed(
            title="💰 Your Balance",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💵 Pocket",
            value=f"{pocket:,} coins",
            inline=True
        )
        
        embed.add_field(
            name="🏦 Bank",
            value=f"{bank:,} coins",
            inline=True
        )
        
        embed.add_field(
            name="💎 Total",
            value=f"{total:,} coins",
            inline=True
        )
        
        # Add marriage bonus info if married
        is_married = await self.bot.data_manager.is_married(ctx.author.id)
        if is_married:
            embed.add_field(
                name="💕 Marriage Bonus",
                value="You receive bonus rewards from being married!",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="daily")
    async def daily_command(self, ctx: commands.Context):
        """Claim daily bonus"""
        # Claim daily bonus
        success, amount = await self.bot.data_manager.economy.claim_daily_bonus(ctx.author.id)
        
        if not success:
            embed = create_error_embed("Failed to claim daily bonus. You may have already claimed it today.")
            await ctx.send(embed=embed)
            return
        
        embed = create_success_embed(
            f"You claimed your daily bonus of {amount:,} coins! 🎉",
            title="Daily Bonus Claimed"
        )
        
        # Check if user is married for bonus message
        is_married = await self.bot.data_manager.is_married(ctx.author.id)
        if is_married:
            embed.add_field(
                name="💕 Marriage Bonus Applied!",
                value="You received extra coins for being married!",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="test")
    async def test_command(self, ctx: commands.Context):
        """Test prefix command"""
        embed = create_success_embed(
            "Prefix commands are working! ✅\nTry: fg profile, fg balance, fg daily, fg help",
            title="Test Command"
        )
        await ctx.send(embed=embed)


async def setup(bot: "FunniGuyBot"):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(Core(bot))