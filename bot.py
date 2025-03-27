# Copyright (c) 2025, Arka Mondal. All rights reserved.
# Use of this source code is governed by a BSD-style license that
# can be found in the LICENSE file.

import discord
import json
import os
import sys
from discord.ext import commands
from config import ROLE_ID, TOKEN

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
        member = ctx.guild.get_memeber(int(member_id))
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
        await ctx.send(f"Vefiication Status: success\n{'\n'.join(f'{key}: {value}' for key, value in claimed.items())}")
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
Created by Arka Mondal ([Arix](https://github.com/arixsnow))!")

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
