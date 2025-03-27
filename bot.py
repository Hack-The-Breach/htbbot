# Copyright (c) 2025, Arka Mondal. All rights reserved.
# Use of this source code is governed by a BSD-style license that
# can be found in the LICENSE file.

import discord
import json
import os
import sys
import datetime
from discord.ext import commands
from config import ROLE_ID, TOKEN, LOG_CHANNEL_ID

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

participants_data = 'participants.json'
if len(sys.argv) > 1:
    participants_data = sys.argv[1]

# Load data
with open(participants_data, 'r') as f:
    participants = json.load(f)

id_map = {value['id']: {'email': key, 'name': value['name'], 'password': value['password']} for key, value in participants.items()}

claimed = {}
claimed_inv = {}
if os.path.exists('claimed.json') and os.path.getsize('claimed.json') > 0:
    with open('claimed.json') as f:
        claimed = json.load(f)

    for key, value in claimed.items():
        claimed_inv[value] = key

@bot.command()
async def verify(ctx, id: str = '', passkey: str = ''):
    if id == '' or passkey == '':
        await ctx.send("Usage: `!verify <id> <password>`")
        return

    # Check if command is used in 'verify' channel
    if ctx.channel.name != 'verify':
        await ctx.send("This command can only be used in the #verify channel.")
        return

    # Validate
    participant = id_map.get(id)
    if not participant:
        await ctx.send(f'Invalid ID: {id}. Please check your ID and try again.')
        return

    # check if the user is trying to verify using another id
    if str(ctx.author.id) in claimed.values() and id != claimed_inv[str(ctx.author.id)]:
        await ctx.send(f'**WARNING!** You have been already verified with another id.<@&{int(ROLE_ID)}>')
        return

    if id in claimed:
        if str(ctx.author.id) == claimed[id]:
            await ctx.send('You have been already verified.')
        else:
            await ctx.send(f'This ID ({id}) has already been claimed.')
        return

    if passkey != id_map[id]['password']:
        await ctx.send(f'Incorrect password for id: {id}')
        return

    # Find the role
    role = discord.utils.get(ctx.guild.roles, name="'25 Participant")
    if not role:
        await ctx.send('Role not found. Contact Organizers.')
        return

    try:
        # Add role and update records
        await ctx.author.add_roles(role)
        claimed[id] = str(ctx.author.id)
        claimed_inv[str(ctx.author.id)] = id

        # Save claimed IDs
        with open('claimed.json', 'w') as f:
            json.dump(claimed, f, indent=4)

        await ctx.send(f'Verified as **{participant["name"]}**! You\'ve received the "{role.name}" role.')
    except discord.Forbidden:
        await ctx.send("I don't have permission to assign roles. Contact Organizers.")
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send("Error processing verification. Contact Organizers.")

@bot.command()
async def ban(ctx, member: discord.Member = None, *, reason=None):
    """Bans a member from the server."""
    # Check if user has Organizer role
    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("You don't have permission to use this command. Organizer role required.")
        return

    # Check if a member was specified
    if member is None:
        await ctx.send("Usage: `!ban @user [reason]`")
        return

    # Cannot ban yourself
    if member == ctx.author:
        await ctx.send("You cannot ban yourself.")
        return

    # Cannot ban users with same or higher role
    if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
        await ctx.send("You cannot ban a member with the same or higher role than you.")
        return

    try:
        # DM the user before banning if possible
        ban_message = f"You have been banned from {ctx.guild.name}"
        if reason:
            ban_message += f" for the following reason: {reason}"
        
        try:
            await member.send(ban_message)
        except discord.HTTPException:
            # Could not DM the user
            pass
            
        # Ban the member
        await ctx.guild.ban(member, reason=reason, delete_message_days=0)
        
        # Confirm the ban
        confirmation = f"**{member}** has been banned"
        if reason:
            confirmation += f" for: {reason}"
        await ctx.send(confirmation)
        
        # Log the ban action
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} ({member}) has been banned",
                color=discord.Color.dark_red(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Banned By", value=f"{ctx.author.mention} ({ctx.author})", inline=False)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            await log_channel.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("I don't have permission to ban members.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred while trying to ban the member: {e}")

@bot.command()
async def unban(ctx, *, member_id=None):
    """Unbans a member from the server."""
    # Check if user has Organizer role
    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("You don't have permission to use this command. Organizer role required.")
        return

    # Check if a member ID was specified
    if member_id is None:
        await ctx.send("Usage: `!unban <user_id>`")
        return
        
    try:
        # Convert string to int if it's a user ID
        try:
            user_id = int(member_id)
            banned_user = discord.Object(id=user_id)
        except ValueError:
            await ctx.send("Please provide a valid user ID.")
            return
            
        # Unban the user
        await ctx.guild.unban(banned_user)
        await ctx.send(f"User with ID {member_id} has been unbanned.")
        
        # Log the unban action
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Unbanned",
                description=f"User with ID {member_id} has been unbanned",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Unbanned By", value=f"{ctx.author.mention} ({ctx.author})", inline=False)
            embed.set_footer(text=f"User ID: {member_id}")
            await log_channel.send(embed=embed)
        
    except discord.NotFound:
        await ctx.send(f"User with ID {member_id} was not found in the ban list.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to unban members.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred while trying to unban the member: {e}")

@bot.command()
async def kick(ctx, member: discord.Member = None, *, reason=None):
    """Kicks a member from the server."""
    # Check if user has Organizer role
    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("You don't have permission to use this command. Organizer role required.")
        return
        
    # Check if a member was specified
    if member is None:
        await ctx.send("Usage: `!kick @user [reason]`")
        return
        
    # Cannot kick yourself
    if member == ctx.author:
        await ctx.send("You cannot kick yourself.")
        return
        
    # Cannot kick users with same or higher role
    if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
        await ctx.send("You cannot kick a member with the same or higher role than you.")
        return
        
    try:
        # DM the user before kicking if possible
        kick_message = f"You have been kicked from {ctx.guild.name}"
        if reason:
            kick_message += f" for the following reason: {reason}"
            
        try:
            await member.send(kick_message)
        except discord.HTTPException:
            # Could not DM the user
            pass
            
        # Kick the member
        await ctx.guild.kick(member, reason=reason)
        
        # Confirm the kick
        confirmation = f"**{member}** has been kicked"
        if reason:
            confirmation += f" for: {reason}"
        await ctx.send(confirmation)
        
        # Log the kick action
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} ({member}) has been kicked",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Kicked By", value=f"{ctx.author.mention} ({ctx.author})", inline=False)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            await log_channel.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("I don't have permission to kick members.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred while trying to kick the member: {e}")

@bot.command()
async def htbhelp(ctx):
    """Displays help information for bot commands."""
    help_message = (
        "**Available Commands:**\n\n"
        "`!verify <id> <password>` - Verify yourself using your participant ID.\n\n"
        "\t**Example Usage:**\n"
        "\t`!verify 12345 password` - Verifies your ID and assigns the appropriate role.\n\n"
        "`!htbwhoareyou` - Display a fun message.\n"
        "`!htbhelp` - Display this help message.\n\n"
        "====== Organizers Only ======\n"
        "`!ban @user [reason]` - Ban a user from the server.\n"
        "`!unban <user_id>` - Unban a user from the server.\n"
        "`!kick @user [reason]` - Kick a user from the server.\n\n"
        "====== Organizers Only ======\n"
        "`!verifystatcheck <id>` - Check the verification status of participant\n"
        "`!htbpurge <amount>` - Delete a specific number of messages from a channel.\n"
    )
    await ctx.send(help_message)

@bot.command()
async def verifystatcheck(ctx, id: str = ''):
    if id == '':
        await ctx.send("Usage: `!verifystatcheck <id>`")
        return

    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("Bruh! you don't have permission to use this command.")
        return

    if ctx.channel.name != 'admin-verify-stat-check':
        await ctx.send("This command can only be used in the #admin-verify-stat-check channel.")
        return

    if id not in claimed:
        await ctx.send(f"Verification Status unknown of id: {id}.")
        return

    await ctx.send(f"Verifciation Status : success\n{id} -> user: `{claimed[id]}` name: {id_map[id]['name']} \
email: {id_map[id]['email']}")

@bot.command()
async def htbpurge(ctx, amount: int = 0):
    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("Bruh! you don't have permission to use this command.")
        return

    # Validate amount
    if amount <= 0:
        await ctx.send("Please provide a positive number of messages to delete.")
        return

    # Discord API limits bulk deletion to 100 messages at a time
    if amount > 100:
        await ctx.send("You can only delete up to 100 messages at a time.")
        return

    try:
        # Delete the command message first
        await ctx.message.delete()

        # Bulk delete messages
        deleted = await ctx.channel.purge(limit=amount)

        # Send a confirmation message
        confirmation = await ctx.send(f"Deleted {len(deleted)} messages.")

        # Auto-delete the confirmation message after 5 seconds
        await confirmation.delete(delay=2)

    except discord.Forbidden:
        await ctx.send("I don't have permission to delete messages.")
    except discord.HTTPException:
        await ctx.send("An error occurred while trying to delete messages.")

@bot.command()
async def htbwhoareyou(ctx):
    await ctx.send("Hey there! I'm the HackTheBreach Bot. Hope you're having an awesome time at the bootcamp!\n\
Created by Arka Mondal ([Arix](https://github.com/arixsnow)) and Suvan Sarkar ([OrganHarvester](https://github.com/Suvansarkar))!")

# Event listeners for logging
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

@bot.event
async def on_message_delete(message):
    # Ignore messages from bots
    if message.author.bot:
        return
        
    # Get the log channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return  # Log channel not found
        
    # Create an embed for the deleted message
    embed = discord.Embed(
        title="Message Deleted",
        description=f"Message by {message.author.mention} deleted in {message.channel.mention}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now()
    )
    
    # Add message content if available
    if message.content:
        # Truncate if too long
        content = message.content
        if len(content) > 1024:
            content = content[:1021] + "..."
        embed.add_field(name="Content", value=content, inline=False)
    
    # Add attachments info if any
    if message.attachments:
        attachment_info = "\n".join([f"[{a.filename}]({a.url})" for a in message.attachments])
        if attachment_info:
            embed.add_field(name="Attachments", value=attachment_info, inline=False)
    
    # Add footer with user info
    embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")
    
    # Send the log
    await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    # Ignore edits by bots or when content hasn't changed
    if before.author.bot or before.content == after.content:
        return
        
    # Get the log channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return  # Log channel not found
        
    # Create an embed for the edited message
    embed = discord.Embed(
        title="Message Edited",
        description=f"Message by {before.author.mention} edited in {before.channel.mention}",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now()
    )
    
    # Add before content
    if before.content:
        # Truncate if too long
        content = before.content
        if len(content) > 1024:
            content = content[:1021] + "..."
        embed.add_field(name="Before", value=content, inline=False)
    
    # Add after content
    if after.content:
        # Truncate if too long
        content = after.content
        if len(content) > 1024:
            content = content[:1021] + "..."
        embed.add_field(name="After", value=content, inline=False)
    
    # Add link to the message
    embed.add_field(
        name="Jump to Message", 
        value=f"[Click here]({after.jump_url})", 
        inline=False
    )
    
    # Add footer with user info
    embed.set_footer(text=f"User ID: {before.author.id} | Message ID: {before.id}")
    
    # Send the log
    await log_channel.send(embed=embed)

@bot.event
async def on_guild_channel_create(channel):
    # Get the log channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return  # Log channel not found
        
    # Get channel type
    if isinstance(channel, discord.TextChannel):
        channel_type = "Text Channel"
    elif isinstance(channel, discord.VoiceChannel):
        channel_type = "Voice Channel"
    elif isinstance(channel, discord.CategoryChannel):
        channel_type = "Category"
    else:
        channel_type = "Channel"
    
    # Get audit logs to find who created the channel
    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            creator = entry.user
            break
    except:
        creator = None
    
    # Create an embed for the channel creation
    embed = discord.Embed(
        title=f"{channel_type} Created",
        description=f"#{channel.name} was created",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now()
    )
    
    # Add creator info if available
    if creator:
        embed.add_field(name="Created By", value=f"{creator.mention} ({creator.name}#{creator.discriminator})", inline=False)
    
    # Add category if applicable
    if hasattr(channel, 'category') and channel.category:
        embed.add_field(name="Category", value=channel.category.name, inline=False)
    
    # Add channel ID
    embed.set_footer(text=f"Channel ID: {channel.id}")
    
    # Send the log
    await log_channel.send(embed=embed)

if __name__ == '__main__':
    if TOKEN == "":
        print("Error: TOKEN is empty!")
        sys.exit(1)

    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("Error: Invalid token.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
