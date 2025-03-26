# Copyright (c) 2025, Arka Mondal. All rights reserved.
# Use of this source code is governed by a BSD-style license that
# can be found in the LICENSE file.

import discord
import json
import os
import sys
from discord.ext import commands
from config import TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Load data
with open('participants.json', 'r') as f:
    participants = json.load(f)

id_map = {value['id']: {'email': key, 'name': value['name']} for key, value in participants.items()}

claimed = {}
if os.path.exists('claimed.json'):
    with open('claimed.json') as f:
        claimed = json.load(f)

@bot.command()
async def verify(ctx, id: str = ''):
    if id == '':
        await ctx.send("Usage: `!verify <id>`")
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

    if id in claimed:
        await ctx.send(f'This ID ({id}) has already been claimed.')
        return

    # Find the role
    role = discord.utils.get(ctx.guild.roles, name="'25 Participant")
    if not role:
        await ctx.send('Role not found. Contact server admin.')
        return

    try:
        # Add role and update records
        await ctx.author.add_roles(role)
        claimed[id] = str(ctx.author.id)

        # Save claimed IDs
        with open('claimed.json', 'w') as f:
            json.dump(claimed, f, indent=4)

        await ctx.send(f'Verified as **{participant["name"]}**! You\'ve received the "{role.name}" role.')
    except discord.Forbidden:
        await ctx.send("I don't have permission to assign roles. Contact serv admin.")
    except Exception as e:
        print(f'Error: {e}')
        await ctx.send("Error processing verification. Contact server admin.")

@bot.command()
async def help(ctx):
    """Displays help information for bot commands."""
    help_message = (
        "**Available Commands:**\n"
        "`!verify <id>` - Verify yourself using your participant ID.\n"
        "`!help` - Display this help message.\n"
        "**Example Usage:**\n"
        "`!verify 12345` - Verifies your ID and assigns the appropriate role.\n\n"
        "====== Admin Only ======"
        "`!verifystatcheck <id>` - Check the verification status of participant (Admin Only)"
    )
    await ctx.send(help_message)

@bot.command()
async def verifystatcheck(ctx, id: str = ''):
    if id == '':
        await ctx.send("Usage: `!verify <id>`")
        return

    if ctx.channel.name != 'admin-verify-stat-check':
        await ctx.send("This command can only be used in the #admin-verify-stat-check channel.")
        return

    if id not in claimed:
        await ctx.send(f"Verification Status Unknown of id: {id}.")
        return

    await ctx.send(f"Verifciation Status : success\n{id} -> user: `{claimed[id]}` name: {id_map[id]['name']} \
email: {id_map[id]['email']}")


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
