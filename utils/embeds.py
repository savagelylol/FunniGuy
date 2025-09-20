"""
Embed utility functions for FunniGuy Discord Bot
"""
import discord
from datetime import datetime
from typing import Optional


def create_basic_embed(
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: discord.Color = discord.Color.blue(),
    footer_text: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    image_url: Optional[str] = None
) -> discord.Embed:
    """
    Create a basic Discord embed with common formatting
    
    Args:
        title: The embed title
        description: The embed description
        color: The embed color (default: blue)
        footer_text: Footer text to add
        thumbnail_url: URL for thumbnail image
        image_url: URL for main image
    
    Returns:
        discord.Embed: Formatted embed object
    """
    embed = discord.Embed(color=color)
    
    if title:
        embed.title = title
    
    if description:
        embed.description = description
    
    if footer_text:
        embed.set_footer(text=footer_text)
    
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    if image_url:
        embed.set_image(url=image_url)
    
    # Add timestamp
    embed.timestamp = datetime.utcnow()
    
    return embed


def create_success_embed(message: str, title: str = "Success") -> discord.Embed:
    """Create a success-themed embed"""
    return create_basic_embed(
        title=f"✅ {title}",
        description=message,
        color=discord.Color.green()
    )


def create_error_embed(message: str, title: str = "Error") -> discord.Embed:
    """Create an error-themed embed"""
    return create_basic_embed(
        title=f"❌ {title}",
        description=message,
        color=discord.Color.red()
    )


def create_info_embed(message: str, title: str = "Info") -> discord.Embed:
    """Create an info-themed embed"""
    return create_basic_embed(
        title=f"ℹ️ {title}",
        description=message,
        color=discord.Color.blue()
    )


def create_warning_embed(message: str, title: str = "Warning") -> discord.Embed:
    """Create a warning-themed embed"""
    return create_basic_embed(
        title=f"⚠️ {title}",
        description=message,
        color=discord.Color.orange()
    )