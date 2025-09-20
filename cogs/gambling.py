"""
Gambling Cog for FunniGuy Discord Bot
Contains all gambling and minigame commands like blackjack, slots, gamble, etc.
"""
import discord
from discord.ext import commands
import random
import asyncio
from typing import Optional, List
import logging

from utils.embeds import create_success_embed, create_error_embed, create_info_embed

logger = logging.getLogger(__name__)


class Gambling(commands.Cog):
    """Gambling and minigame commands"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gamble", aliases=["bet"])
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5 minute cooldown
    async def gamble_command(self, ctx: commands.Context, amount: int = None):
        """Gamble coins with a dice roll"""
        if amount is None:
            embed = create_error_embed("You need to specify an amount to gamble!\nUsage: `fg gamble <amount>`")
            await ctx.send(embed=embed)
            return
            
        if amount <= 0:
            embed = create_error_embed("You need to gamble a positive amount!")
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        pocket, _ = await self.bot.data_manager.get_balance(user_id)
        
        if amount > pocket:
            embed = create_error_embed(f"You don't have {amount} coins in your pocket!")
            await ctx.send(embed=embed)
            return
            
        # Roll dice
        user_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        
        embed = discord.Embed(title="🎲 Gambling Results", color=discord.Color.gold())
        embed.add_field(name="Your Roll", value=f"🎲 {user_roll}", inline=True)
        embed.add_field(name="Bot Roll", value=f"🎲 {bot_roll}", inline=True)
        
        if user_roll > bot_roll:
            # User wins - get 1.8x their bet
            winnings = int(amount * 1.8)
            await self.bot.data_manager.economy.add_coins(user_id, winnings, "pocket", f"Gambling win ({amount} bet)")
            
            embed.add_field(name="Result", value=f"🎉 **YOU WON!**\nYou won **{winnings}** coins!", inline=False)
            embed.color = discord.Color.green()
            
        elif user_roll == bot_roll:
            # Tie - get money back
            embed.add_field(name="Result", value=f"🤝 **TIE!**\nYou get your **{amount}** coins back!", inline=False)
            embed.color = discord.Color.orange()
            
        else:
            # User loses
            await self.bot.data_manager.economy.remove_coins(user_id, amount, "pocket", f"Gambling loss ({amount} bet)")
            
            embed.add_field(name="Result", value=f"💸 **YOU LOST!**\nYou lost **{amount}** coins!", inline=False)
            embed.color = discord.Color.red()
            
        await ctx.send(embed=embed)

    @commands.command(name="slots")
    @commands.cooldown(1, 180, commands.BucketType.user)  # 3 minute cooldown
    async def slots_command(self, ctx: commands.Context, amount: int = None):
        """Play the slot machine"""
        if amount is None:
            embed = create_error_embed("You need to specify an amount to bet!\nUsage: `fg slots <amount>`")
            await ctx.send(embed=embed)
            return
            
        if amount <= 0:
            embed = create_error_embed("You need to bet a positive amount!")
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        pocket, _ = await self.bot.data_manager.get_balance(user_id)
        
        if amount > pocket:
            embed = create_error_embed(f"You don't have {amount} coins in your pocket!")
            await ctx.send(embed=embed)
            return
            
        # Slot machine symbols with different rarities
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]
        weights = [30, 25, 20, 15, 7, 2, 1]  # Rarer symbols have lower weights
        
        # Spin the slots
        slot1 = random.choices(symbols, weights=weights)[0]
        slot2 = random.choices(symbols, weights=weights)[0] 
        slot3 = random.choices(symbols, weights=weights)[0]
        
        embed = discord.Embed(title="🎰 Slot Machine", color=discord.Color.gold())
        
        # Display the slots
        slot_display = f"╔═══════════╗\n║ {slot1} ║ {slot2} ║ {slot3} ║\n╚═══════════╝"
        embed.add_field(name="Spin Results", value=f"```{slot_display}```", inline=False)
        
        # Calculate winnings
        if slot1 == slot2 == slot3:
            # Jackpot - all three match
            multipliers = {
                "🍒": 10, "🍋": 15, "🍊": 20, "🍇": 25, 
                "🔔": 50, "💎": 100, "7️⃣": 777
            }
            multiplier = multipliers.get(slot1, 10)
            winnings = amount * multiplier
            
            await self.bot.data_manager.economy.add_coins(user_id, winnings, "pocket", f"Slots jackpot ({amount} bet)")
            
            embed.add_field(name="Result", value=f"🎊 **JACKPOT!** 🎊\nTriple {slot1}!\nYou won **{winnings}** coins!", inline=False)
            embed.color = discord.Color.gold()
            
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            # Two match - small win
            winnings = int(amount * 2)
            await self.bot.data_manager.economy.add_coins(user_id, winnings, "pocket", f"Slots win ({amount} bet)")
            
            embed.add_field(name="Result", value=f"🎉 **TWO MATCH!**\nYou won **{winnings}** coins!", inline=False)
            embed.color = discord.Color.green()
            
        else:
            # No match - lose bet
            await self.bot.data_manager.economy.remove_coins(user_id, amount, "pocket", f"Slots loss ({amount} bet)")
            
            embed.add_field(name="Result", value=f"💸 **NO MATCH!**\nYou lost **{amount}** coins!", inline=False)
            embed.color = discord.Color.red()
            
        await ctx.send(embed=embed)

    @commands.command(name="blackjack", aliases=["bj"])
    @commands.cooldown(1, 240, commands.BucketType.user)  # 4 minute cooldown
    async def blackjack_command(self, ctx: commands.Context, amount: int = None):
        """Play blackjack against the bot"""
        if amount is None:
            embed = create_error_embed("You need to specify an amount to bet!\nUsage: `fg blackjack <amount>`")
            await ctx.send(embed=embed)
            return
            
        if amount <= 0:
            embed = create_error_embed("You need to bet a positive amount!")
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        pocket, _ = await self.bot.data_manager.get_balance(user_id)
        
        if amount > pocket:
            embed = create_error_embed(f"You don't have {amount} coins in your pocket!")
            await ctx.send(embed=embed)
            return
            
        # Create deck
        suits = ["♠️", "♥️", "♦️", "♣️"]
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        deck = [(rank, suit) for suit in suits for rank in ranks]
        random.shuffle(deck)
        
        # Deal initial cards
        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop(), deck.pop()]
        
        def card_value(card):
            rank = card[0]
            if rank in ["J", "Q", "K"]:
                return 10
            elif rank == "A":
                return 11
            else:
                return int(rank)
                
        def hand_value(cards):
            value = sum(card_value(card) for card in cards)
            aces = sum(1 for card in cards if card[0] == "A")
            
            # Adjust for aces
            while value > 21 and aces > 0:
                value -= 10
                aces -= 1
                
            return value
            
        def format_cards(cards, hide_first=False):
            if hide_first:
                return f"🎴 {cards[1][0]}{cards[1][1]}"
            else:
                return " ".join(f"{card[0]}{card[1]}" for card in cards)
                
        player_value = hand_value(player_cards)
        dealer_value = hand_value(dealer_cards)
        
        embed = discord.Embed(title="♠️ Blackjack", color=discord.Color.blue())
        embed.add_field(name="Your Cards", value=f"{format_cards(player_cards)} (Value: {player_value})", inline=False)
        embed.add_field(name="Dealer Cards", value=f"{format_cards(dealer_cards, hide_first=True)} (Hidden)", inline=False)
        
        # Check for blackjacks
        if player_value == 21 and dealer_value == 21:
            # Both blackjack - tie
            embed.add_field(name="Result", value="🤝 **PUSH!** Both blackjack!", inline=False)
            embed.color = discord.Color.orange()
            
        elif player_value == 21:
            # Player blackjack
            winnings = int(amount * 2.5)
            await self.bot.data_manager.economy.add_coins(user_id, winnings, "pocket", f"Blackjack win ({amount} bet)")
            
            embed.add_field(name="Result", value=f"🎊 **BLACKJACK!**\nYou won **{winnings}** coins!", inline=False)
            embed.color = discord.Color.gold()
            
        elif dealer_value == 21:
            # Dealer blackjack
            await self.bot.data_manager.economy.remove_coins(user_id, amount, "pocket", f"Blackjack loss ({amount} bet)")
            
            embed.add_field(name="Dealer Cards", value=f"{format_cards(dealer_cards)} (Value: {dealer_value})", inline=False)
            embed.add_field(name="Result", value=f"💸 **DEALER BLACKJACK!**\nYou lost **{amount}** coins!", inline=False)
            embed.color = discord.Color.red()
            
        else:
            # Continue game - simplified (no hit/stand for now)
            # Dealer plays automatically
            while dealer_value < 17:
                dealer_cards.append(deck.pop())
                dealer_value = hand_value(dealer_cards)
                
            embed.add_field(name="Dealer Final", value=f"{format_cards(dealer_cards)} (Value: {dealer_value})", inline=False)
            
            if dealer_value > 21:
                # Dealer bust
                winnings = amount * 2
                await self.bot.data_manager.economy.add_coins(user_id, winnings, "pocket", f"Blackjack win ({amount} bet)")
                embed.add_field(name="Result", value=f"🎉 **DEALER BUST!**\nYou won **{winnings}** coins!", inline=False)
                embed.color = discord.Color.green()
                
            elif player_value > dealer_value:
                # Player wins
                winnings = amount * 2
                await self.bot.data_manager.economy.add_coins(user_id, winnings, "pocket", f"Blackjack win ({amount} bet)")
                embed.add_field(name="Result", value=f"🎉 **YOU WIN!**\nYou won **{winnings}** coins!", inline=False)
                embed.color = discord.Color.green()
                
            elif player_value == dealer_value:
                # Push
                embed.add_field(name="Result", value="🤝 **PUSH!** Same value!", inline=False)
                embed.color = discord.Color.orange()
                
            else:
                # Dealer wins
                await self.bot.data_manager.economy.remove_coins(user_id, amount, "pocket", f"Blackjack loss ({amount} bet)")
                embed.add_field(name="Result", value=f"💸 **DEALER WINS!**\nYou lost **{amount}** coins!", inline=False)
                embed.color = discord.Color.red()
                
        await ctx.send(embed=embed)

    @commands.command(name="highlow", aliases=["hl"])
    @commands.cooldown(1, 120, commands.BucketType.user)  # 2 minute cooldown
    async def highlow_command(self, ctx: commands.Context, amount: int = None):
        """Guess if the next number will be higher or lower"""
        if amount is None:
            embed = create_error_embed("You need to specify an amount to bet!\nUsage: `fg highlow <amount>`")
            await ctx.send(embed=embed)
            return
            
        if amount <= 0:
            embed = create_error_embed("You need to bet a positive amount!")
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        pocket, _ = await self.bot.data_manager.get_balance(user_id)
        
        if amount > pocket:
            embed = create_error_embed(f"You don't have {amount} coins in your pocket!")
            await ctx.send(embed=embed)
            return
            
        # Generate first number
        first_number = random.randint(1, 100)
        
        embed = discord.Embed(
            title="🔢 High or Low",
            description=f"The number is **{first_number}**\n\nWill the next number be **higher** or **lower**?",
            color=discord.Color.blue()
        )
        embed.add_field(name="Your Bet", value=f"{amount} coins", inline=True)
        embed.set_footer(text="React with ⬆️ for HIGHER or ⬇️ for LOWER")
        
        message = await ctx.send(embed=embed)
        
        # Add reactions
        await message.add_reaction("⬆️")
        await message.add_reaction("⬇️")
        
        def check(reaction, user):
            return (user == ctx.author and 
                   str(reaction.emoji) in ["⬆️", "⬇️"] and 
                   reaction.message == message)
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            # Generate second number
            second_number = random.randint(1, 100)
            
            # Determine result
            user_guess = str(reaction.emoji)
            correct = False
            
            if second_number > first_number and user_guess == "⬆️":
                correct = True
            elif second_number < first_number and user_guess == "⬇️":
                correct = True
            elif second_number == first_number:
                # Same number - special case
                embed = discord.Embed(
                    title="🔢 High or Low - Results",
                    description=f"First number: **{first_number}**\nSecond number: **{second_number}**\n\n🤯 **SAME NUMBER!** That's crazy!\nYou get your bet back plus a bonus!",
                    color=discord.Color.gold()
                )
                
                bonus = amount // 2
                await self.bot.data_manager.economy.add_coins(user_id, bonus, "pocket", f"High-Low same number bonus ({amount} bet)")
                embed.add_field(name="Result", value=f"🎉 Bonus: **{bonus}** coins!", inline=False)
                
            elif correct:
                # User guessed correctly
                winnings = amount * 2
                await self.bot.data_manager.economy.add_coins(user_id, winnings, "pocket", f"High-Low win ({amount} bet)")
                
                embed = discord.Embed(
                    title="🔢 High or Low - Results",
                    description=f"First number: **{first_number}**\nSecond number: **{second_number}**\n\n🎉 **CORRECT!**\nYou won **{winnings}** coins!",
                    color=discord.Color.green()
                )
                
            else:
                # User guessed wrong
                await self.bot.data_manager.economy.remove_coins(user_id, amount, "pocket", f"High-Low loss ({amount} bet)")
                
                embed = discord.Embed(
                    title="🔢 High or Low - Results", 
                    description=f"First number: **{first_number}**\nSecond number: **{second_number}**\n\n💸 **WRONG!**\nYou lost **{amount}** coins!",
                    color=discord.Color.red()
                )
                
            await message.edit(embed=embed)
            
        except asyncio.TimeoutError:
            embed = create_error_embed("⏰ You took too long to guess! Game cancelled.")
            await message.edit(embed=embed)

    @commands.command(name="scratch")
    @commands.cooldown(1, 600, commands.BucketType.user)  # 10 minute cooldown
    async def scratch_command(self, ctx: commands.Context, amount: int = None):
        """Play a scratch card game"""
        if amount is None:
            embed = create_error_embed("You need to specify an amount to bet!\nUsage: `fg scratch <amount>`")
            await ctx.send(embed=embed)
            return
            
        if amount <= 0:
            embed = create_error_embed("You need to bet a positive amount!")
            await ctx.send(embed=embed)
            return
            
        user_id = ctx.author.id
        pocket, _ = await self.bot.data_manager.get_balance(user_id)
        
        if amount > pocket:
            embed = create_error_embed(f"You don't have {amount} coins in your pocket!")
            await ctx.send(embed=embed)
            return
            
        # Generate scratch card with 9 symbols
        symbols = ["💰", "💎", "🎰", "🍒", "🔔", "⭐", "💸"]
        card = [random.choice(symbols) for _ in range(9)]
        
        # Check for wins (3+ matching symbols)
        symbol_counts = {}
        for symbol in card:
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            
        max_matches = max(symbol_counts.values())
        winning_symbol = None
        
        for symbol, count in symbol_counts.items():
            if count == max_matches and max_matches >= 3:
                winning_symbol = symbol
                break
                
        # Display the card
        card_display = (
            f"{card[0]} | {card[1]} | {card[2]}\n"
            f"{card[3]} | {card[4]} | {card[5]}\n"
            f"{card[6]} | {card[7]} | {card[8]}"
        )
        
        embed = discord.Embed(title="🎫 Scratch Card", color=discord.Color.purple())
        embed.add_field(name="Your Card", value=f"```{card_display}```", inline=False)
        
        if winning_symbol and max_matches >= 3:
            # Calculate winnings based on symbol and matches
            multipliers = {
                "💰": [0, 0, 0, 5, 20, 100],    # 3=5x, 4=20x, 5=100x
                "💎": [0, 0, 0, 10, 50, 500],   # 3=10x, 4=50x, 5=500x
                "🎰": [0, 0, 0, 3, 15, 75],     # 3=3x, 4=15x, 5=75x
                "🍒": [0, 0, 0, 4, 18, 90],     # etc.
                "🔔": [0, 0, 0, 6, 25, 125],
                "⭐": [0, 0, 0, 8, 35, 175],
                "💸": [0, 0, 0, 2, 10, 50],     # Lowest payout
            }
            
            multiplier = multipliers.get(winning_symbol, [0, 0, 0, 2, 10, 50])[max_matches]
            winnings = amount * multiplier
            
            await self.bot.data_manager.economy.add_coins(user_id, winnings, "pocket", f"Scratch card win ({amount} bet)")
            
            embed.add_field(
                name="Result", 
                value=f"🎉 **{max_matches} {winning_symbol} MATCH!**\nYou won **{winnings}** coins!",
                inline=False
            )
            embed.color = discord.Color.gold()
            
        else:
            # No win
            await self.bot.data_manager.economy.remove_coins(user_id, amount, "pocket", f"Scratch card loss ({amount} bet)")
            
            embed.add_field(name="Result", value=f"💸 **NO MATCH!**\nYou lost **{amount}** coins!", inline=False)
            embed.color = discord.Color.red()
            
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(Gambling(bot))