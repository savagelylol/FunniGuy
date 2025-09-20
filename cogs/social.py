"""
Social Cog for FunniGuy Discord Bot
Contains marriage, pets, friends, achievements, and other social features
"""
import discord
from discord.ext import commands
import random
import asyncio
from typing import Optional, List
import logging

from utils.embeds import create_success_embed, create_error_embed, create_info_embed

logger = logging.getLogger(__name__)


class Social(commands.Cog):
    """Social features and interactions"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="marry", aliases=["propose"])
    async def marry_command(self, ctx: commands.Context, user: discord.Member = None):
        """Marry another user"""
        if user is None:
            embed = create_error_embed("You need to specify someone to marry!\nUsage: `fg marry @user`")
            await ctx.send(embed=embed)
            return
            
        if user.id == ctx.author.id:
            embed = create_error_embed("You can't marry yourself! 💔")
            await ctx.send(embed=embed)
            return
            
        if user.bot:
            embed = create_error_embed("You can't marry bots! They don't have feelings... 🤖💔")
            await ctx.send(embed=embed)
            return
            
        # Check if either user is already married
        author_married = await self.bot.data_manager.is_married(ctx.author.id)
        target_married = await self.bot.data_manager.is_married(user.id)
        
        if author_married:
            embed = create_error_embed("You're already married! Divorce first if you want to remarry.")
            await ctx.send(embed=embed)
            return
            
        if target_married:
            embed = create_error_embed(f"{user.display_name} is already married to someone else!")
            await ctx.send(embed=embed)
            return
            
        # Send proposal
        embed = discord.Embed(
            title="💍 Marriage Proposal",
            description=f"{ctx.author.mention} is proposing to {user.mention}!\n\n💕 Will you marry them? 💕",
            color=discord.Color.pink()
        )
        embed.set_footer(text="React with 💍 to accept or 💔 to reject")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("💍")
        await message.add_reaction("💔")
        
        def check(reaction, react_user):
            return (react_user == user and 
                   str(reaction.emoji) in ["💍", "💔"] and 
                   reaction.message == message)
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            
            if str(reaction.emoji) == "💍":
                # Accept proposal
                await self.bot.data_manager.marriage.create_marriage(ctx.author.id, user.id)
                
                embed = create_success_embed(
                    f"🎉 **Congratulations!** 🎉\n"
                    f"{ctx.author.mention} and {user.mention} are now married!\n"
                    f"💕 You both get a 10% bonus on all earnings! 💕",
                    title="Marriage Complete"
                )
                await message.edit(embed=embed)
                
            else:
                # Reject proposal
                embed = create_error_embed(
                    f"💔 **Proposal Rejected!**\n{user.mention} said no... Better luck next time!",
                    title="Marriage Rejected"
                )
                await message.edit(embed=embed)
                
        except asyncio.TimeoutError:
            embed = create_error_embed("⏰ The proposal timed out! No response from the proposed user.")
            await message.edit(embed=embed)

    @commands.command(name="divorce")
    async def divorce_command(self, ctx: commands.Context):
        """Divorce your current spouse"""
        user_id = ctx.author.id
        
        married = await self.bot.data_manager.is_married(user_id)
        if not married:
            embed = create_error_embed("You're not married! Use `fg marry @user` to find love.")
            await ctx.send(embed=embed)
            return
            
        # Get spouse info
        marriage_data = await self.bot.data_manager.marriage.get_marriage(user_id)
        spouse_id = marriage_data.get('spouse_id')
        
        # Confirm divorce
        embed = discord.Embed(
            title="💔 Divorce Confirmation",
            description="Are you sure you want to divorce? This action cannot be undone!\n\nYou'll lose your marriage bonus.",
            color=discord.Color.red()
        )
        embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return (user == ctx.author and 
                   str(reaction.emoji) in ["✅", "❌"] and 
                   reaction.message == message)
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                await self.bot.data_manager.marriage.end_marriage(user_id)
                
                embed = create_success_embed(
                    "💔 **Divorce Complete**\nYou are now single again. Your marriage bonus has been removed.",
                    title="Divorce Finalized"
                )
            else:
                embed = create_info_embed("❌ **Divorce Cancelled**\nYour marriage remains intact!", title="Cancelled")
                
            await message.edit(embed=embed)
            
        except asyncio.TimeoutError:
            embed = create_error_embed("⏰ Divorce confirmation timed out.")
            await message.edit(embed=embed)

    @commands.command(name="pet")
    async def pet_command(self, ctx: commands.Context, action: str = None, *, target: str = None):
        """Manage your virtual pets"""
        if action is None:
            embed = discord.Embed(
                title="🐾 Pet Commands",
                description="Manage your virtual pets!",
                color=discord.Color.blue()
            )
            
            commands_list = [
                "`fg pet adopt <type>` - Adopt a new pet",
                "`fg pet list` - View your pets",
                "`fg pet feed <name>` - Feed your pet",
                "`fg pet play <name>` - Play with your pet",
                "`fg pet rename <old> <new>` - Rename your pet"
            ]
            
            embed.add_field(name="Commands", value="\\n".join(commands_list), inline=False)
            embed.add_field(
                name="Available Pet Types",
                value="dog, cat, bird, fish, hamster, rabbit",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        if action.lower() == "adopt":
            if target is None:
                embed = create_error_embed("Specify a pet type to adopt!\nAvailable: dog, cat, bird, fish, hamster, rabbit")
                await ctx.send(embed=embed)
                return
                
            pet_types = {
                "dog": {"emoji": "🐕", "cost": 500, "happiness": 80},
                "cat": {"emoji": "🐱", "cost": 400, "happiness": 70},
                "bird": {"emoji": "🐦", "cost": 300, "happiness": 85},
                "fish": {"emoji": "🐠", "cost": 200, "happiness": 60},
                "hamster": {"emoji": "🐹", "cost": 250, "happiness": 75},
                "rabbit": {"emoji": "🐰", "cost": 350, "happiness": 90}
            }
            
            if target.lower() not in pet_types:
                embed = create_error_embed("Invalid pet type! Available: " + ", ".join(pet_types.keys()))
                await ctx.send(embed=embed)
                return
                
            pet_info = pet_types[target.lower()]
            user_id = ctx.author.id
            
            # Check if user can afford
            pocket, _ = await self.bot.data_manager.get_balance(user_id)
            if pocket < pet_info["cost"]:
                embed = create_error_embed(f"You need {pet_info['cost']} coins to adopt a {target}!")
                await ctx.send(embed=embed)
                return
                
            # Deduct cost
            await self.bot.data_manager.economy.remove_coins(user_id, pet_info["cost"], "pocket", f"Pet adoption ({target})")
            
            # Generate random pet name
            names = ["Buddy", "Luna", "Max", "Bella", "Charlie", "Lucy", "Rocky", "Molly", "Jack", "Daisy"]
            pet_name = random.choice(names)
            
            embed = create_success_embed(
                f"{pet_info['emoji']} **Pet Adopted!**\\n"
                f"You adopted a {target} named **{pet_name}**!\\n"
                f"Cost: {pet_info['cost']} coins\\n\\n"
                f"Use `fg pet feed {pet_name}` and `fg pet play {pet_name}` to keep them happy!",
                title="New Pet"
            )
            await ctx.send(embed=embed)
            
        elif action.lower() == "list":
            embed = create_info_embed("Your pet collection is coming soon! 🚧", title="Pet List")
            await ctx.send(embed=embed)
            
        else:
            embed = create_error_embed("Valid pet actions: adopt, list, feed, play, rename")
            await ctx.send(embed=embed)

    @commands.command(name="friends")
    async def friends_command(self, ctx: commands.Context, action: str = None, user: discord.Member = None):
        """Manage your friends list"""
        if action is None:
            embed = discord.Embed(
                title="👥 Friends System",
                description="Manage your friends list!",
                color=discord.Color.green()
            )
            
            commands_list = [
                "`fg friends add @user` - Send friend request",
                "`fg friends remove @user` - Remove friend",
                "`fg friends list` - View friends list",
                "`fg friends requests` - View pending requests"
            ]
            
            embed.add_field(name="Commands", value="\\n".join(commands_list), inline=False)
            await ctx.send(embed=embed)
            return
            
        if action.lower() == "add":
            if user is None or user == ctx.author:
                embed = create_error_embed("You need to specify a valid user to add as friend!")
                await ctx.send(embed=embed)
                return
                
            embed = create_success_embed(
                f"Friend request sent to {user.mention}! 👥\\n"
                f"They can accept with `fg friends accept @{ctx.author.name}`",
                title="Friend Request Sent"
            )
            await ctx.send(embed=embed)
            
        elif action.lower() == "list":
            embed = create_info_embed("Your friends list is coming soon! 👥🚧", title="Friends List")
            await ctx.send(embed=embed)
            
        else:
            embed = create_error_embed("Valid friend actions: add, remove, list, requests")
            await ctx.send(embed=embed)

    @commands.command(name="achievements", aliases=["ach"])
    async def achievements_command(self, ctx: commands.Context, user: discord.Member = None):
        """View achievements and progress"""
        if user is None:
            user = ctx.author
            
        embed = discord.Embed(
            title=f"🏆 {user.display_name}'s Achievements",
            description="Track your progress and unlock rewards!",
            color=discord.Color.gold()
        )
        
        # Sample achievements
        achievements = [
            {"name": "First Steps", "desc": "Use your first command", "progress": "✅ Complete", "reward": "100 coins"},
            {"name": "Big Spender", "desc": "Spend 10,000 coins", "progress": "⏳ 5,240/10,000", "reward": "Spender badge"},
            {"name": "Gambler", "desc": "Win 100 gambling games", "progress": "⏳ 23/100", "reward": "Lucky charm"},
            {"name": "Social Butterfly", "desc": "Make 10 friends", "progress": "⏳ 2/10", "reward": "Friend badge"},
            {"name": "Workaholic", "desc": "Work 50 times", "progress": "⏳ 12/50", "reward": "Work multiplier"},
        ]
        
        for ach in achievements:
            embed.add_field(
                name=f"{ach['name']} - {ach['reward']}",
                value=f"{ach['desc']}\\n{ach['progress']}",
                inline=False
            )
            
        embed.set_footer(text="Achievement system coming soon! 🚧")
        await ctx.send(embed=embed)

    @commands.command(name="badges")
    async def badges_command(self, ctx: commands.Context, user: discord.Member = None):
        """View earned badges"""
        if user is None:
            user = ctx.author
            
        embed = discord.Embed(
            title=f"🎖️ {user.display_name}'s Badges",
            description="Collect badges by completing achievements!",
            color=discord.Color.purple()
        )
        
        # Sample badges
        badges = [
            "🆕 Newcomer - Join the server",
            "💰 Rich - Have 100,000+ coins",
            "🎰 Lucky - Win a gambling jackpot",
            "💕 Married - Get married",
            "🐕 Pet Owner - Adopt a pet",
            "👑 Premium - Support the bot"
        ]
        
        embed.add_field(
            name="Available Badges",
            value="\\n".join(badges),
            inline=False
        )
        
        embed.set_footer(text="Badge system coming soon! 🚧")
        await ctx.send(embed=embed)

    @commands.command(name="compare")
    async def compare_command(self, ctx: commands.Context, user: discord.Member = None):
        """Compare your stats with another user"""
        if user is None or user == ctx.author:
            embed = create_error_embed("You need to specify another user to compare with!\nUsage: `fg compare @user`")
            await ctx.send(embed=embed)
            return
            
        # Get both users' data
        author_pocket, author_bank = await self.bot.data_manager.get_balance(ctx.author.id)
        user_pocket, user_bank = await self.bot.data_manager.get_balance(user.id)
        
        author_total = author_pocket + author_bank
        user_total = user_pocket + user_bank
        
        embed = discord.Embed(
            title="📊 User Comparison",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name=f"💰 {ctx.author.display_name}",
            value=f"Pocket: {author_pocket:,}\\nBank: {author_bank:,}\\n**Total: {author_total:,}**",
            inline=True
        )
        
        embed.add_field(
            name="🆚",
            value="vs",
            inline=True
        )
        
        embed.add_field(
            name=f"💰 {user.display_name}",
            value=f"Pocket: {user_pocket:,}\\nBank: {user_bank:,}\\n**Total: {user_total:,}**",
            inline=True
        )
        
        # Determine winner
        if author_total > user_total:
            winner = f"🏆 {ctx.author.display_name} is richer!"
            difference = author_total - user_total
        elif user_total > author_total:
            winner = f"🏆 {user.display_name} is richer!"
            difference = user_total - author_total
        else:
            winner = "🤝 You have the same amount!"
            difference = 0
            
        embed.add_field(
            name="Result",
            value=f"{winner}\\n{f'Difference: {difference:,} coins' if difference > 0 else ''}",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="gift")
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5 minute cooldown
    async def gift_command(self, ctx: commands.Context, user: discord.Member = None, amount: int = None):
        """Gift coins to another user"""
        if user is None or amount is None:
            embed = create_error_embed("Usage: `fg gift @user <amount>`")
            await ctx.send(embed=embed)
            return
            
        if user.id == ctx.author.id:
            embed = create_error_embed("You can't gift coins to yourself!")
            await ctx.send(embed=embed)
            return
            
        if user.bot:
            embed = create_error_embed("You can't gift coins to bots!")
            await ctx.send(embed=embed)
            return
            
        if amount <= 0:
            embed = create_error_embed("Gift amount must be positive!")
            await ctx.send(embed=embed)
            return
            
        if amount < 10:
            embed = create_error_embed("Minimum gift amount is 10 coins!")
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        pocket, _ = await self.bot.data_manager.get_balance(user_id)
        
        if amount > pocket:
            embed = create_error_embed(f"You don't have {amount} coins in your pocket!")
            await ctx.send(embed=embed)
            return
            
        # Transfer coins
        await self.bot.data_manager.economy.remove_coins(user_id, amount, "pocket", f"Gift to {user.name}")
        await self.bot.data_manager.economy.add_coins(user.id, amount, "pocket", f"Gift from {ctx.author.name}")
        
        embed = create_success_embed(
            f"🎁 **Gift Sent!**\\n"
            f"You gave **{amount}** coins to {user.mention}!\\n"
            f"Spreading the wealth! 💖",
            title="Gift Complete"
        )
        
        await ctx.send(embed=embed)
        
        # Try to notify the recipient
        try:
            dm_embed = create_info_embed(
                f"🎁 You received **{amount}** coins from {ctx.author.mention} in {ctx.guild.name}!",
                title="Gift Received"
            )
            await user.send(embed=dm_embed)
        except:
            pass  # User has DMs disabled


async def setup(bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(Social(bot))