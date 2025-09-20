"""
Economy Cog for FunniGuy Discord Bot
Contains all economy-related commands including work, beg, crime, rob, shop, etc.
"""
import discord
from discord.ext import commands
import random
import asyncio
from typing import Optional, List
import logging

from utils.embeds import create_success_embed, create_error_embed, create_info_embed

logger = logging.getLogger(__name__)


class Economy(commands.Cog):
    """Economy commands and functionality"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="beg")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def beg_command(self, ctx: commands.Context):
        """Beg for coins from random people"""
        user_id = ctx.author.id
        
        # Random outcomes with Dank Memer style responses
        outcomes = [
            {"success": True, "amount": 50, "message": "A kind stranger gave you **{amount}** coins! 😊"},
            {"success": True, "amount": 75, "message": "Someone felt bad for you and gave you **{amount}** coins! 💰"},
            {"success": True, "amount": 100, "message": "You found **{amount}** coins on the ground while begging! 🎉"},
            {"success": True, "amount": 25, "message": "A generous person donated **{amount}** coins to you! ❤️"},
            {"success": False, "amount": 0, "message": "Nobody wants to give you coins... sad 😭"},
            {"success": False, "amount": 0, "message": "You got arrested for aggressive begging! 🚔"},
            {"success": False, "amount": 0, "message": "People just walked past you... 😔"},
        ]
        
        outcome = random.choice(outcomes)
        
        if outcome["success"] and outcome["amount"] > 0:
            # Add coins to user's pocket
            await self.bot.data_manager.economy.add_coins(user_id, outcome["amount"], "pocket", "Begging")
            embed = create_success_embed(
                outcome["message"].format(amount=outcome["amount"]),
                title="Begging Results"
            )
        else:
            embed = create_error_embed(outcome["message"], title="Begging Failed")
            
        await ctx.send(embed=embed)

    @commands.command(name="work")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour cooldown
    async def work_command(self, ctx: commands.Context):
        """Work at your job to earn coins"""
        user_id = ctx.author.id
        
        # Different jobs with different pay rates
        jobs = [
            {"name": "McDonald's Employee", "min": 200, "max": 400, "emoji": "🍟"},
            {"name": "Dog Walker", "min": 150, "max": 350, "emoji": "🐕"},
            {"name": "Cashier", "min": 180, "max": 380, "emoji": "💳"},
            {"name": "Delivery Driver", "min": 220, "max": 420, "emoji": "🚗"},
            {"name": "Babysitter", "min": 160, "max": 360, "emoji": "👶"},
            {"name": "Tutor", "min": 250, "max": 450, "emoji": "📚"},
            {"name": "Programmer", "min": 400, "max": 800, "emoji": "💻"},
        ]
        
        job = random.choice(jobs)
        amount = random.randint(job["min"], job["max"])
        
        # Add work bonus from items/prestige if any
        multiplier = await self.bot.data_manager.economy.get_work_multiplier(user_id)
        final_amount = int(amount * multiplier)
        
        await self.bot.data_manager.economy.add_coins(user_id, final_amount, "pocket", f"Working as {job['name']}")
        
        embed = create_success_embed(
            f"{job['emoji']} You worked as a **{job['name']}** and earned **{final_amount}** coins!\n"
            f"{'💰 *Work bonus applied!*' if multiplier > 1 else ''}",
            title="Work Complete"
        )
        await ctx.send(embed=embed)

    @commands.command(name="crime")
    @commands.cooldown(1, 7200, commands.BucketType.user)  # 2 hour cooldown
    async def crime_command(self, ctx: commands.Context):
        """Commit a crime for high risk, high reward coins"""
        user_id = ctx.author.id
        
        crimes = [
            {"name": "Rob a bank", "success_rate": 0.3, "reward": (800, 2000), "penalty": 500},
            {"name": "Steal a car", "success_rate": 0.4, "reward": (600, 1500), "penalty": 400},
            {"name": "Pickpocket someone", "success_rate": 0.6, "reward": (200, 800), "penalty": 200},
            {"name": "Hack into a company", "success_rate": 0.25, "reward": (1000, 3000), "penalty": 800},
            {"name": "Rob a convenience store", "success_rate": 0.5, "reward": (300, 1000), "penalty": 300},
        ]
        
        crime = random.choice(crimes)
        success = random.random() < crime["success_rate"]
        
        if success:
            amount = random.randint(crime["reward"][0], crime["reward"][1])
            await self.bot.data_manager.economy.add_coins(user_id, amount, "pocket", f"Crime: {crime['name']}")
            
            embed = create_success_embed(
                f"🔥 **Crime Successful!**\nYou managed to {crime['name'].lower()} and got away with **{amount}** coins! 💰",
                title="Crime Success"
            )
        else:
            # Check if user has coins to lose
            pocket, _ = await self.bot.data_manager.get_balance(user_id)
            penalty = min(crime["penalty"], pocket)
            
            if penalty > 0:
                await self.bot.data_manager.economy.remove_coins(user_id, penalty, "pocket", f"Crime penalty: {crime['name']}")
                
            embed = create_error_embed(
                f"🚔 **Crime Failed!**\nYou got caught trying to {crime['name'].lower()}!\n"
                f"You lost **{penalty}** coins and learned a lesson... maybe.",
                title="Crime Failed"
            )
            
        await ctx.send(embed=embed)

    @commands.command(name="rob")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # 1 hour cooldown
    async def rob_command(self, ctx: commands.Context, target: discord.Member = None):
        """Rob another user's pocket coins"""
        if target is None:
            embed = create_error_embed("You need to specify someone to rob!\nUsage: `fg rob @user`")
            await ctx.send(embed=embed)
            return
            
        if target.id == ctx.author.id:
            embed = create_error_embed("You can't rob yourself, dummy! 🤦‍♂️")
            await ctx.send(embed=embed)
            return
            
        if target.bot:
            embed = create_error_embed("You can't rob bots! They're broke anyway... 🤖")
            await ctx.send(embed=embed)
            return
            
        # Check target's pocket balance
        target_pocket, _ = await self.bot.data_manager.get_balance(target.id)
        
        if target_pocket < 100:
            embed = create_error_embed(f"{target.display_name} is too poor to rob! They need at least 100 coins in their pocket.")
            await ctx.send(embed=embed)
            return
            
        # Rob success rate (30% base)
        success_rate = 0.3
        
        # Check if target has protection items (padlock, etc)
        # TODO: Implement item effects
        
        if random.random() < success_rate:
            # Success - steal 20-40% of target's pocket
            steal_percentage = random.uniform(0.2, 0.4)
            stolen_amount = int(target_pocket * steal_percentage)
            
            await self.bot.data_manager.economy.remove_coins(target.id, stolen_amount, "pocket", f"Robbed by {ctx.author.name}")
            await self.bot.data_manager.economy.add_coins(ctx.author.id, stolen_amount, "pocket", f"Robbed {target.name}")
            
            embed = create_success_embed(
                f"🔫 **Rob Successful!**\nYou robbed **{stolen_amount}** coins from {target.mention}! 💰\n"
                f"*You're now a wanted criminal... 🚔*",
                title="Robbery Success"
            )
        else:
            # Failure - lose some of your own coins
            robber_pocket, _ = await self.bot.data_manager.get_balance(ctx.author.id)
            penalty = min(200, robber_pocket)
            
            if penalty > 0:
                await self.bot.data_manager.economy.remove_coins(ctx.author.id, penalty, "pocket", "Failed robbery penalty")
                
            embed = create_error_embed(
                f"🚔 **Rob Failed!**\n{target.mention} caught you trying to rob them!\n"
                f"You lost **{penalty}** coins and your dignity... 😭",
                title="Robbery Failed"
            )
            
        await ctx.send(embed=embed)

    @commands.command(name="deposit", aliases=["dep"])
    async def deposit_command(self, ctx: commands.Context, amount: str = None):
        """Deposit coins from pocket to bank"""
        if amount is None:
            embed = create_error_embed("Specify an amount to deposit!\nUsage: `fg deposit <amount/all/max>`")
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        pocket, bank = await self.bot.data_manager.get_balance(user_id)
        
        # Get bank capacity
        bank_capacity = await self.bot.data_manager.economy.get_bank_capacity(user_id)
        available_space = bank_capacity - bank
        
        if available_space <= 0:
            embed = create_error_embed("Your bank is full! You need to upgrade your bank capacity.")
            await ctx.send(embed=embed)
            return
            
        # Parse amount
        if amount.lower() in ["all", "max"]:
            deposit_amount = min(pocket, available_space)
        else:
            try:
                deposit_amount = int(amount)
                if deposit_amount <= 0:
                    raise ValueError()
            except ValueError:
                embed = create_error_embed("Invalid amount! Use a positive number, 'all', or 'max'.")
                await ctx.send(embed=embed)
                return
                
        if deposit_amount > pocket:
            embed = create_error_embed(f"You don't have {deposit_amount} coins in your pocket!")
            await ctx.send(embed=embed)
            return
            
        if deposit_amount > available_space:
            embed = create_error_embed(f"Your bank only has space for {available_space} more coins!")
            await ctx.send(embed=embed)
            return
            
        # Perform the deposit
        await self.bot.data_manager.economy.remove_coins(user_id, deposit_amount, "pocket", "Bank deposit")
        await self.bot.data_manager.economy.add_coins(user_id, deposit_amount, "bank", "Bank deposit")
        
        embed = create_success_embed(
            f"🏦 Successfully deposited **{deposit_amount}** coins to your bank!\n"
            f"Bank: **{bank + deposit_amount:,}/{bank_capacity:,}** coins",
            title="Deposit Successful"
        )
        await ctx.send(embed=embed)

    @commands.command(name="withdraw", aliases=["with"])
    async def withdraw_command(self, ctx: commands.Context, amount: str = None):
        """Withdraw coins from bank to pocket"""
        if amount is None:
            embed = create_error_embed("Specify an amount to withdraw!\nUsage: `fg withdraw <amount/all/max>`")
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        pocket, bank = await self.bot.data_manager.get_balance(user_id)
        
        if bank <= 0:
            embed = create_error_embed("You don't have any coins in your bank!")
            await ctx.send(embed=embed)
            return
            
        # Parse amount
        if amount.lower() in ["all", "max"]:
            withdraw_amount = bank
        else:
            try:
                withdraw_amount = int(amount)
                if withdraw_amount <= 0:
                    raise ValueError()
            except ValueError:
                embed = create_error_embed("Invalid amount! Use a positive number, 'all', or 'max'.")
                await ctx.send(embed=embed)
                return
                
        if withdraw_amount > bank:
            embed = create_error_embed(f"You don't have {withdraw_amount} coins in your bank!")
            await ctx.send(embed=embed)
            return
            
        # Perform the withdrawal
        await self.bot.data_manager.economy.remove_coins(user_id, withdraw_amount, "bank", "Bank withdrawal")
        await self.bot.data_manager.economy.add_coins(user_id, withdraw_amount, "pocket", "Bank withdrawal")
        
        embed = create_success_embed(
            f"🏦 Successfully withdrew **{withdraw_amount}** coins from your bank!\n"
            f"Pocket: **{pocket + withdraw_amount:,}** coins",
            title="Withdrawal Successful"
        )
        await ctx.send(embed=embed)

    @commands.command(name="shop")
    async def shop_command(self, ctx: commands.Context, action: str = None, *, item_name: str = None):
        """View the shop or buy items"""
        if action is None:
            # Show shop
            embed = discord.Embed(
                title="🛒 FunniGuy Shop",
                description="Buy items to help with your adventures!",
                color=discord.Color.gold()
            )
            
            # Featured items
            shop_items = [
                {"name": "🔓 Padlock", "price": 500, "description": "Protects you from robberies"},
                {"name": "🔫 Rifle", "price": 1500, "description": "Required for hunting"},
                {"name": "🎣 Fishing Pole", "price": 800, "description": "Required for fishing"},
                {"name": "🍕 Pizza", "price": 100, "description": "Restores health"},
                {"name": "⚡ Energy Drink", "price": 200, "description": "Work bonus multiplier"},
                {"name": "💎 Rare Gem", "price": 5000, "description": "Valuable collectible"},
            ]
            
            for item in shop_items:
                embed.add_field(
                    name=f"{item['name']} - {item['price']} coins",
                    value=item['description'],
                    inline=False
                )
                
            embed.set_footer(text="Use 'fg shop buy <item name>' to purchase an item!")
            await ctx.send(embed=embed)
            
        elif action.lower() == "buy":
            if item_name is None:
                embed = create_error_embed("Specify an item to buy!\nUsage: `fg shop buy <item name>`")
                await ctx.send(embed=embed)
                return
                
            # TODO: Implement actual item purchasing from shop
            embed = create_info_embed("Shop purchasing is coming soon! 🚧", title="Under Construction")
            await ctx.send(embed=embed)
            
        else:
            embed = create_error_embed("Valid shop actions: view (default), buy\nUsage: `fg shop` or `fg shop buy <item>`")
            await ctx.send(embed=embed)

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory_command(self, ctx: commands.Context, user: discord.Member = None):
        """View your or another user's inventory"""
        if user is None:
            user = ctx.author
            
        # TODO: Implement actual inventory system
        embed = discord.Embed(
            title=f"🎒 {user.display_name}'s Inventory",
            description="Your inventory is empty! Buy some items from the shop.",
            color=discord.Color.blue()
        )
        
        embed.set_footer(text="Inventory system coming soon! 🚧")
        await ctx.send(embed=embed)

    @commands.command(name="weekly")
    @commands.cooldown(1, 604800, commands.BucketType.user)  # 1 week cooldown
    async def weekly_command(self, ctx: commands.Context):
        """Claim your weekly bonus"""
        user_id = ctx.author.id
        amount = 2500
        
        await self.bot.data_manager.economy.add_coins(user_id, amount, "pocket", "Weekly bonus")
        
        embed = create_success_embed(
            f"📅 You claimed your weekly bonus of **{amount}** coins! 🎉\n"
            f"Come back next week for another bonus!",
            title="Weekly Bonus Claimed"
        )
        await ctx.send(embed=embed)

    @commands.command(name="monthly")
    @commands.cooldown(1, 2592000, commands.BucketType.user)  # 30 days cooldown
    async def monthly_command(self, ctx: commands.Context):
        """Claim your monthly bonus"""
        user_id = ctx.author.id
        amount = 10000
        
        await self.bot.data_manager.economy.add_coins(user_id, amount, "pocket", "Monthly bonus")
        
        embed = create_success_embed(
            f"📆 You claimed your monthly bonus of **{amount}** coins! 🎊\n"
            f"That's a lot of coins! See you next month!",
            title="Monthly Bonus Claimed"
        )
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(Economy(bot))