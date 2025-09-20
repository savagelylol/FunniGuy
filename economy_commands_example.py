"""
FunniGuy Discord Bot - Economy Commands Example
Comprehensive demonstration of the economy system features
"""
import discord
from discord.ext import commands
from utils.economy_manager import EconomyManager
from utils.inventory_manager import InventoryManager
from utils.database_manager import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class EconomyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.economy = EconomyManager(self.db)
        self.inventory = InventoryManager(self.db)

    # === BASIC ECONOMY ===
    
    @commands.command(name='balance', aliases=['bal', 'money'])
    async def balance(self, ctx):
        """Check your current balance and economy stats"""
        try:
            user_id = ctx.author.id
            stats = await self.economy.get_economy_stats(user_id)
            
            if not stats:
                await ctx.send("❌ Economy data not found. Use `!register` first!")
                return
            
            balances = stats['balances']
            lifetime = stats['lifetime']
            gambling = stats['gambling']
            
            # Get prestige info
            prestige_data = await self.economy.get_user_prestige(user_id)
            prestige_level = prestige_data.get('prestige_level', 0) if prestige_data else 0
            prestige_mult = prestige_data.get('prestige_multiplier', 1.0) if prestige_data else 1.0
            
            embed = discord.Embed(
                title="💰 Economy Status",
                description=f"Financial overview for {ctx.author.display_name}",
                color=0x00ff00
            )
            
            embed.add_field(
                name="💵 Current Balances",
                value=f"**Pocket:** {balances['pocket']:,} coins\n"
                      f"**Bank:** {balances['bank']:,}/{balances['bank_capacity']:,} coins\n"
                      f"**Total:** {balances['total']:,} coins",
                inline=True
            )
            
            embed.add_field(
                name="📊 Lifetime Stats",
                value=f"**Total Earned:** {lifetime['total_earned']:,} coins\n"
                      f"**Total Spent:** {lifetime['total_spent']:,} coins\n"
                      f"**Net Worth:** {lifetime['net_worth']:,} coins",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Prestige",
                value=f"**Level:** {prestige_level}\n"
                      f"**Multiplier:** {prestige_mult:.1f}x\n"
                      f"**Status:** {'Elite' if prestige_level >= 3 else 'Growing'}",
                inline=True
            )
            
            if gambling['total_gambled'] > 0:
                embed.add_field(
                    name="🎰 Gambling",
                    value=f"**Gambled:** {gambling['total_gambled']:,} coins\n"
                          f"**Won:** {gambling['total_won']:,} coins\n"
                          f"**Streak:** {gambling['gambling_streak']}",
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in balance command: {e}")
            await ctx.send("❌ Error retrieving balance information")

    @commands.command(name='crime')
    async def crime(self, ctx, crime_type: str = "petty_theft"):
        """Commit crimes for money (risky!)"""
        try:
            user_id = ctx.author.id
            
            valid_crimes = ["petty_theft", "pickpocket", "burglary", "bank_heist", "cyber_crime"]
            if crime_type not in valid_crimes:
                await ctx.send(f"❌ Invalid crime type! Choose from: {', '.join(valid_crimes)}")
                return
            
            success, money_change, description, caught = await self.economy.commit_crime(user_id, crime_type)
            
            if success:
                embed = discord.Embed(
                    title="🎭 Crime Success!",
                    description=description,
                    color=0x00ff00
                )
                embed.add_field(name="💰 Earned", value=f"{money_change:,} coins", inline=True)
            else:
                embed = discord.Embed(
                    title="🚔 Crime Failed!",
                    description=description,
                    color=0xff0000
                )
                if caught:
                    embed.add_field(name="💸 Fine", value=f"{money_change:,} coins", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in crime command: {e}")
            await ctx.send("❌ Crime attempt failed due to technical issues")

    @commands.command(name='rob')
    async def rob(self, ctx, target: discord.Member):
        """Rob another user's pocket money"""
        try:
            robber_id = ctx.author.id
            target_id = target.id
            
            success, amount, description = await self.economy.rob_user(robber_id, target_id)
            
            if success:
                embed = discord.Embed(
                    title="💰 Robbery Success!",
                    description=description,
                    color=0x00ff00
                )
                embed.add_field(name="💎 Stolen", value=f"{amount:,} coins", inline=True)
                embed.add_field(name="🎯 Target", value=target.mention, inline=True)
            else:
                embed = discord.Embed(
                    title="🚫 Robbery Failed!",
                    description=description,
                    color=0xff0000
                )
                if "fined" in description:
                    embed.add_field(name="💸 Fine", value=f"{amount:,} coins", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in rob command: {e}")
            await ctx.send("❌ Robbery attempt failed")

    # === PRESTIGE SYSTEM ===
    
    @commands.command(name='prestige')
    async def prestige(self, ctx, confirm: str = None):
        """Check prestige eligibility or prestige (requires confirmation)"""
        try:
            user_id = ctx.author.id
            
            if confirm != "confirm":
                # Show prestige info
                eligible, next_level, requirement = await self.economy.check_prestige_eligibility(user_id)
                economy_data = await self.economy.get_user_economy(user_id)
                
                if not economy_data:
                    await ctx.send("❌ Economy data not found!")
                    return
                
                total_earned = economy_data.get('total_earned', 0)
                prestige_data = await self.economy.get_user_prestige(user_id)
                current_prestige = prestige_data.get('prestige_level', 0) if prestige_data else 0
                
                embed = discord.Embed(
                    title="⭐ Prestige System",
                    description="Reset your progress for permanent bonuses!",
                    color=0x9932cc
                )
                
                embed.add_field(
                    name="📊 Current Status",
                    value=f"**Prestige Level:** {current_prestige}\n"
                          f"**Total Earned:** {total_earned:,} coins\n"
                          f"**Next Requirement:** {requirement:,} coins",
                    inline=False
                )
                
                if eligible:
                    multiplier = self.economy.prestige_multipliers.get(next_level, 1.0)
                    embed.add_field(
                        name="✅ Ready to Prestige!",
                        value=f"**New Level:** {next_level}\n"
                              f"**New Multiplier:** {multiplier:.1f}x earnings\n"
                              f"**Starting Money:** 1000 coins\n\n"
                              f"Use `!prestige confirm` to proceed",
                        inline=False
                    )
                    embed.color = 0x00ff00
                else:
                    needed = requirement - total_earned
                    embed.add_field(
                        name="❌ Not Ready Yet",
                        value=f"Need {needed:,} more coins earned",
                        inline=False
                    )
                    embed.color = 0xff9900
                
                await ctx.send(embed=embed)
                return
            
            # Perform prestige
            success, prestige_info = await self.economy.prestige_user(user_id, confirm=True)
            
            if success:
                embed = discord.Embed(
                    title="⭐ PRESTIGE ACHIEVED!",
                    description=f"Welcome to Prestige Level {prestige_info['new_prestige_level']}!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="🎊 New Benefits",
                    value=f"**Earnings Multiplier:** {prestige_info['prestige_multiplier']:.1f}x\n"
                          f"**Starting Balance:** {prestige_info['starting_balance']:,} coins\n"
                          f"**Previous Lifetime:** {prestige_info['lifetime_earnings']:,} coins",
                    inline=False
                )
                embed.add_field(
                    name="🔄 Reset Progress",
                    value="Your balances and stats have been reset, but you now earn much more!",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Prestige Failed",
                    description=prestige_info.get('error', 'Unknown error'),
                    color=0xff0000
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in prestige command: {e}")
            await ctx.send("❌ Error with prestige system")

    # === ADVANCED BANKING ===
    
    @commands.command(name='bank')
    async def bank_info(self, ctx):
        """View bank information and tier details"""
        try:
            user_id = ctx.author.id
            economy_data = await self.economy.get_user_economy(user_id)
            
            if not economy_data:
                await ctx.send("❌ Economy data not found!")
                return
            
            bank_tier = economy_data.get('bank_tier', 1)
            current_capacity = economy_data.get('bank_capacity', 1000)
            bank_balance = economy_data.get('bank_balance', 0)
            
            # Get tier features
            tier_features = self.economy._get_bank_tier_features(bank_tier)
            
            embed = discord.Embed(
                title="🏛️ Bank Information",
                description=f"Your Tier {bank_tier} Banking Account",
                color=0x4169e1
            )
            
            embed.add_field(
                name="💳 Account Details",
                value=f"**Balance:** {bank_balance:,}/{current_capacity:,} coins\n"
                      f"**Tier:** {bank_tier}/5\n"
                      f"**Utilization:** {(bank_balance/current_capacity*100):.1f}%",
                inline=True
            )
            
            # Show tier features
            features_text = []
            for feature, value in tier_features.items():
                if feature == 'loan_available' and value:
                    features_text.append("💰 Loans Available")
                elif feature == 'passive_income_rate' and value > 0:
                    features_text.append(f"📈 Passive Income: {value}/hour")
                elif feature == 'investment_access' and value:
                    features_text.append("📊 Investment Access")
                elif feature == 'premium_services' and value:
                    features_text.append("✨ Premium Services")
                elif feature == 'vip_status' and value:
                    features_text.append("👑 VIP Status")
            
            embed.add_field(
                name="🎁 Tier Benefits",
                value="\n".join(features_text) if features_text else "Basic banking only",
                inline=True
            )
            
            # Show upgrade info if not max tier
            if bank_tier < 5:
                next_tier = bank_tier + 1
                upgrade_cost = self.economy.bank_tier_costs[next_tier - 1]
                next_capacity = self.economy.bank_tier_capacities[next_tier - 1]
                
                embed.add_field(
                    name="⬆️ Next Tier Upgrade",
                    value=f"**Cost:** {upgrade_cost:,} coins\n"
                          f"**New Capacity:** {next_capacity:,} coins\n"
                          f"Use `!upgrade_bank` to upgrade",
                    inline=False
                )
            else:
                embed.add_field(
                    name="👑 Maximum Tier",
                    value="You have the highest tier banking account!",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in bank command: {e}")
            await ctx.send("❌ Error retrieving bank information")

    @commands.command(name='loan')
    async def loan_info(self, ctx, action: str = None, amount: int = None):
        """Manage loans: check eligibility, take, or repay"""
        try:
            user_id = ctx.author.id
            
            if action is None:
                # Show loan info
                eligible, max_loan, interest_rate = await self.economy.get_loan_eligibility(user_id)
                economy_data = await self.economy.get_user_economy(user_id)
                current_loan = economy_data.get('current_loan', 0) if economy_data else 0
                
                embed = discord.Embed(
                    title="💰 Loan Information",
                    color=0x32cd32 if eligible else 0xff6347
                )
                
                if current_loan > 0:
                    embed.add_field(
                        name="📋 Current Loan",
                        value=f"**Amount Owed:** {current_loan:,} coins\n"
                              f"**Interest Rate:** {economy_data.get('loan_interest_rate', 0.0)*100:.1f}%\n"
                              f"Use `!loan repay [amount]` to repay",
                        inline=False
                    )
                elif eligible:
                    embed.add_field(
                        name="✅ Loan Eligibility",
                        value=f"**Max Loan:** {max_loan:,} coins\n"
                              f"**Interest Rate:** {interest_rate*100:.1f}%\n"
                              f"**Min Amount:** 1,000 coins\n"
                              f"Use `!loan take <amount>` to borrow",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="❌ Not Eligible",
                        value="Requirements:\n• Bank tier 2+\n• No existing loan\n• Sufficient earning history",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                return
            
            if action == "take" and amount:
                success, loan_info = await self.economy.take_loan(user_id, amount)
                
                if success:
                    embed = discord.Embed(
                        title="💰 Loan Approved!",
                        description=f"You have borrowed {amount:,} coins",
                        color=0x00ff00
                    )
                    embed.add_field(
                        name="📋 Loan Details",
                        value=f"**Borrowed:** {loan_info['amount']:,} coins\n"
                              f"**Total to Repay:** {loan_info['total_repayment']:,} coins\n"
                              f"**Interest:** {loan_info['interest_amount']:,} coins ({loan_info['interest_rate']*100:.1f}%)",
                        inline=False
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Loan Denied",
                        description=loan_info.get('error', 'Unknown error'),
                        color=0xff0000
                    )
                
                await ctx.send(embed=embed)
                
            elif action == "repay":
                success, repay_info = await self.economy.repay_loan(user_id, amount)
                
                if success:
                    embed = discord.Embed(
                        title="✅ Loan Payment",
                        description=f"Repaid {repay_info['amount_paid']:,} coins",
                        color=0x00ff00
                    )
                    
                    if repay_info['fully_paid']:
                        embed.add_field(
                            name="🎉 Loan Fully Paid!",
                            value="Your loan has been completely repaid!",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="💳 Remaining Balance",
                            value=f"{repay_info['remaining_loan']:,} coins",
                            inline=False
                        )
                else:
                    embed = discord.Embed(
                        title="❌ Payment Failed",
                        description=repay_info.get('error', 'Unknown error'),
                        color=0xff0000
                    )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Invalid loan command! Use: `!loan` (info), `!loan take <amount>`, or `!loan repay [amount]`")
            
        except Exception as e:
            logger.error(f"Error in loan command: {e}")
            await ctx.send("❌ Error with loan system")

    @commands.command(name='passive')
    async def passive_income(self, ctx):
        """Collect accumulated passive income"""
        try:
            user_id = ctx.author.id
            success, income = await self.economy.collect_passive_income(user_id)
            
            if success and income > 0:
                embed = discord.Embed(
                    title="📈 Passive Income Collected!",
                    description=f"You collected {income:,} coins from passive income",
                    color=0x00ff00
                )
                embed.add_field(
                    name="💡 Tip",
                    value="Passive income is generated based on your bank tier. Upgrade your bank for higher rates!",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="📈 Passive Income",
                    description="No passive income to collect right now",
                    color=0xff9900
                )
                embed.add_field(
                    name="Requirements",
                    value="• Bank tier 2+ required\n• Income accumulates over time",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in passive command: {e}")
            await ctx.send("❌ Error collecting passive income")

    # === ITEM EFFECTS SYSTEM ===
    
    @commands.command(name='effects')
    async def active_effects(self, ctx):
        """View your currently active item effects"""
        try:
            user_id = ctx.author.id
            effects_data = await self.economy.get_user_active_effects(user_id)
            
            embed = discord.Embed(
                title="✨ Active Effects",
                description="Your currently active item bonuses",
                color=0x9932cc
            )
            
            if not effects_data:
                embed.add_field(
                    name="No Effects Active",
                    value="Use items to gain temporary bonuses!",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            temp_effects = effects_data.get('temporary_effects', [])
            perm_effects = effects_data.get('permanent_effects', [])
            
            if temp_effects:
                temp_text = []
                for effect in temp_effects:
                    effect_type = effect.get('effect_type', 'unknown')
                    value = effect.get('value', 0)
                    duration = effect.get('duration', 0)
                    
                    if effect_type.endswith('_multiplier'):
                        temp_text.append(f"**{effect_type.replace('_', ' ').title()}:** +{value*100:.0f}% ({duration}s left)")
                    else:
                        temp_text.append(f"**{effect_type.replace('_', ' ').title()}:** +{value} ({duration}s left)")
                
                embed.add_field(
                    name="⏰ Temporary Effects",
                    value="\n".join(temp_text),
                    inline=False
                )
            
            if perm_effects:
                perm_text = []
                for effect in perm_effects:
                    effect_type = effect.get('effect_type', 'unknown')
                    value = effect.get('value', 0)
                    
                    if effect_type.endswith('_multiplier'):
                        perm_text.append(f"**{effect_type.replace('_', ' ').title()}:** +{value*100:.0f}%")
                    else:
                        perm_text.append(f"**{effect_type.replace('_', ' ').title()}:** +{value}")
                
                embed.add_field(
                    name="🔮 Permanent Effects",
                    value="\n".join(perm_text),
                    inline=False
                )
            
            if not temp_effects and not perm_effects:
                embed.add_field(
                    name="No Effects Active",
                    value="Use consumable items to gain bonuses!",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in effects command: {e}")
            await ctx.send("❌ Error retrieving active effects")

async def setup(bot):
    await bot.add_cog(EconomyCommands(bot))