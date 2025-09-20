"""
Utility Cog for FunniGuy Discord Bot
Contains utility commands like help, leaderboard, settings, etc.
"""
import discord
from discord.ext import commands
import logging
from typing import Optional, List
import math

from utils.embeds import create_success_embed, create_error_embed, create_info_embed

logger = logging.getLogger(__name__)


class Utility(commands.Cog):
    """Utility commands and functionality"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context, *, category: str = None):
        """Show help for all commands or a specific category"""
        
        if category is None:
            # Main help menu
            embed = discord.Embed(
                title="🤖 FunniGuy Bot - Command Help",
                description="A complete Dank Memer clone with 80+ commands!\nUse `fg help <category>` for detailed commands.",
                color=discord.Color.blue()
            )
            
            categories = {
                "💰 Economy": "economy - Work, beg, crime, rob, bank, shop, inventory",
                "🎲 Gambling": "gambling - Blackjack, slots, gamble, highlow, scratch",
                "😄 Fun": "fun - 8ball, joke, roast, hack, ship, rate, emojify",
                "👥 Social": "social - Marriage, pets, friends, profile (coming soon)",
                "🛠️ Utility": "utility - Help, leaderboard, settings",
                "ℹ️ Core": "core - Ping, info, balance, daily, profile"
            }
            
            for category_name, description in categories.items():
                embed.add_field(name=category_name, value=description, inline=False)
                
            embed.set_footer(text="Example: fg help economy")
            
        elif category.lower() in ["economy", "eco", "money"]:
            embed = discord.Embed(
                title="💰 Economy Commands",
                description="Make money and manage your finances!",
                color=discord.Color.gold()
            )
            
            commands_list = [
                "`fg beg` - Beg for coins (30s cooldown)",
                "`fg work` - Work at a job (1h cooldown)", 
                "`fg crime` - Commit crimes for money (2h cooldown)",
                "`fg rob @user` - Rob another user (1h cooldown)",
                "`fg daily` - Claim daily bonus (24h cooldown)",
                "`fg weekly` - Claim weekly bonus (7d cooldown)",
                "`fg monthly` - Claim monthly bonus (30d cooldown)",
                "`fg deposit <amount>` - Put coins in bank",
                "`fg withdraw <amount>` - Take coins from bank",
                "`fg shop` - View the item shop",
                "`fg inventory` - View your items",
                "`fg balance` - Check your money"
            ]
            
            embed.description += "\n\n" + "\n".join(commands_list)
            
        elif category.lower() in ["gambling", "gamble", "games"]:
            embed = discord.Embed(
                title="🎲 Gambling Commands", 
                description="Risk it all for big rewards!",
                color=discord.Color.red()
            )
            
            commands_list = [
                "`fg gamble <amount>` - Roll dice vs bot",
                "`fg slots <amount>` - Play slot machine",
                "`fg blackjack <amount>` - Play blackjack",
                "`fg highlow <amount>` - Guess higher/lower",
                "`fg scratch <amount>` - Scratch card game"
            ]
            
            embed.description += "\n\n" + "\n".join(commands_list)
            
        elif category.lower() in ["fun", "meme", "jokes"]:
            embed = discord.Embed(
                title="😄 Fun Commands",
                description="Entertainment and meme commands!",
                color=discord.Color.purple()
            )
            
            commands_list = [
                "`fg 8ball <question>` - Ask magic 8-ball",
                "`fg joke` - Get a random joke",
                "`fg roast @user` - Roast someone",
                "`fg hack @user` - Fake hack someone",
                "`fg ship @user1 @user2` - Ship calculator", 
                "`fg rate <thing>` - Rate something out of 10",
                "`fg kill @user` - Fake kill someone",
                "`fg emojify <text>` - Convert text to emojis",
                "`fg clap <text>` - Add clap emojis",
                "`fg fortune` - Get fortune cookie",
                "`fg fact` - Random fun fact"
            ]
            
            embed.description += "\n\n" + "\n".join(commands_list)
            
        elif category.lower() in ["social", "marriage", "pets"]:
            embed = discord.Embed(
                title="👥 Social Commands",
                description="Social features (coming soon!)",
                color=discord.Color.pink()
            )
            
            embed.add_field(name="Coming Soon", value="Marriage, pets, friends, trading, and more!", inline=False)
            
        elif category.lower() in ["utility", "util", "settings"]:
            embed = discord.Embed(
                title="🛠️ Utility Commands",
                description="Helpful utility commands!",
                color=discord.Color.green()
            )
            
            commands_list = [
                "`fg help [category]` - Show this help menu",
                "`fg leaderboard` - View money leaderboard", 
                "`fg ping` - Check bot latency",
                "`fg info` - Bot information"
            ]
            
            embed.description += "\n\n" + "\n".join(commands_list)
            
        else:
            embed = create_error_embed(
                f"Unknown category '{category}'!\nValid categories: economy, gambling, fun, social, utility"
            )
            
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard_command(self, ctx: commands.Context, category: str = "money"):
        """Show leaderboards for various stats"""
        
        if category.lower() in ["money", "coins", "bal", "balance"]:
            embed = discord.Embed(
                title="💰 Money Leaderboard",
                description="Top richest users (coming soon!)",
                color=discord.Color.gold()
            )
            
            # TODO: Implement actual leaderboard from database
            embed.add_field(
                name="🏆 Top Users",
                value="Leaderboard system coming soon! 🚧\nYour stats are being tracked!",
                inline=False
            )
            
        elif category.lower() in ["level", "levels", "xp", "exp"]:
            embed = discord.Embed(
                title="⭐ Level Leaderboard",
                description="Top users by level (coming soon!)", 
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🏆 Top Users",
                value="Level leaderboard coming soon! 🚧",
                inline=False
            )
            
        else:
            embed = create_error_embed(
                f"Unknown leaderboard category '{category}'!\nValid categories: money, level"
            )
            
        await ctx.send(embed=embed)

    @commands.command(name="cooldowns", aliases=["cd"])
    async def cooldowns_command(self, ctx: commands.Context):
        """Check your command cooldowns"""
        user_id = ctx.author.id
        
        embed = discord.Embed(
            title="⏰ Your Cooldowns",
            description="Command cooldowns and when you can use them again",
            color=discord.Color.orange()
        )
        
        # Get cooldown info from bot's command cooldowns
        cooldown_commands = {
            "beg": "30 seconds",
            "work": "1 hour", 
            "crime": "2 hours",
            "rob": "1 hour",
            "daily": "24 hours",
            "weekly": "7 days",
            "monthly": "30 days",
            "gamble": "5 minutes",
            "slots": "3 minutes", 
            "blackjack": "4 minutes",
            "highlow": "2 minutes",
            "scratch": "10 minutes"
        }
        
        ready_commands = []
        cooldown_commands_list = []
        
        for cmd_name, cooldown_time in cooldown_commands.items():
            command = self.bot.get_command(cmd_name)
            if command:
                # Check if command is on cooldown
                bucket = command._buckets.get_bucket(ctx.message)
                retry_after = bucket.get_retry_after()
                
                if retry_after:
                    # On cooldown
                    hours, remainder = divmod(int(retry_after), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    if hours:
                        time_left = f"{hours}h {minutes}m {seconds}s"
                    elif minutes:
                        time_left = f"{minutes}m {seconds}s"
                    else:
                        time_left = f"{seconds}s"
                        
                    cooldown_commands_list.append(f"`{cmd_name}` - {time_left} left")
                else:
                    # Ready to use
                    ready_commands.append(f"`{cmd_name}`")
                    
        if ready_commands:
            embed.add_field(
                name="✅ Ready to Use",
                value=" • ".join(ready_commands[:10]),  # Limit to prevent embed being too long
                inline=False
            )
            
        if cooldown_commands_list:
            embed.add_field(
                name="⏱️ On Cooldown", 
                value="\n".join(cooldown_commands_list[:10]),
                inline=False
            )
            
        if not ready_commands and not cooldown_commands_list:
            embed.description = "All your commands are ready to use! 🎉"
            
        await ctx.send(embed=embed)

    @commands.command(name="stats")
    async def stats_command(self, ctx: commands.Context, user: discord.Member = None):
        """View detailed statistics for a user"""
        if user is None:
            user = ctx.author
            
        embed = discord.Embed(
            title=f"📊 {user.display_name}'s Statistics",
            color=discord.Color.blue()
        )
        
        # TODO: Get actual stats from database
        embed.add_field(name="Commands Used", value="Coming soon! 🚧", inline=True)
        embed.add_field(name="Money Earned", value="Coming soon! 🚧", inline=True) 
        embed.add_field(name="Gambling Wins", value="Coming soon! 🚧", inline=True)
        embed.add_field(name="Items Owned", value="Coming soon! 🚧", inline=True)
        embed.add_field(name="Achievement Points", value="Coming soon! 🚧", inline=True)
        embed.add_field(name="Level", value="Coming soon! 🚧", inline=True)
        
        embed.set_footer(text="Detailed statistics system coming soon!")
        await ctx.send(embed=embed)

    @commands.command(name="prefix")
    @commands.has_permissions(administrator=True)
    async def prefix_command(self, ctx: commands.Context, new_prefix: str = None):
        """Change the bot's command prefix (Admin only)"""
        if new_prefix is None:
            embed = create_info_embed(
                f"Current prefix: `{self.bot.command_prefix}`\n"
                f"Usage: `{self.bot.command_prefix}prefix <new_prefix>`",
                title="Command Prefix"
            )
            await ctx.send(embed=embed)
            return
            
        if len(new_prefix) > 5:
            embed = create_error_embed("Prefix cannot be longer than 5 characters!")
            await ctx.send(embed=embed)
            return
            
        # For now, just show a message. In a real implementation, 
        # you'd save this to the database per-guild
        embed = create_info_embed(
            f"Prefix change is not implemented yet! 🚧\n"
            f"The bot will always use `fg ` as the prefix for now.",
            title="Prefix Change"
        )
        await ctx.send(embed=embed)

    @commands.command(name="invite")
    async def invite_command(self, ctx: commands.Context):
        """Get bot invite link"""
        # Create invite URL with necessary permissions
        permissions = discord.Permissions(
            read_messages=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            use_external_emojis=True
        )
        
        invite_url = discord.utils.oauth_url(self.bot.user.id, permissions=permissions)
        
        embed = discord.Embed(
            title="🤖 Invite FunniGuy Bot",
            description=f"[Click here to invite me to your server!]({invite_url})",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Features",
            value="• 80+ Commands\n• Economy System\n• Gambling Games\n• Fun Commands\n• And much more!",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="support")
    async def support_command(self, ctx: commands.Context):
        """Get support information"""
        embed = discord.Embed(
            title="🆘 Support & Information",
            description="Need help with FunniGuy Bot?",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📚 Commands",
            value="Use `fg help` to see all commands!",
            inline=False
        )
        embed.add_field(
            name="🐛 Found a Bug?",
            value="This bot is a Dank Memer clone created by AI!\nReport issues to your bot admin.",
            inline=False
        )
        embed.add_field(
            name="💡 Suggestions",
            value="Have ideas for new features? Let us know!",
            inline=False
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(Utility(bot))