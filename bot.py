# Copyright (c) 2025, Arka Mondal. All rights reserved.
# Use of this source code is governed by a BSD-style license that
# can be found in the LICENSE file.

import discord
import json
import os
import sys
import datetime
from discord.ext import commands
from typing import Optional
from config import ROLE_ID, TOKEN, LOG_CHANNEL_ID, WELCOME_CHANNEL_ID

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.bans = True
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
async def htbclearverifystat(ctx):
    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("Bruh! you don't have permission to use this command.")
        return

    if ctx.channel.name != 'admin-verify-stat-check':
        await ctx.send("This command can only be used in the #admin-verify-stat-check channel.")
        return

    role = discord.utils.get(ctx.guild.roles, name="'25 Participant")
    if not role:
        await ctx.send("Error: Role '25 Participant not found.")
        return

    rm_count = 0
    rm_list = {}
    for htbid, member_id in claimed.items():
        member = ctx.guild.get_member(int(member_id))
        if member and role in member.roles:
            await member.remove_roles(role)
            rm_count += 1
            rm_list[htbid] = member_id

    # delete purged member list from verification status
    for htbid in rm_list.keys():
        del claimed[htbid]

    for member_id in rm_list.values():
        del claimed_inv[member_id]

    with open('claimed.json', 'w') as f:
        json.dump(claimed, f, indent=4)

    await ctx.send(f"Removed \"'25 Participant\" from {rm_count} members.\nMember list: {' '.join(rm_list.values())}")


@bot.command()
async def htbverify(ctx, id: str = '', passkey: str = ''):
    if id == '' or passkey == '':
        await ctx.send("Usage: `!htbverify <id> <password>`")
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
async def htbban(ctx, member: Optional[discord.Member] = None, reason: Optional[str] = None):
    """Bans a member from the server."""
    # Check if user has Organizer role
    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("You don't have permission to use this command. Organizer role required.")
        return

    # Check if a member was specified
    if member is None:
        await ctx.send("Usage: `!htbban @user [reason]`")
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
        ban_message = f"You have been banned from {ctx.guild.name}."
        if reason:
            ban_message += f" Reason: {reason}"

        try:
            await member.send(ban_message)
        except discord.HTTPException:
            pass  # Ignore if the user has DMs closed

        # Ban the member
        await ctx.guild.ban(member, reason=reason, delete_message_seconds=0)

        # Confirmation message
        confirmation = f"{member} has been banned."
        if reason:
            confirmation += f" Reason: {reason}"
        await ctx.send(confirmation)

        # Log the ban action
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if isinstance(log_channel, discord.TextChannel):
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} ({member}) has been banned",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
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
async def htbunban(ctx, member_id: Optional[int] = None):
    """Unbans a member from the server."""
    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("You don't have permission to use this command. Organizer role required.")
        return

    if member_id is None:
        await ctx.send("Usage: `!htbunban <user_id>`")
        return

    try:
        # Fetch the list of banned users properly
        banned_users = [ban async for ban in ctx.guild.bans()]
        user = next((ban_entry.user for ban_entry in banned_users if ban_entry.user.id == member_id), None)

        if user is None:
            await ctx.send(f"User with ID {member_id} was not found in the ban list.")
            return

        # Unban the user
        await ctx.guild.unban(user)
        await ctx.send(f"User {user} ({member_id}) has been unbanned.")

        # DM the user before unbanning if possible
        # ban_message = "You have been unbanned"
        # member = await bot.fetch_user(member_id)
        # try:
        #     await member.send(ban_message)
        # except discord.HTTPException:
        #     pass

        # Log the unban action
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if isinstance(log_channel, discord.TextChannel):  # Ensure it's a text channel
            embed = discord.Embed(
                title="Member Unbanned",
                description=f"{user.mention} ({user}) has been unbanned",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Unbanned By", value=f"{ctx.author.mention} ({ctx.author})", inline=False)
            embed.set_footer(text=f"User ID: {user.id}")
            await log_channel.send(embed=embed)

    except discord.Forbidden:
        await ctx.send("I don't have permission to unban members.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred while trying to unban the member: {e}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def htbkick(ctx, member: Optional[discord.Member], reason: Optional[str] = None):
    """Kicks a member from the server."""
    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("You don't have permission to use this command. Organizer role required.")
        return

    if member is None:
        await ctx.send("Usage: `!htbkick @user [reason]`")
        return

    if member == ctx.author:
        await ctx.send("You cannot kick yourself.")
        return

    if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
        await ctx.send("You cannot kick a member with the same or higher role than you.")
        return

    try:
        kick_message = f"You have been kicked from {ctx.guild.name}"
        if reason:
            kick_message += f" for the following reason: {reason}"

        try:
            await member.send(kick_message)
        except discord.HTTPException:
            pass  # Could not DM the user

        await ctx.guild.kick(member, reason=reason)

        confirmation = f"{member} has been kicked"
        if reason:
            confirmation += f" for: {reason}"
        await ctx.send(confirmation)

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if isinstance(log_channel, discord.TextChannel):  # Ensure it's a text channel
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} ({member}) has been kicked",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
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
        "`!htbverify <id> <password>` - Verify yourself using your participant ID.\n\n"
        "\t**Example Usage:**\n"
        "\t`!htbverify 12345 password` - Verifies your ID and assigns the appropriate role.\n\n"
        "`!htbwhoareyou` - Display a fun message.\n"
        "`!htbhelp` - Display this help message.\n\n"
        "====== Organizers Only ======\n"
        "`!htbban @user [reason]` - Ban a user from the server.\n"
        "`!htbunban <user_id>` - Unban a user from the server.\n"
        "`!htbkick @user [reason]` - Kick a user from the server.\n"
        "`!htbverifystatcheck <id>|dumpall` - Check the verification status of participant\n"
        "`!htbpurge <count>` - Purge #count messages\n"
        "`!htbclearverifystat` - Purge all verification status of all participants\n"
    )
    await ctx.send(help_message)

@bot.command()
async def htbverifystatcheck(ctx, id: str = ''):
    if id == '':
        await ctx.send("Usage: `!htbverifystatcheck <id>`")
        return

    has_role = discord.utils.get(ctx.author.roles, name='Organizer')
    if not has_role:
        await ctx.send("Bruh! you don't have permission to use this command.")
        return

    if ctx.channel.name != 'admin-verify-stat-check':
        await ctx.send("This command can only be used in the #admin-verify-stat-check channel.")
        return

    if id == 'dumpall':
        id_string = '\n'.join(f'{key}: {value}' for key, value in claimed.items())
        await ctx.send(f"**Vefiication Status: success**\n{id_string}")
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
    print(f'{bot.user.name if bot.user else "Unkown"} has connected to Discord!')
    guild_str = 'guilds' if len(bot.guilds) > 1 else 'guild'
    print(f"Bot is in {len(bot.guilds)} {guild_str}")

@bot.event
async def on_member_join(member):
    """Event handler for when a member joins the server."""

    # Get the welcome channel
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not isinstance(welcome_channel, discord.TextChannel):
        return

    # Create welcome embed
    embed = discord.Embed(
        title=f"Welcome to {member.guild.name}!",
        description=f"Hey {member.mention}, welcome to our server! We're glad to have you here.",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.utcnow()  # Use UTC for consistency
    )

    # Add user avatar if available
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)

    # Add welcome GIF
    embed.set_image(url="https://i.pinimg.com/originals/4e/9e/1f/4e9e1f5a41b738e3066d135da871a46c.gif")

    # Add server info
    embed.add_field(
        name="Getting Started",
        value="Please read the server rules <#1353659054257602610> and head over to the <#1354154665419477093> channel to verify your account.",
        inline=False
    )

    # Add member count
    embed.set_footer(text=f"You are member #{member.guild.member_count}")

    # Send welcome message with a ping to the new member
    await welcome_channel.send(content=f"Hey {member.mention}, welcome to the server!", embed=embed)

    # Also log the join in the log channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if isinstance(log_channel, discord.TextChannel):
        log_embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} ({member}) has joined the server",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        log_embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        log_embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        log_embed.set_footer(text=f"User ID: {member.id}")
        await log_channel.send(embed=log_embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    # Ensure log_channel is a TextChannel before sending messages
    if not isinstance(log_channel, discord.TextChannel):
        return

    embed = discord.Embed(
        title="Message Deleted",
        description=f"Message by {message.author.mention} deleted in {message.channel.mention}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )

    # Add message content if available
    if message.content:
        content = message.content[:1021] + "..." if len(message.content) > 1024 else message.content
        embed.add_field(name="Content", value=content, inline=False)

    if message.attachments:
        attachment_info = "\n".join(f"[{a.filename}]({a.url})" for a in message.attachments)
        if len(attachment_info) > 1024:
            attachment_info = attachment_info[:1021] + "..."
        embed.add_field(name="Attachments", value=attachment_info, inline=False)

    embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")

    await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return

    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    # Ensure log_channel is a TextChannel before sending messages
    if not isinstance(log_channel, discord.TextChannel):
        return

    embed = discord.Embed(
        title="Message Edited",
        description=f"Message by {before.author.mention} edited in {before.channel.mention}",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.utcnow()
    )

    # Add before content if it exists
    if before.content:
        content = before.content[:1021] + "..." if len(before.content) > 1024 else before.content
        embed.add_field(name="Before", value=content, inline=False)

    # Add after content if it exists
    if after.content:
        content = after.content[:1021] + "..." if len(after.content) > 1024 else after.content
        embed.add_field(name="After", value=content, inline=False)

    embed.add_field(
        name="Jump to Message",
        value=f"[Click here]({after.jump_url})",
        inline=False
    )

    embed.set_footer(text=f"User ID: {before.author.id} | Message ID: {before.id}")

    await log_channel.send(embed=embed)

@bot.event
async def on_guild_channel_create(channel):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    # Ensure log_channel is a TextChannel before sending messages
    if not isinstance(log_channel, discord.TextChannel):
        return

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
    creator = None
    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            if entry.target and isinstance(entry.target, discord.abc.GuildChannel):  # Ensure target exists and is a channel
                if entry.target.id == channel.id:
                    creator = entry.user
                    break
    except discord.Forbidden:
        print("Bot lacks permission to view audit logs.")
    except discord.HTTPException as e:
        print(f"Failed to fetch audit logs: {e}")

    embed = discord.Embed(
        title=f"{channel_type} Created",
        description=f"#{channel.name} was created",
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )

    if creator:
        embed.add_field(name="Created By", value=f"{creator.mention} ({creator.name}#{creator.discriminator})", inline=False)

    if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)) and channel.category:
        embed.add_field(name="Category", value=channel.category.name, inline=False)

    embed.set_footer(text=f"Channel ID: {channel.id}")

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
