"""
Fun Cog for FunniGuy Discord Bot
Contains all fun and meme commands like 8ball, joke, roast, hack, ship, etc.
"""
import discord
from discord.ext import commands
import random
import aiohttp
import asyncio
from typing import Optional, List
import logging

from utils.embeds import create_success_embed, create_error_embed, create_info_embed

logger = logging.getLogger(__name__)


class Fun(commands.Cog):
    """Fun and meme commands"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="8ball", aliases=["eightball"])
    async def eightball_command(self, ctx: commands.Context, *, question: str = None):
        """Ask the magic 8-ball a question"""
        if question is None:
            embed = create_error_embed("You need to ask a question!\nUsage: `fg 8ball <question>`")
            await ctx.send(embed=embed)
            return
            
        responses = [
            "🎱 It is certain",
            "🎱 Without a doubt",
            "🎱 Yes definitely",
            "🎱 You may rely on it",
            "🎱 As I see it, yes",
            "🎱 Most likely",
            "🎱 Outlook good",
            "🎱 Yes",
            "🎱 Signs point to yes",
            "🎱 Reply hazy, try again",
            "🎱 Ask again later",
            "🎱 Better not tell you now",
            "🎱 Cannot predict now",
            "🎱 Concentrate and ask again",
            "🎱 Don't count on it",
            "🎱 My reply is no",
            "🎱 My sources say no",
            "🎱 Outlook not so good",
            "🎱 Very doubtful",
            "🎱 No way Jose"
        ]
        
        response = random.choice(responses)
        
        embed = discord.Embed(
            title="🔮 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="joke")
    async def joke_command(self, ctx: commands.Context):
        """Get a random joke"""
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What do you call a fake noodle? An impasta!",
            "Why did the math book look so sad? Because it had too many problems!",
            "What do you call a dinosaur that crashes his car? Tyrannosaurus Wrecks!",
            "Why can't a bicycle stand up by itself? It's two tired!",
            "What do you call a fish wearing a crown? A king fish!",
            "Why don't skeletons fight each other? They don't have the guts!",
            "What's the best thing about Switzerland? I don't know, but the flag is a big plus!"
        ]
        
        joke = random.choice(jokes)
        
        embed = create_success_embed(joke, title="😂 Random Joke")
        await ctx.send(embed=embed)

    @commands.command(name="roast")
    async def roast_command(self, ctx: commands.Context, user: discord.Member = None):
        """Roast yourself or another user"""
        if user is None:
            user = ctx.author
            
        roasts = [
            "{user} is so ugly, when they were born the doctor slapped their parents!",
            "{user}'s brain is so small, if it was a grain of rice, a ant would starve!",
            "I'd call {user} stupid, but that would be an insult to stupid people.",
            "{user} brings everyone so much joy... when they leave the room!",
            "If {user} was any more inbred, they'd be a sandwich!",
            "{user} is proof that evolution CAN go in reverse!",
            "I'm not saying {user} is dumb, but they got hit by a parked car!",
            "{user} is like a cloud. When they disappear, it's a beautiful day!",
            "The only way {user} could be uglier is if I could see their personality!",
            "{user} is so fake, Barbie is jealous!"
        ]
        
        roast = random.choice(roasts).format(user=user.display_name)
        
        embed = discord.Embed(
            title="🔥 ROASTED! 🔥",
            description=roast,
            color=discord.Color.red()
        )
        embed.set_footer(text="Just kidding! You're awesome! ❤️")
        
        await ctx.send(embed=embed)

    @commands.command(name="hack")
    async def hack_command(self, ctx: commands.Context, user: discord.Member = None):
        """Hack another user (fake)"""
        if user is None:
            embed = create_error_embed("You need to specify someone to hack!\nUsage: `fg hack @user`")
            await ctx.send(embed=embed)
            return
            
        if user.id == ctx.author.id:
            embed = create_error_embed("You can't hack yourself! 🤦‍♂️")
            await ctx.send(embed=embed)
            return
            
        # Fake hacking sequence
        embed = discord.Embed(
            title="💻 HACKING IN PROGRESS...",
            description=f"Target: {user.mention}",
            color=discord.Color.green()
        )
        
        message = await ctx.send(embed=embed)
        
        # Fake loading sequence
        steps = [
            "🔍 Scanning for vulnerabilities...",
            "🔐 Bypassing security protocols...", 
            "📊 Analyzing user data...",
            "💾 Extracting information...",
            "🎯 Hack complete!"
        ]
        
        for step in steps:
            await asyncio.sleep(2)
            embed.description = f"Target: {user.mention}\n\n{step}"
            await message.edit(embed=embed)
        
        # Final result with fake personal info
        passwords = ["password123", "abc123", "ilovemom", "qwerty", "123456", "hunter2"]
        browsers = ["Chrome", "Firefox", "Safari", "Edge", "Internet Explorer"]
        
        embed = discord.Embed(
            title="✅ HACK SUCCESSFUL!",
            color=discord.Color.red()
        )
        embed.add_field(name="Email", value=f"{user.name.lower()}@gmail.com", inline=True)
        embed.add_field(name="Password", value=random.choice(passwords), inline=True)  
        embed.add_field(name="Browser", value=random.choice(browsers), inline=True)
        embed.add_field(name="Last Login", value="Just now", inline=True)
        embed.add_field(name="IP Address", value="127.0.0.1", inline=True)
        embed.add_field(name="Location", value="Your house", inline=True)
        embed.set_footer(text="⚠️ This is fake! Don't actually hack people!")
        
        await message.edit(embed=embed)

    @commands.command(name="ship")
    async def ship_command(self, ctx: commands.Context, user1: discord.Member = None, user2: discord.Member = None):
        """Ship two users together and see their compatibility"""
        if user1 is None:
            user1 = ctx.author
            
        if user2 is None:
            embed = create_error_embed("You need to specify two users to ship!\nUsage: `fg ship @user1 @user2`")
            await ctx.send(embed=embed)
            return
            
        # Generate compatibility percentage
        compatibility = random.randint(0, 100)
        
        # Determine relationship status based on percentage
        if compatibility >= 90:
            status = "💕 Perfect Match! Soulmates!"
            color = discord.Color.from_rgb(255, 20, 147)  # Deep pink
        elif compatibility >= 75:
            status = "💖 Very Compatible! Love is in the air!"
            color = discord.Color.from_rgb(255, 105, 180)  # Hot pink
        elif compatibility >= 50:
            status = "💘 Good Match! Could work out!"
            color = discord.Color.from_rgb(255, 182, 193)  # Light pink
        elif compatibility >= 25:
            status = "💔 Not the best match... but who knows?"
            color = discord.Color.orange()
        else:
            status = "💥 Disaster! Run away!"
            color = discord.Color.red()
            
        # Create ship name
        name1 = user1.display_name
        name2 = user2.display_name
        ship_name = name1[:len(name1)//2] + name2[len(name2)//2:]
        
        embed = discord.Embed(
            title="💕 Ship Calculator",
            color=color
        )
        embed.add_field(name="Couple", value=f"{user1.mention} + {user2.mention}", inline=False)
        embed.add_field(name="Ship Name", value=ship_name, inline=True)
        embed.add_field(name="Compatibility", value=f"{compatibility}%", inline=True)
        embed.add_field(name="Status", value=status, inline=False)
        
        # Add progress bar
        filled = int(compatibility / 10)
        empty = 10 - filled
        progress_bar = "💖" * filled + "💔" * empty
        embed.add_field(name="Love Meter", value=progress_bar, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="rate")
    async def rate_command(self, ctx: commands.Context, *, thing: str = None):
        """Rate something out of 10"""
        if thing is None:
            embed = create_error_embed("You need to specify something to rate!\nUsage: `fg rate <thing>`")
            await ctx.send(embed=embed)
            return
            
        rating = random.randint(0, 10)
        
        # Determine emoji based on rating
        if rating >= 9:
            emoji = "🔥"
            comment = "AMAZING!"
        elif rating >= 7:
            emoji = "👍"
            comment = "Pretty good!"
        elif rating >= 5:
            emoji = "😐"
            comment = "Meh..."
        elif rating >= 3:
            emoji = "👎"
            comment = "Not great..."
        else:
            emoji = "🗑️"
            comment = "Trash!"
            
        embed = discord.Embed(
            title="⭐ Rating",
            description=f"I rate **{thing}** a **{rating}/10** {emoji}\n\n*{comment}*",
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="kill")
    async def kill_command(self, ctx: commands.Context, user: discord.Member = None):
        """Kill another user (fake)"""
        if user is None:
            embed = create_error_embed("You need to specify someone to kill!\nUsage: `fg kill @user`")
            await ctx.send(embed=embed)
            return
            
        if user.id == ctx.author.id:
            embed = create_error_embed("You can't kill yourself! Get some help! 💚")
            await ctx.send(embed=embed)
            return
            
        weapons = [
            "🔫 shot", "⚔️ stabbed", "🗡️ sliced", "🏹 arrowed", "💣 exploded",
            "🔨 hammered", "⛏️ pickaxed", "🪓 axed", "🧨 dynamited", "☠️ poisoned"
        ]
        
        locations = [
            "in the kitchen", "at school", "in the library", "at the park",
            "in space", "underwater", "on a mountain", "in a volcano",
            "at McDonald's", "in Discord"
        ]
        
        weapon = random.choice(weapons)
        location = random.choice(locations)
        
        embed = discord.Embed(
            title="💀 MURDER SCENE",
            description=f"{ctx.author.mention} {weapon.split()[1]} {user.mention} {location}!",
            color=discord.Color.red()
        )
        embed.add_field(name="Weapon", value=weapon.split()[0], inline=True)
        embed.add_field(name="Location", value=location, inline=True)
        embed.add_field(name="Status", value="💀 DEAD", inline=True)
        embed.set_footer(text="⚠️ This is fake! Nobody was actually harmed!")
        
        await ctx.send(embed=embed)

    @commands.command(name="emojify")
    async def emojify_command(self, ctx: commands.Context, *, text: str = None):
        """Convert text to emojis"""
        if text is None:
            embed = create_error_embed("You need to provide text to emojify!\nUsage: `fg emojify <text>`")
            await ctx.send(embed=embed)
            return
            
        if len(text) > 100:
            embed = create_error_embed("Text is too long! Maximum 100 characters.")
            await ctx.send(embed=embed)
            return
            
        # Convert letters to regional indicators
        emoji_text = ""
        for char in text.lower():
            if char.isalpha():
                emoji_text += f":regional_indicator_{char}: "
            elif char == " ":
                emoji_text += "   "
            else:
                emoji_text += char + " "
                
        if len(emoji_text) > 2000:
            embed = create_error_embed("Emojified text is too long!")
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="✨ Emojified Text",
            description=emoji_text,
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="clap")
    async def clap_command(self, ctx: commands.Context, *, text: str = None):
        """Add clap emojis between words"""
        if text is None:
            embed = create_error_embed("You need to provide text!\nUsage: `fg clap <text>`")
            await ctx.send(embed=embed)
            return
            
        clapped_text = " 👏 ".join(text.split())
        
        if len(clapped_text) > 2000:
            embed = create_error_embed("Clapped text is too long!")
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="👏 Clapped Text",
            description=clapped_text,
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="fortune")
    async def fortune_command(self, ctx: commands.Context):
        """Get a fortune cookie message"""
        fortunes = [
            "🥠 You will find happiness in a new friendship.",
            "🥠 Your future is as bright as your faith allows it to be.",
            "🥠 A journey of a thousand miles begins with a single step.",
            "🥠 You will discover a new source of income soon.",
            "🥠 The best time to plant a tree was 20 years ago. The second best time is now.",
            "🥠 Your hard work will soon pay off.",
            "🥠 Love is on its way to you.",
            "🥠 You will overcome all obstacles.",
            "🥠 Good things happen to those who wait.",
            "🥠 Your future looks very promising."
        ]
        
        fortune = random.choice(fortunes)
        
        embed = create_success_embed(fortune, title="🔮 Fortune Cookie")
        await ctx.send(embed=embed)

    @commands.command(name="fact")
    async def fact_command(self, ctx: commands.Context):
        """Get a random fun fact"""
        facts = [
            "🧠 Octopuses have three hearts and blue blood!",
            "🦒 A giraffe's tongue is 18-20 inches long and blue-black in color!",
            "🐝 Honey never spoils. Archaeologists have found honey in Egyptian tombs that's over 3000 years old!",
            "🦋 Butterflies taste with their feet!",
            "🐧 Penguins can't taste sweet, sour, or spicy foods - only salty and bitter!",
            "🦘 Kangaroos can't walk backwards!",
            "🐨 Koalas sleep 18-22 hours per day!",
            "🦎 Geckos can run up glass surfaces and hang upside down!",
            "🐙 An octopus has eight arms and zero tentacles!",
            "🦩 Flamingos are pink because they eat shrimp and algae!"
        ]
        
        fact = random.choice(facts)
        
        embed = create_info_embed(fact, title="🤓 Fun Fact")
        await ctx.send(embed=embed)


async def setup(bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(Fun(bot))