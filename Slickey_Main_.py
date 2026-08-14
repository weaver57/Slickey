import asyncio
import io
import os
import random
import re
import sqlite3
import traceback
import time
import json
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands, AllowedMentions
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput, Select
from discord.utils import get
from discord.errors import Forbidden
#import pymysql
import asyncpg
import utils, Slickey_Secondary_, ai_cog, permission_system
#from cachetools import TTLCache
from dotenv import load_dotenv
load_dotenv()

from utils import (find_closest_role, find_closest_member, is_command_blocked, is_authorized_or_not, only_for_setprefix, permissions_check_decorator, active_role_timers, active_begging_requests, jackpot_game, active_auctions, responded_messages,
                   tower_games, jailed_users_data, PERMISSIONS_LIST, PERMISSIONS_DICT, format_timedelta, convert_to_seconds, unmute_member, key_permissions, mod_perms, admin_perms, get_message_count, get_num_slaves_owned, get_days_on_server, calculate_slave_price, get_user_balance, update_user_balance, add_transaction, is_slave, is_master, get_master_of_slave, get_top_slaves, get_slaves_of_master, has_permission_for_slave, color_wars, create_empty_grid, check_win_condition, process_chain_reactions, update_points, active_games, purchase_command_for_slave,
                   get_unpurchased_commands, generate_leaderboard, random_emojis, get_user_level, memname_choice, create_gun_config, create_game_board_embed, create_initial_game_state, calculate_hand_size, deal_cards, operation_active, get_cell_emoji, ColorWarButton, memory_games, update_game_content, determine_winner, db_pool, init_db_pool, ShopPaginationView, CategorySelect, ACTIONS)

intents = discord.Intents.all()


chota_wigu_bot_token = os.getenv("BOT_TOKEN_1")
bada_wigu_bot_token = os.getenv("BOT_TOKEN_2")


#prefix_cache = TTLCache(maxsize=1024, ttl=600)  # 10-minute cache

async def get_prefix(bot, message):
    if not message.guild:
        return "w."
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    #key = f"{guild_id}:{user_id}"

    #if key in prefix_cache:
        #print("Used cached memory here.")
        #return prefix_cache[key]

    if utils.db_pool is None or utils.db_pool._closed:
        return "w."


    async with utils.db_pool.acquire(timeout=5.0) as conn:
        user_prefix = await conn.fetchrow("SELECT prefix FROM user_prefixes WHERE user_id = $1", user_id)
        if user_prefix:
            #prefix_cache[key] = user_prefix["prefix"]
            #print("Inserted cached memory here.")
            return user_prefix["prefix"]

        guild_prefix = await conn.fetchrow("SELECT prefix FROM server_prefixes WHERE guild_id = $1", guild_id)
        if guild_prefix:
            #prefix_cache[key] = guild_prefix["prefix"]
            #print("Inserted cached memory here.")
            return guild_prefix["prefix"]

    
    #prefix_cache[key] = "w."
    #print("Inserted cached memory here.")
    return "w."

async def resolve_prefix(guild_id: int | None, user_id: int) -> str:
    """Same lookup priority as get_prefix(), but usable from an Interaction (no Message object)."""
    if guild_id is None:
        return "w."
    if utils.db_pool is None or utils.db_pool._closed:
        return "w."
    try:
        async with utils.db_pool.acquire(timeout=5.0) as conn:
            user_prefix = await conn.fetchrow("SELECT prefix FROM user_prefixes WHERE user_id = $1", str(user_id))
            if user_prefix:
                return user_prefix["prefix"]
            guild_prefix = await conn.fetchrow("SELECT prefix FROM server_prefixes WHERE guild_id = $1", str(guild_id))
            if guild_prefix:
                return guild_prefix["prefix"]
    except Exception:
        return "w."
    return "w."



bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
permission_system.install(bot, lambda: utils.db_pool)




async def block_or_command_autocomplete(interaction: discord.Interaction, current: str):
    permission_type = interaction.namespace.permission_type
    block_choices = ["yazy", "memory","colorwars", "say", "spam", "ping", "hello", "buckshot", "selfprefix", "echo", "av", "img", "afk", "msgcount", "bn", "setprefix", "setnick", "mute", "unmute", "ban", "unban", "purgereaction", "stealsticker", "roleroulette", "showperm", "setperm", "role", "setrole", "whois", "modlogs", "purge", "leaderboard", "cf", "tower", "diceroll", "wish", "jackpot", "help", "shinecrown", "fanmaster", "minerock", "fetchwater", "bakebread", "trade", "slrefund", "slrelease", "escape", "tribute", "tip", "slinfo", "slshow", "slbuy", "shop", "buycmd", "beg", "daily", "give", "slwhip", "slrole", "slkick", "slsetnick", "sljail", "slunmute", "slmute", "slunjail", "wallet", "chkprice", 'waifu', 'wtags'] + ACTIONS
    
    command_choices = ["say", "spam", "echo", "setnick", "mute", "unmute", "ban", "unban", "role", "purgereaction",
                       "stealsticker",
                       "roleroulette", "setperm", "setrole", "whois", "modlogs"]

    if permission_type == "block":
        return [app_commands.Choice(name=cmd, value=cmd) for cmd in block_choices if current.lower() in cmd][:25]
    elif permission_type == "command":
        return [app_commands.Choice(name=cmd, value=cmd) for cmd in command_choices if current.lower() in cmd][:25]
    return []


@bot.command(name="giveperm", aliases=['gp', 'GP', 'Giveperm', 'GIVEPERM', "Gp"], description="Give user permissions and roles.")
async def give_permission(ctx, target: discord.Member, permission_type: str, command_name: str = None):
    await ctx.reply("`giveperm` is retired. Use `/permissions role-*` and `/permissions rule-*`.")
    return
    # <---REMOVE---> legacy implementation (unreachable)
    if not permission_system.is_superuser(ctx.author.id, ctx.guild.owner_id):
        await ctx.reply("Only Server Owner can use this command.")
        return

    async with utils.db_pool.acquire() as conn:
        try:
            if permission_type == 'command':
                if not command_name:
                    await ctx.send("You must specify a command name for the 'command' permission type.")
                    return

                if await conn.fetchval("SELECT 1 FROM command_permissions WHERE guild_id = $1 AND user_id = $2 AND command_name = $3",
                ctx.guild.id, target.id, command_name):
                    await ctx.send(f"{target.mention} already has permission for the `{command_name}` command.")
                    return

                await conn.execute(
                "INSERT INTO command_permissions (guild_id, user_id, command_name) VALUES ($1, $2, $3)",
                ctx.guild.id, target.id, command_name)
                await conn.execute(
                    "INSERT INTO roles (guild_id, user_id, role, level) VALUES ($1, $2, $3, $4)",
                    ctx.guild.id, target.id, permission_type, 1)
                
                message = f"Gave {target.mention} permission for the `{command_name}` command."

            elif permission_type in ['moderator', 'admin', 'authorized']:
                existing_role = await conn.fetchval( "SELECT role FROM roles WHERE guild_id = $1 AND user_id = $2 AND role IN ('moderator','admin','authorized')", ctx.guild.id, target.id)

                if existing_role:
                    await ctx.send(f"{target.mention} already has the role `{existing_role}`. Please remove it first.")
                    return
                
                await conn.execute( "INSERT INTO roles (guild_id, user_id, role, level) VALUES ($1, $2, $3, $4)", ctx.guild.id, target.id, permission_type, PERM_LEVELS[permission_type])

                message = f"Assigned {permission_type} role to {target.mention}"

            elif permission_type == 'block':
                if not command_name:
                    await ctx.send("You must specify a command to block.")
                    return

                if await conn.fetchval( "SELECT 1 FROM blocked_commands WHERE guild_id = $1 AND user_id = $2 AND command_name = $3", ctx.guild.id, target.id, command_name):
                    await ctx.send(f"{target.display_name} is already blocked from {command_name}.")
                    return

                await conn.execute( "INSERT INTO blocked_commands (guild_id, user_id, command_name) VALUES ($1, $2, $3)", ctx.guild.id, target.id, command_name)
                
                message = f"Blocked {target.mention} from using {command_name}"

            else:
                await ctx.send("Invalid permission type.")
                return

            await ctx.send(message)

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")


    # <---REMOVE--->

@give_permission.error
async def give_permission_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title="Give Permission", description=(
            "Gives one of the bot's internal permissions to the user.\n\n**Syntax**: `giveperm @user permission`"),
                              color=discord.Color.blue())
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        await ctx.reply("Bad argument provided. Please check your input.")
    else:
        await ctx.reply(f"An error occurred: {str(error)}")


@bot.tree.command(name="giveperm", description="Give user permissions and roles.")
@app_commands.describe(target="The user to assign the permission to.",
                       permission_type="Type of permission to grant/block.",
                       command_name="Specify the command (only for 'command' and 'block' options).")
@app_commands.choices(permission_type=[
    app_commands.Choice(name="Command", value="command"),
    app_commands.Choice(name="Block Command", value="block"),
    app_commands.Choice(name="Moderator", value="moderator"),
    app_commands.Choice(name="Admin", value="admin"),
    app_commands.Choice(name="Authorized", value="authorized")
])
@app_commands.autocomplete(command_name=block_or_command_autocomplete)
async def give_perm(interaction: discord.Interaction, target: discord.Member, permission_type: app_commands.Choice[str],
                    command_name: str = None):
    await interaction.response.send_message("`giveperm` is retired. Use `/permissions role-*` and `/permissions rule-*`.", ephemeral=True)
    return
    # <---REMOVE---> legacy implementation (unreachable)
    if not permission_system.is_superuser(interaction.user.id, interaction.guild.owner_id):
        await interaction.response.send_message("Only the Server Owner can use this command.", ephemeral=True)
        return

    async with utils.db_pool.acquire() as conn:
        try:
            if permission_type.value == 'command':
                if not command_name:
                    await interaction.response.send_message(
                        "You must specify a command name for the 'Command' permission type.", ephemeral=True)
                    return

                if await conn.fetchval("SELECT 1 FROM command_permissions WHERE guild_id = $1 AND user_id = $2 AND command_name = $3",interaction.guild.id, target.id, command_name):
                    await interaction.response.send_message(f"{target.mention} already has permission for the `{command_name}` command.", ephemeral=True)
                    return

                await conn.execute("INSERT INTO command_permissions (guild_id, user_id, command_name) VALUES ($1, $2, $3)",interaction.guild.id, target.id, command_name)
                await conn.execute("INSERT INTO roles (guild_id, user_id, role, level) VALUES ($1, $2, $3, $4)",interaction.guild.id, target.id, permission_type.value, 1)

                message = f"Gave {target.mention} permission for the `{command_name}` command."

            elif permission_type.value in ['moderator', 'admin', 'authorized']:

                existing_role = await conn.fetchval("SELECT role FROM roles WHERE guild_id = $1 AND user_id = $2 AND role IN ('moderator','admin','authorized')", interaction.guild.id, target.id)
                if existing_role:
                    await interaction.response.send_message(
                        f"{target.mention} already has the role `{existing_role}`. Please remove it first.",
                        ephemeral=True)
                    return

                await conn.execute("INSERT INTO roles (guild_id, user_id, role, level) VALUES ($1, $2, $3, $4)",
                interaction.guild.id, target.id, permission_type.value, PERM_LEVELS[permission_type.value])
                
                message = f"Assigned `{permission_type.name}` role to {target.mention}."

            elif permission_type.value == 'block':
                if not command_name:
                    await interaction.response.send_message("You must specify a command to block.", ephemeral=True)
                    return

                if await conn.fetchval( "SELECT 1 FROM blocked_commands WHERE guild_id = $1 AND user_id = $2 AND command_name = $3", interaction.guild.id, target.id, command_name):
                    await interaction.response.send_message(
                        f"{target.display_name} is already blocked from `{command_name}`.", ephemeral=True)
                    return

                await conn.execute("INSERT INTO blocked_commands (guild_id, user_id, command_name) VALUES ($1, $2, $3)",interaction.guild.id, target.id, command_name)
                
                message = f"Blocked {target.mention} from using `{command_name}`."

            else:
                await interaction.response.send_message("Invalid permission type.", ephemeral=True)
                return


            await interaction.response.send_message(message)

        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)


    # <---REMOVE--->

@bot.command(name="takeperm", aliases=["tp", "TP", "Takeperm", "TAKEPERM", "Tp"], description="Remove user permissions and roles.")
async def take_permission(ctx, target: discord.Member, permission_type: str, command_name: str = None):
    await ctx.reply("`takeperm` is retired. Use `/permissions role-*` and `/permissions rule-*`.")
    return
    # <---REMOVE---> legacy implementation (unreachable)
    if not permission_system.is_superuser(ctx.author.id, ctx.guild.owner_id):
        await ctx.reply("Only Server Owner can use this command.")
        return
    async with utils.db_pool.acquire() as conn:
        try:
            if permission_type == 'block':
                if not command_name:
                    await ctx.send("You must specify a command to unblock.")
                    return

                if not await conn.fetchval("SELECT 1 FROM blocked_commands WHERE guild_id = $1 AND user_id = $2 AND command_name = $3",ctx.guild.id, target.id, command_name):
                    await ctx.send(f"{target.display_name} is not blocked from {command_name}.")
                    return

                await conn.execute("DELETE FROM blocked_commands WHERE guild_id = $1 AND user_id = $2 AND command_name = $3",ctx.guild.id, target.id, command_name)
                
                message = f"Unblocked {target.display_name} from {command_name}"

            elif permission_type in ['moderator', 'admin', 'authorized']:
                if not await conn.fetchval( "SELECT 1 FROM roles WHERE guild_id = $1 AND user_id = $2 AND role = $3", ctx.guild.id, target.id, permission_type):
                    await ctx.send(f"{target.display_name} does not have the `{permission_type}` role.")
                    return

                await conn.execute( "DELETE FROM roles WHERE guild_id = $1 AND user_id = $2 AND role = $3", ctx.guild.id, target.id, permission_type)

                message = f"Removed {permission_type} role from {target.display_name}"
            
            elif permission_type == "command":
                if not command_name:
                    await ctx.send("You must specify a command.")
                    return

                if not await conn.fetchval("SELECT 1 FROM roles WHERE guild_id = $1 AND user_id = $2 AND role = $3",
                ctx.guild.id, target.id, permission_type):
                    await ctx.send(f"{target.display_name} does not have the `{permission_type}` command.")
                    return

                await conn.execute( "DELETE FROM roles WHERE guild_id = $1 AND user_id = $2 AND role = $3", ctx.guild.id, target.id, permission_type)

                await conn.execute( "DELETE FROM command_permissions WHERE guild_id = $1 AND user_id = $2 AND command_name = $3", ctx.guild.id, target.id, command_name)

                message = f"Removed {command_name} permission from {target.display_name}."
            else:
                await ctx.send("Invalid permission type.")
                return


            await ctx.send(message)

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")


    # <---REMOVE--->

@take_permission.error
async def take_permission_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title="Take Permission", description=(
            "Takes one of the bot's internal permissions from the user.\n\n**Syntax**: `takeperm @user permission`"),
                              color=discord.Color.blue())
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        await ctx.reply("Bad argument provided. Please check your input.")
    else:
        await ctx.reply(f"An error occurred: {str(error)}")


@bot.tree.command(name="takeperm", description="Remove user permissions and roles.")
@app_commands.describe(target="The user to remove the permission from.",
                       permission_type="Type of permission to remove.",
                       command_name="Specify the command (only for 'command' and 'block' types).")
@app_commands.choices(permission_type=[
    app_commands.Choice(name="Command", value="command"),
    app_commands.Choice(name="Block Command", value="block"),
    app_commands.Choice(name="Moderator", value="moderator"),
    app_commands.Choice(name="Admin", value="admin"),
    app_commands.Choice(name="Authorized", value="authorized")])
@app_commands.autocomplete(command_name=block_or_command_autocomplete)
async def take_perm(interaction: discord.Interaction, target: discord.Member, permission_type: app_commands.Choice[str],
                    command_name: str = None):
    await interaction.response.send_message("`takeperm` is retired. Use `/permissions role-*` and `/permissions rule-*`.", ephemeral=True)
    return
    # <---REMOVE---> legacy implementation (unreachable)
    if not permission_system.is_superuser(interaction.user.id, interaction.guild.owner_id):
        await interaction.response.send_message("Only the Server Owner can use this command.", ephemeral=True)
        return

    async with utils.db_pool.acquire() as conn:
        try:
            if permission_type.value == 'block':
                if not command_name:
                    await interaction.response.send_message("You must specify a command to unblock.", ephemeral=True)
                    return

                if not await conn.fetchval( "SELECT 1 FROM blocked_commands WHERE guild_id = $1 AND user_id = $2 AND command_name = $3", interaction.guild.id, target.id, command_name):
                    await interaction.response.send_message(f"{target.display_name} is not blocked from `{command_name}`.", ephemeral=True)
                    return

                await conn.execute( "DELETE FROM blocked_commands WHERE guild_id = $1 AND user_id = $2 AND command_name = $3", interaction.guild.id, target.id, command_name)
                

                message = f"Unblocked {target.mention} from `{command_name}`."

            elif permission_type.value in ['moderator', 'admin', 'authorized']:
                
                if not await conn.fetchval("SELECT 1 FROM roles WHERE guild_id = $1 AND user_id = $2 AND role = $3", interaction.guild.id, target.id, permission_type.value):
                    await interaction.response.send_message(f"{target.display_name} does not have the `{permission_type.name}` role.", ephemeral=True)
                    return

                await conn.execute("DELETE FROM roles WHERE guild_id = $1 AND user_id = $2 AND role = $3",interaction.guild.id, target.id, permission_type.value)
          
                message = f"Removed `{permission_type.name}` role from {target.mention}."

            elif permission_type.value == 'command':
                if not command_name:
                    await interaction.response.send_message("You must specify a command name.", ephemeral=True)
                    return

                if not await conn.fetchval("SELECT 1 FROM command_permissions WHERE guild_id = $1 AND user_id = $2 AND command_name = $3", interaction.guild.id, target.id, command_name):
                    await interaction.response.send_message(
                        f"{target.display_name} does not have permission for `{command_name}`.", ephemeral=True)
                    return
                
                await conn.execute("DELETE FROM roles WHERE guild_id = $1 AND user_id = $2 AND role = $3",interaction.guild.id, target.id, permission_type.value)

                await conn.execute("DELETE FROM command_permissions WHERE guild_id = $1 AND user_id = $2 AND command_name = $3",interaction.guild.id, target.id, command_name)

                message = f"Removed `{command_name}` permission from {target.mention}."

            else:
                await interaction.response.send_message("Invalid permission type.", ephemeral=True)
                return

            await interaction.response.send_message(message)

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)


    # <---REMOVE--->

@bot.command(name="botperm", aliases=['BOTPERM', 'bp', 'Botperm', 'BP', 'Bp'], description="List all users with roles, command permissions, and blocked commands.")
async def list_botperms(ctx):
    await ctx.reply("`botperm` is retired. Use `/permissions role-list` and `/permissions rule-list`.")
    return
    # <---REMOVE---> legacy implementation (unreachable)
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "botperm"):
        return

    async with utils.db_pool.acquire(timeout=5.0) as conn:
        try:

            roles_data = await conn.fetch(""" WITH all_users AS (
          SELECT guild_id, user_id FROM roles WHERE guild_id = $1
          UNION
          SELECT guild_id, user_id FROM command_permissions WHERE guild_id = $2
          UNION
          SELECT guild_id, user_id FROM blocked_commands WHERE guild_id = $3
        )
        SELECT a.user_id,
               STRING_AGG(DISTINCT r.role, ', ')        AS roles,
               STRING_AGG(DISTINCT cp.command_name, ', ') AS commands,
               STRING_AGG(DISTINCT bc.command_name, ', ') AS blocked_commands
        FROM all_users a
        LEFT JOIN roles r  ON a.guild_id = r.guild_id  AND a.user_id = r.user_id
        LEFT JOIN command_permissions cp 
             ON a.guild_id = cp.guild_id 
            AND a.user_id = cp.user_id
        LEFT JOIN blocked_commands bc 
             ON a.guild_id = bc.guild_id 
            AND a.user_id = bc.user_id
        WHERE a.guild_id = $4
        GROUP BY a.user_id """, ctx.guild.id, ctx.guild.id, ctx.guild.id, ctx.guild.id)

            if not roles_data:
                await ctx.send("No users found in the role lists.")
                return

            embed = discord.Embed(
                title="Bot Permissions Overview",
                color=discord.Color.gold(),
                description="Below is the list of users with their roles and command permissions."
            )
            for user_id, role, commands, blocked_commands in roles_data:
                member = ctx.guild.get_member(int(user_id))
                display_name = member.display_name if member else f"Unknown (ID: {user_id})"
                roles_list = sorted(set(role.split(', '))) if role and role.strip() else []
                roles_str = ", ".join(roles_list) if roles_list else "None"
                commands_list = sorted(set(commands.split(', '))) if commands and commands.strip() else []
                commands_str = ", ".join(commands_list) if commands_list else "None"
                if blocked_commands and blocked_commands.strip():
                    blocked_list = sorted(set(blocked_commands.split(', ')))
                    blocked_str = ", ".join(blocked_list)
                    # Always show blocked commands, even if there are command permissions:
                    if commands_str != "None":
                        commands_str += f" (Blocked: {blocked_str})"
                    else:
                        commands_str = f"(Blocked: {blocked_str})"
                embed.add_field(name=display_name, value=f"**Roles:** {roles_str}\n**Commands:** {commands_str}",
                                inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")


    # <---REMOVE--->

@bot.tree.command(name="botperm", description="List all users with roles, command permissions, and blocked commands.")
async def bot_perms(interaction: discord.Interaction):
    await interaction.response.send_message("`botperm` is retired. Use `/permissions role-list` and `/permissions rule-list`.", ephemeral=True)
    return
    # <---REMOVE---> legacy implementation (unreachable)
    if not await is_authorized_or_not(interaction, interaction.guild.id, interaction.user.id, "botperm"):
        return

    async with utils.db_pool.acquire(timeout=5.0) as conn:
        try:

            roles_data = await conn.fetch("""
        WITH all_users AS (
          SELECT guild_id, user_id FROM roles WHERE guild_id = $1
          UNION
          SELECT guild_id, user_id FROM command_permissions WHERE guild_id = $2
          UNION
          SELECT guild_id, user_id FROM blocked_commands WHERE guild_id = $3
        )
        SELECT a.user_id,
               STRING_AGG(DISTINCT r.role, ', ')        AS roles,
               STRING_AGG(DISTINCT cp.command_name, ', ') AS commands,
               STRING_AGG(DISTINCT bc.command_name, ', ') AS blocked_commands
        FROM all_users a
        LEFT JOIN roles r  ON a.guild_id = r.guild_id  AND a.user_id = r.user_id
        LEFT JOIN command_permissions cp 
             ON a.guild_id = cp.guild_id 
            AND a.user_id = cp.user_id
        LEFT JOIN blocked_commands bc 
             ON a.guild_id = bc.guild_id 
            AND a.user_id = bc.user_id
        WHERE a.guild_id = $4
        GROUP BY a.user_id """, interaction.guild.id, interaction.guild.id, interaction.guild.id, interaction.guild.id)

            if not roles_data:
                await interaction.response.send_message("No users found in the role lists.", ephemeral=True)
                return

            embed = discord.Embed(
                title="Bot Permissions Overview",
                color=discord.Color.gold(),
                description="Below is the list of users with their roles and command permissions."
            )

            for user_id, role, commands, blocked_commands in roles_data:
                member = interaction.guild.get_member(int(user_id))
                display_name = member.display_name if member else f"Unknown (ID: {user_id})"
                roles_list = sorted(set(role.split(', '))) if role and role.strip() else []
                roles_str = ", ".join(roles_list) if roles_list else "None"
                commands_list = sorted(set(commands.split(', '))) if commands and commands.strip() else []
                commands_str = ", ".join(commands_list) if commands_list else "None"
                if blocked_commands and blocked_commands.strip():
                    blocked_list = sorted(set(blocked_commands.split(', ')))
                    blocked_str = ", ".join(blocked_list)
                    # Always show blocked commands, even if there are command permissions:
                    if commands_str != "None":
                        commands_str += f" (Blocked: {blocked_str})"
                    else:
                        commands_str = f"(Blocked: {blocked_str})"

                embed.add_field(name=display_name, value=f"**Roles:** {roles_str}\n**Commands:** {commands_str}",
                                inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)


# extensions = ["Slickey_Main_Two", "cmd.msgcount"]

# for filename in os.listdir('./cmd'):
#    if filename.endswith('.py'):
#        bot.load_extension(f'cmd.{filename[:-3]}')


allowed = AllowedMentions(
    everyone=False,  # disable @everyone and @here
    roles=False,     # disable role mentions
    users=True       # still allow direct @user pings if you want
)

@bot.tree.command(name="afk", description="Sets your AFK status.")
@app_commands.describe(reason="The reason for going AFK.")
async def afk(interaction: discord.Interaction, reason: str = "AFK"):
    user_id = interaction.user.id
    guild_id = interaction.guild.id

    if await is_command_blocked(guild_id, user_id, "afk"):
        await interaction.response.send_message("You are blocked from using afk.", ephemeral=True)
        return

    async with utils.db_pool.acquire() as cursor:
        await cursor.execute('''INSERT INTO afk_users (user_id, guild_id, reason, start_time) VALUES ($1, $2, $3, $4) ON CONFLICT(user_id, guild_id) DO UPDATE SET reason = excluded.reason, start_time = excluded.start_time''', str(user_id), str(guild_id), reason, str(datetime.utcnow().isoformat()))

    safe_mentions = AllowedMentions(
        users=True,      # keep @yourname if you really need it
        roles=False,     # NO role pings allowed
        everyone=False,  # NO @everyone or @here
    )

    await interaction.response.send_message(f"**{interaction.user.mention}** is now AFK: {reason}\n", allowed_mentions=safe_mentions)


@bot.command(name='afk', aliases=['Afk', 'AFK'], help=f'Sets AFK of a user.\n**Syntax**: afk reason')
@commands.guild_only()
async def afk(ctx, *, reason: str = "AFK"):
    user_id = ctx.author.id
    guild_id = ctx.guild.id

    if await is_command_blocked(guild_id, user_id, "afk"):
        await ctx.reply("You are blocked from using afk.")
        return

    async with utils.db_pool.acquire() as cursor:
        await cursor.execute('''INSERT INTO afk_users (user_id, guild_id, reason, start_time) VALUES ($1, $2, $3, $4) ON CONFLICT(user_id, guild_id) DO UPDATE SET reason = excluded.reason, start_time = excluded.start_time''', str(user_id), str(guild_id), reason, str(datetime.utcnow().isoformat()))
    
    safe_mentions = AllowedMentions(
        users=True,
        roles=False,
        everyone=False
    )

    await ctx.reply(f"**{ctx.author.mention}** is now AFK: {reason}\n", allowed_mentions=safe_mentions)


@tasks.loop(seconds=2)
async def reset_responded_messages():
    responded_messages.clear()

def current_hour():
    now = datetime.now(timezone.utc)
    return now.replace(minute=0, second=0, microsecond=0)


@bot.event # This function is done with postgres modification.
async def on_message(message):
    global replied_to_message
    #global db_pool
    #if db_pool is None:
        #await init_db_pool()

    if message.author.bot:
        return

    safe = AllowedMentions(
                users=True,      # let you ping the AFK user if you want
                roles=False,     # kill any @Role in the reason
                everyone=False   # kill @everyone / @here
            )

    # if not await get_automod_status(message.guild.id, "profane_words"):
    #    return
    # async with aiosqlite.connect('automod.db') as db:
    #    async with db.execute("SELECT word FROM profane_words WHERE guild_id = ?", (message.guild.id,)) as cursor:
    #        rows = await cursor.fetchall()
    #        banned_words = [row[0] for row in rows]

    # if any(word in message.content.lower() for word in banned_words):
    #    await message.delete()

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    total = len(utils.db_pool._holders)
    busy = sum(1 for h in utils.db_pool._holders if getattr(h, "_in_use", False))
    idle = total - busy
    print(f"Pool stats → total: {total}, busy: {busy}, idle: {idle}")


    if bot.user.mentioned_in(message) and not message.mention_everyone and not message.reference:

        # Prefixes Logic
        async with utils.db_pool.acquire() as conn:
            user_prefix_row = await conn.fetchrow("SELECT prefix FROM user_prefixes WHERE user_id = $1", user_id)
            guild_prefix_row = await conn.fetchrow("SELECT prefix FROM server_prefixes WHERE guild_id = $1", guild_id)

        embed = discord.Embed(title="Bot Prefix Information", color=discord.Color.blue())
        embed.add_field(name="Server Prefix", value=guild_prefix_row["prefix"] if guild_prefix_row else "w. (default)", inline=False)
        embed.add_field(name="Your Personal Prefix", value=user_prefix_row["prefix"] if user_prefix_row else "None", inline=False)

        await message.channel.send(embed=embed)

    # Spawn Random Kero Counter

    roww = await utils.db_pool.fetchrow("SELECT spawn_enabled FROM spawn_counters WHERE guild_id = $1", guild_id)
    
    spawn_on = not (roww and roww["spawn_enabled"] is False)
    if spawn_on:
        if message.guild:
            #conn = await get_db_connection()

            async with utils.db_pool.acquire() as conn:
                row = await conn.fetchrow("SELECT message_counter, target_messages FROM spawn_counters WHERE guild_id = $1", guild_id)
            if row:
                current_count, target = row
                current_count += 1
            else:
                current_count = 1
                target = random.randint(190, 300)

            if current_count >= target:

                new_target = random.randint(190, 300)
                async with utils.db_pool.acquire() as cursor:
                    await cursor.execute("""UPDATE spawn_counters SET message_counter = $1, target_messages = $2 WHERE guild_id = $3 """, 0, new_target, guild_id)

                images = ["epic.jpg", "common.jpg", "legend.png", "rare.jpg"]
                choice1 = ["oppress", "make", "claim", "whip", "auction", "catch", "torture"]
                choice2 = ["blackie", "slave", "nutella", "negro", "nigger", "nigga"]
                that_specific_phrase = random.choice(choice1) + ' ' + random.choice(choice2)
                random_image = random.choice(images)
                random_kero = random.randint(50, 150)

                spawn_message = await message.channel.send(
                    f"Send the message `{that_specific_phrase}` to claim 💷 {random_kero} Kero.",
                    file=discord.File(random_image))

                def check(m):
                    return m.content.lower() == that_specific_phrase and m.channel == message.channel

                try:
                    response = await bot.wait_for("message", timeout=120, check=check)
                    winner = response.author
                    await message.channel.send(f"🎉 {winner.display_name} claimed **💷 {random_kero} Kero**! Congrats!")
                    await update_user_balance(winner.id, random_kero)
                    await add_transaction(None, winner.id, random_kero, "spawn", int(guild_id))
                    await spawn_message.delete()
                except asyncio.TimeoutError:
                    await message.channel.send("⏰ Timeout! No one claimed the Kero in time.")
                    await spawn_message.delete()
            else:
                async with utils.db_pool.acquire() as cursor:
                    if row:
                        await cursor.execute("UPDATE spawn_counters SET message_counter = $1 WHERE guild_id = $2", current_count, guild_id)
                    else:
                        await cursor.execute("""INSERT INTO spawn_counters (guild_id, message_counter, target_messages) VALUES ($1, $2, $3)""", guild_id, current_count, target)

    # Message Counts
    
    async with utils.db_pool.acquire() as cursor:
        await cursor.execute(""" INSERT INTO message_counts (user_id, guild_id, message_count, last_message_at) VALUES ($1, $2, 1, NOW()) ON CONFLICT (user_id, guild_id) DO UPDATE SET message_count   = message_counts.message_count + 1, last_message_at = NOW();""", int(user_id), int(guild_id))

        h = current_hour()
        await cursor.execute("""
            INSERT INTO public.message_hourly_counts (user_id, guild_id, hour_ts, count)
            VALUES ($1, $2, $3, 1)
            ON CONFLICT (user_id, guild_id, hour_ts)
            DO UPDATE SET count = message_hourly_counts.count + 1
        """, int(user_id), int(guild_id), h)

        #await cursor.execute("""
        #    INSERT INTO public.message_hourly_counts (user_id, guild_id, hour_ts, count)
        #    VALUES ($1, $2, date_trunc('hour', now()), 1)
        #    ON CONFLICT (user_id, guild_id, hour_ts)
        #    DO UPDATE SET count = message_hourly_counts.count + 1
        #""", int(user_id), int(guild_id))
    
        afk_entry = await cursor.fetchrow( "SELECT reason, start_time FROM afk_users WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)

    if afk_entry:
        start_time = datetime.fromisoformat(afk_entry[1])
        time_away = datetime.utcnow() - start_time
        formatted_time = format_timedelta(time_away)

        async with utils.db_pool.acquire() as cursor:
            mentions = await cursor.fetch(""" SELECT mentioner_id, message_link, mention_time FROM afk_mentions WHERE user_id = $1 AND guild_id = $2 """, user_id, guild_id)

        lines = []
        for m in mentions:
            # m[0]: mentioner_id, m[1]: message_link, m[2]: mention_time
            try:
                mentioner = message.guild.get_member(int(m[0]))
                mentioner_name = mentioner.display_name if mentioner else m[0]
            except Exception:
                mentioner_name = m[0]
            try:
                parts = m[1].split('/')
                # Expected format: "https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
                channel_id = int(parts[5]) if len(parts) > 5 else None
                channel = message.guild.get_channel(channel_id) if channel_id else None
                channel_mention = channel.mention if channel else "Unknown Channel"
            except Exception:
                channel_mention = "Unknown Channel"
            try:

                mention_delta = datetime.fromisoformat(m[2]) - start_time
                formatted_delta = format_timedelta(mention_delta)
            except Exception:
                formatted_delta = "Unknown"
            line = f"[Message]({m[1]}) from {mentioner_name} in {channel_mention}: (AFK for {formatted_delta})"
            lines.append(line)
        mention_list = "\n".join(lines) if lines else "You were not mentioned."

        welcome_back_msg = await message.channel.send(embed=discord.Embed(title="Welcome Back!",
                                                                          description=f"{message.author.mention}, you are no longer AFK!!\nTime away: **{formatted_time}**.\n\nMentions while AFK:\n{mention_list}",
                                                                          color=discord.Color.green()), allowed_mentions=safe)

        async with utils.db_pool.acquire() as cursor:
            await cursor.execute("DELETE FROM afk_users WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)
            await cursor.execute("DELETE FROM afk_mentions WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)

        async def _del_later(msg, delay):
            await asyncio.sleep(delay)
            try:
                await msg.delete()
            except:
                pass

        # kick off the task without awaiting it
        asyncio.create_task(_del_later(welcome_back_msg, 45))

    mentioned_afk_users = set()
    for user in message.mentions:
        async with utils.db_pool.acquire() as cursor:
            afk_entry = await cursor.fetchrow("""SELECT reason, start_time FROM afk_users WHERE user_id = $1 AND guild_id = $2""", str(user.id), guild_id)

        if afk_entry:
            reason, start_time = afk_entry
            time_away = datetime.utcnow() - datetime.fromisoformat(start_time)
            formatted_time = format_timedelta(time_away)

            msg_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
            mention_time = datetime.utcnow().isoformat()

            async with utils.db_pool.acquire() as cursor:
                await cursor.execute(""" INSERT INTO afk_mentions (user_id, guild_id, mentioner_id, message_link, mention_time) VALUES ($1, $2, $3, $4, $5) """, str(user.id), guild_id, user_id, str(msg_link), str(mention_time))

                await message.channel.send(f"**{user.display_name}** has been AFK for **{formatted_time}**. Reason: {reason}", allowed_mentions=safe)

            mentioned_afk_users.add(user.id)

    if message.reference and message.reference.resolved:
        replied_message = message.reference.resolved
        original_user_id = replied_message.author.id

        if original_user_id not in mentioned_afk_users:
            async with utils.db_pool.acquire() as cursor:
                afk_entry = await cursor.fetchrow("""SELECT reason, start_time FROM afk_users WHERE user_id = $1 AND guild_id = $2 """, str(original_user_id), guild_id)

            if afk_entry:
                reason, start_time = afk_entry
                time_away = datetime.utcnow() - datetime.fromisoformat(start_time)
                formatted_time = format_timedelta(time_away)

                msg_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"

                mention_time = datetime.utcnow().isoformat()
                async with utils.db_pool.acquire() as cursor:
                    await cursor.execute("""INSERT INTO afk_mentions (user_id, guild_id, mentioner_id, message_link, mention_time) VALUES ($1, $2, $3, $4, $5) """, str(original_user_id), guild_id, user_id, str(msg_link), str(mention_time))

                await message.channel.send(
                    f"**{replied_message.author.display_name}** has been AFK for **{formatted_time}**. Reason: {reason}", allowed_mentions=safe)

                responded_messages[original_user_id] = True

    await bot.process_commands(message)


@bot.event # This function is done with postgres modification.
async def on_member_remove(member):
    guild_id = member.guild.id

    async with utils.db_pool.acquire() as conn:
        await conn.execute("DELETE FROM afk_users WHERE user_id = $1 AND guild_id = $2", str(member.id), str(member.guild.id))
        await conn.execute("DELETE FROM afk_mentions WHERE user_id = $1 AND guild_id = $2", str(member.id), str(member.guild.id))

        # Custom Slickey role assignments and user-targeted policies do not
        # survive a member leaving the server.
        await conn.execute("DELETE FROM bot_role_memberships WHERE guild_id = $1 AND user_id = $2", guild_id, member.id)
        await conn.execute("DELETE FROM bot_permission_rules WHERE guild_id = $1 AND subject_type = 'user' AND subject_id = $2", guild_id, member.id)


@bot.event # This function is done with postgres modification.
async def on_member_update(before, after):
    mute_role = discord.utils.get(after.guild.roles, name="Mute")
    kick_role = discord.utils.get(after.guild.roles, name="Kick")
    ban_role = discord.utils.get(after.guild.roles, name="Ban")

    if mute_role in after.roles and mute_role not in before.roles:
        await after.timeout(timedelta(minutes=2))
        await after.guild.system_channel.send(
            embed=discord.Embed(title="User Muted", description=f"{after.display_name} has been muted for 2 minutes.",
                                color=discord.Color.red()))
    elif mute_role not in after.roles and mute_role in before.roles:
        await after.timeout(None)

    if before.timed_out_until and not after.timed_out_until:
        if mute_role in after.roles:
            await after.remove_roles(mute_role)
            await after.guild.system_channel.send(embed=discord.Embed(title="Manual Timeout Removal", description=f"{after.display_name}'s timeout was manually removed, so the **Mute** role was also removed.", color=discord.Color.orange()))

    if kick_role in after.roles and kick_role not in before.roles:
        await after.kick(reason="Kicked by Kick role")
        await after.guild.system_channel.send(embed=discord.Embed(title="User Kicked",
                                                                  description=f"{after.display_name} was kicked due to the Kick role.",
                                                                  color=discord.Color.orange()))

    if ban_role in after.roles and ban_role not in before.roles:
        await after.ban(reason="Banned by Ban role")
        await after.guild.system_channel.send(embed=discord.Embed(title="User Banned",
                                                                  description=f"{after.display_name} was banned due to the Ban role.",
                                                                  color=discord.Color.dark_red()))

    if before.id in active_role_timers:
        role_data = active_role_timers[before.id]
        if isinstance(role_data, dict):
            removed_roles = [role for role in before.roles if role not in after.roles]

            assigned_role = None
            if removed_roles:
                assigned_role = removed_roles[0]

            if assigned_role in before.roles and assigned_role not in after.roles:
                task = role_data.get("task")
                if task:
                    task.cancel()

                active_role_timers.pop(before.id, None)

                embed = discord.Embed(
                    title="Role Removed Before Specified Time",
                    description=f"**{after.display_name}'s** {assigned_role.mention} role was removed manually before the time expired.",
                    color=discord.Color.blurple())
                channel = bot.get_channel(role_data["channel_id"])
                if channel:
                    await channel.send(embed=embed)


@bot.event # This function is done with postgres modification.
async def on_member_unban(guild, member):
    text_channel = next(
        (channel for channel in guild.text_channels if channel.permissions_for(guild.me).create_instant_invite), None)
    if text_channel is None:
        print(f"No accessible text channels to create an invite in for {guild.name}.")
        return "Unable to create an invite."
    try:
        invite = await text_channel.create_invite(max_uses=1, unique=True)
        await member.send(
            f"Hello, **{member.display_name}**!🎉🎉\nYou've been unbanned from **{guild.name}**.\nIf you want to join our server again, here is your invite link:\n\n{invite}")
    except discord.Forbidden:
        guild.system_channel.send(f"Could not send a DM to {member.name} ({member.id}), they may have DMs disabled.")
        print(f"Could not send a DM to {member.name} ({member.id}), they may have DMs disabled.")
    except Exception as e:
        print(f"An error occurred: {e}")


@bot.event # This function is done with postgres modification.
async def on_member_join(member):
    guild = member.guild

    async with utils.db_pool.acquire() as cursor:
        setup_done = await cursor.fetchval("SELECT setup_done FROM setup_status WHERE guild_id = $1", str(guild.id))

    if setup_done != 1:
        return

    async with utils.db_pool.acquire() as cursor:
        user_exists = await cursor.fetchval("SELECT 1 FROM users WHERE user_id = $1", member.id)
        #joined = await cursor.fetchrow("SELECT joined_at FROM users WHERE user_id = $1 AND guild_id = $2", member.id, guild.id)
        joined_guild = await cursor.fetchval("SELECT 1 FROM users WHERE user_id = $1 AND guild_id = $2", member.id, guild.id)
        awarded = await cursor.fetchval("SELECT 1 FROM starter_packs WHERE user_id = $1", member.id)

        if not user_exists:
            await cursor.execute("""
                INSERT INTO users (user_id, guild_id, joined_at, balance)
                VALUES ($1, $2, $3, $4)
            """, member.id, guild.id, member.joined_at or datetime.utcnow(), 0)

        elif not joined_guild:
            bal = await get_user_balance(member.id)
            await cursor.execute("""
                INSERT INTO users (user_id, guild_id, joined_at, balance)
                VALUES ($1, $2, $3, $4)
            """, member.id, guild.id, member.joined_at or datetime.utcnow(), bal)

        if not awarded:
            await update_user_balance(member.id, 1000)
            await cursor.execute("INSERT INTO starter_packs (user_id) VALUES ($1)", member.id)

        await cursor.execute("""INSERT INTO message_counts (user_id, guild_id, message_count, last_message_at) VALUES ($1, $2, 1, now()) ON CONFLICT (user_id, guild_id) DO NOTHING """, member.id, guild.id)

        print(f"User {member.id} - {member.display_name} initialized in guild {guild.name}.")



@bot.event  # This function is done with postgres modification.
async def on_guild_update(before, after):
    async with utils.db_pool.acquire() as conn:
        setup_done = await conn.fetchval( "SELECT setup_done FROM setup_status WHERE guild_id = $1", str(after.id))

    if setup_done == 1 and before.owner != after.owner:
        new_owner_id = after.owner.id

        # Ownership is resolved live by permission_system.evaluate(), so no
        # stored owner role needs updating after a Discord ownership transfer.
        if after.system_channel:
            await after.system_channel.send(f"Slickey ownership now follows {after.owner.mention} automatically.")


@bot.event  # This function is done with postgres modification.
async def on_guild_join(guild):

    #async with utils.db_pool.acquire() as conn:
        #setup_done = await conn.fetchval( "SELECT setup_done FROM setup_status WHERE guild_id = $1", str(guild.id))
        
    #if not setup_done:
    if guild.system_channel:
            await guild.system_channel.send("To fully utilize my features, please run the </setup:1338619326764417056> command (Administrator or Owner only).")


@bot.event
async def on_raw_reaction_add(payload):
    # ignore self‑reactions

    author_id = None
    if payload.member:
        # payload.member is the user object of the reactor, NOT the message author!
        # so we still need the message author…
        # best bet: fetch the message and grab its .author.id
        channel = bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        author_id = msg.author.id

    if payload.user_id == author_id:
        return

    async with utils.db_pool.acquire() as conn:
        await conn.execute("""INSERT INTO message_reactions (message_id, author_id, guild_id, reactor_id, emoji) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING""", payload.message_id, author_id, payload.guild_id, payload.user_id, str(payload.emoji))


@bot.event
async def on_raw_reaction_remove(payload):
    async with utils.db_pool.acquire() as conn:
        await conn.execute("""DELETE FROM message_reactions WHERE message_id = $1 AND reactor_id = $2 AND emoji = $3 """, payload.message_id, payload.user_id, str(payload.emoji))

#2025-07-28 20:14:33 ERROR    discord.client Ignoring exception in on_raw_reaction_remove
#Traceback (most recent call last):
#  File "C:\Program Files\Python313\Lib\site-packages\discord\client.py", line 481, in _run_event
#    await coro(*args, **kwargs)
#  File "d:\PycharmProjects\Slickey_Bot\Slickey_Main_.py", line 963, in on_raw_reaction_remove
#    async with utils.db_pool.acquire() as conn:

#AttributeError: 'NoneType' object has no attribute 'acquire'


@bot.event # This function is done with postgres modification.
async def on_guild_remove(guild):
    async with utils.db_pool.acquire() as conn:
        await conn.execute("DELETE FROM bot_permission_rules WHERE guild_id = $1", guild.id)
        await conn.execute("DELETE FROM bot_permission_audit_log WHERE guild_id = $1", guild.id)
        await conn.execute("DELETE FROM bot_permission_roles WHERE guild_id = $1", guild.id)
        await conn.execute( "DELETE FROM setup_status WHERE guild_id = $1", str(guild.id))

pending_joins: dict[tuple[int, int], datetime] = {}

@bot.event
async def on_voice_state_update(member, before, after):
    print(f"[VoiceEvent] {member} from {before.channel} → {after.channel}")
    uid, gid = member.id, member.guild.id

    # 1) user joined a VC
    if before.channel is None and after.channel is not None:
        pending_joins[(uid, gid)] = datetime.now(timezone.utc)
        print(f"  → queued join at {pending_joins[(uid,gid)]}")

    # 2) user left or switched channel
    elif (before.channel is not None and after.channel is None) or (before.channel is not None and after.channel is not None and before.channel.id != after.channel.id):
        join_time = pending_joins.pop((uid, gid), None)
        print(f"  → popped join_time = {join_time}")
        if not join_time:
            return
        
        leave_time = datetime.now(timezone.utc)
        duration = leave_time - join_time
        print(f"  → measured duration = {duration}")

        async with utils.db_pool.acquire() as conn:
            await conn.execute(""" INSERT INTO voice_sessions (user_id, guild_id, join_ts, leave_ts, duration)
                VALUES ($1, $2, $3, $4, $5) """, uid, gid, join_time, leave_time, duration)


@bot.event # This function is done with postgres modification.
async def on_ready():
    start = time.time()
    
    global db_pool
    if db_pool is None:
        await init_db_pool()

    # Safe to run on reconnects; migrations use IF NOT EXISTS and upserts.
    await permission_system.initialize_permission_system(utils.db_pool)

    #await utils.setup_database()
    #await utils.initialize_database()
    #await utils.setup_permissions()
    #await utils.get_automod_db()
    #utils.setup_modlog_Database()

    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        review_required = await permission_system.sync_command_catalog(utils.db_pool, bot)
        if review_required:
            print("Permission review required before these commands can be used: " + ", ".join(sorted(review_required)))
        for command in await bot.tree.fetch_commands():
            print(f"Command registered: {command.name}")
        print(f"\nSynced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    async with utils.db_pool.acquire() as conn:
        for guild in bot.guilds:

            setup_done = await conn.fetchval("SELECT setup_done FROM setup_status WHERE guild_id = $1", str(guild.id))
            
            if setup_done != 1:
                print(f"Skipped Initialization for {guild.name}.")
                continue

            members = guild.members
            #member_ids = [m.id for m in members]

            # 1) Fetch existing guild‑user rows (joined_at & balance)
            rows = await conn.fetch("SELECT user_id, joined_at, balance FROM users WHERE guild_id = $1", guild.id)

            msg_rows = await conn.fetch("""SELECT user_id, guild_id FROM message_counts WHERE guild_id = $1""", guild.id)

            msg_existing = {(r['user_id'], r['guild_id']) for r in msg_rows}

            existing = {r["user_id"]: (r["joined_at"], r["balance"]) for r in rows}

            # 2) Fetch who’s already claimed a starter pack
            starter_rows = await conn.fetch("SELECT user_id FROM starter_packs")
            starters = {r["user_id"] for r in starter_rows}

            to_insert_users = []
            to_award = []
            to_insert_msg = []

            # 3) In Python, figure out which members need inserts vs awards
            for m in members:
                if m.bot:
                    continue
                if m.id not in existing:
                    # grab their real global balance or default 0
                    bal = existing.get(m.id, (None, 0))[1]
                    joined_at_val = m.joined_at or datetime.utcnow()
                    to_insert_users.append((m.id, guild.id, joined_at_val, bal))    

                if m.id not in starters:
                    to_award.append(m.id)

                key = (m.id, guild.id)
                if key not in msg_existing:
                    to_insert_msg.append((m.id, guild.id, 1))

            # 4a) Bulk‑insert new guild entries (with correct balances)
            if to_insert_users:
                await conn.executemany("""INSERT INTO users (user_id, guild_id, joined_at, balance) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id, guild_id) DO NOTHING""", to_insert_users)

            # 4b) Bulk‑award starter packs
            if to_award:
                # bump balance in one go
                await conn.execute("UPDATE users SET balance = balance + 1000 WHERE user_id = ANY($1::bigint[])", to_award)
                # mark them claimed
                await conn.executemany( "INSERT INTO starter_packs (user_id) VALUES ($1) ON CONFLICT DO NOTHING", [(uid,) for uid in to_award])

            if to_insert_msg:
                await conn.executemany("""INSERT INTO message_counts (user_id, guild_id, message_count, last_message_at) VALUES ($1, $2, $3, now()) ON CONFLICT (user_id, guild_id) DO NOTHING """, to_insert_msg)

    duration = time.time() - start
    print(f"The duration of initialization is {duration:.2f} seconds.")
    print("Initialization completed for all servers.")


@bot.event # This function is done with postgres modification.
async def on_close():
    await utils.db_pool.close()
    #print("Database connection pool closed.")





@bot.tree.command(name="setup", description="Initialize the bot in this server (Admin/Owner only)")
async def setup(interaction: discord.Interaction):
    if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
        await interaction.response.send_message("You don't have permission to run this command.", ephemeral=True)
        return

    guild = interaction.guild
    global operation_active
    operation_active = True

    await interaction.response.send_message("Starting setup...", ephemeral=False)


    #conn_perm = await aiosqlite.connect("permissions.db")
    #master_conn = await get_masterslave_connection()
    #conn = await get_db_connection()

    owner_id = guild.owner.id

    await interaction.followup.send("Creating required roles...", ephemeral=True)
    for role_name in ["Kick", "Mute", "Ban"]:
        await asyncio.sleep(0)
        if not operation_active:
            await interaction.followup.send("Operation halted. Setup aborted.", ephemeral=False)
            return
        if not discord.utils.get(guild.roles, name=role_name):
            await guild.create_role(name=role_name, reason=f"Required for bot functionality: {role_name}")


    
    async with utils.db_pool.acquire() as cursor:

        await interaction.followup.send("Slickey owner access follows Discord ownership automatically.", ephemeral=True)

        await interaction.followup.send("Registering members...", ephemeral=True)
        for member in guild.members:
            await asyncio.sleep(0)
            if not operation_active:
                await interaction.followup.send("Operation halted. Setup aborted.", ephemeral=False)
                return

        params = [(m.id, guild.id, m.joined_at or datetime.utcnow()) for m in guild.members]
            
            #joined = await cursor.fetchval("SELECT joined_at FROM users WHERE user_id = $1 AND guild_id = $2", member.id, guild.id)

        await cursor.executemany("""INSERT INTO users (user_id, guild_id, joined_at, balance) VALUES ($1, $2, $3, COALESCE((SELECT balance FROM users WHERE user_id = $1 LIMIT 1),0)) ON CONFLICT (user_id, guild_id) DO NOTHING """, params)


        
        await interaction.followup.send("Awarding starter packs to all members...", ephemeral=True)

        member_ids = [m.id for m in guild.members]

        rows = await cursor.fetch("SELECT user_id FROM starter_packs WHERE user_id = ANY($1)", member_ids)
        
        awarded = {r["user_id"] for r in rows}
        
        to_award = [mid for mid in member_ids if mid not in awarded]

        for mid in to_award:
            await update_user_balance(mid, 1000)

        await cursor.executemany("INSERT INTO starter_packs (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING", [(mid,) for mid in to_award])
        
        #await interaction.response.defer(ephemeral=True)

        await interaction.followup.send("Opening message counter for everyone...", ephemeral=True)

        params = [(m.id, guild.id) for m in guild.members if not m.bot]
            
        await cursor.executemany("""INSERT INTO message_counts (user_id, guild_id, message_count, last_message_at) VALUES ($1, $2, 1, now()) ON CONFLICT (user_id, guild_id) DO NOTHING """, params)


        await cursor.execute("INSERT INTO setup_status (guild_id, setup_done) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET setup_done = EXCLUDED.setup_done", str(guild.id), 1)

    await interaction.followup.send("Owner role assigned and setup marked as complete.", ephemeral=True)
    await interaction.followup.send("Setup completed successfully!", ephemeral=False)


@bot.tree.command(name="msgcount", description="Retrieves the total message count of a user in the server.")
@app_commands.describe(user="Optional mention, ID, or username of the user to get the message count for.")
async def msgcount(interaction: discord.Interaction, user: str = None):
    target_user = interaction.user
    guild = interaction.guild
    #conn = await get_db_connection()

    if await is_command_blocked(guild.id, interaction.user.id, "msgcount"):
        await interaction.response.send_message("You are blocked from using msgcount.", ephemeral=True)
        return

    user_arg = user
    if user_arg:
        user = None
        try:
            if user_arg.isdigit():
                user = guild.get_member(int(user_arg)) or await bot.fetch_user(int(user_arg))
            elif user_arg.startswith('<@') and user_arg.endswith('>'):
                user_id = int(user_arg.strip('<@!>'))
                user = guild.get_member(user_id) or await bot.fetch_user(user_id)
            else:
                closest_member, confidence = await find_closest_member(interaction, user_arg)
                if closest_member and confidence > 60:
                    user = closest_member

            if not user:
                raise ValueError("Unable to resolve the user.")

            target_user = user

        except ValueError:
            await interaction.response.send_message(embed=discord.Embed(
                title="User Not Found",
                description=f"Unable to resolve the user: `{user_arg}`. Please provide a valid mention, ID, or simply name.",
                color=discord.Color.red()), ephemeral=True)
            return

    try:
        # Fetch the message count from the database
        async with utils.db_pool.acquire() as cursor:
            message_count = await cursor.fetchval("SELECT message_count FROM message_counts WHERE user_id = $1 AND guild_id = $2", int(target_user.id), int(guild.id))
            last_24h = await cursor.fetchval("""SELECT COALESCE(SUM(count), 0) FROM public.message_hourly_counts WHERE user_id = $1 AND guild_id = $2 AND hour_ts >= NOW() - INTERVAL '24 hours' """, int(target_user.id), int(guild.id))

        if message_count is not None:
            await interaction.response.send_message(embed=discord.Embed(
                title="Message Count",
                description=(f"**{target_user.display_name}** has sent a total of **{message_count}** messages in this server.\n"
                f"**Last 24 Hours**: **{last_24h}** messages."),
                color=discord.Color.dark_teal()))
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title="No Message",
                description=f"**{target_user.display_name}** has no recorded messages in this server.",
                color=discord.Color.dark_teal()))

    except asyncpg.PostgresError as e:
        await interaction.response.send_message("An error occurred while retrieving the message count.", ephemeral=True)
        print(f"Database error: {e}")


@bot.command(name="msgcount", aliases=['msg', 'messagecount', 'count', 'messages', 'message'],  help="Retrieves the total message count of the respective user in the server.\n**Syntax**: msgcount @user(s)")
@commands.guild_only()
async def messagecount(ctx, *, user_arg: str = None):
    target_user = ctx.author
    #conn = await get_db_connection()

    if await is_command_blocked(ctx.guild.id, ctx.author.id, "msgcount"):
        await ctx.reply("You are blocked from using msgcount.")
        return

    if user_arg:
        user = None
        if user_arg.isdigit():
            user = ctx.guild.get_member(int(user_arg)) or await bot.fetch_user(int(user_arg))
        elif user_arg.startswith('<@') and user_arg.endswith('>'):
            user_id = int(user_arg.strip('<@!>'))
            user = ctx.guild.get_member(user_id) or await bot.fetch_user(user_id)
        else:
            closest_member, confidence = await find_closest_member(ctx, user_arg)
            if closest_member and confidence > 60:
                user = closest_member

        if not user:
            await ctx.reply(embed=discord.Embed(
                title="User Not Found",
                description=f"Unable to resolve the user: `{user_arg}`. Please provide a valid mention, ID, or name.",
                color=discord.Color.red()))
            return

        target_user = user

    try:
        async with utils.db_pool.acquire() as cursor:
            message_count = await cursor.fetchval("SELECT message_count FROM message_counts WHERE user_id = $1 AND guild_id = $2", int(target_user.id), int(ctx.guild.id))
            last_24h = await cursor.fetchval("""SELECT COALESCE(SUM(count), 0) FROM public.message_hourly_counts WHERE user_id = $1 AND guild_id = $2 AND hour_ts >= NOW() - INTERVAL '24 hours' """, int(target_user.id), int(ctx.guild.id))

        if message_count is not None:
            await ctx.reply(embed=discord.Embed(
                title="Message Count",
                description=(f"**{target_user.display_name}** has sent a total of **{message_count}** messages in this server.\n"
                f"**Last 24 Hours**: **{last_24h}** messages."),
                color=discord.Color.dark_teal()))
        else:
            await ctx.reply(embed=discord.Embed(
                title="No Message",
                description=f"**{target_user.display_name}** has no recorded messages in this server.",
                color=discord.Color.dark_teal()))

    except asyncpg.PostgresError as e:
        # Handle database errors
        await ctx.reply("An error occurred while retrieving message count.")
        print(f"Database error: {e}")


@bot.tree.command(name="img",
                  description="Displays the global avatar of the mentioned users or yourself if no one is mentioned.")
@app_commands.describe(members="To see Global image for a user or multiple users.")
async def slash_image(interaction: discord.Interaction, members: str = None):
    if await is_command_blocked(interaction.guild.id, interaction.user.id, "img"):
        await interaction.response.send_message("You are blocked from using img.")
        return

    if not members:

        embed = discord.Embed(title="Your Avatar", color=discord.Color.dark_teal())
        embed.set_image(url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed)
    else:
        member_inputs = members.split()
        embeds = []
        for member_input in member_inputs:
            try:

                if member_input.startswith("<@") and member_input.endswith(">"):  # Mention format
                    member_id = int(member_input[2:-1])  # Extract user ID from mention
                    member = interaction.guild.get_member(member_id)
                else:
                    member = await interaction.guild.fetch_member(int(member_input))

                if member and member.avatar:
                    embed = discord.Embed(title=f"**{member.display_name}'s** Avatar", color=discord.Color.dark_teal())
                    embed.set_image(url=member.avatar.url)
                    embeds.append(embed)

            except ValueError:

                member, confidence = await find_closest_member(interaction, member_input)
                if member and confidence > 60:
                    embed = discord.Embed(title=f"**{member.display_name}'s** Avatar", color=discord.Color.dark_teal())
                    embed.set_image(url=member.avatar.url)
                    embeds.append(embed)
                else:
                    em = discord.Embed(title="Error",
                                       description=f"Could not find a member with input: **{member_input}**",
                                       color=discord.Color.red())
                    embeds.append(em)
                    continue

        if embeds:
            await interaction.response.send_message(embeds=embeds)


@bot.command(name='img',
             help=f'Displays the global avatar of the mentioned users or yourself if no one is mentioned.\n**Syntax**: img @user(s)')
@commands.guild_only()
async def image(ctx, *, members: str = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "img"):
        await ctx.reply("You are blocked from using img.")
        return

    if not members:
        embed = discord.Embed(title="Your Avatar", color=discord.Color.dark_teal())
        embed.set_image(url=ctx.author.avatar.url)
        await ctx.send(embed=embed)
    else:
        for member_input in members:
            # Try to convert mentions or IDs to Member objects
            try:
                member = await commands.MemberConverter().convert(ctx, member_input)

                if member and member.avatar:
                    embed = discord.Embed(title=f"**{member.display_name}'s** Avatar", color=discord.Color.dark_teal())
                    embed.set_image(url=member.avatar.url)
                    await ctx.send(embed=embed)

            except commands.BadArgument:
                member, confidence = await find_closest_member(ctx, member_input)
                if member and confidence > 60:
                    embed = discord.Embed(title=f"**{member.display_name}'s** Avatar", color=discord.Color.dark_teal())
                    embed.set_image(url=member.avatar.url)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(
                        discord.Embed(title="Error",
                                      description=f"Could not find a member with input: **{member_input}**",
                                      color=discord.Color.red()))
                continue


@bot.command(name='av',
             help=f'Displays the server specific avatar of the mentioned users in the server or yourself if no one is mentioned.\n**Syntax**: av @user(s)')
@commands.guild_only()
async def avatar(ctx, *members: str):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "av"):
        await ctx.reply("You are blocked from using av.")
        return

    if not members:
        # Show the author's avatar if no members are mentioned
        embed = discord.Embed(title="Your Server Avatar", color=discord.Color.dark_teal())
        embed.set_image(url=ctx.author.display_avatar.url)  # Use display_avatar for server-specific avatar
        await ctx.send(embed=embed)
    else:
        for member_input in members:
            # Try to convert mentions or IDs to Member objects
            try:
                member = await commands.MemberConverter().convert(ctx, member_input)

                if member and member.avatar:
                    embed = discord.Embed(title=f"**{member.display_name}'s** Server Avatar",
                                          color=discord.Color.dark_teal())
                    embed.set_image(url=member.display_avatar.url)  # Use display_avatar for server-specific avatar
                    await ctx.send(embed=embed)

            except commands.BadArgument:
                member, confidence = await find_closest_member(ctx, member_input)
                if member and confidence > 60:  # Ensure confidence is high enough
                    embed = discord.Embed(title=f"**{member.display_name}'s** Server Avatar",
                                          color=discord.Color.dark_teal())
                    embed.set_image(url=member.display_avatar.url)  # Use display_avatar for server-specific avatar
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(
                        discord.Embed(title="Error",
                                      description=f"Could not find a member with input: **{member_input}**",
                                      color=discord.Color.red()))
                continue


@bot.command(name='bn', help='Displays the global banner of the mentioned users or yourself if no one is mentioned.\n**Syntax**: bn @user(s)')
@commands.guild_only()
async def bn(ctx, *, members: str = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "bn"):
        await ctx.reply("You are blocked from using bn.")
        return

    if members is None:
        user = await bot.fetch_user(ctx.author.id)  # Use fetch_user for complete data

        # Check if the user has a banner
        if user.banner:
            embed = discord.Embed(title="Your Banner", color=discord.Color.dark_teal())
            embed.set_image(url=user.banner.url)  # Set the banner image
            embed.add_field(name="Download Banner", value=f"[Click Here]({user.banner.url})", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("You don't have a banner.")
    else:
        # Split the members input into separate items
        member_inputs = members.split()

        for member_input in member_inputs:
            member_input = member_input.strip()  # Clean up whitespace
            member_user = None
            member_id = None

            # Try to resolve the input to a mention or numeric ID
            if member_input.startswith('<@') and member_input.endswith('>'):
                # Extract the ID from mention format
                member_id = int(member_input.replace('<@', '').replace('>', '').replace('!', ''))
            elif member_input.isnumeric():
                # If it's numeric, assume it's a user ID
                member_id = int(member_input)
            else:
                # Use RapidFuzz to find the closest match as a fallback
                member_user, confidence = await find_closest_member(ctx, member_input)
                if member_user and confidence > 60:
                    member_id = member_user.id
                else:
                    await ctx.send(embed=discord.Embed(title="Error",
                                                       description=f"Could not find a close match for: **{member_input}**.",
                                                       color=discord.Color.red()))
                    continue

            # Fetch user by ID if applicable
            if member_id is not None:
                try:
                    member_user = await bot.fetch_user(member_id)
                except discord.NotFound:
                    await ctx.send(embed=discord.Embed(title="Error",
                                                       description=f"Could not find a user with ID: **{member_id}**.",
                                                       color=discord.Color.red()))
                    continue

            if member_user:
                if member_user.banner:
                    embed = discord.Embed(title=f"{member_user.display_name}'s Banner", color=discord.Color.dark_teal())
                    embed.set_image(url=member_user.banner.url)  # Set the banner image
                    embed.add_field(name="Download Banner", value=f"[Click Here]({member_user.banner.url})",
                                    inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(embed=discord.Embed(title="No Banner",
                                                       description=f"{member_user.display_name} does not have a banner set.",
                                                       color=discord.Color.red()))



@bot.tree.command(name="bn", description="Displays the global banner of the mentioned users or yourself if no one is mentioned.")
@app_commands.describe(members="Mention users, IDs, or usernames separated by spaces")
async def slash_bn(interaction: discord.Interaction, members: str = None):
    if await is_command_blocked(interaction.guild.id, interaction.user.id, "bn"):
        await interaction.response.send_message("You are blocked from using bn.", ephemeral=True)
        return
    
    if not members:
        user = await bot.fetch_user(interaction.user.id)
        if user.banner:
            embed = discord.Embed(title="Your Banner", color=discord.Color.dark_teal())
            embed.set_image(url=user.banner.url)
            embed.add_field(name="Download Banner", value=f"[Click Here]({user.banner.url})", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("You don't have a banner.")
        return

    # Acknowledge the command and switch to follow-ups for multiple replies
    await interaction.response.defer()

    # Process each input token
    for member_input in members.split():
        member_input = member_input.strip()
        member_user = None
        member_id = None

        # Resolve mention or ID
        if member_input.startswith('<@') and member_input.endswith('>'):
            member_id = int(member_input.replace('<@', '').replace('>', '').replace('!', ''))
        elif member_input.isnumeric():
            member_id = int(member_input)
        else:
            # Fallback fuzzy search
            member_user, confidence = await find_closest_member(interaction, member_input)
            if member_user and confidence > 60:
                member_id = member_user.id
            else:
                err = discord.Embed(title="Error", description=f"Could not find a close match for: **{member_input}**.", color=discord.Color.red())
                await interaction.followup.send(embed=err)
                continue

        # Fetch the user object if we have an ID
        if member_id is not None:
            try:
                member_user = await bot.fetch_user(member_id)
            except discord.NotFound:
                err = discord.Embed(title="Error", description=f"Could not find a user with ID: **{member_id}**.", color=discord.Color.red())
                await interaction.followup.send(embed=err)
                continue

        # Build and send banner embed or no-banner notice
        if member_user and member_user.banner:
            embed = discord.Embed(title=f"{member_user.display_name}'s Banner", color=discord.Color.dark_teal())
            embed.set_image(url=member_user.banner.url)
            embed.add_field(name="Download Banner", value=f"[Click Here]({member_user.banner.url})", inline=False)
            await interaction.followup.send(embed=embed)
        else:
            no_banner = discord.Embed(title="No Banner",
                                     description=f"{member_user.display_name if member_user else member_input} does not have a banner set.",
                                     color=discord.Color.red())
            await interaction.followup.send(embed=no_banner)



#def _evict_prefix_cache_for_guild(guild_id: str):
#       remove every key that belongs to this guild
#    for key in list(prefix_cache.keys()):
#        if key.startswith(f"{guild_id}:"):
#            prefix_cache.pop(key, None)

#def _evict_prefix_cache_for_user(guild_id: str, user_id: str):
#    key = f"{guild_id}:{user_id}"
#    prefix_cache.pop(key, None)



@bot.command(name='setprefix', help=f'Change the prefix of this bot.\n**Syntax**: setprefix new_prefix or type "delete" for deleting the set-prefix')
@commands.guild_only()
async def set_prefix(ctx, new_prefix: str):
    if not await only_for_setprefix(ctx.guild.id, ctx.author.id):
        await ctx.reply("You are not allowed to use this command. Only admin and above level users can use this command.")
        return

    if await is_command_blocked(ctx.guild.id, ctx.author.id, "setprefix"):
        await ctx.reply("You are blocked from using setprefix.")
        return

    async with utils.db_pool.acquire() as exec:
        if new_prefix.lower() == "delete" or new_prefix.lower() == "del":
            await exec.execute("DELETE FROM server_prefixes WHERE guild_id = $1", str(ctx.guild.id))
            await ctx.send(embed=discord.Embed(title="Server Prefix Disabled",
                                               description="The server-prefix has been disabled.",
                                               color=discord.Color.green()))
            return

        if len(new_prefix) > 5:
            await ctx.send("Prefix cannot be longer than 5 characters.")
            return

        await exec.execute("INSERT INTO server_prefixes (guild_id, prefix) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET prefix = EXCLUDED.prefix", str(ctx.guild.id), new_prefix,)

    bot.command_prefix = new_prefix

    await ctx.send(
        embed=discord.Embed(title="Prefix Changed", description=f"Command prefix changed to: **{new_prefix}**",
                            color=discord.Color.green()))
    
    #_evict_prefix_cache_for_guild(str(ctx.guild.id))
    #print("Removed the cached memory of this server's prefix.")


@set_prefix.error
async def set_prefix_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="Set Prefix",
                                           description="Changes the prefix of this bot. Syntax: `setprefix new_prefix`",
                                           color=discord.Color.dark_blue()))
    elif isinstance(error, commands.BadArgument):
        await ctx.send("The prefix must be a string.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.command(name='selfprefix',
             help='Set your own prefix for this server.\n**Syntax**: selfprefix new_prefix or type "delete" for deleting the self-prefix')
@commands.guild_only()
async def self_prefix(ctx, new_prefix: str):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "selfprefix"):
        await ctx.reply("You are blocked from using selfprefix command.")
        return
    
    guild_id = str(ctx.guild.id)
    user_id  = str(ctx.author.id)

    async with utils.db_pool.acquire() as conn:
        if new_prefix.lower() == "delete" or new_prefix.lower() == "del":
            await conn.execute("DELETE FROM user_prefixes WHERE user_id = $1", str(ctx.author.id))
            await ctx.send(embed=discord.Embed(title="Self-Prefix Disabled",
                                               description="Your self-prefix has been disabled globally.",
                                               color=discord.Color.green()))
            return

        if len(new_prefix) > 5:
            await ctx.send("Prefix cannot be longer than 5 characters.")
            return

        await conn.execute("INSERT INTO user_prefixes (user_id, prefix) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET prefix = EXCLUDED.prefix", str(ctx.author.id), new_prefix)
        await ctx.send(embed=discord.Embed(title="Self-Prefix Set",
                                           description=f"Your self-prefix has been set to: **{new_prefix}**",
                                           color=discord.Color.green()))
        
        #_evict_prefix_cache_for_user(guild_id, user_id)
        #print("Removed the cached memory of this user's prefix.")


@self_prefix.error
async def self_prefix_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="Self Prefix",
                                           description="Changes your personal prefix for yourself across the bot.\n\n**Syntax**: `selfprefix new_prefix`",
                                           color=discord.Color.dark_blue()))
    elif isinstance(error, commands.BadArgument):
        await ctx.send("The prefix must be a string.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.command(name='setnick',
             help=f"Change the nickname of a given member to a desired one.\n**Syntax**: setnick @user new_nickname")
@commands.guild_only()
@commands.bot_has_permissions(manage_nicknames=True)
async def set_nick(ctx, user_arg: str = None, *, new_nick: str = None):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "setnick"):
        return

    if not user_arg and not new_nick:
        return await ctx.send(
            embed=discord.Embed(title="Setnick", description="Changes the nickname of a given member to a desired one.",
                                color=discord.Color.dark_blue()))

    member = None
    if user_arg.isdigit():
        member = ctx.guild.get_member(int(user_arg)) or await bot.fetch_user(int(user_arg))
    elif user_arg.startswith('<@') and user_arg.endswith('>'):
        user_id = int(user_arg.strip('<@!>'))
        member = ctx.guild.get_member(user_id) or await bot.fetch_user(user_id)
    else:
        closest_member, confidence = await find_closest_member(ctx, user_arg)
        if closest_member and confidence > 60:
            member = closest_member
        else:
            await ctx.reply(f"Can't find the user {user_arg}")
            return

    if not member or not isinstance(member, discord.Member):
        return await ctx.send(embed=discord.Embed(
            title="User Not Found",
            description=f"Unable to resolve the user: `{user_arg}`. Please provide a valid mention, ID, or name.",
            color=discord.Color.red()
        ))

    if not await permissions_check_decorator(ctx, member, 'setnick'):
        return

    if member.top_role >= ctx.guild.me.top_role:
        return await ctx.send(embed=discord.Embed(
            title="Insufficient Permissions",
            description="I cannot change the nickname of this user because they have a higher or equal role than me.",
            color=discord.Color.red()
        ))

    # Check if the new nickname is valid
    if len(new_nick) > 64:
        await ctx.reply("Nickname cannot be longer than 64 characters.")
        return

    original_name = member.display_name
    err = []

    # Attempt to change the nickname
    try:
        await member.edit(nick=new_nick)
        #add_modlog("SetNick", member.id, ctx.author.id, f"Nickname changed from **{original_name}** to **{new_nick}**.")
        await ctx.send(embed=discord.Embed(title="Nickname Changed",
                                           description=f"Nickname for {member.name} has been changed to `{new_nick}`.",
                                           color=discord.Color.green()))
    except discord.Forbidden:
        err.append("I can't change this user's nickname for some reason.")
    except discord.HTTPException:
        err.append("Failed to change the nickname due to a network error.")
    except Exception as e:
        err.append(f"An unexpected error occurred: {str(e)}")

    if err:
        await ctx.send(embed=discord.Embed(title="Error", description="".join(err), color=discord.Color.red()))

@set_nick.error
async def set_nick_error(ctx, error):
    er = []
    if isinstance(error, commands.BotMissingPermissions):
        er.append(
            "I do not have the necessary permissions to mute this user. Please ensure I have the Moderate Members permission.")
    elif isinstance(error, commands.CommandInvokeError):
        er.append(f"An error occurred while invoking the command: {error}")
    else:
        er.append(f"An error occurred: {str(error)}")
    if er:
        await ctx.send(embed=discord.Embed(title="Error", description="".join(er), color=discord.Color.red()))


@bot.tree.command(name="setnick", description="Change the nickname of a given member to a desired one.")
@commands.guild_only()
@commands.bot_has_permissions(manage_nicknames=True)
@app_commands.describe(user="Mention, ID, or name of the user", new_nick="The new nickname to set")
async def slash_setnick(interaction: discord.Interaction, user: str = None, new_nick: str = None):
    # Authorization check
    if not await is_authorized_or_not(interaction, interaction.guild.id, interaction.user.id, "setnick"):
        await interaction.response.send_message("You don't have permission to use this.", ephemeral=True)
        return

    if not user or not new_nick:
        help_embed = discord.Embed( title="Setnick", description="Changes the nickname of a given member to a desired one.", color=discord.Color.dark_blue())
        await interaction.response.send_message(embed=help_embed, ephemeral=True)
        return
    await interaction.response.defer()

    # Resolve user
    member = None
    if user.isdigit():
        member = interaction.guild.get_member(int(user)) or await bot.fetch_user(int(user))
    elif user.startswith('<@') and user.endswith('>'):
        user_id = int(user.strip('<@!>'))
        member = interaction.guild.get_member(user_id) or await bot.fetch_user(user_id)
    else:
        closest_member, confidence = await find_closest_member(interaction, user)
        if closest_member and confidence > 60:
            member = closest_member
        else:
            await interaction.followup.send(f"Can't find the user {user}", ephemeral=True)
            return

    # Ensure member is a guild Member
    if not member or not isinstance(member, discord.Member):
        err = discord.Embed(
            title="User Not Found",
            description=f"Unable to resolve the user: `{user}`. Provide a valid mention, ID, or name.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=err)
        return

    # Permission hierarchy check
    if not await permissions_check_decorator(interaction, member, 'setnick'):
        return

    if member.top_role >= interaction.guild.me.top_role:
        err = discord.Embed(
            title="Insufficient Permissions",
            description="I cannot change the nickname of this user because they have a higher or equal role than me.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=err)
        return

    # Nickname length check
    if len(new_nick) > 64:
        await interaction.followup.send("Nickname cannot be longer than 64 characters.", ephemeral=True)
        return

    original_name = member.display_name
    errors = []

    # Attempt to change nickname
    try:
        await member.edit(nick=new_nick)
        #add_modlog("SetNick", member.id, interaction.user.id, f"Nickname changed from **{original_name}** to **{new_nick}**.")
        success = discord.Embed(
            title="Nickname Changed",
            description=f"Nickname for {member.name} has been changed to `{new_nick}`.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=success)
    except discord.Forbidden:
        errors.append("I don't have permission to change this user's nickname.")
    except discord.HTTPException:
        errors.append("Failed to change the nickname due to a network error.")
    except Exception as e:
        errors.append(f"An unexpected error occurred: {e}")

    if errors:
        err_embed = discord.Embed(title="Error", description="\n".join(errors), color=discord.Color.red())
        await interaction.followup.send(embed=err_embed)



@bot.command(name="mute",
             help=f"Mute multiple or single users for a specified amount of time.\n**Syntax**: mute @user(or user_ID) time reason")
@commands.guild_only()
@commands.bot_has_permissions(moderate_members=True)
async def mute(ctx, *, args):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "mute"):
        return

    guild = ctx.guild

    # Split arguments
    split_args = args.split(' ')

    user_mentions = [arg for arg in split_args if arg.startswith('<@') and arg.endswith('>') or arg.isdigit()]

    if not user_mentions:
        await ctx.send("Please provide at least one valid user to mute.")
        return

    duration_unit = next((arg for arg in split_args if len(arg) > 1 and arg[:-1].isdigit() and arg[-1] in "smhd"), "2m")
    reason_args = [arg for arg in split_args if arg not in user_mentions and arg != duration_unit]
    reason = ' '.join(reason_args) if reason_args else 'No reason provided'

    # Validate and convert time
    if duration_unit:
        duration = int(duration_unit[:-1])
        unit = duration_unit[-1]
        time = convert_to_seconds(duration, unit)
    else:
        await ctx.send("Invalid or missing duration. Please use formats like `30s` or `2m`.")
        return

    if time is None or time > 2419200:  # 28 days limit
        await ctx.send("Invalid time! Ensure it's under 28 days and use `s`, `m`, `h`, or `d` as units.")
        return

    dm_message = f"You have been muted in **{ctx.guild.name}** for **{duration}{unit}**. Reason: **{reason}**."

    # Prepare to collect results
    muted_users = []
    users_not_found_set = set()
    already_muted_users = []
    error_messages = []

    # Process valid members for muting
    for mention in user_mentions:
        clean_user_id = mention.strip('<@!>')
        if clean_user_id.isdigit():
            member = guild.get_member(int(clean_user_id))
            if not await permissions_check_decorator(ctx, member, 'mute'):
                continue

            if member is None:  # Handle not found users
                try:
                    user = await bot.fetch_user(int(clean_user_id))
                    users_not_found_set.add(user.display_name)
                except discord.NotFound:
                    users_not_found_set.add(f"User ID {clean_user_id} (not found)")
                continue

            if member.is_timed_out():
                already_muted_users.append(member)
                continue

            # Mute logic
            try:
                mute_until = discord.utils.utcnow() + timedelta(seconds=time)
                await member.timeout(mute_until, reason=reason)
                asyncio.create_task(unmute_member(ctx, member, duration, unit))
                #add_modlog("Mute", member.id, ctx.author.id, f"Duration: **{duration}{unit}**, Reason: **{reason}**")

                # Attempt to send a DM
                try:
                    await member.send(embed=discord.Embed(
                        title=f"You've been Muted by **{ctx.author.display_name}**",
                        description=dm_message,
                        color=discord.Color.random()
                    ))
                except discord.Forbidden:
                    pass  # Skip DM if sending fails

                muted_users.append(member)
                await asyncio.sleep(0.1)  # Avoid rate limiting


            except discord.Forbidden:
                error_messages.append(f"I can't mute **{member.display_name}** for some reason.")
            except discord.HTTPException:
                error_messages.append(f"An error occurred while muting **{member.display_name}**.")
            except Exception as e:
                error_messages.append(f"An unexpected error occurred: *{e}*")
        else:
            users_not_found_set.add(mention.strip('<@!>'))

    # Send results of muting
    if muted_users:
        muted_users_names = ', '.join([user.display_name for user in muted_users])
        embed = discord.Embed(
            title="Mute Successful",
            description=f"The following users were muted for **{duration}{unit}**:\n**{muted_users_names}**\nReason: *{reason}*",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # Report users not found
    if users_not_found_set:
        users_not_found_names = ', '.join(users_not_found_set)
        embed = discord.Embed(
            title="Users Not Found",
            description=f"The following users were not found in the server:\n**{users_not_found_names}**",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    # Handle already muted users
    if already_muted_users:
        already_muted_names = ', '.join([user.display_name for user in already_muted_users])
        embed = discord.Embed(
            title="Already Muted",
            description=f"The following users are already muted:\n**{already_muted_names}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    # Handle any error messages
    if error_messages:
        embed = discord.Embed(
            title="Errors Encountered",
            description="\n".join(error_messages),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@mute.error
async def mute_error(ctx, error):
    """Handles both interactions (slash commands) and command contexts (prefix commands)."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="Mute",
                                           description="Mutes a specific user or multiple users at a time with optional time and reason.\n**Default Time** - 2m\n**Default Reason** - No reason provided\n\n**Syntax**: `mute @user(or user_ID) time reason`",
                                           color=discord.Color.dark_blue()))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "I do not have the necessary permissions to mute this user. Please ensure I have the Moderate Members permission.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.command(name="unmute",
             help=f"Unmute one or multiple users who have been timed out.\n**Syntax**: unmute @user(or user_ID) reason")
@commands.guild_only()
@commands.bot_has_permissions(moderate_members=True)
async def unmute(ctx, *, args):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "unmute"):
        return

    guild = ctx.guild

    # Split arguments
    split_args = args.split(' ')

    # Extract user mentions or IDs
    user_mentions = [arg for arg in split_args if arg.startswith('<@') or arg.isdigit()]

    # Extract reason
    reason_args = [arg for arg in split_args if arg not in user_mentions]
    reason = ' '.join(reason_args) if reason_args else 'No reason provided'

    dm_message = f"You have been unmuted in **{ctx.guild.name}**.\nYou can now participate in chats and have fun again :)"

    # Prepare to collect results
    unmuted_users = []
    users_not_found_set = set()
    already_unmuted_users = []
    error_messages = []

    # Process valid members for unmuting
    for mention in user_mentions:
        clean_user_id = mention.strip('<@!>')
        if clean_user_id.isdigit():
            member = guild.get_member(int(clean_user_id))

            if not await permissions_check_decorator(ctx, member, 'unmute'):
                continue

            if member is None:  # Handle users not found in the server
                try:
                    user = await bot.fetch_user(int(clean_user_id))
                    users_not_found_set.add(user.display_name)
                except discord.NotFound:
                    users_not_found_set.add(f"User ID {clean_user_id} (not found)")
                continue

            if not member.is_timed_out():
                already_unmuted_users.append(member)
                continue

            # Unmute logic
            try:
                await member.edit(timed_out_until=None)
                #add_modlog("Unmute", member.id, ctx.author.id, f"Reason: **{reason}**.")  # Removes the timeout

                # Attempt to send a DM
                try:
                    await member.send(embed=discord.Embed(
                        title=f"You've been Unmuted by **{ctx.author.display_name}**!!",
                        description=dm_message,
                        color=discord.Color.random()
                    ))
                except discord.Forbidden:
                    pass  # Skip DM if sending fails

                unmuted_users.append(member)
                await asyncio.sleep(0.1)  # Avoid rate limiting

            except discord.Forbidden:
                error_messages.append(f"I can't unmute **{member.display_name}** for some reason.")
            except discord.HTTPException:
                error_messages.append(f"An error occurred while unmuting **{member.display_name}**.")
            except Exception as e:
                error_messages.append(f"An unexpected error occurred: *{e}*")
        else:
            users_not_found_set.add(mention.strip('<@!>'))

    # Send results of unmuting
    if unmuted_users:
        unmuted_users_names = ', '.join([user.display_name for user in unmuted_users])
        embed = discord.Embed(
            title="Unmute Successful",
            description=f"The following users were unmuted:\n**{unmuted_users_names}**\nReason: *{reason}*",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # Report users not found
    if users_not_found_set:
        users_not_found_names = ', '.join(users_not_found_set)
        embed = discord.Embed(
            title="Users Not Found",
            description=f"The following users were not found in the server:\n**{users_not_found_names}**",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    # Handle already unmuted users
    if already_unmuted_users:
        already_unmuted_names = ', '.join([user.display_name for user in already_unmuted_users])
        embed = discord.Embed(
            title="Already Unmuted",
            description=f"The following users are already unmuted:\n**{already_unmuted_names}**",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    # Handle any error messages
    if error_messages:
        embed = discord.Embed(
            title="Errors Encountered",
            description="\n".join(error_messages),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@unmute.error
async def unmute_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            title="Unmute",
            description="Unmutes a given user or multiple users with an optional reason argument.\n**Default Reason** - No reason provided\n\n**Syntax**: `unmute @user(or user_ID) reason`",
            color=discord.Color.dark_blue()
        ))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "I do not have the necessary permissions to mute this user. Please ensure that I've Moderate Members permission before trying again.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")


massban_group = app_commands.Group(name="massban", description="Mass ban members in various modes such as /massban all, or /massban role etc.")


@massban_group.command(name="all", description="Ban all members")
@app_commands.describe(reason="The reason for the ban (default: 'No reason provided')")
async def massban_all(interaction: discord.Interaction, reason: str = "No reason provided"):
    not_banned = []
    banned_count = 0
    not_banned_count = 0
    guild = interaction.guild
    global operation_active
    operation_active = True

    decision = await permission_system.evaluate(utils.db_pool, guild_id=interaction.guild.id, user_id=interaction.user.id,
                                                guild_owner_id=interaction.guild.owner_id, command_name="massban",
                                                channel_id=interaction.channel_id)
    if not decision.allowed:
        await interaction.response.send_message(
            f"You cannot use massban here. {decision.reason}.",
            ephemeral=True)
        return

    await interaction.response.send_message("Are you sure you want to ban **all** members? Type `CONFIRM` to proceed.")
    try:
        confirm_msg = await bot.wait_for("message", check=lambda
            m: m.author == interaction.user and m.content.upper() == "CONFIRM", timeout=30)
    except asyncio.TimeoutError:
        await interaction.followup.send("Ban all command timed out. Operation cancelled.")
        return

    progress_msg = await interaction.followup.send("Mass-ban in progress...", ephemeral=True)

    for member in guild.members:
        if not operation_active:
            await interaction.followup.send("Mass ban operation halted by stop command.", ephemeral=False)
            return
        try:
            await guild.ban(member, reason=reason)
            banned_count += 1
            await asyncio.sleep(0.45)
        except Exception as e:
            not_banned_count += 1
            continue

    result_msg = f"Banned **{banned_count}** members."
    if not_banned_count >= 1:
        result_msg += f"\nSome errors occurred: Was not able to ban **{not_banned_count}** members."
    await interaction.followup.send(result_msg, ephemeral=False)


@massban_group.command(name="number", description="Ban a specific number of random members")
@app_commands.describe(number="The number of random members to ban", reason="The reason for the ban")
async def massban_number(interaction: discord.Interaction, number: int, reason: str = "No reason provided"):
    not_banned = []
    banned_count = 0
    not_banned_count = 0
    global operation_active
    operation_active = True

    decision = await permission_system.evaluate(utils.db_pool, guild_id=interaction.guild.id, user_id=interaction.user.id,
                                                guild_owner_id=interaction.guild.owner_id, command_name="massban",
                                                channel_id=interaction.channel_id)
    if not decision.allowed:
        await interaction.response.send_message(
            f"You cannot use massban here. {decision.reason}.",
            ephemeral=True)
        return

    if number is None or number <= 0:
        await interaction.response.send_message("Please provide a valid number of members to ban.", ephemeral=True)
        return

    bannable_members = [m for m in interaction.guild.members]
    if not bannable_members:
        await interaction.response.send_message("No members found.", ephemeral=True)
        return

    if number > len(bannable_members):
        number = len(bannable_members)

    selected_members = random.sample(bannable_members, number)
    banned_members = []

    class ShowUsersView(discord.ui.View):
        def __init__(self, banned_users, user_id):
            super().__init__(timeout=180)  # 3 minute timeout
            self.banned_users = banned_users
            self.user_id = user_id

        @discord.ui.button(label="Show Users", style=discord.ButtonStyle.grey)
        async def show_users(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ This button is not for you!", ephemeral=True)
                return

            user_list = "\n".join([f"{name} (ID: {id})" for name, id in
                                   self.banned_users]) if self.banned_users else "No users were banned"
            await interaction.response.send_message(f"**Banned Users:**\n{user_list}", ephemeral=True)

        async def on_timeout(self):
            self.show_users.disabled = True
            await self.message.edit(view=self)

    progress_msg = await interaction.response.send_message("Mass-ban in progress...", ephemeral=True)

    for member in selected_members:
        if not operation_active:
            await interaction.followup.send("Mass ban operation halted by stop command.", ephemeral=False)
            return
        try:
            await interaction.guild.ban(member, reason=reason)
            banned_count += 1
            banned_members.append((member.display_name, member.id))
            await asyncio.sleep(0.3)
        except Exception as e:
            not_banned.append(member.display_name)
            not_banned_count += 1

    embed = discord.Embed(title="Massban Executed",
                          description=f"Banned **{banned_count}** out of **{number}** selected members.",
                          color=discord.Color.green())

    if not_banned:
        embed.add_field(name="Not Banned", value=", ".join(not_banned[:10]) + ("..." if len(not_banned) > 10 else ""),
                        inline=False)

    view = ShowUsersView(banned_members, interaction.user.id)
    msg = await interaction.followup.send(embed=embed, view=view, ephemeral=False)
    view.message = msg


@massban_group.command(name="role", description="Ban members with a specific role")
@app_commands.describe(role="The target role", number="The number of members to ban (enter a number; 0 for all)",
                       reason="The reason for the ban")
async def massban_role(interaction: discord.Interaction, role: discord.Role, number: int, reason: str = "No reason provided"):
    not_banned = []
    banned_count = 0
    not_banned_count = 0
    guild = interaction.guild
    global operation_active
    operation_active = True

    decision = await permission_system.evaluate(utils.db_pool, guild_id=interaction.guild.id, user_id=interaction.user.id,
                                                guild_owner_id=interaction.guild.owner_id, command_name="massban",
                                                channel_id=interaction.channel_id)
    if not decision.allowed:
        await interaction.response.send_message(
            f"You cannot use massban here. {decision.reason}.",
            ephemeral=True)
        return

    if role is None:
        await interaction.response.send_message("Please provide a role for the 'role' mode.", ephemeral=True)
        return

    target_members = [m for m in guild.members if role in m.roles]
    if not target_members:
        await interaction.response.send_message(f"No bannable members found with the role **{role.name}**.",
                                                ephemeral=True)
        return

    # Ensure the number field is provided.
    if number is None:
        await interaction.response.send_message("Please provide the number of members to ban (enter 0 for all).",
                                                ephemeral=True)
        return

    # If user inputs 0, then ban all available members.
    if number == 0:
        selected_members = target_members
    else:
        if number > len(target_members):
            await interaction.response.send_message(
                f"Error: Maximum bannable members with role **{role.name}** is {len(target_members)}. Please provide a number between 1 and {len(target_members)}, or use 0 for all.",
                ephemeral=True
            )
            return
        else:
            selected_members = random.sample(target_members, number)

    progress_msg = await interaction.response.send_message("Mass-ban in progress...", ephemeral=True)

    for member in selected_members:
        if not operation_active:
            await interaction.followup.send("Mass ban operation halted by stop command.", ephemeral=False)
            return
        try:
            await guild.ban(member, reason=reason)
            banned_count += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            not_banned.append(member.display_name)
            not_banned_count += 1

    embed = discord.Embed(
        title=f"Massban (Role: {role.name}) Executed",
        description=f"Banned **{banned_count}** members with the role **{role.name}**.",
        color=discord.Color.green()
    )

    if not_banned:
        embed.add_field(
            name="Not Banned",
            value=", ".join(not_banned[:10]) + ("..." if len(not_banned) > 10 else ""),
            inline=False
        )
    await interaction.followup.send(embed=embed, ephemeral=False)
    return


@massban_group.command(name="date", description="Ban members who joined on a specific date")
@app_commands.describe(day="The day of the join date", month="The month of the join date",
                       year="The year of the join date",
                       number="The number of members to ban (enter a number; 0 for all)",
                       reason="The reason for the ban")
async def massban_date(interaction: discord.Interaction, day: int, month: int, year: int, number: int,
                       reason: str = "No reason provided"):
    not_banned = []
    banned_count = 0
    not_banned_count = 0
    guild = interaction.guild
    global operation_active
    operation_active = True

    decision = await permission_system.evaluate(utils.db_pool, guild_id=interaction.guild.id, user_id=interaction.user.id,
                                                guild_owner_id=interaction.guild.owner_id, command_name="massban",
                                                channel_id=interaction.channel_id)
    if not decision.allowed:
        await interaction.response.send_message(
            f"You cannot use massban here. {decision.reason}.",
            ephemeral=True)
        return

    if day is None or month is None or year is None:
        await interaction.response.send_message("Please provide valid day, month, and year for 'date' mode.",
                                                ephemeral=True)
        return

    try:
        ban_date = datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        await interaction.response.send_message("Invalid date provided.", ephemeral=True)
        return

    if ban_date < guild.created_at:
        await interaction.response.send_message(
            f"Provided date {ban_date.strftime('%d/%m/%Y')} is before the server was created on {guild.created_at.strftime('%d/%m/%Y')}.",
            ephemeral=True
        )
        return

    if ban_date > datetime.now(timezone.utc):
        await interaction.response.send_message("Provided date is in the future.", ephemeral=True)
        return

    members_to_ban = [
        member for member in guild.members
        if member.joined_at is not None and
           member.joined_at.day == day and
           member.joined_at.month == month and
           member.joined_at.year == year
    ]
    if not members_to_ban:
        await interaction.response.send_message("No members found who joined on the specified date.", ephemeral=True)
        return

    # Ensure the number field is provided.
    if number is None:
        await interaction.response.send_message("Please provide the number of members to ban (enter 0 for all).",
                                                ephemeral=True)
        return

    if number == 0:
        selected_members = members_to_ban
    else:
        if number > len(members_to_ban):
            await interaction.response.send_message(
                f"Error: Maximum bannable members on {day}/{month}/{year} is {len(members_to_ban)}. Please provide a number between 1 and {len(members_to_ban)}, or use 0 for all.",
                ephemeral=True
            )
            return
        else:
            selected_members = random.sample(members_to_ban, number)

    await interaction.response.send_message(
        f"Are you sure you want to ban **{len(selected_members)}** members who joined on {day}/{month}/{year}? Type `CONFIRM` to proceed.",
        ephemeral=False
    )
    try:
        confirm_msg = await bot.wait_for(
            "message",
            check=lambda m: m.author == interaction.user and m.content.upper() == "CONFIRM",
            timeout=30
        )
    except asyncio.TimeoutError:
        await interaction.followup.send("Ban by join date command timed out. Operation cancelled.", ephemeral=False)
        return

    progress_msg = await interaction.followup.send("Mass-ban in progress...", ephemeral=True)

    for member in selected_members:
        if not operation_active:
            await interaction.followup.send("Mass ban operation halted by stop command.", ephemeral=False)
            return
        try:
            await guild.ban(member, reason=reason)
            banned_count += 1
            await asyncio.sleep(0.35)
        except Exception as e:
            not_banned.append(member.display_name)
            not_banned_count += 1

    result_msg = f"Banned **{banned_count}** members who joined on {day}/{month}/{year}."
    if not_banned_count >= 1:
        result_msg += f"\nSome errors occurred: Was not able to ban **{not_banned_count}** members."
    await interaction.followup.send(result_msg, ephemeral=False)


bot.tree.add_command(massban_group)


@bot.command(name="ban",
             help=f"Ban multiple or single users by their user IDs or mentions\n**Syntax**: ban @user(or user_ID) reason")
@commands.guild_only()
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, *, args):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "ban"):
        return

    guild = ctx.guild
    dm_message = f"You have been banned from **{ctx.guild.name}**.\nHope you had a good time in there :)"
    split_args = args.split(' ')

    user_mentions = [arg for arg in split_args if arg.startswith('<@') or arg.isdigit()]
    reason = ' '.join(
        [arg for arg in split_args if arg not in user_mentions]) if user_mentions else 'No reason provided'

    banned_users = []
    users_that_are_already_banned_list = set()
    error_messages = []

    already_banned_users = set()
    async for ban_entry in guild.bans():
        already_banned_users.add(ban_entry.user.id)

    for mention in user_mentions:
        clean_user_id = mention.strip('<@!>')

        if clean_user_id.isdigit():
            try:
                user = await bot.fetch_user(int(clean_user_id))

                if not await permissions_check_decorator(ctx, user, 'ban'):
                    continue

                if user.id in already_banned_users:
                    users_that_are_already_banned_list.add(f"**{user.display_name}**")
                    continue

                try:
                    await guild.ban(user, reason=reason)
                    #add_modlog("Ban", user.id, ctx.author.id, f"Reason: **{reason}**")

                    try:
                        await user.send(embed=discord.Embed(
                            title=f"You've been Banned by **{ctx.author.display_name}**",
                            description=dm_message,
                            color=discord.Color.random()
                        ))
                    except discord.Forbidden:
                        pass

                    banned_users.append(user)
                    await asyncio.sleep(0.2)

                except discord.HTTPException:
                    error_messages.append(f"Failed to ban **{user.display_name}** due to an HTTP error.")
                except Exception as e:
                    error_messages.append(f"Failed to ban **{user.display_name}** due to: {e}")

            except discord.NotFound:
                error_messages.append(f"For some reason I can't find User ID **{clean_user_id}**")
            except Exception as e:
                error_messages.append(f"Invalid user ID {clean_user_id}: {e}")
        else:  # If it's an invalid mention or non-digit ID
            error_messages.append(f"Invalid ID or mention: {mention}")

    if banned_users:
        banned_users_names = ', '.join([user.display_name for user in banned_users])
        embed = discord.Embed(
            title="Ban Successful",
            description=f"The following users were banned:\n**{banned_users_names}**\nReason: **{reason if reason else 'No reason provided'}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    if users_that_are_already_banned_list:
        users_already_banned = ', '.join(users_that_are_already_banned_list)
        embed = discord.Embed(
            title="Users Already Banned",
            description=f"The following users are already banned:\n**{users_already_banned}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    if error_messages:
        embed = discord.Embed(
            title="Errors encountered",
            description="\n".join(error_messages),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Please mention valid members or provide valid user IDs.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            title="Ban",
            description="Bans a given user or multiple users with an optional reason argument.\n**Default Reason** - No reason provided\n\n\n**Syntax**: `ban @user(or user_ID) reason`",
            color=discord.Color.dark_blue()))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "I do not have the necessary permissions to ban this user. Please ensure that I've Ban Members permission before trying again.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.tree.command(name="ban", description="Ban multiple or single users by their user IDs or mentions.")
async def bann(interaction: discord.Interaction, target: discord.Member, reason: str = "No reason provided"):
    if not await is_authorized_or_not(interaction, interaction.guild.id, interaction.user.id, "ban"):
        return

    guild = interaction.guild
    dm_message = f"You have been banned from **{guild.name}**.\nHope you had a good time in there :)"
    members = [target]

    banned_users = []
    users_that_are_already_banned_list = set()
    error_messages = []

    already_banned_users = set()
    async for ban_entry in guild.bans():
        already_banned_users.add(ban_entry.user.id)

    for member in members:
        if not await permissions_check_decorator(interaction, member, 'ban'):
            continue

        if member.id in already_banned_users:
            users_that_are_already_banned_list.add(f"**{member.display_name}**")
            continue

        try:
            await guild.ban(member, reason=reason)
            #add_modlog("Ban", member.id, interaction.user.id, f"Reason: **{reason}**")
            try:
                await member.send(embed=discord.Embed(
                    title=f"You've been Banned by **{interaction.user.display_name}**",
                    description=dm_message,
                    color=discord.Color.random()
                ))
            except discord.Forbidden:
                pass

            banned_users.append(member)
            await asyncio.sleep(0.2)
        except discord.HTTPException:
            error_messages.append(f"Failed to ban **{member.display_name}** due to an HTTP error.")
        except Exception as e:
            error_messages.append(f"Failed to ban **{member.display_name}** due to: {e}")

    # Prepare responses
    responses = []
    if banned_users:
        banned_users_names = ', '.join([user.display_name for user in banned_users])
        embed = discord.Embed(
            title="Ban Successful",
            description=f"The following users were banned:\n**{banned_users_names}**\nReason: **{reason if reason else 'No reason provided'}**",
            color=discord.Color.green()
        )
        responses.append(embed)
    if users_that_are_already_banned_list:
        users_already_banned = ', '.join(users_that_are_already_banned_list)
        embed = discord.Embed(
            title="Users Already Banned",
            description=f"The following users are already banned:\n**{users_already_banned}**",
            color=discord.Color.blue()
        )
        responses.append(embed)
    if error_messages:
        embed = discord.Embed(
            title="Errors encountered",
            description="\n".join(error_messages),
            color=discord.Color.red()
        )
        responses.append(embed)

    if responses:
        await interaction.response.send_message(embed=responses[0])
        for embed in responses[1:]:
            await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message("No users were banned.", ephemeral=True)


massunban_group = app_commands.Group(name="massunban", description="Mass Unban Commands")


@massunban_group.command(name="all", description="Unban all banned members.")
async def massunban_all(interaction: discord.Interaction):
    decision = await permission_system.evaluate(utils.db_pool, guild_id=interaction.guild.id, user_id=interaction.user.id,
                                                guild_owner_id=interaction.guild.owner_id, command_name="massunban",
                                                channel_id=interaction.channel_id)
    if not decision.allowed:
        await interaction.response.send_message(
            f"You cannot use massunban here. {decision.reason}.",
            ephemeral=True)
        return
    guild = interaction.guild
    global operation_active
    operation_active = True

    await interaction.response.send_message("Unbanning all banned members...", ephemeral=False)
    bans = [ban async for ban in guild.bans()]
    unbanned_users = []
    error_messages = []
    if not bans:
        await interaction.followup.send("No members found to unban.", ephemeral=False)
        return

    for ban_entry in bans:
        if not operation_active:
            await interaction.followup.send("Mass unban operation halted by stop command.", ephemeral=False)
            return
        user = ban_entry.user
        try:
            await guild.unban(user)
            #add_modlog("Unban", user.id, interaction.user.id, f"Unbanned by **{interaction.user.display_name}**.")
            unbanned_users.append(f"**{user.name}** (ID: **{user.id}**)")
            await asyncio.sleep(0.4)
        except discord.NotFound:
            error_messages.append(f"User **{user.name}** (ID: **{user.id}**) is not banned.")
        except Exception as e:
            error_messages.append(f"Failed to unban **{user.name}** (ID: **{user.id}**) due to *{e}*")
    embed = discord.Embed(
        title="Mass Unban",
        description="All banned members have been unbanned!",
        color=discord.Color.green()
    )
    if unbanned_users:
        embed.add_field(name="Unbanned Users", value="\n".join(unbanned_users), inline=False)
    await interaction.followup.send(embed=embed)
    if error_messages:
        error_embed = discord.Embed(title="Errors Encountered", description="\n".join(error_messages),
                                    color=discord.Color.red())
        await interaction.followup.send(embed=error_embed)


bot.tree.add_command(massunban_group)


@bot.command(name="unban",
             help=f"Unban multiple or single users by their IDs and mentions or unban all.\n**Syntax**: unban user_ID(or mention)")
@commands.guild_only()
@commands.bot_has_permissions(ban_members=True)
async def unban(ctx, *, members: str = None):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "unban"):
        return

    guild = ctx.guild

    if members is None or members.strip() == "":
        return await ctx.send(embed=discord.Embed(title="Unban",
                                                  description="Unbans a given user or multiple users based on their user id.\nAlso sends an invite link to the DMs of the user unbanned for server rejoining automatically\n\n**Syntax**: `unban user_ID or mention`.",
                                                  color=discord.Color.dark_blue()))

    member_list = members.split()  # Split the input members by spaces
    unbanned_users = []
    error_messages = []
    not_found_messages = []  # To collect user not found messages

    for member in member_list:
        try:
            if member.startswith('<@') and member.endswith('>'):
                member = member.strip('<@!>')

            if not member.isdigit() or len(member) < 17 or len(member) > 19:
                error_messages.append(
                    f"Invalid user ID: **{member}**.")
                continue

            user = await bot.fetch_user(int(member))
            await guild.unban(user)
            #add_modlog("Unban", user.id, ctx.author.id, f"Unbanned by **{ctx.author.display_name}**.")
            unbanned_users.append(f"**{user.display_name}** (ID: **{user.id}**)")  # Store unbanned user's name and ID
            await asyncio.sleep(0.5)
        except discord.NotFound:
            not_found_messages.append(f"User ID: **{member}** is not banned.")
        except discord.Forbidden:
            error_messages.append(f"I can't unban **{member}** somehow.")
        except Exception as e:
            error_messages.append(f"Failed to unban user **{member}** - *{e}*")

        # After processing all members, create and send separate embeds
    if unbanned_users:
        embed_unbanned = discord.Embed(
            title="Unban Successful",
            color=discord.Color.green()
        )
        embed_unbanned.add_field(name="The following users have been successfully unbanned:",
                                 value="\n".join(unbanned_users), inline=False)
        await ctx.send(embed=embed_unbanned)

    if error_messages:
        embed_errors = discord.Embed(
            title="Errors Encountered",
            color=discord.Color.red()
        )
        embed_errors.add_field(name="The following errors occurred during the unban process:",
                               value="\n".join(error_messages), inline=False)
        await ctx.send(embed=embed_errors)

    if not_found_messages:
        embed_not_found = discord.Embed(
            title="Users Not Found",
            color=discord.Color.red()
        )
        embed_not_found.add_field(name='The following users were not found in the ban list:',
                                  value="\n".join(not_found_messages), inline=False)
        await ctx.send(embed=embed_not_found)


@unban.error
async def unban_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Please mention valid members or provide valid user IDs.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "I do not have the necessary permissions to unban this user. Please ensure that I've Ban Members permission before trying again.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.tree.command(name="unban", description="Unban a user by their id or mention.")
async def unban(interaction: discord.Interaction, member: str, reason: str = "No reason provided"):
    if not await is_authorized_or_not(interaction, interaction.guild.id, interaction.user.id, "unban"):
        return

    guild = interaction.guild
    target = None

    # If input is digits, treat it as an ID.
    if member.isdigit():
        try:
            target = await bot.fetch_user(int(member))
        except Exception:
            target = None
    # If input looks like a mention.
    elif member.startswith("<@") and member.endswith(">"):
        cleaned = member.strip("<@!>")
        if cleaned.isdigit():
            try:
                target = await bot.fetch_user(int(cleaned))
            except Exception:
                target = None

    if not target:
        await interaction.response.send_message(f"Could not resolve user: `{member}`", ephemeral=True)
        return

    try:
        await guild.unban(target)
        #add_modlog("Unban", target.id, interaction.user.id, f"Unbanned by **{interaction.user.display_name}**.")
        await interaction.response.send_message(embed=discord.Embed(title=f"Unban Successful",
                                                                    description=f"Successfully unbanned **{target.display_name}** (ID: **{target.id}**) with reason: **{reason}**",
                                                                    color=discord.Color.green()), ephemeral=False)
    except discord.NotFound:
        await interaction.response.send_message(f"User **{target.display_name}** (ID: **{target.id}**) is not banned.",
                                                ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(
            f"I don't have permission to unban **{target.display_name}** (ID: **{target.id}**).", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"Failed to unban **{target.display_name}** (ID: **{target.id}**) - *{e}*", ephemeral=True)


    

















# Slash command to ping user

# @bot.tree.command(name="ping", description="Get your ping")
# async def ping(interaction: discord.Interaction):
# if not is_authorized(interaction.user.id):
# return await interaction.response.send_message("You don't have permission to run this command. Please contact the owner for access.", ephemeral=True)
# latency = bot.latency * 1000  # Convert to milliseconds
# await interaction.response.send_message(f"Pong!! `{latency:.2f} ms`.")


@bot.command(name="purgereaction", help=f"Purge reactions from the last messages.\n**Syntax**: purgereaction amount")
@commands.bot_has_permissions(manage_messages=True)  # Ensure the user has permission to manage messages
async def purge_reaction(ctx, amount: int):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "purgereaction"):
        return
    global operation_active
    operation_active = True

    # Check if the amount is a positive number
    if amount <= 0:
        return await ctx.send(
            f"Please provide a positive number of messages to purge reactions from. **{amount}** is not a suitable number.")

    # Get the channel where the command was executed
    channel = ctx.channel

    # Confirm the action
    await ctx.send(f"Purging up to **{amount}** reactions from the last messages...")

    reactions_purged = 0  # Track the number of reactions purged

    try:
        # Fetch the last N messages
        async for message in channel.history(limit=400):
            if reactions_purged == amount:
                break

            # Process each reaction on the message
            for reaction in message.reactions:
                # Calculate how many reactions we can still purge
                reactions_to_remove = min(reaction.count, amount - reactions_purged)

                for _ in range(reactions_to_remove):
                    if not operation_active:
                        await ctx.send("Purge Reaction operation halted by stop command.")
                        return
                    await message.clear_reaction(reaction.emoji)
                    reactions_purged += 1
                    await asyncio.sleep(1)  # Delay to avoid rate limiting

                    # Stop if we've reached the desired amount
                    if reactions_purged == amount:
                        break

            # Check again to break the outer loop if we've reached the desired amount
            if reactions_purged == amount:
                break

    except Exception as e:
        embedError = discord.Embed(title="Error!!", description=f"Failed to purge reactions due to *{e}*",
                                   color=discord.Color.red())
        return await ctx.send(embed=embedError)

    # Create an embed for the success message
    embed = discord.Embed(
        title="Purge Reactions",
        description=f"Successfully purged **{reactions_purged}** reactions!",
        color=discord.Color.green()
    )

    # Send the embed
    await ctx.send(embed=embed)
    #add_modlog("Purged Reactions", None, ctx.author.id, f"Total purged amount: **{reactions_purged}**.")


@purge_reaction.error
async def purge_reaction_error(ctx, error):
    errr = []
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            title="Purge Reactions",
            description="Purge a given number of reactions from the last messages.\n\n**Syntax**: `purgereaction amount`",
            color=discord.Color.dark_blue()
        ))
    elif isinstance(error, commands.BotMissingPermissions):
        errr.append(
            "I do not have the necessary permissions to unban this user. Please ensure that I've Manage Messages permission before trying again.")
    elif isinstance(error, commands.CommandInvokeError):
        errr.append(f"An error occurred while invoking the command: {error}")
    elif isinstance(error, commands.BadArgument):
        errr.append("Please mention valid members or provide valid user IDs.")
    else:
        errr.append(f"An error occurred: *{str(error)}*")
    if errr:
        errEmbd = discord.Embed(title="Error", description="".join(errr), color=discord.Color.red())
        await ctx.send(embed=errEmbd)


@bot.command(name="stealsticker", help=f"Steals a sticker from a message.\n**Syntax**: steal_sticker message_ID")
@commands.bot_has_permissions(manage_emojis=True)
async def steal_sticker(ctx, message_id: str, sticker_name: str = None):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "stealsticker"):
        return

    guild = ctx.guild

    # Validate message_id
    if not message_id.isdigit() or len(message_id) > 19 or len(message_id) < 17:
        return await ctx.send("Invalid message ID. Please provide a valid numeric message ID.")

    # Fetch the channel and the message
    channel = ctx.channel

    try:
        message = await channel.fetch_message(int(message_id))
    except discord.NotFound:
        return await ctx.send("Message not found. Please provide a valid message ID.")

    # Check if the message contains stickers
    if len(message.stickers) == 0:
        return await ctx.send("There is no sticker in the message to steal.")

    # Get the first sticker from the message
    sticker = message.stickers[0]
    errors = []

    # Read the sticker data and wrap it in BytesIO
    try:
        sticker_data = await sticker.read()
        sticker_file = io.BytesIO(sticker_data)
    except Exception as e:
        return await ctx.send(f"Failed to read the sticker: {str(e)}", ephemeral=True)

    # Handle the emoji
    emoji_object = discord.utils.get(guild.emojis, name='skull')
    if emoji_object is None:
        emoji_object = ':smiley:'
        emoji_message = "The specified emoji was not found. Proceeding without an emoji."
    else:
        emoji_message = ""

    # Determine the sticker limit based on server Nitro level
    nitro_level = guild.premium_tier
    max_stickers = {0: 5, 1: 15, 2: 30, 3: 60}[nitro_level]
    current_sticker_count = len(guild.stickers)

    # Check if the server has enough sticker slots available
    if current_sticker_count >= max_stickers:
        return await ctx.send("The sticker slots are full. Please remove a sticker before adding a new one.")

    # Use provided name or fall back to the sticker's existing name
    if sticker_name is None or sticker_name.strip() == "":
        sticker_name = sticker.name

    # Check for duplicate sticker names
    existing_sticker = discord.utils.get(guild.stickers, name=sticker_name)
    if existing_sticker is not None:
        sticker_name += "_copy"  # Append "_copy" to the name to make it unique

    # Create the sticker
    try:
        new_sticker = await guild.create_sticker(
            name=sticker_name,
            description=f"Sticker copied from message ID **{message_id}**",
            file=discord.File(sticker_file, filename=f"{sticker_name}.png"),
            emoji=emoji_object
        )

        # Create an embed for the success message
        embed = discord.Embed(
            title="Sticker Stolen Successfully!",
            description=f"Successfully stole the sticker! Sticker name: `{new_sticker.name}`. {emoji_message}",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    except discord.HTTPException as e:
        errors.append(f"Failed to create sticker due to: *{str(e)}*")
    except Exception as e:
        errors.append(f"An unexpected error occurred: *{str(e)}*")

    if errors:
        embedErr = discord.Embed(title="Error", description="".join(errors), color=discord.Color.red())
        await ctx.send(embed=embedErr)


@steal_sticker.error
async def steal_sticker_error(ctx, error):
    err = []
    if isinstance(error, commands.MissingRequiredArgument):
        err.append("You need to mention a proper message ID for this command to work.")
    else:
        err.append(f"An error occurred: *{str(error)}*")

    if err:
        errEmbd = discord.Embed(title="Error", description="".join(err), color=discord.Color.red())
        await ctx.send(embed=errEmbd)


@bot.command(name="roleroulette",
             help="Temporarily assigns a random role to a user for a set period\n**Syntax**: roleroulette @user(or user_ID) time")
@commands.guild_only()
@commands.bot_has_permissions(manage_roles=True)
async def role_roulette(ctx, member_input: str, time_arg: str = '2m'):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "roleroulette"):
        return

    guild = ctx.guild

    # Error handling for bot's permission

    try:
        member = await commands.MemberConverter().convert(ctx, member_input)
    except commands.BadArgument:
        matched_member, confidence = await find_closest_member(ctx, member_input)
        if matched_member and confidence > 60:
            member = matched_member
        else:
            return await ctx.send(
                discord.Embed(title="Error", description=f"Could not find a member matching: **{member_input}**",
                              color=discord.Color.red()))

    if not await permissions_check_decorator(ctx, member, 'roleroulette'):
        return

    available_roles = [role for role in guild.roles if
                       not role.managed and role not in member.roles and role < guild.me.top_role]

    if not available_roles:
        return await ctx.send("There are no eligible roles left to assign to this user.")

    random_role = random.choice(available_roles)

    limits = {'s': 60, 'm': 60, 'h': 24, 'd': 28}

    duration_unit = next((arg for arg in time_arg.split() if len(arg) > 1 and arg[:-1].isdigit() and arg[-1] in "smhd"),
                         "2m")

    if len(duration_unit) < 2 or not duration_unit[:-1].isdigit() or duration_unit[-1] not in "smhd":
        return await ctx.send(
            embed=discord.Embed(title="Error",
                                description="Invalid time format! Use something like `10s`, `5m`, `2h`, etc.",
                                color=discord.Color.red()), ephemeral=True)

    amount = int(duration_unit[:-1])
    unit = duration_unit[-1]

    if amount > limits[unit]:
        return await ctx.reply(f"The maximum allowed {unit} is {limits[unit]}.", ephemeral=True)

    time_in_seconds = convert_to_seconds(amount, unit)

    # If member already has an active timer, remove their existing role first
    if member.id in active_role_timers:
        role_data = active_role_timers.get(member.id)  # Access safely using `.get()`

        if role_data:  # Check if role_data exists
            existing_task = role_data.get("task")
            if existing_task:
                existing_task.cancel()  # Cancel the old task

            # Remove the old role from the user
            existing_role_id = role_data.get("role_id")
            existing_role = guild.get_role(existing_role_id)
            if existing_role:
                try:
                    await member.remove_roles(existing_role)
                except discord.HTTPException:
                    pass

        # Remove the timer entry if it exists
        active_role_timers.pop(member.id, None)

    errorMESSAGES1 = []
    # Try assigning the role and catch potential errors
    try:
        await member.add_roles(random_role)
        embed = discord.Embed(
            title="Role Roulette 🎲",
            description=f"{random_role.mention} has been assigned to **{member.display_name}** for **{amount}{unit}**!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        #add_modlog("Role Roulette", member.id, ctx.author.id, f"Duration: **{amount}{unit}**")

        active_role_timers[member.id] = {
            "role_id": random_role.id,
            "channel_id": ctx.channel.id,
            "task": asyncio.create_task(remove_role_after_time(ctx, member, random_role, time_in_seconds))
        }

    except discord.Forbidden:
        return await ctx.send(f"I can't assign that role to {member.display_name} for some reason.")

    except discord.HTTPException as e:
        return await ctx.send(f"Failed to assign the role due to: {str(e)}")

    except Exception as e:
        return await ctx.send(f"An unexpected error occurred: {str(e)}")


@bot.tree.command(name="role_roulette", description="Temporarily assigns a random role to a user for a set period")
@app_commands.describe(
    member_input="Mention or ID of the user to assign a random role",
    time="Duration for which the role will be assigned (e.g., 2m, 1h)")
@app_commands.autocomplete(member_input=memname_choice)
async def role_roulet(interaction: discord.Interaction, member_input: str, time: str = '2m'):
    if not await is_authorized_or_not(interaction, interaction.guild.id, interaction.user.id, "roleroulette"):
        return

    guild = interaction.guild

    member = discord.utils.get(guild.members,
                               id=int(member_input[3:-1]) if member_input.startswith('<@') else int(member_input))

    if member is None:
        return await interaction.response.send_message("Member not found!", ephemeral=True)

    if not await permissions_check_decorator(interaction, member, 'roleroulette'):
        return

    available_roles = [role for role in guild.roles if
                       not role.managed and role not in member.roles and role < guild.me.top_role]

    if not available_roles:
        return await interaction.response.send_message("There are no eligible roles left to assign to this user.",
                                                       ephemeral=True)

    random_role = random.choice(available_roles)

    limits = {'s': 60, 'm': 60, 'h': 24, 'd': 28}

    duration_unit = next((arg for arg in time.split() if len(arg) > 1 and arg[:-1].isdigit() and arg[-1] in "smhd"),
                         "2m")

    if len(duration_unit) < 2 or not duration_unit[:-1].isdigit() or duration_unit[-1] not in "smhd":
        return await interaction.response.send_message(
            embed=discord.Embed(title="Error",
                                description="Invalid time format! Use something like `10s`, `5m`, `2h`, etc.",
                                color=discord.Color.red()), ephemeral=True)

    amount = int(duration_unit[:-1])
    unit = duration_unit[-1]

    if amount > limits[unit]:
        return await interaction.response.send_message(f"The maximum allowed {unit} is {limits[unit]}.", ephemeral=True)

    time_in_seconds = convert_to_seconds(amount, unit)

    # If member already has an active timer, remove their existing role first
    if member.id in active_role_timers:
        role_data = active_role_timers.get(member.id)  # Access safely using `.get()`

        if role_data:  # Check if role_data exists
            existing_task = role_data.get("task")
            if existing_task:
                existing_task.cancel()  # Cancel the old task

            # Remove the old role from the user
            existing_role_id = role_data.get("role_id")
            existing_role = guild.get_role(existing_role_id)
            if existing_role:
                try:
                    await member.remove_roles(existing_role)
                except discord.HTTPException:
                    pass

        # Remove the timer entry if it exists
        active_role_timers.pop(member.id, None)

    try:
        await member.add_roles(random_role)
        embed = discord.Embed(
            title="Role Roulette 🎲",
            description=f"{random_role.mention} has been assigned to **{member.display_name}** for **{amount}{unit}**!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        #add_modlog("Role Roulette", member.id, interaction.user.id, f"Duration: **{amount}{unit}**")

        active_role_timers[member.id] = {
            "role_id": random_role.id,
            "channel_id": interaction.channel.id,
            "task": asyncio.create_task(remove_role_after_time(interaction, member, random_role, time_in_seconds))
        }

    except discord.Forbidden:
        return await interaction.response.send_message(
            f"I can't assign that role to {member.display_name} for some reason.", ephemeral=True)

    except discord.HTTPException as e:
        return await interaction.response.send_message(f"Failed to assign the role due to: {str(e)}", ephemeral=True)

    except Exception as e:
        return await interaction.response.send_message(f"An unexpected error occurred: {str(e)}", ephemeral=True)


@tasks.loop(count=1)
async def remove_role_after_time(context, member, role, time_in_seconds):
    await asyncio.sleep(time_in_seconds - 1)

    guild = getattr(context, 'guild', None) or context.guild

    if guild.get_member(member.id) is None:
        active_role_timers.pop(member.id, None)
        return

    if member.id in active_role_timers:
        role_data = active_role_timers.get(member.id)
        task = role_data.get("task")

        if task and task == asyncio.current_task():
            active_role_timers.pop(member.id, None)

            try:
                await member.remove_roles(role)
                embed = discord.Embed(
                    title="Role Removed!",
                    description=f"**{member.display_name}'s** {role.mention} role has been removed after the specified time.",
                    color=discord.Color.blue()
                )
                if isinstance(context, discord.Interaction):
                    await context.channel.send(embed=embed)
                else:
                    await context.send(embed=embed)
            except discord.Forbidden:
                error_message = f"Couldn't remove {role.mention} from {member.mention} due to insufficient permissions."
                if isinstance(context, discord.Interaction):
                    await context.channel.send(error_message)
                else:
                    await context.send(error_message)
            except discord.HTTPException as e:
                error_message = f"Error removing the role due to: {str(e)}"
                if isinstance(context, discord.Interaction):
                    await context.channel.send(error_message)
                else:
                    await context.send(error_message)
            except Exception as e:
                error_message = f"Error removing the role due to: {str(e)}"
                if isinstance(context, discord.Interaction):
                    await context.channel.send(error_message)
                else:
                    await context.send(error_message)


@role_roulette.error
async def role_roulette_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="Role Roulette 🎲",
                                           description="Temporarily assigns a random role to a user for a set period\nTime is an optional argument.\n\n**Syntax**: `roleroulette @user(or user_ID) time`",
                                           color=discord.Color.dark_blue()))
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("User not found. Please mention a valid user or use their ID.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "I do not have the necessary permissions to use this command. Please ensure that I've Manage Roles permission before trying again.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An error occurred: {str(error)}")


def chunk_permissions_list(perms, chunk_size=10):  # 10 permissions per chunk
    chunks = []
    current_chunk = []

    for index, (perm, description) in enumerate(perms, start=1):
        entry = f"{index}. `{perm}`: {description}\n"
        current_chunk.append(entry)
        if len(current_chunk) == chunk_size:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


class PermissionListView(View):
    def __init__(self, permission_chunks):
        super().__init__(timeout=180)  # Timeout for buttons
        self.permission_chunks = permission_chunks
        self.current_page = 0

    # Updates the embed to the current page
    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"Available Permissions (Page {self.current_page + 1}/{len(self.permission_chunks)})",
            description="".join(self.permission_chunks[self.current_page]),
            color=discord.Color.gold()  # Yellow embed
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # 'Previous' Button on the left
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, row=0)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_embed(interaction)

    # 'Next' Button on the right
    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, row=0)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.permission_chunks) - 1:
            self.current_page += 1
            await self.update_embed(interaction)


@bot.command(name="showperm",
             help=f"Displays a list of all possible permissions with descriptions.\n**Syntax**: showperm")
@commands.guild_only()
async def show_perms(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "showperm"):
        await ctx.reply("You are blocked from using showperm.")
        return

    permission_chunks = chunk_permissions_list(PERMISSIONS_LIST)

    # Create the view with buttons for navigation
    view = PermissionListView(permission_chunks)

    # Send the first embed with buttons
    embed = discord.Embed(
        title=f"Available Permissions (Page 1/{len(permission_chunks)})",
        description="".join(permission_chunks[0]),
        color=discord.Color.gold()  # Yellow embed
    )
    await ctx.send(embed=embed, view=view)


@bot.command(name="setperm",
             help=f"Toggle permissions for a specified role.\n**Syntax**: setperm @role(or role_ID) permission(or permission no.)")
@commands.guild_only()
@commands.bot_has_permissions(manage_roles=True)
async def set_perm(ctx, role: str, *, perm: str):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "setperm"):
        return

    guild = ctx.guild
    member = ctx.author.id

    matched_role = discord.utils.get(ctx.guild.roles, mention=role) or (
        discord.utils.get(ctx.guild.roles, id=int(role)) if role.isdigit() else None)
    if matched_role:
        role_obj = matched_role
    else:
        role_obj, confidence = await find_closest_role(ctx, role)
        if role_obj and confidence > 60:
            pass  # role_obj is already assigned
        else:
            await ctx.send(embed=discord.Embed(
                title="Error",
                description=f"Could not find a role close to: **{role}**.",
                color=discord.Color.red()
            ))
            return

    if perm.isdigit():
        perm = PERMISSIONS_DICT.get(perm)
        if not perm:
            return await ctx.send(embed=discord.Embed(title="Error",
                                                      description="Invalid permission number. Please refer to the `showperm` command for valid numbers.",
                                                      color=discord.Color.red()))

    # Check if the permission is valid
    valid_permissions = [p[0] for p in PERMISSIONS_LIST]  # Extract permission names
    if perm not in valid_permissions:
        return await ctx.send(embed=discord.Embed(title="Error",
                                                  description="Invalid permission! Type `showperm` to check for correct permission.",
                                                  color=discord.Color.red()))

    # Get current permissions of the role
    current_permissions = role_obj.permissions

    if not hasattr(current_permissions, perm):
        return await ctx.send(f"Permission `{perm}` not found for this role.")

    current_value = getattr(current_permissions, perm)
    new_permissions = discord.Permissions(permissions=current_permissions.value)
    setattr(new_permissions, perm, not current_value)

    try:
        await role_obj.edit(permissions=new_permissions)
        toggle_status = "Enabled" if not current_value else "Disabled"
        #add_modlog("Set Perm", None, ctx.author.id, f"{toggle_status} **{perm}** for **{role_obj.name}**.")
        embed = discord.Embed(
            title="Permissions Updated",
            description=f"Successfully **{toggle_status}** `{perm}` permission for role {role_obj.mention}.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send(embed=discord.Embed(title="Error", description="I don't have permission to modify that role.",
                                           color=discord.Color.red()))
    except discord.HTTPException as e:
        await ctx.send(
            embed=discord.Embed(title="Error", description=f"Failed to update permissions due to an error: *{str(e)}*",
                                color=discord.Color.red()))
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="Error", description=f"An unexpected error occurred: *{str(e)}*",
                                           color=discord.Color.red()))


@set_perm.error
async def set_perm_error(ctx, error):
    errorMSG = []
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="Set Perm",
                                           description="Toggles a permission for a given role. Permissions might include:\n1. add reactions, 2. administrator, 4. ban_members, 5. change nickname, 10. kick members, 11. manage channels, 14. manage messages, 18. mention everyone.\nFor other permissions type `.show_perm`\n\n**Syntax**: `setperm @role(or role_ID) permission(or permission no.)`",
                                           color=discord.Color.dark_blue()))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "I do not have the necessary permissions to use this command. Please ensure that I've Manage Roles permission before trying again.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        errorMSG.append(f"An error occurred: {str(error)}")

    if errorMSG:
        embed = discord.Embed(title="Error", description="".join(errorMSG), color=discord.Color.red())
        await ctx.send(embed=embed)




@bot.command(name="role", help=f"Toggles a role for a given user or multiple users.\n**Syntax**: role @user @role")
@commands.guild_only()
@commands.bot_has_permissions(manage_roles=True)
async def role(ctx, *args):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "role"):
        return

    # Check for required arguments
    if len(args) < 2:
        await ctx.send(embed=discord.Embed(
            title="Role",
            description="Toggles a role for a given user or multiple users.\n\n**Syntax**: `role @user @role`",
            color=discord.Color.dark_blue()
        ))
        return

    # Extract the role and user IDs from arguments
    role_arg = args[-1]
    user_args = args[:-1]

    # Initialize tracking lists
    not_in_server, added_role, removed_role, hierarchy_error = [], [], [], []

    try:
        role = await commands.RoleConverter().convert(ctx, role_arg)
    except commands.BadArgument:
        role, confidence = await find_closest_role(ctx, role_arg)
        if confidence < 60:
            await ctx.send(embed=discord.Embed(title="Error",
                                               description=f"Role '{role_arg}' not found. Please mention a valid role or provide a correct role ID.",
                                               color=discord.Color.red()))
            print(f"The closest match to '{role_arg}' is '{role.name}' with {confidence:.2f}% confidence.")
            return

    if not role:
        await ctx.send(embed=discord.Embed(
            title="Error",
            description=f"Role '{role_arg}' not found. Please mention a valid role or provide a correct role ID.",
            color=discord.Color.red()
        ))
        return

    # Check bot's permissions
    if ctx.guild.me.top_role <= role:
        await ctx.send(embed=discord.Embed(
            title="Permission Error",
            description="I don't have permission to manage this role due to its hierarchy position.",
            color=discord.Color.red()
        ))
        return

    # Process each user
    for user_id in user_args:
        user_id = user_id.strip("<>@! ")
        member = ctx.guild.get_member(int(user_id))
        if not await permissions_check_decorator(ctx, member, 'role'):
            continue

        if member is None:
            not_in_server.append(user_id)
            continue
        if ctx.author.top_role <= member.top_role:
            hierarchy_error.append(f"**{member.display_name}** (ID: **{member.id}**)")
            continue

        try:
            if role in member.roles:
                await member.remove_roles(role)
                #add_modlog("Role Removed", member.id, ctx.author.id, f"Role **{role.name}** removed from **{member.display_name}**")
                removed_role.append(f"**{member.display_name}**, (ID: **{member.id})**")
            else:
                await member.add_roles(role)
                #add_modlog("Role Added", member.id, ctx.author.id, f"Role **{role.name}** added to ..{member.display_name}**.")
                added_role.append(f"**{member.display_name}**, (ID: **{member.id})**")
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title="Permission Error",
                description=f"I don't have permission to modify roles for {member.display_name}.",
                color=discord.Color.red()
            ))
            return

    # Prepare and send embeds for results
    if not_in_server:
        await ctx.send(embed=discord.Embed(
            title="Not in Server",
            description="\n".join(f"<@{uid}>" for uid in not_in_server),
            color=discord.Color.red()
        ))

    if hierarchy_error:
        await ctx.send(embed=discord.Embed(
            title="Role Hierarchy Error",
            description="Cannot add/remove the role for the following users due to role hierarchy restrictions:\n"
                        + "\n".join(hierarchy_error),
            color=discord.Color.red()
        ))

    success_embed = discord.Embed(title="Role Toggle Summary", color=discord.Color.green())
    if added_role:
        success_embed.add_field(name=f"Role Added - {role.name}", value="\n".join(added_role), inline=False)
    if removed_role:
        success_embed.add_field(name=f"Role Removed - {role.name}", value="\n".join(removed_role), inline=False)

    # Send the summary if there were any additions or removals
    if added_role or removed_role:
        await ctx.send(embed=success_embed)


@role.error
async def role_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "I do not have the necessary permissions to use this command. Please ensure that I've Manage Roles permission before trying again.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An error occurred while processing this command: {str(error)}")


#

@bot.command(name="setrole", help=f"Sets a role to your desired position in Role Hierarchy.\n**Syntax**: setrole @role position")
@commands.guild_only()
@commands.bot_has_permissions(manage_roles=True)
async def setrole(ctx, role_arg: str, position: int):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "setrole"):
        return

    try:
        role = await commands.RoleConverter().convert(ctx, role_arg)
    except commands.BadArgument:
        matched_role, confidence = await find_closest_role(ctx, role_arg)
        if matched_role and confidence > 60:
            role = matched_role
        else:
            await send_embed_with_roles(ctx, title="Error",
                                        description=f"Role '{role_arg}' not found. Please mention a valid role or provide a correct role ID.",
                                        color=discord.Color.red())
            return

    # Check if the bot has permission to manage this role
    if not ctx.guild.me.top_role > role:
        await send_embed_with_roles(ctx, title="Permission Error",
                                    description="I can't manage this role due to its hierarchy position.",
                                    color=discord.Color.red())
        return

    # Ensure the desired position is valid
    roles = ctx.guild.roles
    if position < 1 or position >= len(roles):
        await send_embed_with_roles(ctx, title="Position Error",
                                    description="Please provide a valid position within the role hierarchy.",
                                    color=discord.Color.red())
        return

    current_position = roles.index(role) + 1  # Get the 1-based index for comparison
    if current_position == position:  # No need to move if it's already in the desired position
        await send_embed_with_roles(ctx, title="No Change Needed",
                                    description=f"The role '{role.name}' is already at position {position}.",
                                    color=discord.Color.yellow())
        return

    # Attempt to reposition the role
    try:
        # Create a list of roles in their current order
        role_positions = list(roles)

        # Remove the role and insert it at the desired position
        role_positions.remove(role)  # Remove the role from the list
        role_positions.insert(position - 1, role)  # Insert at the correct position (0-based)

        # Prepare the dictionary for role positions
        position_dict = {r: idx for idx, r in enumerate(role_positions)}

        # Update the role positions
        await ctx.guild.edit_role_positions(position_dict)
        #add_modlog("Set Role", None, ctx.author.id, f"Role **{role}** set to position **{position - 1}** from **{current_position + 1}**.")

        # Find neighboring roles after the update
        sorted_roles = sorted(ctx.guild.roles, key=lambda r: r.position)
        new_position = sorted_roles.index(role)

        lower_role = sorted_roles[new_position + 1] if new_position < len(sorted_roles) - 1 else None
        higher_role = sorted_roles[new_position - 1] if new_position > 0 else None

        # Success embed with neighboring role info
        success_embed = discord.Embed(
            title="Success",
            description=f"Role **{role.name}** (ID: **{role.id}**) has been moved to position {position}.",
            color=discord.Color.green()
        )
        if higher_role:
            success_embed.add_field(name="Above Role", value=f"{higher_role.position + 1}. **{higher_role.name}**",
                                    inline=False)
        if lower_role:
            success_embed.add_field(name="Below Role", value=f"{lower_role.position + 1}. **{lower_role.name}**",
                                    inline=False)

        await send_embed_with_roles(ctx, embed=success_embed)

    except discord.Forbidden:
        await send_embed_with_roles(ctx, title="Permission Error",
                                    description="I don't have permission to change the role positions.",
                                    color=discord.Color.red())
    except Exception as e:
        await send_embed_with_roles(ctx, title="Error",
                                    description=f"An unexpected error occurred: {str(e)}",
                                    color=discord.Color.red())


async def send_embed_with_roles(ctx, title=None, description=None, color=discord.Color.default(), embed=None):
    # Generate role list in descending order
    sorted_roles = sorted(ctx.guild.roles, key=lambda r: r.position)
    role_list = "\n".join([f"{idx + 1}. **{r.name}**" for idx, r in enumerate(sorted_roles)])

    # Create the button to show roles
    show_roles_button = Button(label="Show Roles", style=discord.ButtonStyle.primary)

    # Callback to show the roles list as an ephemeral message
    async def show_roles_callback(interaction: discord.Interaction):
        if interaction.user == ctx.author:
            await interaction.response.send_message(embed=discord.Embed(
                title="Current Role Hierarchy",
                description=role_list or "No roles available.",
                color=discord.Color.blue()
            ), ephemeral=True)
        else:
            await interaction.response.send_message("Only the command initiator can use this button.", ephemeral=True)

    # Assign the callback and add the button to the view
    show_roles_button.callback = show_roles_callback
    view = View()
    view.add_item(show_roles_button)

    # Send the embed with the button
    if embed:
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=discord.Embed(
            title=title,
            description=description,
            color=color
        ), view=view)


@setrole.error
async def set_role_position_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await send_embed_with_roles(ctx, title="Set Role Position",
                                    description="Sets a role to your desired position in Role Hierarchy.\n\n**Syntax**: `setrole @role position`",
                                    color=discord.Color.dark_blue())
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(
            "I do not have the necessary permissions to use this command. Please ensure that I've Manage Roles permission before trying again.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"An error occurred while invoking the command: {error}")
    else:
        await ctx.send(f"An error occurred: {str(error)}")


@bot.command(name="whois", aliases=["w", "W", "who", "profile", "WHO", "Who"], help=f"Give you info about yourself or another user.\n**Syntax**: w @user(s) or whois @user(s)")
async def whois(ctx, *args):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "w" or "whois"):
        await ctx.reply("You are blocked from using whois (w).")
        return

    members = []

    # If no args are given, default to command author
    if not args:
        members = [ctx.author]
    else:
        for arg in args:
            try:
                if arg.isdigit():  # Check if the argument is an ID
                    member = ctx.guild.get_member(int(arg))
                else:  # Check if it's a mention
                    arg = arg.strip('<@!>')
                    member = ctx.guild.get_member(int(arg)) if arg.isdigit() else None
                if not member:
                    raise commands.BadArgument

                members.append(member)
            except commands.BadArgument:
                matched_member, confidence = await find_closest_member(ctx, arg)
                if matched_member and confidence > 70:
                    members.append(matched_member)
                else:
                    await ctx.send(f"Could not find a user matching '{arg}'.")
                    continue

    for member in members:

        roles = sorted(member.roles[1:], key=lambda role: role.position, reverse=True)
        permissions = [key_permissions[perm] for perm, value in member.guild_permissions if
                       value and perm in key_permissions]
        permissions_display = ", ".join(permissions)
        if len(permissions_display) > 1024:
            permissions_display = permissions_display[:1021] + "..."

        #boost_count = get_boost_count(str(member.id), str(ctx.guild.id))
        #banner = member.banner.url if member.banner else None
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🌙",
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚪"
        }

        if member == ctx.guild.owner:
            acknowledgement = "Server Owner"
        elif 'Administrator' in permissions or len([perm for perm in admin_perms if perm in permissions]) >= 9:
            acknowledgement = "Administrator"
        elif len([perm for perm in mod_perms if perm in permissions]) >= 3:
            acknowledgement = "Moderator"
        else:
            acknowledgement = "Normal Member"

        user_id = member.id  # Define user_id
        guild_id = ctx.guild.id  # Define guild_id

        #conn = await get_db_connection()
        async with utils.db_pool.acquire() as cursor:
            result = await cursor.fetchrow('SELECT message_count FROM message_counts WHERE user_id = $1 AND guild_id = $2', member.id, ctx.guild.id)

            message_count = result['message_count'] if result else 0
        #database = await get_masterslave_connection()
        #async with utils.db_pool.acquire() as cursor:
            slaves = await cursor.fetch("SELECT slave_id FROM ownerships WHERE master_id = $1 AND guild_id = $2", user_id, guild_id)
            master_record = await cursor.fetchrow("SELECT master_id FROM ownerships WHERE slave_id = $1 AND guild_id = $2", user_id, guild_id)

        number_of_slaves = await get_num_slaves_owned(member.id, ctx.guild.id)
        price_slave = await calculate_slave_price(ctx, user_id, guild_id)

        #kero_balance = await get_user_balance(member.id)

        # Embed setup
        embed = discord.Embed(
            title=f"📄 User Information for {member.display_name}",
            color=member.top_role.color if member.top_role else discord.Color.default()
        )
        embed.set_thumbnail(url=member.display_avatar.url)  # Server-specific avatar

        # Basic Info Section
        basic_info = (
            f"**User ID**: `{member.id}`\n"
            f"**Username**: {member.name}\n"
            # f"**Nickname**: {member.nick if member.nick else 'N/A'}\n"
            f"**Account Created**: {member.created_at.strftime('%Y-%m-%d')}\n"
            f"**Joined Server**: {member.joined_at.strftime('%Y-%m-%d')}\n"
            f"**Status**: {status_emoji.get(member.status, '⚪')} {member.status}\n"
            #f"**Highest Role**: {member.top_role.mention}\n"
            f"**Message Count**: {message_count}\n"
            f"**Worth: 🪙 {price_slave} Kero**"
        )
        embed.add_field(name="Basic Info", value=basic_info, inline=False)

        # Roles Section
        if roles:
            mentions = [role.mention for role in roles]
            display  = []
            total = len(mentions)


            for m in mentions:
                tentative = display + [m]
                remaining = total - len(tentative)
                suffix = f" | and {remaining} more" if remaining > 0 else ""
                joined = " | ".join(tentative) + suffix

                if len(joined) <= 1024:
                    display.append(m)
                else:
                    break

            remaining = total - len(display)
            roles_display = " | ".join(display)
            if remaining > 0:
                roles_display += f" | and {remaining} more"

            embed.add_field(name=f"Roles ({len(roles)})", value=roles_display, inline=False)
        else:
            embed.add_field(name="Roles (0)", value="No roles", inline=False)

        # Permissions Section
        embed.add_field(name="Key Permissions", value=permissions_display if permissions else "None", inline=False)

        embed.add_field(name="Acknowledgements", value=acknowledgement, inline=False)

        if master_record:
            master_id = master_record[0]
            master_member = ctx.guild.get_member(master_id)
            if master_member:
                embed.add_field(name="Master", value=master_member.display_name, inline=False)

        else:
            if not slaves:
                embed.add_field(name="Slaves", value="No slaves found.", inline=False)
            else:
                slave_details_combined = f"Total Number of Slaves: {number_of_slaves}\n"
                for index, (slave_id,) in enumerate(slaves, start=1):
                    slave_member = ctx.guild.get_member(slave_id)
                    if slave_member:
                        slave_details_combined += f"{index}. **{slave_member.display_name}**\n"
                    else:
                        slave_member = await bot.fetch_user(slave_id)
                        slave_details_combined += f"{index}. **{slave_member.display_name}** [Not in this Server] (ID: {slave_id})\n"

                embed.add_field(name="Slaves", value=slave_details_combined, inline=False)

        embed.set_footer(text=f"Requested on {datetime.now().strftime('%Y-%m-%d')}")

        # Send the embed
        await ctx.send(embed=embed)

    # Close the connection



MAX_PURGE_AMOUNT = 500
_MENTION_RE = re.compile(r"^<@!?(\d+)>$")

def _extract_member_id(token: str):
    m = _MENTION_RE.match(token)
    return int(m.group(1)) if m else None

def build_predicate(mode: str, member_ids: set[int] | None):
    """mode: 'all' | 'bots' | 'users'. member_ids: optional set to restrict to specific authors."""
    def predicate(message):
        if member_ids and message.author.id not in member_ids:
            return False
        if mode == "bots" and not message.author.bot:
            return False
        if mode == "users" and message.author.bot:
            return False
        return True
    return predicate

async def _purge_matching(channel, amount: int, predicate, search_multiplier: int = 5, hard_search_cap: int = 2000):
    """Deletes up to `amount` messages satisfying predicate. `limit` on channel.purge is a search
    window, not a delete count — this wrapper stops actually deleting once `amount` is hit, while
    the window itself is capped so a sparse filter can't trigger an unbounded history scan."""
    remaining = amount

    def check(message):
        nonlocal remaining
        if remaining <= 0:
            return False
        if predicate(message):
            remaining -= 1
            return True
        return False

    search_limit = min(amount * search_multiplier, hard_search_cap)
    return await channel.purge(limit=search_limit, check=check, bulk=True)

@bot.command(name="purge", help=(
    "Deletes messages in bulk.\n"
    "**Syntax**:\n"
    "  purge <amount>                       — delete last <amount> messages\n"
    "  purge bots <amount>                  — delete <amount> bot messages\n"
    "  purge users <amount>                 — delete <amount> human messages\n"
    "  purge @user [@user2 ...] <amount>    — delete <amount> messages from those member(s)"
))
@commands.guild_only()
@commands.bot_has_permissions(manage_messages=True, read_message_history=True)
async def purge(ctx, *args):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "purge"):
        return

    if not args:
        return await ctx.send(
            "Usage: `purge <amount>` / `purge bots <amount>` / `purge users <amount>` / `purge @user... <amount>`"
        )

    mode = "all"
    rest = args
    first = args[0].lower()
    if first in ("bots", "bot"):
        mode, rest = "bots", args[1:]
    elif first in ("users", "user"):
        mode, rest = "users", args[1:]

    if not rest or not rest[-1].isdigit():
        return await ctx.send("You must end the command with a valid amount, e.g. `purge @user 20`.")

    amount = int(rest[-1])
    if not (1 <= amount <= MAX_PURGE_AMOUNT):
        return await ctx.send(f"Amount must be between 1 and {MAX_PURGE_AMOUNT}.")

    member_ids = set()
    for token in rest[:-1]:
        mid = _extract_member_id(token)
        if mid is None:
            return await ctx.send(f"`{token}` isn't a valid `@mention`. Only user mentions are accepted here.")
        member_ids.add(mid)

    predicate = build_predicate(mode, member_ids or None)

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    try:
        deleted = await _purge_matching(ctx.channel, amount, predicate)
    except discord.Forbidden:
        return await ctx.send("I don't have permission to delete messages here.", delete_after=8)
    except discord.HTTPException as e:
        return await ctx.send(f"Failed to purge messages: {e}", delete_after=8)

    confirm = await ctx.send(f"🧹 Deleted **{len(deleted)}** message(s).")
    await confirm.delete(delay=5)

@purge.error
async def purge_error(ctx, error):
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I need `Manage Messages` and `Read Message History` permissions to do that.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command only works in a server.")
    else:
        await ctx.send("An error occurred while trying to purge messages.")
        print(f"Purge error: {error}")




@app_commands.command(name="purge", description="Bulk delete messages in this channel.")
@app_commands.describe(
    amount=f"Number of messages to delete (1-{MAX_PURGE_AMOUNT}).",
    filter="Optionally restrict to bot-only or human-only messages.",
    member="Optionally restrict to messages from this member only.",
)
@app_commands.choices(filter=[
    app_commands.Choice(name="All messages", value="all"),
    app_commands.Choice(name="Bot messages only", value="bots"),
    app_commands.Choice(name="Human messages only", value="users"),
])
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.checks.bot_has_permissions(manage_messages=True, read_message_history=True)
async def purge_slash(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, MAX_PURGE_AMOUNT],
    filter: app_commands.Choice[str] = None,
    member: discord.Member = None,
):
    if not await is_authorized_or_not(interaction, interaction.guild.id, interaction.user.id, "purge"):
        return

    mode = filter.value if filter else "all"
    member_ids = {member.id} if member else None
    predicate = build_predicate(mode, member_ids)

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        deleted = await _purge_matching(interaction.channel, amount, predicate)
    except discord.Forbidden:
        return await interaction.followup.send("I don't have permission to delete messages here.", ephemeral=True)
    except discord.HTTPException as e:
        return await interaction.followup.send(f"Failed to purge messages: {e}", ephemeral=True)

    await interaction.followup.send(f"🧹 Deleted **{len(deleted)}** message(s).", ephemeral=True)

@purge_slash.error
async def purge_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need `Manage Messages` permission to use this.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message("I need `Manage Messages` permission to do that.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An unexpected error occurred: {error}", ephemeral=True)

# @bot.command(name="purge", help=f"Deletes messages in bulk.\n**Syntax**: purge 20")
# @commands.bot_has_permissions(manage_messages=True)
# @commands.guild_only()
# async def purge(ctx, *args):
#     if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "purge"):
#         return

#     user_ids_set = set()

#     if not args:
#         await ctx.send("Please provide a number or specify 'user' or 'bot'.")
#         return

#     try:
#         if args[0].isdigit():
#             number_to_purge = int(args[0])
#             if number_to_purge < 1:
#                 await ctx.send("You must specify a number greater than 0.")
#                 return

#             await ctx.message.delete()
#             deleted = await ctx.channel.purge(limit=number_to_purge)
#             #add_modlog("Purged", None, ctx.author.id, f"Purged a total of **{number_to_purge}** messages.")
#             # await ctx.send(f"Purged {len(deleted)} messages.")
#             return

#         elif args[0].lower() in ["user", "bot"]:
#             if len(args) < 2 or not args[1].isdigit():
#                 await ctx.send("Please specify the number of messages to purge after 'user' or 'bot'.")
#                 return

#             number_to_purge = int(args[1])
#             if number_to_purge < 1:
#                 await ctx.send("Please specify a number greater than 0.")
#                 return
#             check = None

#             if args[0].lower() == "user":
#                 def check(message):
#                     return not message.author.bot  # Delete only user messages
#             elif args[0].lower() == "bot":
#                 def check(message):
#                     return message.author.bot  # Delete only bot messages

#             await ctx.message.delete()
#             deleted = await ctx.channel.purge(limit=number_to_purge, check=check)  # +1 to include command msg
#             deleted_count = len(deleted)

#             if deleted_count > 0 and deleted[0] == ctx.message:
#                 deleted_count -= 1

#             # await ctx.send(f"Deleted {deleted_count} {'user' if args[0].lower() == 'user' else 'bot'} messages.")
#             return



#         # Combine both user mentions and IDs into a set for checking
#         else:
#             # Combine both user mentions and IDs into a set for checking
#             if len(args) < 2:
#                 await ctx.send("Usage: `!purge @User1 @User2 [number]`")
#                 return

#             user_mentions = [arg.strip('<@!>') for arg in args if arg.startswith('<@') and arg.endswith('>')]
#             user_ids = [arg for arg in args if arg.isdigit()]
#             user_ids_set = set(user_mentions)

#             # Check if there's at least one user specified
#             if not user_ids_set or user_ids:
#                 await ctx.send("Please specify one or more user mentions.")
#                 return

#             # Check if the last argument is a number to purge
#             try:
#                 if not args[-1].isdigit():
#                     await ctx.send("Please specify a valid number greater than 0 as the last argument.")
#                     return
#                 number_to_purge = int(args[-1])  # Get the last argument as the number to purge
#                 if number_to_purge < 1:
#                     raise ValueError("Number must be greater than 0.")
#             except ValueError:
#                 await ctx.send("Please specify a valid number greater than 0.")
#                 return

#             # Ensure the number to purge is greater than 0
#             if number_to_purge < 1:
#                 await ctx.send("Please specify a number greater than 0.")
#                 return

#             # Fetch the messages first and filter them
#             deleted_messages = []
#             async for message in ctx.channel.history(limit=500):  # Fetch messages first
#                 if str(message.author.id) in user_ids_set:
#                     deleted_messages.append(message)

#             # Now delete messages, limited to the count specified
#             deleted_count = min(len(deleted_messages), number_to_purge)  # Limit the number to delete
#             if deleted_count > 0:
#                 await ctx.message.delete()
#                 await ctx.channel.purge(limit=number_to_purge, check=lambda m: str(
#                     m.author.id) in user_ids_set)  # Delete only the required messages
#             # await ctx.send(f"Deleted {deleted_count} message(s) from specified user(s).")
#             else:
#                 await ctx.send("No messages found from the specified user(s) in the last few messages.")


#     except Exception as e:
#         await ctx.send("An error occurred while trying to purge messages.")
#         print(f"Error: {e}")


async def fetch_logs(moderator_id, page, limit=5):
    offset = page * limit
    connman = sqlite3.connect("modlogs.db")
    cursor = connman.cursor()

    query = (
        "SELECT action, timestamp, user_id, details FROM logs WHERE moderator_id = ? "
        "ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    )
    cursor.execute(query, (moderator_id, limit, offset))

    logs = cursor.fetchall()
    connman.close()

    return logs


async def create_embed(logs, member, page):
    embed = discord.Embed(title=f"Actions by {member.display_name}", color=discord.Color.blurple())
    if not logs:
        embed.description = "No logs found."
    else:
        for action, timestamp, user_id, details in logs:
            if isinstance(timestamp, str):
                try:
                    # If it's a string, assume it's already formatted as 'YYYY-MM-DD' or similar.
                    formatted_date = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                except ValueError:
                    print(f"Unexpected timestamp format: {timestamp}")
                    continue
            elif isinstance(timestamp, (int, float)):
                formatted_date = datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d')
            embed.add_field(
                name=f"{action} - {formatted_date}",
                value=f"Affected User: <@{user_id}> - {details}",
                inline=False
            )
    embed.set_footer(text=f"Page {page + 1}")
    return embed


@bot.command(name="modlogs",
             help=f"Gives the list of moderation actions done by a Moderator or an Admin using this bot.\n**Syntax**: modlogs")
async def modlogs(ctx, member: discord.Member = None):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "modlogs"):
        return

    page = 0

    if member is None:
        member = ctx.author  # Use the command invoker's ID to fetch their own logs

    logs = await fetch_logs(member.id, page)  # Fetch logs for the current user who invoked the command
    embed = await create_embed(logs, member, page)

    # Define the button view with pagination controls
    view = View()
    next_button = Button(label="Next", style=discord.ButtonStyle.primary)
    previous_button = Button(label="Previous", style=discord.ButtonStyle.primary)

    async def next_callback(interaction):
        nonlocal page
        page += 1
        logs = await fetch_logs(ctx.author.id, page)  # Fetch logs for the current user who invoked the command
        if not logs:  # Stop increasing pages if no more logs
            page -= 1
            return
        new_embed = await create_embed(logs, member, page)
        await interaction.response.edit_message(embed=new_embed, view=view)

    async def previous_callback(interaction):
        nonlocal page
        if page > 0:
            page -= 1
            logs = await fetch_logs(ctx.author.id, page)  # Fetch logs for the current user who invoked the command
            new_embed = await create_embed(logs, member, page)
            await interaction.response.edit_message(embed=new_embed, view=view)

    next_button.callback = next_callback
    previous_button.callback = previous_callback

    view.add_item(previous_button)
    view.add_item(next_button)
    await ctx.send(embed=embed, view=view)


# --------------------------- LINE SEPARATES FROM MODERATION COMMANDS TO SLAVE COMMANDS ----------------------------------------------

@bot.command(name="getmem")
async def get_memberr(ctx, target:discord.Member = None):
    member = ctx.guild.get_member(target.id)
    await ctx.reply(f"{member.display_name} is in this server.")
    if member is None:
        try:
            member = await bot.fetch_user(target.id)
            await ctx.reply(f"{member.display_name} is not in this server.")
        except discord.NotFound:
            return None


@bot.command(name="debug")
async def debug_list_slaves(ctx):
    guild_id_int   = ctx.guild.id           # int, for ownerships.guild_id (BIGINT)
    guild_id_float = float(ctx.guild.id)
    try:
        #database = await get_masterslave_connection()
        rows = await utils.db_pool.fetch("""SELECT u.user_id, u.balance, u.joined_at FROM users u LEFT JOIN ownerships o ON u.user_id = o.slave_id AND o.guild_id = $1::bigint WHERE u.guild_id = $1::bigint AND o.slave_id IS NULL """, guild_id_int)

        semaphore = asyncio.Semaphore(10)
        results   = []

        async def process_user(row):
            async with semaphore:
                uid = int(row["user_id"])
                # Resolve member
                member = ctx.guild.get_member(uid)
                if member is None:
                    try:
                        member = await ctx.guild.fetch_member(uid)
                    except discord.NotFound:
                        return None

                # Calculate the price
                price = await calculate_slave_price(ctx, uid, guild_id_int)
                return member.display_name, price

        # 2) Process each row sequentially (avoids giant gather)
        for row in rows:
            res = await process_user(row)
            if res:
                results.append(res)

        # 3) Sort and send top 50
        results.sort(key=lambda x: x[1], reverse=True)
        debug_lines = [f"{name}: {price} Keros" for name, price in results[:50]]
        await ctx.send("```\n" + "\n".join(debug_lines) + "\n```")
    
    except Exception as e:
        print(f"Error in debug_list_slaves command: {e}")
        await ctx.send("An error occurred while generating the slave price list.")





@bot.command(name='shop',
             help=f"An interactive shop that will give bring you various items you can buy with 💷 Kero.\n**Syntax**: shop [asc|desc]")
async def shop(ctx, order: str = "desc"):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "shop"):
        await ctx.reply("You are blocked from using `shop` command.")
        return
    #guild = ctx.guild
    top_slaves = await get_top_slaves(ctx, ctx.guild.id, order)
    #print(f"Top slaves fetched: {top_slaves}")  # Debug

    non_bot_slaves = [slave for slave in top_slaves if not ctx.guild.get_member(slave[0]).bot]
    print(f"Non-bot slaves available: {non_bot_slaves}")

    if not non_bot_slaves:
        embed = discord.Embed(title="🌟 **The Grand Slave Market** 🌟",
                              description="No slaves are currently available for purchase. Please check back later!",
                              color=discord.Color.gold())
        await ctx.send(embed=embed)
        return

    per_page = 5
    total_pages = (len(non_bot_slaves) - 1) // per_page + 1
    view = ShopPaginationView(ctx, non_bot_slaves, per_page, total_pages)

    embed = await view.create_embed()
    view.message = await ctx.send(embed=embed, view=view)


@bot.command(name='buycmd', help="Buy specific commands for your slave with this command using 💷 Kero.\n**Syntax**: buycmd @user <command>")
async def buy_command(ctx, slave: discord.Member, command_name: str):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "buycmd"):
        await ctx.reply("You are blocked from using `buycmd`.")
        return

    master_id = ctx.author.id
    slave_id = slave.id
    guild_id = ctx.guild.id

    if await is_slave(master_id, guild_id):
        await ctx.reply("You are a slave, you cannot use that command.")
        return

    async with utils.db_pool.acquire() as conn:
        exists = await conn.fetchval("""SELECT 1 FROM ownerships WHERE master_id = $1 AND slave_id  = $2 AND guild_id  = $3 """, master_id, slave_id, guild_id)

        if not exists:
            await ctx.send("You are not the master of this slave.")
            return

    available_commands = await get_unpurchased_commands(ctx, slave_id, master_id, guild_id)
    if command_name not in available_commands:
        await ctx.send(f"The command `{command_name}` is either invalid or already purchased.")
        return

    command_cost = available_commands[command_name]
    user_balance = await get_user_balance(ctx.author.id)

    if user_balance < command_cost:
        await ctx.send("You do not have enough Kero to purchase this command.")
        return

    await update_user_balance(ctx.author.id, -command_cost)
    await purchase_command_for_slave(ctx, master_id, slave_id, command_name)
    await add_transaction(master_id, slave_id, -command_cost, "buycmd", ctx.guild.id)

    await ctx.reply(f"Command `{command_name}` successfully purchased for {slave.display_name}.")


@bot.command(name='chkprice', aliases=['chk', 'chkeckprice', 'Chk'], help=f"Check the worth of any potential user that can be bought as salve using 💷 Kero (even yourself).\n**Syntax**: chkprice @user")
async def check_price(ctx, member: discord.Member = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "chkprice"):
        await ctx.reply("You are blocked from using `chkprice`.")
        return

    if member is None:
        member = ctx.author

    # Calculate the slave price asynchronously
    price = await calculate_slave_price(ctx, member.id, ctx.guild.id)

    if member == ctx.author:
        await ctx.reply(f"Your worth as a potential slave is **🪙 {price} Kero**")
    else:
        await ctx.reply(f"The price of **{member.display_name}** is **🪙 {price} Kero**")


@bot.command(name='wallet', aliases=['wl', 'Wl'], help=f"Amount of 💷 Kero in your account. Can also view the wallet of your slave if you have one.\n**Syntax**: wallet")
async def balance(ctx, member: discord.Member = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "wallet"):
        await ctx.reply("You are blocked from using `wallet`.")
        return

    if member and member.id != ctx.author.id:
        await ctx.reply("🚫 You can only view your own wallet.", ephemeral=True)
        return
    
    target = ctx.author

    balance = await get_user_balance(target.id)
    await ctx.reply(f"**{target.display_name}** has a balance of **💷 {round(balance)} Kero**.")




@bot.command(name='balance')
@commands.is_owner()
async def admin_only_balance(ctx, member: discord.Member = None):
    if member:
        target = member
    else:
        target = ctx.author

    balance = await get_user_balance(target.id)
    await ctx.reply(f"**{target.display_name}** has a balance of **💷 {round(balance)} Kero**.")




PERMISSIONS_LIST = [
        ("add_reactions", "Allows the user to add reactions to messages."),
        ("administrator", "Grants all permissions."),
        ("attach_files", "Allows the user to attach files."),
        ("ban_members", "Allows the user to ban members from the server."),
        ("change_nickname", "Allows the user to change their own nickname."),
        ("connect", "Allows the user to connect to voice channels."),
        ("create_instant_invite", "Allows the user to create instant invites."),
        ("deafen_members", "Allows the user to deafen members in voice channels."),
        ("embed_links", "Allows the user to embed links."),
        ("kick_members", "Allows the user to kick members from the server."),
        ("manage_channels", "Allows the user to manage and create channels."),
        ("manage_emojis", "Allows the user to manage emojis."),
        ("manage_guild", "Allows the user to manage server settings."),
        ("manage_messages", "Allows the user to delete messages of others."),
        ("manage_nicknames", "Allows the user to manage nicknames of others."),
        ("manage_roles", "Allows the user to manage and assign roles."),
        ("manage_webhooks", "Allows the user to manage webhooks."),
        ("mention_everyone", "Allows the user to mention @everyone and @here."),
        ("move_members", "Allows the user to move members between voice channels."),
        ("read_message_history", "Allows the user to read message history."),
        ("read_messages", "Allows the user to read messages in channels."),
        ("send_messages", "Allows the user to send messages in channels."),
        ("send_tts_messages", "Allows the user to send text-to-speech messages."),
        ("speak", "Allows the user to speak in voice channels."),
        ("stream", "Allows the user to stream in voice channels."),
        ("use_external_emojis", "Allows the user to use emojis from other servers."),
        ("use_voice_activation", "Allows the user to use voice activity detection."),
        ("view_audit_log", "Allows the user to view the audit log."),
        ("view_channel", "Allows the user to view a channel."),
        ("priority_speaker", "Allows the user to speak over others in voice channels."),
        ("mute_members", "Allows the user to mute members in voice channels."),
        ("request_to_speak", "Allows the user to request to speak in voice channels."),
        ("send_messages_in_threads", "Allows the user to send messages in threads."),
        ("start_embedded_activities", "Allows the user to start activities in voice channels."),
        ("use_application_commands", "Allows the user to use application commands."),
        ("manage_threads", "Allows the user to manage threads."),
        ("create_public_threads", "Allows the user to create public threads."),
        ("create_private_threads", "Allows the user to create private threads."),
        ("set_nickname", "Allows the user to set the nicknames of members."),
        ("moderate_members", "Allows the user to moderate members in the server.")
    ]

previous = {}

@bot.command(name="sljail", help=f"A slave command that lets you jail your slave.\n**Syntax**: sljail @user")
async def jail(ctx, slave: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "sljail"):
        await ctx.reply("You are blocked from using `sljail`.")
        return
    master_id = ctx.author.id
    slave_id = slave.id

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return

    if await is_slave(master_id, ctx.guild.id):
        await ctx.reply("You are a slave, you cannot use that command.")
        return

    # Check if master has permission to jail the slave
    if not await has_permission_for_slave(ctx, master_id, slave_id, "Jail"):
        await ctx.send("You don't have the authority to jail this slave.")
        return

    if slave_id in jailed_users_data:
        await ctx.send(f"{slave.display_name} is already jailed.")
        return

    guild = ctx.guild
    
    tasks = []

    REVOKE = ["send_messages", "add_reactions", "create_public_threads", "create_private_threads", "send_messages_in_threads",
        "embed_links", "attach_files", "use_external_emojis", "use_application_commands", "create_instant_invite",
        "send_tts_messages", "change_nickname" ]  

    for ch in guild.text_channels:
        before = ch.overwrites_for(slave)
        if not ch.permissions_for(slave).send_messages:
            continue
        ow = before.copy()
        for p in REVOKE:
            setattr(ow, p, False)
        if ow != before:
            previous[ch.id] = before
            tasks.append(ch.set_permissions(slave, overwrite=ow))

    for ch in guild.voice_channels:
        before = ch.overwrites_for(slave)
        if not ch.permissions_for(slave).connect:
            continue
        ow = before.copy()
        ow.connect = False
        if ow != before:
            previous[ch.id] = before
            tasks.append(ch.set_permissions(slave, overwrite=ow))

    if tasks:
        await asyncio.gather(*tasks)

    jailed_users_data[slave_id] = {
        "jailed_by": master_id,
        "overwrites": previous
    }

    await ctx.send(f"{slave.mention} has been jailed by {ctx.author.mention}.")


@bot.command(name="slunjail", help=f"A slave command that lets you unjail your slave.\n**Syntax**: slunjail @user")
async def unjail(ctx, slave: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slunjail"):
        await ctx.reply("You are blocked from using `slunjail`.")
        return

    master_id = ctx.author.id
    slave_id = slave.id

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return

    if await is_slave(master_id, ctx.guild.id):
        await ctx.reply("You are a slave, you cannot use that command.")
        return

    if not await has_permission_for_slave(ctx, master_id, slave_id, "Unjail"):
        await ctx.send("You don't have the authority to unjail this slave.")
        return

    data = jailed_users_data.get(slave.id)
    if not data:
        await ctx.send(f"{slave.display_name} is not currently jailed.")
        return
    
    old_overwrites = data.get("overwrites", {})

    tasks = []

    for chan_id, before in old_overwrites.items():
        ch = ctx.guild.get_channel(chan_id)
        if ch:
            tasks.append(ch.set_permissions(slave, overwrite=before))

    if tasks:
        await asyncio.gather(*tasks)

    jailed_users_data.pop(slave_id, None)

    await ctx.send(
        f"{slave.mention} has been unjailed by {ctx.author.mention}. They have access to text and voice channels again.")


@bot.command(name="slmute", aliases=['Slmute'], help=f"A slave command that lets you mute your slave.\n**Syntax**: slmute @user")
async def timeout(ctx, slave: discord.Member, duration: str, reason: str = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slmute"):
        await ctx.reply("You are blocked from using `slmute`.")
        return

    master_id = ctx.author.id
    slave_id = slave.id

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return

    if await is_slave(master_id, ctx.guild.id):
        await ctx.reply("You are a slave, you cannot use that command.")
        return

    if not await has_permission_for_slave(ctx, master_id, slave_id, "Mute"):
        await ctx.send("You don't have the authority to mute this slave.")
        return

    # Convert duration to seconds
    seconds = parse_duration(duration)
    if seconds is None:
        await ctx.send("Invalid duration format. Use '5m', '3h', etc.")
        return

    if not slave.is_timed_out():
        await slave.timeout(discord.utils.utcnow() + timedelta(seconds=seconds), reason=reason)
        await ctx.send(f"{slave.display_name} has been timed out for {duration} by it's owner.")
    else:
        await ctx.reply("This user is already timed out.")


def parse_duration(duration):
    match = re.match(r"(\d+)([smhd])", duration)
    if not match:
        return None

    amount, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return amount
    elif unit == "m":
        return amount * 60
    elif unit == "h":
        return amount * 3600
    elif unit == "d":
        return amount * 86400


@bot.command(name="slunmute", aliases=['Slunmute'], help=f"A slave command that lets you unmute your slave.\n**Syntax**: slunmute @user")
async def unmute(ctx, member: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slunmute"):
        await ctx.reply("You are blocked from using `slunmute`.")
        return

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return

    # Check if the member is a slave of the master
    if not await is_slave(member.id, ctx.guild.id):
        await ctx.send("This user is not your slave.")
        return

    if not await has_permission_for_slave(ctx, ctx.author.id, member.id, "Unmute"):
        await ctx.send("You don't have the authority to unmute this slave.")
        return

    try:
        if member.is_timed_out():
            await member.edit(timed_out_until=None)
            await ctx.send(f"**{member.display_name}** has been unmuted.")
        else:
            await ctx.send(f"**{member.display_name}** is not currently muted.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to unmute this user.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred: {e}")


@bot.command(name="slkick", aliases=['Slkick'], help=f"A slave command that lets you kick your slave out of the server.\n**Syntax**: slkick @user")
async def kick(ctx, slave: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slkick"):
        await ctx.reply("You are blocked from using `slkick`.")
        return

    master_id = ctx.author.id
    slave_id = slave.id

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return

    if await is_slave(master_id, ctx.guild.id):
        await ctx.reply("You are a slave, you cannot use that command.")
        return

    if not await has_permission_for_slave(ctx, master_id, slave_id, "Kick"):
        await ctx.send("You don't have the authority to kick this slave.")
        return

    await slave.kick()
    await ctx.send(f"{slave.mention} has been kicked by {ctx.author.mention}.")


@bot.command(name="slsetnick", alises=['Slsetnick'], help=f"A slave command that lets you change nickname for your slave.\n**Syntax**: slsetnick @user")
async def setnickname(ctx, user_arg: str = None, *, nickname: str):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slsetnick"):
        await ctx.reply("You are blocked from using `slsetnick`.")
        return

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return
    member = None
    if user_arg.isdigit():
        member = ctx.guild.get_member(int(user_arg)) or await bot.fetch_user(int(user_arg))
    elif user_arg.startswith('<@') and user_arg.endswith('>'):
        user_id = int(user_arg.strip('<@!>'))
        member = ctx.guild.get_member(user_id) or await bot.fetch_user(user_id)
    else:
        closest_member, confidence = await find_closest_member(ctx, user_arg)
        if closest_member and confidence > 60:
            member = closest_member

    if not member or not isinstance(member, discord.Member):
        return await ctx.send(embed=discord.Embed(
            title="User Not Found",
            description=f"Unable to resolve the user: `{user_arg}`. Please provide a valid mention, ID, or name.",
            color=discord.Color.red()
        ))

    if not await is_slave(member.id, ctx.guild.id):
        await ctx.send("This user is not your slave.")
        return

    if not await has_permission_for_slave(ctx, ctx.author.id, member.id, "Setnick"):
        await ctx.send("You don't have the authority to change the nickname of this slave.")
        return

    await member.edit(nick=nickname)
    await ctx.send(f"Nickname for {member.name} has been set to {nickname}.")


@bot.command(name='slrole', aliases=['Slrole'], help=f"A slave command that lets you change roles for your slave.\n**Syntax**: slrole @user")
async def toggle_role(ctx, member: discord.Member, role_name: str):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slrole"):
        await ctx.reply("You are blocked from using `slrole`.")
        return

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return

    if not await is_slave(member.id, ctx.guild.id):
        await ctx.send("This user is not your slave.")
        return

    if not await has_permission_for_slave(ctx, ctx.author.id, member.id, "Role"):
        await ctx.send("You don't have the authority to use role command on this slave.")
        return

    try:
        role = await commands.RoleConverter().convert(ctx, role_name)
    except commands.BadArgument:
        role, confidence = await find_closest_role(ctx, role_name)
        if confidence < 60:
            await ctx.send(embed=discord.Embed(title="Error", description=f"Role '{role_name}' not found. Please mention a valid role or provide a correct role ID.", color=discord.Color.red()))
            print(f"The closest match to '{role_name}' is '{role.name}' with {confidence:.2f}% confidence.")
            return

    if not ctx.guild.me.top_role > role:
        await ctx.send("I don't have permission to manage this role due to its hierarchy position.")
        return

    # Check if the slave already has the role
    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"**{role.name}** role has been removed from {member.display_name}.")
    else:
        await member.add_roles(role)
        await ctx.send(f"**{role.name}** role has been assigned to {member.display_name}.")


@bot.command(name="slwhip", help=f"A slave command that lets you whip your slave.\n**Syntax**: slwhip @user")
async def whip(ctx, member: discord.Member = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slwhip"):
        await ctx.reply("You are blocked from using `slwhip`.")
        return

    if await is_slave(ctx.author.id, ctx.guild.id):
        is_master = await get_master_of_slave(ctx, ctx.author.id, ctx.guild.id)
        await ctx.reply(
            f"Keep yourself in yo lines faggot. Bro {is_master.mention} this slave of yours is crossing it's line. Whip him hard!!")
        return

    if not await is_slave(member.id, ctx.guild.id):
        await ctx.reply("That guy's not your slave bro.")
        return

    master = await get_master_of_slave(ctx, member.id, ctx.guild.id)
    if master.id != ctx.author.id:
        await ctx.reply("You're not that slave's master bro.")
        return

    if not member:
        await ctx.reply("🔥 Whips your slave and helps you keep that 'thing' in it's line.")
        return

    if not await has_permission_for_slave(ctx, ctx.author.id, member.id, "Whip"):
        await ctx.send("You don't have the authority to whip this slave. Buy it from the shop.")
        return

    whip_folder = "./whip"  # Replace with the actual path to your folder

    # Get a list of all files in the folder
    gif_files = [f for f in os.listdir(whip_folder) if f.endswith(('.gif', '.webp', '.jpg', '.png'))]

    if not gif_files:
        await ctx.reply("❌ No GIFs found in the whip folder!")
        return

    chosen_gif = random.choice(gif_files)
    gif_path = os.path.join(whip_folder, chosen_gif)

    lines = [
        f"😈 {member.mention}, you're being whipped Faggot! {ctx.author.mention} brought the pain!",
        f"🔥 {member.mention}, feel the sting of {ctx.author.mention}'s wrath!",
        f"💥 {member.mention}, you've been disciplined by {ctx.author.mention}! Ouch!",
        f"😏 {ctx.author.mention} just reminded {member.mention} who's in charge. Stay in line next time faggot!",
        f"😂 {member.mention}, that's what you get for stepping out of line! Thanks, {ctx.author.mention}!",
        f"🤡 {member.mention}, you should’ve thought twice before messing with {ctx.author.mention}!",
        f"🫡 Respect, {ctx.author.mention}! That whip landed perfectly on {member.mention}'s butt!",
        f"👀 Oof, {member.mention}! {ctx.author.mention} didn't hold back!",
        f"😬 {member.mention}, that whip from {ctx.author.mention} was personal!",
        f"💀 RIP, {member.mention}'s pride. Courtesy of {ctx.author.mention}'s whip."
    ]

    descriptions = [
        f"**{ctx.author.mention} reminds {member.mention} who's boss with a savage whip!**",
        f"**{member.mention}, consider this a lesson from {ctx.author.mention}!**",
        f"**{ctx.author.mention} unleashes a brutal whip on {member.mention}!**",
        f"**{ctx.author.mention} didn't hold back this time, Good job bro. {member.mention}, now suck his dick if you don't want the same thing to happen again.**"
    ]

    # Pick a random line
    titles = random.choice(lines)
    descript = random.choice(descriptions)

    # Create an embed
    embed = discord.Embed(title="", description=descript, color=discord.Color.random())
    embed.set_image(url=f"attachment://{chosen_gif}")
    await ctx.send(titles, embed=embed, file=discord.File(gif_path))


@bot.command(name='give', help=f"Give some Kero to another user.\n**Syntax**: give @user amount")
async def give(ctx, member: discord.Member, amount: int):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "give"):
        await ctx.reply("You are blocked from using `give`.")
        return
    sender_id, receiver_id = ctx.author.id, member.id
    guild_id = ctx.guild.id  # Fetch guild_id for guild-specific functionality

    if await is_slave(sender_id, guild_id):
        await ctx.send("Slaves are not allowed to give Kero to anyone.")
        return
    if await is_slave(receiver_id, guild_id):
        await ctx.send("You cannot give Kero to a slave.")
        return

    if amount <= 0:
        await ctx.send("The amount must be greater than zero.")
        return

    sender_balance = await get_user_balance(sender_id)
    if sender_balance < amount:
        await ctx.send("You don't have enough Kero to complete this transaction.")
        return

    await update_user_balance(ctx.author.id, -amount)
    await update_user_balance(member.id, amount)
    await add_transaction(ctx.author.id, member.id, amount, "give", ctx.guild.id)

    await ctx.send(f"{ctx.author.mention} has given {amount} Kero to {member.mention}!")


@bot.command(name='tip', help=f"Allows a master to tip their slave some Kero.\n**Syntax**: tip @slave amount")
async def tip(ctx, member: discord.Member, amount: int):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "tip"):
        await ctx.reply("You are blocked from using `tip`.")
        return
    giver_id, receiver_id = ctx.author.id, member.id
    guild_id = ctx.guild.id

    if not await is_master(giver_id, guild_id):
        await ctx.reply("Only masters can use the tip command.")
        return

    if not await is_slave(receiver_id, guild_id):
        await ctx.reply(f"{member.display_name} is not a slave.")
        return

    master_of_slave = await get_master_of_slave(ctx, receiver_id, guild_id)
    if not master_of_slave or master_of_slave.id != giver_id:
        await ctx.reply(f"{member.display_name} is not your slave.")
        return

    if amount <= 0:
        await ctx.reply("The tip amount must be greater than zero.")
        return

    giver_balance = await get_user_balance(giver_id)
    if giver_balance < amount:
        await ctx.reply("You don't have enough Kero to tip that amount.")
        return

    await update_user_balance(giver_id, -amount)
    await update_user_balance(receiver_id, amount)
    await add_transaction(giver_id, receiver_id, amount, "tip", guild_id)

    await ctx.reply(f"You tipped **{amount} Kero** to your slave {member.display_name}!")


@bot.command(name='tribute', help=f"Allows a slave to pay tribute to their master.\n**Syntax**: tribute amount")
async def tribute(ctx, amount: int):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "tribute"):
        await ctx.reply("You are blocked from using `tribute`.")
        return
    sender_id = ctx.author.id
    guild_id = ctx.guild.id

    if not await is_slave(sender_id, guild_id):
        await ctx.send("Only slaves can pay tribute to their master.")
        return

    master = await get_master_of_slave(ctx, sender_id, guild_id)
    if not master:
        await ctx.send("You don't have a master to pay tribute to.")
        return

    if amount <= 0:
        await ctx.send("The tribute amount must be greater than zero.")
        return

    master_id = master.id

    sender_balance = await get_user_balance(sender_id)
    if sender_balance < amount:
        await ctx.send("You don't have enough Kero to pay that amount as tribute.")
        return

    await update_user_balance(sender_id, -amount)
    await update_user_balance(master_id, amount)
    await add_transaction(sender_id, master_id, amount, "tribute", guild_id)

    await ctx.send(f"You have paid a tribute of **{amount} Kero** to your master {master.display_name}!")


@bot.command(name='beg', help=f"Lets you beg for some 💷 Kero to any user.\n**Syntax**: beg @user")
async def beg(ctx, member: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "beg"):
        await ctx.reply("You are blocked from using `beg`.")
        return
    global operation_active
    operation_active = True

    sender_id, receiver_id = ctx.author.id, member.id
    guild_id = ctx.guild.id  # Fetch guild_id for guild-specific functionality

    if sender_id == receiver_id:
        await ctx.reply("You can't beg yourself for Kero!")
        return
    if receiver_id in active_begging_requests:
        await ctx.reply(f"{member.display_name} is already handling a begging request. Please wait until they're done.")
        return

    active_begging_requests[receiver_id] = sender_id
    await ctx.send(
        f"{member.mention}, {ctx.author.mention} is begging you for Kero. Type `Accept` to give them some Kero, or `Reject` to deny.")

    def check(message):
        return message.author.id == receiver_id and message.content.lower() in ["accept", "reject"]

    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
        if not operation_active:
            await ctx.send("Operation halted by stop command.")
            return
        if msg.content.lower() == "accept":
            try:
                amount = random.randint(50,150)

                receiver_balance = await get_user_balance(receiver_id)
                if receiver_balance < amount:
                    amount = receiver_balance
                if receiver_balance <= 0:  # Pass guild_id to check balance
                    await ctx.send(f"{member.display_name} doesn't have enough Kero to give.")
                else:
                    await update_user_balance(receiver_id, -amount)
                    ab = amount
                    if await is_slave(sender_id, ctx.guild.id):
                        master = await get_master_of_slave(ctx, sender_id, ctx.guild.id)
                        master_share = int(amount * 0.2)
                        ab = amount - master_share

                        await update_user_balance(master.id, master_share)
                        await add_transaction(sender_id, master.id, master_share, "beg (slave money)", guild_id)
                        await ctx.reply(
                            f"💸 Since you are a slave, 20% ({master_share} Kero) of your received Kero has been transferred to your master **{master.display_name}**.")

                    await update_user_balance(sender_id, ab)
                    await add_transaction(sender_id, receiver_id, amount, "beg", guild_id)
                    await ctx.send(
                        f"{ctx.author.mention} you got **{amount} Kero** from {member.display_name}!!\nKeep some pocket change on yourself faggot, got nothing else to do beside begging?")
            except Exception as e:
                await ctx.send("An error occurred during the transaction. Please try again later.")
                print(e)
        else:
            await ctx.send(
                f"{ctx.author.mention}, your begging request was rejected.\nNow fuck off and clean some dirty poops, atleast you'll get paid that way faggot!")
    except asyncio.TimeoutError:
        await ctx.send("The request timed out. Try begging again later.")
    finally:
        active_begging_requests.pop(receiver_id, None)


@bot.command(name='daily', help=f"Gives a small amount of 💷 Kero every day. Refreshes every 12 hours.\n**Syntax**: daily")
@commands.cooldown(rate=1, per=24*3600, type=commands.BucketType.user)
async def daily(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "daily"):
        await ctx.reply("You are blocked from using `daily`.")
        return
    try:
        user_id = ctx.author.id

        amount = random.randint(50, 150)
        winner_share = amount
        if await is_slave(user_id, ctx.guild.id):
            master = await get_master_of_slave(ctx, user_id, ctx.guild.id)

            master_share = int(amount * 0.2)
            winner_share = amount - master_share

            await update_user_balance(master.id, master_share)
            await add_transaction(None, master.id, master_share, "daily (slave money)", ctx.guild.id)

            await ctx.send(
                    f"💸 Since you are a slave, 20% ({master_share} Kero) of your daily reward has been transferred to your master **{master.display_name}**.")

        await update_user_balance(user_id, winner_share)
        await add_transaction(None, ctx.author.id, winner_share, "daily", ctx.guild.id)

        await ctx.reply(
                f"**{ctx.author.display_name}**, you have received your daily reward of **💷 {winner_share} Kero**!.\n"f"Come back in 12 hours for your next daily reward.")

    except Exception as e:
        traceback.print_exc()
        await ctx.send(f"⚠️ Something went wrong in `daily`: `{e.__class__.__name__}: {e}`")
        await ctx.send("An error occurred. Please try again later.")
        print(e)

@daily.error
async def daily_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        await ctx.reply(f"🕒 Try again in {hours}h {minutes}m.")
    else:
        raise error




@bot.command(name='slbuy', help=f"Buy slaves from shop using 💷 Kero.\n**Syntax**: slbuy @user")
async def buy(ctx, member: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slbuy"):
        await ctx.reply("You are blocked from using `slbuy`.")
        return

    buyer_id, slave_id = ctx.author.id, member.id
    guild_id = ctx.guild.id
    if buyer_id == slave_id:
        await ctx.reply("You cannot buy yourself as a slave!")
        return

    if await is_slave(slave_id, guild_id):
        master = await get_master_of_slave(ctx, slave_id, guild_id)
        await ctx.reply(
            f"This user is already owned by someone in this guild and cannot be bought again. His Master is {master.display_name}.")
        return

    if await is_slave(buyer_id, guild_id):
        master2 = await get_master_of_slave(ctx, buyer_id, guild_id)
        await ctx.reply(
            f"Faggot, stay in your lines. Don't try to buy another slave!!\nYo {master2.mention} keep your slave in his lines. He is crossing boundaries.")
        return

    buyer_balance = await get_user_balance(buyer_id)
    price = await calculate_slave_price(ctx, slave_id, ctx.guild.id)

    # Ensure buyer has enough Kero
    if buyer_balance < price:
        await ctx.send("You don't have enough Kero to buy this slave.")
        return

    # Deduct Kero and add slave ownership to the database

    
    async with utils.db_pool.acquire() as cursor:
        owned = await cursor.fetch("SELECT slave_id FROM ownerships WHERE master_id = $1 AND guild_id = $2", buyer_id, guild_id)

        # Deduct Kero and update ownership
        await update_user_balance(buyer_id, -price)
        await cursor.execute(""" INSERT INTO ownerships (master_id, slave_id, purchase_price, guild_id, master_guild_id, slave_guild_id) VALUES ($1, $2, $3, $4, $4, $4) """, buyer_id, slave_id, price, guild_id)
        if owned:
            params = [(r["slave_id"], guild_id) for r in owned]
            await cursor.executemany( "DELETE FROM ownerships WHERE slave_id = $1 AND guild_id = $2", params)
            await cursor.executemany("DELETE FROM purchased_slave_commands WHERE slave_id = $1 AND guild_id = $2", params)

    await add_transaction(buyer_id, slave_id, price, "slbuy", guild_id)

    freed_slaves_msg = ""
    if owned:
        freed_slaves_msg = f"\n\n{member.display_name} was a master with slaves. All their slaves have been freed and their permissions revoked!"
    await ctx.send(f"{ctx.author.mention} has successfully bought {member.mention} as a slave for **{price} Kero!**" + freed_slaves_msg)


@bot.command(name='iw')
@commands.is_owner()
async def increase_wallet(ctx, amount: int = 0, member: discord.Member = None):
    target_id = member.id if member else ctx.author.id
    await update_user_balance(target_id, amount)
    await ctx.send(f"Added **{amount} Kero** to {'your' if not member else member.display_name}'s wallet.")


@bot.command(name='dw')
@commands.is_owner()
async def decrease_wallet(ctx, amount: int = 0, member: discord.Member = None):
    target_id = member.id if member else ctx.author.id
    await update_user_balance(target_id, -amount)
    await ctx.send(f"Deducted **{amount} Kero** from {'your' if not member else member.display_name}'s wallet.")


@bot.command(name='slshow', aliases=['Slshow'], help=f"Show how many slaves you have, if any.\n**Syntax**: slshow")
async def showsl(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slshow"):
        await ctx.reply("You are blocked from using `slshow`.")
        return
    user = ctx.author  # Default to the author if no member is provided
    user_id = user.id
    guild_id = ctx.guild.id

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return

    if await is_slave(user_id, guild_id):
        master__ = await get_master_of_slave(ctx, user_id, guild_id)
        await ctx.reply(
            f"Stfu you dirty ass nigger. Don't you fuckin' dare you this command.\n{master__} Oi bro, this nigga of yours is trying to use this command. Beat this filty thing to death. ||KYS||")

    # Retrieve the user's slaves
    #database = await get_masterslave_connection()
    async with utils.db_pool.acquire() as cursor:
        slaves = await cursor.fetch("SELECT slave_id FROM ownerships WHERE master_id = $1 AND guild_id = $2", user_id, guild_id)
        

    if not slaves:
        await ctx.reply(f"You do not own any slaves. Buy some from the shop first!!")
        return

    # Collect details for each slave
    slave_details = []
    for (slave_id,) in slaves:
        # Fetch the slave's message count
        message_count = await get_message_count(slave_id, guild_id)
        wallet_balance = await get_user_balance(slave_id)
        current_price = await calculate_slave_price(ctx, slave_id, guild_id)
        slave_member = ctx.guild.get_member(slave_id)
        if slave_member:
            slave_details.append(f"**{slave_member.display_name}**\n"
                                 f"**Message Count**: {message_count}\n"
                                 f"**Current Price**: 🪙 {current_price} Kero\n"
                                 f"**Wallet Balance**: 💷 {wallet_balance} Kero\n")
        else:
            slave_member = await bot.fetch_user(slave_id)
            slave_details.append(f"**{slave_member.display_name}** [Not in this Server]\n"
                                 f"**Message Count**: {message_count}\n"
                                 f"**Current Price**: 🪙 {current_price} Kero\n"
                                 f"**Wallet Balance**: 💷 {wallet_balance} Kero\n")
    embed = discord.Embed(title=f"Your Slaves", color=discord.Color.blue())
    for detail in slave_details:
        embed.add_field(name="", value=detail, inline=False)

    await ctx.send(embed=embed)


@bot.command(name='slinfo', aliases=['Slinfo'], help=f"Shows info about a specific slave of yours.\n**Syntax**: slinfo @your_slave")
async def slaveinfo(ctx, slave: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slinfo"):
        await ctx.reply("You are blocked from using `slinfo`.")
        return
    master_id = ctx.author.id
    guild_id = ctx.guild.id

    if not await is_master(ctx.author.id, ctx.guild.id):
        await ctx.send("You are not a master.")
        return

    if await is_slave(master_id, guild_id):
        master__ = await get_master_of_slave(ctx, slave.id, guild_id)
        await ctx.reply(
            f"Stfu you dirty ass nigger. Don't you fuckin' dare you this command.\n{master__} Oi bro, this nigga of yours is trying to use this command. Beat this filty thing to death. ||KYS||")
        return

    async with utils.db_pool.acquire() as cursor:
        result = await cursor.fetchrow(""" SELECT master_id FROM ownerships WHERE slave_id = $1 AND guild_id = $2 """, slave.id, guild_id)

    if not result:
        await ctx.reply(f"{slave.display_name} is not a slave of someone in this server.")

    if not result or result["master_id"] != master_id:
        await ctx.reply(f"{slave.display_name} is not your slave, so you cannot view their information.")
        return

    # Fetch slave's stats
    message_count = await get_message_count(slave.id, guild_id)
    kero_balance = await get_user_balance(slave.id)
    days_on_server = await get_days_on_server(slave.id, guild_id)

    async with utils.db_pool.acquire() as cursor:
        rows = await cursor.fetch("""SELECT command FROM purchased_slave_commands WHERE master_id = $1 AND slave_id = $2 AND guild_id = $3 """, master_id, slave.id, guild_id)
        bought_permissions = {r["command"] for r in rows}

    # Define all available permissions
    all_permissions = ["Jail", "Unjail", "Kick", "Setnick", "Mute", "Unmute", "Role", "Whip"]

    # Permissions status: bought and not bought
    bought = [perm for perm in all_permissions if perm in bought_permissions]
    not_bought = [perm for perm in all_permissions if perm not in bought_permissions]

    # Build embed to display slave information
    embed = discord.Embed(
        title=f"🖤 Slave Info for {slave.display_name}",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=slave.display_avatar.url)

    embed.add_field(name="", value=(
        f"**Username**: {slave.name}\n"
        f"**Joined Server**: {slave.joined_at.strftime('%Y-%m-%d')}\n"
        f"**Message Count**: {message_count}\n"
        f"**Wallet**: 💷 {kero_balance} Kero\n"
        f"**Days on Server**: {days_on_server} days\n"
    ), inline=False)

    embed.add_field(name="Bought Permissions", value="\n".join(bought) if bought else "No permissions bought.",
                    inline=False)
    embed.add_field(name="Not Bought Permissions",
                    value="\n".join(not_bought) if not_bought else "All permissions bought.", inline=False)

    await ctx.send(embed=embed)


@slaveinfo.error
async def slaveinfo_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="Slinfo",
                                           description="Shows info about a specific slave of yours.\n**Syntax**: `slinfo @your_slave`",
                                           color=discord.Color.blue()))
    elif isinstance(error, commands.MemberNotFound):
        await ctx.reply(f"The specified slave is not found in this server.")


@bot.command(name='escape', aliases=['Escape'], help=f"Lets a slave escape it's master for twice the amount of Kero the Master originally bought the slave for.\n**Syntax**: escape @user)")
async def escape(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "escape"):
        await ctx.reply("You are blocked from using `escape`.")
        return

    slave_id = ctx.author.id
    master_id = await get_master_of_slave(ctx, slave_id, ctx.guild.id)
    master = await get_master_of_slave(ctx, slave_id, ctx.guild.id)
    if isinstance(master_id, discord.Member):  # If master_id is a Member object, extract its ID
        master_id = master_id.id
    if master_id is None:
        await ctx.reply("You are not someone's slave bro. If you really wanna use this command so much, how about becoming Neko and Lucky's slave for once?")
        return

    slave_balance = await get_user_balance(slave_id)


    async with utils.db_pool.acquire() as cursor:
        result = await cursor.fetchrow("""SELECT amount FROM transactions WHERE receiver_id = $1 AND sender_id = $2 AND guild_id = $3 AND type = 'slbuy' ORDER BY timestamp DESC LIMIT 1 """, slave_id, master_id, ctx.guild.id)

        if result:
            og_price = result['amount']
        else:
            og_price = 0

    req_kero = og_price * 2

    if slave_balance >= req_kero:
        await ctx.send(f"**{ctx.author.mention}** has successfully escaped from the clutches of their master **{master.display_name}** for **💷 {req_kero} Kero**!")
        await update_user_balance(ctx.author.id, -req_kero)
        ok = await calculate_slave_price(ctx, slave_id, ctx.guild.id)
        await notify_wishers_on_slave_freed(ctx, slave_id, ctx.guild.id, ok)

        await add_transaction(ctx.author.id, None, -req_kero, "escape", ctx.guild.id)

        async with utils.db_pool.acquire() as cursor:
            await cursor.execute("""DELETE FROM purchased_slave_commands WHERE slave_id = $1 AND master_id = $2 AND guild_id = $3 """, slave_id, master_id, ctx.guild.id)

            await cursor.execute("""DELETE FROM ownerships WHERE slave_id = $1 AND guild_id = $2 """, slave_id, ctx.guild.id)


    else:
        kero_needed = req_kero - slave_balance
        kero_message = f"You need **💷 {kero_needed}** more Kero to escape."

        await ctx.reply(kero_message)


@bot.command(name='slrelease', aliases=['Slrelease'], help=f"Lets the master release it's slave, and in return, the master gets some amount as refund.\n**Syntax**: slrelease @user")
async def release(ctx, member: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slrelease"):
        await ctx.reply("You are blocked from using `slrelease`.")
        return
    master_id, slave_id = ctx.author.id, member.id
    guild_id = ctx.guild.id  # Get guild_id for guild-specific functionality

    if await is_master(master_id, ctx.guild.id):

        async with utils.db_pool.acquire() as cursor:
            exists = await cursor.fetchval( "SELECT 1 FROM ownerships WHERE master_id = $1 AND slave_id = $2 AND guild_id = $3", master_id, slave_id, guild_id)

            if not exists:
                await ctx.send(f"{ctx.author.mention}, you do not own {member.display_name} as a slave.")
                return
            
            purchase_price = await cursor.fetchval( "SELECT purchase_price FROM ownerships WHERE master_id = $1 AND slave_id = $2 AND guild_id = $3", master_id, slave_id, guild_id)
            
            if purchase_price is None:
                await ctx.send("Error retrieving slave's purchase price.")
                return

            refund_amount = int(purchase_price * (random.randint(20, 40) / 100))

            await update_user_balance(master_id, refund_amount)
            await cursor.execute("""DELETE FROM ownerships WHERE master_id = $1 AND slave_id = $2 AND guild_id = $3 """, master_id, slave_id, guild_id)

            await cursor.execute("DELETE FROM purchased_slave_commands WHERE master_id = $1 AND slave_id = $2 AND guild_id = $3", master_id, slave_id, guild_id)


        ok = await calculate_slave_price(ctx, slave_id, guild_id)
        await notify_wishers_on_slave_freed(ctx, slave_id, guild_id, ok)
        await ctx.send(f"{ctx.author.mention} has released {member.mention} from slavery and received **{refund_amount} Kero** as a refund.")

        await add_transaction(None, ctx.author.id, refund_amount, "slrelease", ctx.guild.id)

    else:
        await ctx.send("You must atleast own a slave to use this command nega.")


@bot.command(name='slrefund', aliases=['Slrefund'], help=f"Lets you see the actual amount of refund you could get if you release a particular slave right now.\n**Syntax**: slrefund @user")
async def slrefund(ctx, member: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "slrefund"):
        await ctx.reply("You are blocked from using `slrefund`.")
        return
    master_id = ctx.author.id
    slave_id = member.id
    guild_id = ctx.guild.id

    if await is_master(master_id, ctx.guild.id):

        async with utils.db_pool.acquire() as cursor:
            purchase_price = await cursor.fetchval("""SELECT purchase_price FROM ownerships WHERE master_id = $1 AND slave_id  = $2 AND guild_id  = $3 """, master_id, slave_id, guild_id)
            
            if purchase_price is None:
                await ctx.send(f"{ctx.author.mention}, you do not own {member.display_name} as a slave.")
                return

            lower_refund = int(purchase_price * 0.20)
            upper_refund = int(purchase_price * 0.40)
            # random_refund = random.randint(lower_refund, upper_refund)

        # Send a message with refund details
        await ctx.reply(f"Releasing {member.display_name} will refund you anywhere between **{lower_refund} Kero** and **{upper_refund} Kero**.")
    else:
        await ctx.reply("Atleast become an owner of a slave yourself first before using this command nigga.")


@bot.command(name="trade", aliases=['Trade'], help=f"Lets two users trade for Kero and Slaves.\n**Syntax**: trade offer(slave mention or Kero) @user")
async def trade(ctx, offered: str, target_user: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "trade"):
        await ctx.reply("You are blocked from using `trade`.")
        return
    initiator = ctx.author
    guild_id = ctx.guild.id

    if await is_slave(initiator.id, guild_id) or await is_slave(target_user.id, guild_id):
        msg = (f"{initiator.mention}, slaves cannot initiate trades." if await is_slave(initiator.id, guild_id) else f"{target_user.mention} is a slave and cannot engage in trades.")
        await ctx.send(msg)
        return

    async def parse_offer(value):
        if value.isdigit() and len(value) < 14:
            return int(value), "Kero"
        try:
            return await commands.MemberConverter().convert(ctx, value), "as a Slave"
        except commands.BadArgument:
            return None, None

    offer_value, offer_type = await parse_offer(offered)
    if not offer_value:
        await ctx.send("Invalid offer. You can only offer an amount of Kero or a slave (mention or ID).")
        return

    await ctx.send(
        f"{target_user.mention}, {ctx.author.display_name} is offering {offer_value} {offer_type} for a trade. Please reply with either:\n"
        "- A Kero amount or a slave mention/ID of yours to proceed.\n"
        "- Or type `reject` to decline the trade.")

    response = None
    start_time = asyncio.get_event_loop().time()

    while not response:
        try:
            msg = await bot.wait_for("message", check=lambda m: m.author == target_user and m.channel == ctx.channel,
                                     timeout=60 - (asyncio.get_event_loop().time() - start_time), )
            if msg.content.lower() == "reject":
                await ctx.send(f"{target_user.mention} has rejected the trade.")
                return
            response = await parse_offer(msg.content)
            if not response[0]:
                # await ctx.send(f"{target_user.mention}, invalid response. Please provide Kero or a valid slave.")
                response = None  # Reset for valid input
        except asyncio.TimeoutError:
            await ctx.send(f"{target_user.mention} did not respond in time. Trade cancelled.")
            return
    requested_value, requested_type = response

    await ctx.send(
        f"{initiator.mention}, {target_user.display_name} has advanced the trade: Your {offer_value} {offer_type} for their {requested_value} {requested_type}.\n"
        "Type `confirm` to accept or `reject` to decline."
    )

    final_response = None
    start_time = asyncio.get_event_loop().time()
    while not final_response:
        try:
            msg = await bot.wait_for(
                "message",
                check=lambda m: m.author == initiator and m.channel == ctx.channel,
                timeout=60 - (asyncio.get_event_loop().time() - start_time),
            )
            if msg.content.lower() == "reject":
                await ctx.send("Trade has been cancelled by the initiator.")
                return
            if msg.content.lower() == "confirm":
                final_response = "confirm"
        except asyncio.TimeoutError:
            await ctx.send(f"{initiator.mention} did not respond in time. Trade cancelled.")
            return

    async with utils.db_pool.acquire() as conn:
        if offer_type == "Kero" and requested_type == "Kero":
            await ctx.send("Kero-to-Kero trades are not allowed. Only Slave-to-Slave and Kero-to-Slave trades are allowed.")
            return

        elif offer_type == "Kero" and requested_type == "as a Slave":
            initiator_balance = await get_user_balance(initiator.id)

            if initiator_balance < offer_value:
                await ctx.reply("You do not have enough Kero for this trade.")
                return

            owner = await conn.fetchval("SELECT master_id FROM ownerships WHERE slave_id = $1 AND guild_id = $2", requested_value.id, guild_id)

            if not owner or owner != target_user.id:
                await ctx.send(f"{target_user.mention} does not own the specified slave.")
                return

            await conn.execute("UPDATE ownerships SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3", initiator.id, requested_value.id, guild_id)

            await conn.execute("UPDATE purchased_slave_commands SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3", initiator.id, requested_value.id, guild_id)


            await update_user_balance(initiator.id, -offer_value)
            await update_user_balance(target_user.id, offer_value)

            await add_transaction(initiator.id, target_user.id, offer_value, "trade", guild_id)
        
            await add_transaction(target_user.id, initiator.id, requested_value.id, "trade", guild_id)

        elif offer_type == "as a Slave" and requested_type == "Kero":
            owner = await conn.fetchval("SELECT master_id FROM ownerships WHERE slave_id = $1 AND guild_id = $2", offer_value.id, guild_id)

            if not owner or owner[0] != initiator.id:
                await ctx.reply("You do not own the specified slave.")
                return

            target_balance = await conn.fetchval("SELECT balance FROM users WHERE user_id = $1 AND guild_id = $2", target_user.id, guild_id) or 0


            if target_balance < requested_value:
                await ctx.reply(f"{target_user.mention} does not have enough Kero for this trade.")
                return

            await conn.execute("UPDATE ownerships SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3", target_user.id, offer_value.id, guild_id)
            
            await conn.execute("UPDATE purchased_slave_commands SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3", target_user.id, offer_value.id, guild_id)

            await update_user_balance(target_user.id, -requested_value)
            await update_user_balance(initiator.id, requested_value)

            await add_transaction(initiator.id, target_user.id, offer_value.id, "trade", guild_id)
        
            await add_transaction(target_user.id, initiator.id, requested_value, "trade", guild_id)

        elif offer_type == "as a Slave" and requested_type == "as a Slave":
            
            owner_offer = await conn.fetchval( "SELECT master_id FROM ownerships WHERE slave_id = $1 AND guild_id = $2", offer_value.id, guild_id)
            
            owner_request = await conn.fetchval( "SELECT master_id FROM ownerships WHERE slave_id = $1 AND guild_id = $2", requested_value.id, guild_id)

            if not owner_offer or owner_offer[0] != initiator.id:
                await ctx.send("You do not own the offered slave.")
                return
            if not owner_request or owner_request[0] != target_user.id:
                await ctx.send("The other user does not own the requested slave.")
                return
            
            await conn.execute( "UPDATE ownerships SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3", target_user.id, offer_value.id, guild_id)

            await conn.execute( "UPDATE ownerships SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3", initiator.id, requested_value.id, guild_id)

            await conn.execute( "UPDATE purchased_slave_commands SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3", target_user.id, offer_value.id, guild_id)

            await conn.execute( "UPDATE purchased_slave_commands SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3", initiator.id, requested_value.id, guild_id)

            await add_transaction(initiator.id, target_user.id, offer_value.id, "trade", guild_id)
        
            await add_transaction(target_user.id, initiator.id, requested_value.id, "trade", guild_id)


        await ctx.send(
            f"Trade successfully completed: {initiator.mention} traded their **{offer_value} {offer_type}** for {target_user.mention}'s **{requested_value} {requested_type}**.")

@bot.command(name="fetchwater", aliases=['Fetchwater'], help=f"Helps a slave earn some Kero by fetching water for it's master.\n**Syntax**: fetchwater")
@commands.cooldown(rate=1, per=30*60, type=commands.BucketType.user)
async def fetch_water(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "fetchwater"):
        await ctx.reply("You are blocked from using `fetchwater`.")
        return
    slave_id = ctx.author.id
    command_name = "fetch_water"
    if await is_slave(slave_id, ctx.guild.id):

        number = ''.join(random.choices('0123456789', k=10))
        await ctx.send(f"Please type this number correctly within 30 seconds: {number}", delete_after=5)

        try:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            response = await bot.wait_for("message", timeout=30.0, check=check)
            if response.content == number:
                reward = random.randint(10, 50)
                await update_user_balance(slave_id, reward)
                await add_transaction(None, ctx.author.id, reward, "fetch_water", ctx.guild.id)
                await ctx.reply(f"🎉 Success! You earned {reward} Keros!")
            else:
                await ctx.reply("❌ Incorrect number! Try again next time.")

        except asyncio.TimeoutError:
            await ctx.reply("⏳ Time's up! You missed your chance!")

    else:
        await ctx.reply("Nigga you ain't someone's slave, so you can't use this command.")

@fetch_water.error
async def fetch_water_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        await ctx.reply(f"🕒 Try again in {minutes} minutes.")
    else:
        raise error

@bot.command(name="bakebread", aliases=['Bakebread'], help=f"Helps a slave earn some Kero by baking bread for it's master.\n**Syntax**: bakebread")
@commands.cooldown(rate=1, per=30*60, type=commands.BucketType.user)
async def bake_bread(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "bakebread"):
        await ctx.reply("You are blocked from using `bakebread`.")
        return
    slave_id = ctx.author.id

    if await is_slave(slave_id, ctx.guild.id):

        # Simple math question
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        correct_answer = None

        oper = ["+", "/", "-", "X"]
        operation = random.choice(oper)
        if operation == "+":
            correct_answer = int(num1 + num2)
        elif operation == "-":
            correct_answer = int(num1 - num2)
        elif operation == "X":
            correct_answer = int(num1 * num2)
        elif operation == "/":
            correct_answer = int(num1 / num2) if num2 != 0 else 0

        await ctx.send(f"Solve this math question within 30 seconds: {num1} {operation} {num2} = ?")

        try:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            response = await bot.wait_for("message", timeout=30.0, check=check)
            if response.content.isdigit() and int(response.content) == correct_answer:
                reward = random.randint(10, 50)
                await update_user_balance(slave_id, reward)
                await add_transaction(None, ctx.author.id, reward, "bake_bread", ctx.guild.id)
                await ctx.reply(f"🎉 Success! You earned {reward} Keros!")
            else:
                await ctx.reply(f"❌ Incorrect answer! The correct answer is {correct_answer}. Try again next time.")

        except asyncio.TimeoutError:
            await ctx.reply("⏳ Time's up! You missed your chance!")

    else:
        await ctx.reply("Nigga you ain't someone's slave, so you can't use this command.")

@bake_bread.error
async def bake_bread_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        await ctx.reply(f"🕒 Try again in {minutes} minutes.")
    else:
        raise error

@bot.command(name="fanmaster",help=f"Helps a slave earn some Kero by fanning some air to it's master.\n**Syntax**: fanmaster")
@commands.cooldown(rate=1, per=30*60, type=commands.BucketType.user)
async def fan_master(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "fanmaster"):
        await ctx.reply("You are blocked from using `fanmaster`.")
        return
    slave_id = ctx.author.id
    if await is_slave(slave_id, ctx.guild.id):
        now = datetime.now()

        emojis = random_emojis()
        emoji_string = ''.join(emojis)
        await ctx.send(f"Type these emojis in the correct order within 30 seconds: {' '.join(emojis)}", delete_after=4)

        try:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            response = await bot.wait_for("message", timeout=30.0, check=check)
            if response.content.replace(" ", "") == emoji_string:
                reward = random.randint(10, 50)
                await update_user_balance(slave_id, reward)
                await add_transaction(None, ctx.author.id, reward, "fan_master", ctx.guild.id)
                await ctx.reply(f"🎉 Success! You earned {reward} Keros!")
            else:
                await ctx.reply("❌ Incorrect emojis! Try again next time.")

        except asyncio.TimeoutError:
            await ctx.reply("⏳ Time's up! You missed your chance!")

    else:
        await ctx.reply("Nigga you ain't someone's slave, so you can't use this command.")

@fan_master.error
async def fan_master_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        await ctx.reply(f"🕒 Try again in {minutes} minutes.")
    else:
        raise error


@bot.command(name="minerock", help=f"Helps a slave earn some Kero by mining rocks.\n**Syntax**: minerock")
@commands.cooldown(rate=1, per=30*60, type=commands.BucketType.user)
async def mine_rock(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "minerock"):
        await ctx.reply("You are blocked from using `minerock`.")
        return
    slave_id = ctx.author.id
    if await is_slave(slave_id, ctx.guild.id):
        now = datetime.now()
        emoji_to_react = random_emojis()[0]

        try:
            def check(reaction, user):
                return user == ctx.author and reaction.message.channel == ctx.channel and reaction.emoji == emoji_to_react

            message = await ctx.send(
                f"React with {emoji_to_react} on your `minerock` message to mine the rock within 30 seconds!",
                delete_after=2)
            await bot.wait_for("reaction_add", timeout=30.0, check=check)
            reward = random.randint(10, 50)
            await update_user_balance(slave_id, reward)
            await add_transaction(None, ctx.author.id, reward, "mine_rock", ctx.guild.id)
            await ctx.reply(f"🎉 Success! You mined the rock and earned {reward} Keros!")

        except asyncio.TimeoutError:
            await ctx.reply("⏳ Time's up! You missed your chance!")

    else:
        await ctx.reply("Nigga you ain't someone's slave, so you can't use this command.")

@mine_rock.error
async def mine_rock_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        await ctx.reply(f"🕒 Try again in {minutes} minutes.")
    else:
        raise error


@bot.command(name="shinecrown", help=f"Helps a slave earn some Kero by praising it's master.\n**Syntax**: shinecrown")
@commands.cooldown(rate=1, per=30*60, type=commands.BucketType.user)
async def shine_crown(ctx):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "shinecrown"):
        await ctx.reply("You are blocked from using `shinecrown`.")
        return
    slave_id = ctx.author.id
    master = await get_master_of_slave(ctx, slave_id, ctx.guild.id)
    #command_name = "shine_crown"

    if await is_slave(slave_id, ctx.guild.id):
        await ctx.send("Praise your master three times within 30 seconds!")
        praised_count = 0
        start_time = datetime.now()

        try:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            while praised_count < 3 and (datetime.now() - start_time).seconds < 30:
                response = await bot.wait_for("message", timeout=30.0, check=check)
                if "master" in response.content.lower() or "praise" in response.content.lower() or master.mention in response.content.lower() or master.display_name in response.content.lower():
                    praised_count += 1

            if praised_count >= 3:
                reward = random.randint(10, 50)
                await update_user_balance(slave_id, reward)
                await add_transaction(None, ctx.author.id, reward, "shine_crown", ctx.guild.id)
                await ctx.reply(f"🎉 Success! You earned {reward} Keros for praising your master!")
            else:
                await ctx.reply("⏳ Time's up! You missed your chance to praise your master.")

        except asyncio.TimeoutError:
            await ctx.reply("⏳ Time's up! You missed your chance!")

    else:
        await ctx.reply("Nigga you ain't someone's slave, so you can't use this command.")

@shine_crown.error
async def shine_crown_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        await ctx.reply(f"🕒 Try again in {minutes} minutes.")
    else:
        raise error

@bot.command(name='cf', aliases=['CF', 'Cf'], help=f"Gamble Kero by using coinflip\n**Syntax**: cf bet_amount side(default = random)")
@commands.cooldown(1, 10, commands.BucketType.user)
async def cf(ctx, bet_amount: str, side: str = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "cf"):
        await ctx.reply("You are blocked from using `cf`.")
        return

    user_id = ctx.author.id
    guild_id = ctx.guild.id

    if side is None:
        side = random.choice(['heads', 'tails'])
    else:
        side = side.lower()
        if side in ['h', 'heads']:
            side = 'heads'
        elif side in ['t', 'tails']:
            side = 'tails'
        else:
            await ctx.reply("Please choose a valid side: `heads`/`h` or `tails`/`t`.")
            return

    user_bal = await get_user_balance(user_id)

    if not user_bal:
        balance = 0
    else:
        balance = user_bal

    if bet_amount == "all":
        bet = min(balance, 10000)
    else:
        try:
            bet = int(bet_amount)
            if bet <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(
                "Please enter a valid bet amount (positive integer) or `all` to bet your entire balance.")
            return

    if bet > 10000:
        await ctx.reply("🚫 Maximum bet is 10,000 Kero.")
        return

    if bet > balance:
        await ctx.reply(f"Insufficient Kero! You only have `{balance}` Kero in your wallet.")
        return

    result = random.choices(
        population=[side, "heads" if side == "tails" else "tails"],
        weights=[0.49, 0.51])[0]
    if result == side:
        new_balance = balance + bet
        await ctx.reply(
            f"The coin landed on `{result}`! 🎉 You won `{round(bet)}` Kero and now have `{round(new_balance)}` Kero in your wallet.")
        winner_share = bet
        if await is_slave(user_id, guild_id):
            master = await get_master_of_slave(ctx, user_id, guild_id)
            master_share = int(bet * 0.2)
            winner_share = bet - master_share

            await update_user_balance(master.id, master_share)

            await ctx.send(f"💸 Since you are a slave, 20% ({master_share} Kero) of your winnings has been transferred to your master **{master.display_name}**.\nYou receive the remaining **{winner_share} Kero**!")

        await update_user_balance(user_id, winner_share)
    else:
        new_balance = balance - bet
        await ctx.send(
            f"The coin landed on `{result}`. 😢 You lost `{round(bet)}` Kero and now have `{round(new_balance)}`.")
        await update_user_balance(user_id, -bet)

    await add_transaction(None, user_id, -bet if result != side else bet, "coinflip", guild_id)

@cf.error
async def cf_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"You're on cooldown! Try again in {error.retry_after:.2f} seconds.",
                       delete_after=error.retry_after)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="Coinflip",
                                           description="Bet an amount on a coinflip and get your bet doubled or lose all of it.\n\n**Syntax**: cf bet_amount side(default = heads)"))
    else:
        raise error


@bot.command(name='diceroll', help=f"Gamble Kero by using diceroll. If lost, you lose 2X Kero of your original bet. If won, you get 6X Kero the amount of your bet.\n**Syntax**: diceroll bet_amount side")
async def diceroll(ctx, bet_amount: str, guess: int):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "diceroll"):
        await ctx.reply("You are blocked from using `diceroll`.")
        return
    user_id = ctx.author.id
    guild_id = ctx.guild.id

    # Check if guess is between 1 and 6
    if guess not in range(1, 7):
        await ctx.reply("Please choose a number between 1 and 6.")
        return

    user_bal = await get_user_balance(user_id)

    if not user_bal:
        balance = 0
    else:
        balance = user_bal

    if bet_amount == "all":
        bet = min(balance, 10000)
    else:
        try:
            bet = int(bet_amount)
            if bet <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(
                "Please enter a valid bet amount (positive integer) or `all` to bet your entire balance.")
            return
        
    if bet > 10000:
        await ctx.reply("🚫 Maximum bet is 10,000 Kero.")
        return

    if bet > balance:
        await ctx.reply(f"Insufficient Kero! You only have `{balance}` Kero in your wallet.")
        return

    roll = random.choices(
        population=[guess, random.randint(1, 6)],
        weights=[0.20, 0.80])[0]

    if roll == guess:
        new_balance = bet * 6
        await ctx.reply(
            f"The dice rolled a `{roll}`! 🎉 You guessed it right and won `{round(new_balance)}` Kero. Your balance is now `{round(balance +(bet * 6))}` Kero.")
    else:
            # Lose case (2x multiplier, but no negative balance)
        new_balance = -(bet * 2)
        await ctx.send(
            f"The dice rolled a `{roll}`. 😢 You guessed wrong and lost `{round(bet * 2)}` Kero. Your new balance is `{round(max(0, balance -(bet * 2)))}`.")

    winner_share = new_balance

    if await is_slave(user_id, guild_id) and new_balance > bet:
        master = await get_master_of_slave(ctx, user_id, guild_id)

        master_share = int((new_balance) * 0.2)
        winner_share = new_balance - master_share

        await update_user_balance(master.id, master_share)

        await ctx.send(f"💸 Since you are a slave, 20% **({master_share} Kero)** of your winnings has been transferred to your master **{master.display_name}**.\nYou receive the remaining **{winner_share} Kero**!")

    await update_user_balance(user_id, winner_share)

    await add_transaction(None, user_id, -bet * 2 if roll != guess else bet * 6, "diceroll", guild_id)


@bot.command(name='jackpot',
             help=f"Pools all the money from many users and then decide the random lucky user who gets all that money.\n**Syntax**: jackpot start")
async def jackpot(ctx, bet_amount: str = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "jackpot"):
        await ctx.reply("You are blocked from using `jackpot`.")
        return
    user_id = ctx.author.id
    guild_id = ctx.guild.id

    if bet_amount == 'start':
        if guild_id in jackpot_game and jackpot_game[guild_id]['timer'] is not None:
            await ctx.send("A jackpot game is already in progress. Wait for it to finish.")
            return

        jackpot_game[guild_id] = {
            'creator': user_id,
            'participants': {},
            'total_pot': 0,
            'timer': None
        }
        await ctx.send(
            f"Jackpot game started! The pool is now open! Type `jackpot <amount>` to join! Minimum bet is 100 Kero. The game will end in 5 minutes or when the initiator types `jackpot stop`.")
        jackpot_game[guild_id]['timer'] = asyncio.create_task(jackpot_timer(ctx, guild_id))
        return

    if bet_amount == 'stop' and user_id == jackpot_game[guild_id]['creator']:
        # Stop the jackpot before 5 minutes
        await stop_jackpot(ctx, guild_id)
        return

    if bet_amount:
        try:
            bet = int(bet_amount)
        except ValueError:
            await ctx.send("Please enter a valid bet amount in numbers.")
            return

        if bet < 100:
            await ctx.send("The minimum amount to join the jackpot is 100 Kero.")
            return

        if guild_id in jackpot_game and user_id in jackpot_game[guild_id]['participants']:
            await ctx.send(f"You've already joined the jackpot, {ctx.author.mention}!")
            return

        user_bal = await get_user_balance(user_id)
        if user_bal < bet:
            await ctx.send(f"You don't have enough Kero! You only have {user_bal} Kero.")
            return
        new_balance = max(0, user_bal - bet)
        await update_user_balance(user_id, -bet)

        jackpot_game[guild_id]['participants'][user_id] = bet
        jackpot_game[guild_id]['total_pot'] += bet

        await ctx.send(
            f"{ctx.author.mention} has joined the jackpot with a bet of **{bet} Kero**! Total pool: **{jackpot_game[guild_id]['total_pot']} Kero**.")
        return


async def jackpot_timer(ctx, guild_id):
    await asyncio.sleep(300)  # 5 minutes
    if guild_id in jackpot_game and jackpot_game[guild_id]['timer'] is not None:
        await stop_jackpot(ctx, guild_id)


async def stop_jackpot(ctx, guild_id):
    if guild_id in jackpot_game:
        game_data = jackpot_game[guild_id]
        if game_data['timer'] is None:
            return
        if not game_data['participants']:
            await ctx.send("No one joined the jackpot! Ending game...")
            if guild_id in jackpot_game:
                game_data = jackpot_game[guild_id]

                # Cancel the timer if it's still running
                if game_data['timer'] is not None:
                    game_data['timer'].cancel()

                jackpot_game.pop(guild_id, None)
                return

        participants = jackpot_game[guild_id]['participants']
        total_pot = jackpot_game[guild_id]['total_pot']
        winner_id = random.choice(list(game_data['participants'].keys()))

        if await is_slave(winner_id, guild_id):
            master = await get_master_of_slave(ctx, winner_id, guild_id)
            master_share = int(total_pot * 0.2)
            winner_amount = total_pot - master_share

            await update_user_balance(master.id, master_share)
            await ctx.send(
                f"💸 The winner {winner_id.mention} is a slave! **20% ({master_share} Kero)** of the jackpot was transferred to their master {master.display_name}.\n"
                f"{winner_id.mention} receives the remaining **{winner_amount} Kero**!")
        else:
            winner_amount = total_pot
            await ctx.send(
                f"The jackpot has ended! The winner is {winner_id.mention}! 🎉 Total prize: **{winner_amount} Kero**! **{winner_id.display_name}** wins it all!")

        await update_user_balance(winner_id, winner_amount)

        if guild_id in jackpot_game:
            game_data = jackpot_game[guild_id]

            # Cancel the timer if it's still running
            if game_data['timer'] is not None:
                game_data['timer'].cancel()

            jackpot_game.pop(guild_id, None)
            return


@bot.command(name="auction", help=f"Auction your slave and other users who are interested will bet on it.\n**Syntax**: auction start @user")
async def auction(ctx, action: str, *args):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "auction"):
        await ctx.reply("You are blocked from using `auction`.")
        return
    user_id = ctx.author.id
    guild_id = ctx.guild.id
    auctioneer = ctx.author

    if await is_slave(user_id, guild_id):
        await ctx.send("You're a slave faggot, you cannot hold any auctions. Better stay in yo line.")
        return

    if action.lower() == "start":
        if len(args) < 1:
            await ctx.send("Please mention the slave to auction.")
            return
        if guild_id in active_auctions and active_auctions[guild_id]['auction_open']:
            await ctx.send(
                "There is already an active auction in this guild. You cannot start a new one until the current auction ends.")
            return

        target = args[0]
        try:
            slave_mention = await commands.MemberConverter().convert(ctx, target)
        except commands.MemberNotFound:
            await ctx.send("Could not find the specified member.")
            return

        # Verify ownership in the database
        async with utils.db_pool.acquire() as cursor:
            slave = await cursor.fetchrow("""SELECT * FROM ownerships WHERE master_id = $1 AND slave_id = $2 AND guild_id = $3 """, user_id, slave_mention.id, guild_id)

            if not slave:
                await ctx.send("You don't own this slave to auction.")
                return

        # Initialize the auction data
        active_auctions[guild_id] = {
            'slave_id': slave_mention.id,
            'highest_bidder': None,
            'highest_bid': 0,
            'end_time': time.time() + 60,
            'auctioneer': ctx.author,
            'auction_open': True
        }
        await ctx.send(
            f"Auction for {slave_mention.mention} has started! Use `auction bid <amount>` to place your bids. The auction will end when there are no more bids for 60 seconds or when the initiator types `auction stop`.")

        async def end_auction():
            await asyncio.sleep(60)
            if guild_id in active_auctions and active_auctions[guild_id]['auction_open']:
                auction = active_auctions.pop(guild_id)
                if auction['highest_bidder']:
        
                    async with utils.db_pool.acquire() as cursor:
                        await cursor.execute(
                            """UPDATE ownerships SET master_id = $1, purchase_price = $2 WHERE slave_id = $3 AND guild_id = $4""",
                            auction['highest_bidder'].id, auction['highest_bid'], auction['slave_id'], guild_id)
                        await cursor.execute(
                            "UPDATE purchased_slave_commands SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3",
                            auction['highest_bidder'].id, auction['slave_id'], guild_id)
                        await update_user_balance(auction['highest_bidder'].id, -(auction['highest_bid']))
                        await update_user_balance(ctx.author.id, auction['highest_bid'])

                    await ctx.send(
                        f"**Auction completed!** {auction['highest_bidder'].mention} has won the slave for **{auction['highest_bid']} Kero**!")
                else:
                    await ctx.send("The auction ended with no bids.")

        asyncio.create_task(end_auction())

    elif action.lower() == "bid":
        if guild_id not in active_auctions or not active_auctions[guild_id]['auction_open']:
            await ctx.reply("No active auction in this server.")
            return

        if ctx.author == active_auctions[guild_id]['auctioneer']:
            await ctx.reply("You cannot bid in your own auction.")
            return
        if len(args) < 1:
            await ctx.send("Please specify a bid amount.")
            return

        if time.time() > active_auctions[guild_id]['end_time']:
            await ctx.reply("The auction has ended. Please wait for results.")
            return

        try:
            amount = int(args[0])
            print(f"Raw amount input: {amount}")
        except ValueError:
            await ctx.send("Invalid bid amount. Please enter a numeric value.")
            return

        if not amount or amount <= 0:
            await ctx.send("Your bid must be a positive number.")
            return

        if amount <= active_auctions[guild_id]['highest_bid']:
            await ctx.send("Your bid must be higher than the current highest bid.")
            return

        balance = await get_user_balance(user_id)
        if balance < amount:
            await ctx.send("You don't have enough funds for this bid.")
            return

        active_auctions[guild_id]['highest_bid'] = amount
        active_auctions[guild_id]['highest_bidder'] = ctx.author
        active_auctions[guild_id]['end_time'] = time.time() + 60  # Reset timer

        await ctx.send(
            f"New highest bid of {amount} by {ctx.author.mention}. Any other bidders out there who wants to bid for this slave?")

    elif action.lower() == "stop":
        if guild_id not in active_auctions or active_auctions[guild_id]['auctioneer'] != ctx.author:
            await ctx.send("You are not authorized to stop this auction.")
            return

        auction = active_auctions.pop(guild_id)

        if auction['highest_bidder']:

            async with utils.db_pool.acquire() as cursor:
                await cursor.execute(
                    """UPDATE ownerships SET master_id = $1, purchase_price = $2 WHERE slave_id = $3 AND guild_id = $4""",
                    auction['highest_bidder'].id, auction['highest_bid'], auction['slave_id'], guild_id)
                await cursor.execute(
                    "UPDATE purchased_slave_commands SET master_id = $1 WHERE slave_id = $2 AND guild_id = $3",
                    auction['highest_bidder'].id, auction['slave_id'], guild_id)
                await update_user_balance(auction['highest_bidder'].id, -(auction['highest_bid']))
                await update_user_balance(ctx.author.id, (auction['highest_bid']))

            await ctx.send(
                f"**Auction completed!** {auction['highest_bidder'].mention} has won the slave for **{auction['highest_bid']} Kero**!")
        else:
            await ctx.send("The auction ended with no bids.")

    else:
        await ctx.send("Invalid action. Use `start`, `bid`, or `stop`.")


@bot.command(name='wish', help="Wish for a slave to notify you when they are free.\n**Syntax**: wish @user")
async def wish(ctx, slave: discord.Member):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "wish"):
        await ctx.reply("You are blocked from using `wish`.")
        return
    wisher = ctx.author
    guild_id = ctx.guild.id

    # Check if the user is a slave
    if await is_slave(wisher.id, guild_id):
        await ctx.reply("Slaves cannot use the `wish` command. Nice try!")
        return

    # Check if the target is a slave and has a master
    if not await is_slave(slave.id, guild_id):
        await ctx.reply(f"{slave.display_name} is not a slave or does not have a master!")
        return


    async with utils.db_pool.acquire() as cursor:
        existing_wish = await cursor.fetchrow("""SELECT * FROM wishes WHERE wisher_id = $1 AND slave_id  = $2 AND guild_id  = $3""", wisher.id, slave.id, guild_id)

    if existing_wish:
        await ctx.reply(f"You already wished for {slave.display_name}!")
        return

    # Add the wish to the database
    async with utils.db_pool.acquire() as cursor:
        await cursor.execute("""INSERT INTO wishes (wisher_id, slave_id, guild_id) VALUES ($1, $2, $3)""", wisher.id, slave.id, guild_id)

    await ctx.reply(f"You have wished for **{slave.display_name}**. You will be notified when they are free!")


async def notify_wishers_on_slave_freed(ctx, slave_id, guild_id, price):
    
    async with utils.db_pool.acquire() as cursor:
        wishers = await cursor.fetch(""" SELECT wisher_id FROM wishes WHERE slave_id = $1 AND guild_id = $2 """, slave_id, guild_id)

    if wishers:
        slave_member = ctx.guild.get_member(slave_id)  # Get slave's Discord user
        for wisher_id in wishers:
            wisher = ctx.guild.get_member(wisher_id[0])  # Get wisher's Discord user
            message = (
                f"The slave **{slave_member.display_name}** is now free!\n"
                f"Their price is currently **{price} Kero**. Act fast before someone else grabs it!"
            )
            # Notify in DM
            try:
                await wisher.send(embed=discord.Embed(title="🔔 Wish Notification!", description=message,
                                                      color=discord.Color.random()))
            except discord.Forbidden:
                pass  # User has DMs disabled, skip

            # Notify in server (ping the user)
            guild = bot.get_guild(guild_id)
            if guild:
                member = guild.get_member(wisher_id[0])
                if member:
                    await guild.system_channel.send(f"{member.mention} {message}")

        # Remove the wishes from the database
        async with utils.db_pool.acquire() as cursor:
            await cursor.execute(""" DELETE FROM wishes WHERE slave_id = $1 AND guild_id = $2 """, slave_id, guild_id)

@bot.command(name="tower", help=f"Climb the tower to get rich!!\n**Syntax**: tower start <bet_amount>")
async def tower(ctx, action: str, bet: int = None):

    return await ctx.reply("In Development right now.")

    if await is_command_blocked(ctx.guild.id, ctx.author.id, "tower"):
        await ctx.reply("You are blocked from using `tower`.")
        return
    prefix = ctx.prefix
    user_id = ctx.author.id
    now = datetime.utcnow()

    if action == "start":
        if user_id in cooldowns and cooldowns[user_id] > now:
            remaining_time = cooldowns[user_id] - now
            minutes, seconds = divmod(remaining_time.total_seconds(), 60)
            await ctx.send(
                f"⏳ You can only start a new Tower game after every 60 minutes.\n"
                f"Try again in {int(minutes)}m {int(seconds)}s.")
            return

        if user_id in tower_games:
            await ctx.reply(
                f"⚠️ You already have an active Tower game. Use `{prefix}tower climb` or `{prefix}tower stop`.")
            return

        if bet is None or bet <= 10:
            await ctx.reply("⚠️ You must specify a bet greater than 10 Kero to start the game.")
            return
        user_balance = await get_user_balance(user_id)
        if user_balance < bet:
            await ctx.reply(f"⚠️ You don't have enough Kero to place that bet. Your balance: {user_balance} Kero.")
            return

        # await update_user_balance(user_id, -bet)
        tower_games[user_id] = {
            "current_floor": 0,
            "current_reward": 0,
            "bet": bet,
        }
        await ctx.send(
            f"🎲 {ctx.author.mention}, you've started the Tower game with a bet of **{bet} Kero**!\n"
            f"Climb to higher floors by typing `{prefix}tower climb`.\nType `{prefix}tower stop` to cash out your winnings.")
        return

    elif action == "climb":
        game_data = tower_games.get(user_id)
        if not game_data:
            await ctx.send(f"⚠️ You need to start the game first with `{prefix}tower start <bet>`.")
            return

        current_floor = game_data["current_floor"]
        bet = game_data["bet"]

        floor_data = {
            1: {"reward_multiplier": 1.2, "loss_multiplier": 1.0},
            2: {"reward_multiplier": 1.4, "loss_multiplier": 1.2},
            3: {"reward_multiplier": 1.6, "loss_multiplier": 1.4},
            4: {"reward_multiplier": 1.8, "loss_multiplier": 1.6},
            5: {"reward_multiplier": 2.0, "loss_multiplier": 1.8},
            6: {"reward_multiplier": 2.2, "loss_multiplier": 2.0},
            7: {"reward_multiplier": 2.4, "loss_multiplier": 2.2},
            8: {"reward_multiplier": 2.6, "loss_multiplier": 2.4},
            9: {"reward_multiplier": 2.8, "loss_multiplier": 2.6},
            10: {"reward_multiplier": 3.0, "loss_multiplier": 2.8}
        }

        # floor_data = {
        #    1: {"reward_increase": 0.15, "loss_increase": 1.0, "next_loss_increase": 1.0},
        #    2: {"reward_increase": 0.15, "loss_increase": 1.0, "next_loss_increase": 1.1},
        #    3: {"reward_increase": 0.25, "loss_increase": 1.1, "next_loss_increase": 1.2},
        #    4: {"reward_increase": 0.35, "loss_increase": 1.2, "next_loss_increase": 1.3},
        #    5: {"reward_increase": 0.45, "loss_increase": 1.3, "next_loss_increase": 1.5},
        #    6: {"reward_increase": 0.6, "loss_increase": 1.5, "next_loss_increase": 1.7},
        #    7: {"reward_increase": 0.75, "loss_increase": 1.7, "next_loss_increase": 2.0},
        #    8: {"reward_increase": 1.0, "loss_increase": 2.0, "next_loss_increase": 2.25},
        #    9: {"reward_increase": 1.5, "loss_increase": 2.25, "next_loss_increase": 2.5},
        #    10: {"reward_increase": 3.0, "loss_increase": 2.5, "next_loss_increase": 0}}

        if current_floor >= 10:
            await ctx.reply(
                "🚀 Wohooooooooo~ You've reached the TOP FLOOR against all odds! Good Job man!! You're hella lucky. I'm jealous of you now, shi...\nAnyways, cash out with `tower stop` to get all your rewards.")
            return

        next_floor = current_floor + 1
        floor_info = floor_data.get(next_floor)
        if not floor_info:
            await ctx.send("⚠️ No data for this floor. Please contact support.")
            return

        success_chance = max(5, 90 - 10 * current_floor)  # 90%, 80%, ..., 5%
        loss_amount = int(bet * floor_info["loss_multiplier"])
        reward_gain = int(bet * (floor_info["reward_multiplier"] - 1))
        game_data["current_round_loss"] = loss_amount
        game_data["current_round_reward"] = reward_gain

        wallet_balance = await get_user_balance(user_id)
        if wallet_balance < loss_amount:
            await ctx.reply(
                f"⚠️ You don't have enough Kero to bear the loss if you fall. Loss would be **{loss_amount} Kero**.\n"
                f"Type `{prefix}tower stop` to cash out your current reward of **{game_data['current_reward']} Kero**.")
            return

        outcome = random.randint(1, 100)
        if outcome <= success_chance:
            game_data["current_floor"] = next_floor
            game_data["current_reward"] += reward_gain
            nxtfloorloss = int(floor_data.get(next_floor)["loss_multiplier"] * bet)

            await ctx.reply(
                f"🎉 Success! You've climbed to **Floor {next_floor}**.\n 💰 Reward for this climb: **{reward_gain} Kero**. Total Reward: **{game_data['current_reward']} Kero**\n"
                f"🎲 Next floor success chance: **{max(5, success_chance - 10)}%**\n"
                f"💥 If you fall, you'll lose **{nxtfloorloss} Kero**.\n"
                f"Type `{prefix}tower climb` to keep climbing or `{prefix}tower stop` to cash out.")
        else:
            await update_user_balance(user_id, -game_data["current_round_loss"])
            tower_games.pop(user_id, None)
            cooldowns[user_id] = now + timedelta(minutes=60)
            await ctx.send(
                f"💥 You fell from the Tower and lost **{game_data['current_round_loss']} Kero.** Better luck next time!")
        return

    elif action == "stop":
        game_data = tower_games.get(user_id)
        if not game_data:
            await ctx.send("⚠️ You don't have an active Tower game to stop.")
            return

        reward = game_data["current_reward"]
        floor = game_data["current_floor"]
        total_winnings = reward + game_data["bet"]

        if await is_slave(user_id, ctx.guild.id):
            master = await get_master_of_slave(ctx, user_id, ctx.guild.id)
            master_share = int(total_winnings * 0.2)
            total_winnings -= master_share

            await update_user_balance(master.id, master_share)
            await ctx.send(
                f"💸 {ctx.author.mention}, since you are a slave, **20% ({master_share} Kero)** of your winnings were transferred to your master {master.display_name}.")
        await update_user_balance(user_id, total_winnings)
        tower_games.pop(user_id, None)
        cooldowns[user_id] = now + timedelta(minutes=60)
        await ctx.send(
            f"🎉 {ctx.author.mention}, you've cashed out from **Floor {floor}** with **{reward} Kero**! Well played!")
        return

    await ctx.reply("⚠️ Invalid action. Use `start`, `climb`, or `stop`.")


@tower.error
async def tower_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(
            f"Join the Tower and gamble for fun!! Type `{ctx.prefix}tower start <bet_amount>` to get started.")




@bot.tree.command(name="buckshot", description="Challenge another player to Buckshot Roulette!")
async def buckshotroulette(interaction: discord.Interaction, target: discord.Member):
    if await is_command_blocked(interaction.guild.id, interaction.user.id, "buckshot"):
        await interaction.response.send_message("You are blocked from using buckshot command.")
        return

    if target.bot or target.id == interaction.user.id:
        await interaction.response.send_message("Please choose a valid (non-bot) opponent!", ephemeral=True)
        return

    for game in active_games.values():
        if str(interaction.user.id) in [game["challenger"], game["challenged"]] or str(target.id) in [game["challenger"], game["challenged"]]:
            await interaction.response.send_message("Either you or the target is already in an active game.", ephemeral=True)
            return
    msg = f"**Buckshot Roulette Challenge**\n{interaction.user.mention} challenges {target.mention} to Buckshot Roulette! Do you accept?"

    view = ChallengeView(interaction.user, target)
    await interaction.response.send_message(msg, view=view)
    message = await interaction.original_response()
    view.message = message

class ChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, challenged: discord.Member, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.challenged = challenged
        self.message = None

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="Challenge timed out. No response received.", view=None)
            except Exception:
                pass

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("Only the challenged player can accept.", ephemeral=True)
            return

        state = create_initial_game_state(self.challenger.id, self.challenged.id)
        state["challenger"] = str(self.challenger.id)
        state["challenged"] = str(self.challenged.id)

        
        game_id = max(active_games.keys(), default=0) + 1
        state["game_id"] = game_id

        active_games[game_id] = state

        board_embed = await create_game_board_embed(interaction.guild, state)
        view = GameView(state, self.challenger, self.challenged, game_id, interaction.guild)

        turn_member = interaction.guild.get_member(int(state["turn"]))
        content = f"Current Turn: {turn_member.mention}"
        game_message = await interaction.channel.send(content=content, embed=board_embed, view=view)
        view.game_message = game_message

        await interaction.message.delete()
        self.stop()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("Only the challenged player can reject.", ephemeral=True)
            return
        await interaction.response.send_message("Challenge rejected.", ephemeral=True)
        await interaction.message.delete()

class GameView(discord.ui.View):
    def __init__(self, game_state: dict, challenger: discord.Member, challenged: discord.Member, game_id: int,
                 guild: discord.Guild, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.game_state = game_state
        self.challenger = challenger
        self.challenged = challenged
        self.game_id = game_id
        self.guild = guild
        self.game_message = None  # Will hold the public game board message

    async def on_timeout(self):
        board_embed = await create_game_board_embed(self.guild, self.game_state)
        board_embed.add_field(name="🏆 Game Over", value="Game timed out. It's a tie!", inline=False)
        #await update_game_in_db(self.game_id, self.game_state)
        await self.game_message.edit(embed=board_embed, view=None)
        active_games.pop(self.game_id, None)

    def _resolve_shot(self):
        idx = self.game_state["gun_config"]["current_index"]
        chamber = self.game_state["gun_config"]["chamber"]
        if idx >= len(chamber):
            return None
        return "loaded" if chamber[idx] else "empty"

    def _advance_chamber(self):
        self.game_state["gun_config"]["current_index"] += 1

    def _apply_damage(self, user_id: int, damage: int):
        uid = str(user_id)
        self.game_state["health"][uid] = max(0, self.game_state["health"][uid] - damage)

    def _next_turn(self):
        current = str(self.game_state["turn"])
        opponent_id = str(self.challenged.id) if current == str(self.challenger.id) else str(self.challenger.id)
        # If opponent is handcuffed (skip_turn active), decrement and keep current turn.
        if self.game_state["skip_turn"].get(opponent_id, 0) > 0:
            self.game_state["skip_turn"][opponent_id] -= 1
        else:
            self.game_state["turn"] = int(opponent_id)

    @discord.ui.button(label="Shoot Self", style=discord.ButtonStyle.danger)
    async def shoot_self(self, interaction: discord.Interaction, button: discord.ui.Button):
        global operation_active
        if not operation_active:
            operation_active = True

            await interaction.followup.send("Buckshot Roulette command halted by stop command.", ephemeral=False)
            return
        if interaction.user.id != self.game_state["turn"]:
            await interaction.response.send_message("It's not your turn.", ephemeral=True)
            return
        await interaction.response.defer()
        outcome = self._resolve_shot()
        if outcome is None:
            await self._end_round(interaction)
            return
        if outcome == "loaded":
            damage = 1
            self.game_state.setdefault("damage_multiplier", {})
            if self.game_state.get("damage_multiplier", {}).get(str(interaction.user.id), 1) > 1:
                damage *= 2
            self._apply_damage(interaction.user.id, damage)
            result = f"{interaction.user.mention} shot themselves and lost {damage} health!"
            self._next_turn()
        else:
            result = f"{interaction.user.mention} fired at themselves, but the chamber was empty."
        # Reset multiplier regardless of outcome:
        self.game_state["damage_multiplier"][str(interaction.user.id)] = 1
        await self._post_action(interaction, result)

    @discord.ui.button(label="Shoot Opponent", style=discord.ButtonStyle.primary)
    async def shoot_opponent(self, interaction: discord.Interaction, button: discord.ui.Button):
        global operation_active
        operation_active = True
        if not operation_active:
            await interaction.followup.send("Buckshot Roulette command halted by stop command.", ephemeral=False)
            return
        if interaction.user.id != self.game_state["turn"]:
            await interaction.response.send_message("It's not your turn.", ephemeral=True)
            return
        await interaction.response.defer()
        opponent_id = int(self.challenged.id) if interaction.user.id == self.challenger.id else int(self.challenger.id)
        outcome = self._resolve_shot()
        if outcome is None:
            await self._end_round(interaction)
            return
        if outcome == "loaded":
            damage = 1
            self.game_state.setdefault("damage_multiplier", {})
            if self.game_state.get("damage_multiplier", {}).get(str(interaction.user.id), 1) > 1:
                damage *= 2
            self._apply_damage(opponent_id, damage)
            result_msg = f"{interaction.user.mention} shot <@{opponent_id}> and dealt {damage} damage!"
        else:
            result_msg = f"{interaction.user.mention} fired at <@{opponent_id}>, but the chamber was empty."
        # Reset multiplier for active user regardless:
        self.game_state["damage_multiplier"][str(interaction.user.id)] = 1
        self._next_turn()
        await self._post_action(interaction, result_msg)

    @discord.ui.button(label="Use Card", style=discord.ButtonStyle.secondary)
    async def use_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        global operation_active
        operation_active = True
        if not operation_active:
            await interaction.followup.send("Buckshot Roulette command halted by stop command.", ephemeral=False)
            return
        if interaction.user.id != self.game_state["turn"]:
            await interaction.response.send_message("It's not your turn.", ephemeral=True)
            return
        await interaction.response.send_message("Choose a card to use:", view=CardSelectView(self), ephemeral=True)

    @discord.ui.button(label="Forfeit", style=discord.ButtonStyle.red)
    async def forfeit(self, interaction: discord.Interaction, button: discord.ui.Button):
        global operation_active
        operation_active = True
        if not operation_active:
            await interaction.followup.send("Buckshot Roulette command halted by stop command.", ephemeral=False)
            return
        if interaction.user.id not in [self.challenger.id, self.challenged.id]:
            await interaction.response.send_message("You are not part of this game.", ephemeral=True)
            return

        winner_id = self.challenged.id if interaction.user.id == self.challenger.id else self.challenger.id
        winner_member = self.guild.get_member(winner_id)
        board_embed = await create_game_board_embed(interaction.guild, self.game_state)
        board_embed.add_field(name="🏆 Game Over", value=f"{winner_member.display_name} wins by forfeit!", inline=False)
        #await update_game_in_db(self.game_id, self.game_state)
        await self.game_message.edit(embed=board_embed, view=None)
        await interaction.response.send_message(f"Game over! {winner_member.display_name} wins by forfeit!", ephemeral=False)
        active_games.pop(self.game_id, None)

    async def _post_action(self, interaction: discord.Interaction, result_msg: str):
        # Log action (keep only the last 3 actions)
        action_log = self.game_state.get("action_log", [])
        action_log.append(f"{result_msg}")
        self.game_state["action_log"] = action_log[-4:]

        self._advance_chamber()

        health_challenger = self.game_state["health"].get(str(self.challenger.id), 0)
        health_challenged = self.game_state["health"].get(str(self.challenged.id), 0)
        

        if health_challenger <= 0 or health_challenged <= 0:
            winner_id = self.challenged.id if health_challenger <= 0 else self.challenger.id
            board_embed = await create_game_board_embed(interaction.guild, self.game_state)
            winner_member = interaction.guild.get_member(winner_id)
            board_embed.add_field(name="🏆 Game Over", value=f"{winner_member.display_name} wins!", inline=False)
            #await update_game_in_db(self.game_id, self.game_state)
            await self.game_message.edit(embed=board_embed, view=None)
            await interaction.followup.send(f"Game over! {winner_member.display_name} wins!", ephemeral=False)
            active_games.pop(self.game_id, None)
            return
        
        if self.game_state["gun_config"]["current_index"] >= len(self.game_state["gun_config"]["chamber"]):
                    await self._end_round(interaction)
                    return

        #await update_game_in_db(self.game_id, self.game_state)
        board_embed = await create_game_board_embed(interaction.guild, self.game_state)

        current_turn_id = self.game_state["turn"]
        turn_member = self.guild.get_member(int(current_turn_id))
        content = f"Current Turn: {turn_member.mention}"
        await self.game_message.edit(content=content, embed=board_embed, view=self)


    async def _end_round(self, interaction: discord.Interaction):
        self.game_state["round"] += 1
        self.game_state["gun_config"] = create_gun_config()

        #hand_size = random.randint(2, 3) if self.game_state["gun_config"]["total"] < 6 else random.randint(3, 5)
        #new_hand = deal_cards(hand_size)
        total_shells = self.game_state["gun_config"]["total"]

        size = calculate_hand_size(total_shells)
        for player in [self.challenger.id, self.challenged.id]:
            self.game_state["hands"][str(player)] = deal_cards(size)

        self.game_state.setdefault("action_log", []).append("🔁 New round started! New shells and cards dealt.")

        board_embed = await create_game_board_embed(interaction.guild, self.game_state)
        current_turn_id = self.game_state["turn"]
        turn_member = self.guild.get_member(int(current_turn_id))
        content = f"Current Turn: {turn_member.mention}"
        await self.game_message.edit(content=content, embed=board_embed, view=self)

class CardSelectView(discord.ui.View):
    def __init__(self, game_view: GameView, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.game_view = game_view
        hand = self.game_view.game_state["hands"].get(str(game_view.game_state["turn"]), [])
        card_descriptions = {
            "Beer": "Ejects the current shell.",
            "Magnifying Glass": "Reveals the current shell status.",
            "Cigarette Pack": "Regain 1 health.",
            "Handcuffs": "Blocks opponent's next turn.",
            "Hand Saw": "Next shot deals 2x damage.",
            "Burner Phone": "Reveals one upcoming shell's status.",
            "Inverter": "Swaps the polarity of current shell.",
            "Crowbar": "Steal one card from opponent.",
            "Expired Medicine": "50% chance to regain 2 health; otherwise, lose 1."
        }
        options = []
        seen = {}
        for i, card in enumerate(hand):
            count = seen.get(card, 0)
            seen[card] = count + 1
            options.append(discord.SelectOption(
                label=card,
                value=f"{card}-{count}",
                description=card_descriptions.get(card, "")
            ))
        self.add_item(CardSelect(options, self.game_view))

class CardSelect(discord.ui.Select):
    def __init__(self, options, game_view: GameView):
        super().__init__(placeholder="Select a card", min_values=1, max_values=1, options=options)
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]  # e.g. "Beer-0"
        card = selected_value.split("-")[0]
        user_id = str(interaction.user.id)
        hand = self.game_view.game_state["hands"].get(user_id, [])
        if card not in hand:
            await interaction.response.send_message("Card not found in your hand.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        result = await process_card_effect(card, interaction, self.game_view)
        hand.remove(card)
        action_log = self.game_view.game_state.get("action_log", [])
        action_log.append(result)
        self.game_view.game_state["action_log"] = action_log[-3:]
        self.game_view.game_state["hands"][user_id] = hand
        #await update_game_in_db(self.game_view.game_id, self.game_view.game_state)
        board_embed = await create_game_board_embed(interaction.guild, self.game_view.game_state)
        await self.game_view.game_message.edit(embed=board_embed, view=self.game_view)

async def process_card_effect(card: str, interaction: discord.Interaction, game_view: GameView):
    active_id = str(interaction.user.id)
    opponent_id = str(game_view.challenged.id) if interaction.user.id == game_view.challenger.id else str(
        game_view.challenger.id)

    if card in ["Magnifying Glass", "Burner Phone"]:
        if card == "Magnifying Glass":
            idx = game_view.game_state["gun_config"]["current_index"]
            chamber = game_view.game_state["gun_config"]["chamber"]
            status = "Loaded" if chamber[idx] else "Empty"
            private_result = f"🔍 Current shell is **{status}**"
            public_result = f"{interaction.user.mention} used Magnifying Glass."
        elif card == "Burner Phone":
            chamber = game_view.game_state["gun_config"]["chamber"]
            idx = game_view.game_state["gun_config"]["current_index"]
            if idx < len(chamber) - 1:
                reveal_index = random.randint(idx + 1, len(chamber) - 1)
                status = "Loaded" if chamber[reveal_index] else "Empty"
                private_result = f"📞 Shell #{reveal_index + 1} is **{status}**."
            else:
                private_result = "📞 No shells to reveal."
            public_result = f"{interaction.user.mention} used Burner Phone."
        await interaction.followup.send(private_result, ephemeral=True)
        return public_result

    if card == "Beer":
        idx = game_view.game_state["gun_config"]["current_index"]
        chamber = game_view.game_state["gun_config"]["chamber"]
        if idx < len(chamber):
            ejected = chamber.pop(idx)
            game_view.game_state["gun_config"]["total"] -= 1
            if ejected:
                game_view.game_state["gun_config"]["loaded"] -= 1
            else:
                game_view.game_state["gun_config"]["empty"] -= 1
            return f"{interaction.user.mention} used Beer and ejected a **{'loaded' if ejected else 'empty'}** shell."
        return f"{interaction.user.mention} used Beer, but the chamber was already empty."

    elif card == "Cigarette Pack":
        max_health = game_view.game_state["max_health"]
        if game_view.game_state["health"][active_id] < max_health:
            game_view.game_state["health"][active_id] += 1
            return f"{interaction.user.mention} used {card}. Regained 1 health."
        else:
            return f"{interaction.user.mention} used {card}. Health is already full."

    elif card == "Handcuffs":
        game_view.game_state["skip_turn"][opponent_id] = game_view.game_state["skip_turn"].get(opponent_id, 0) + 1
        return f"{interaction.user.mention} used {card}. Opponent's next turn blocked."

    elif card == "Hand Saw":
        game_view.game_state.setdefault("damage_multiplier", {})[active_id] = 2

        return f"{interaction.user.mention} used {card}. Next shot deals double damage."
    elif card == "Inverter":
        idx = game_view.game_state["gun_config"]["current_index"]
        chamber = game_view.game_state["gun_config"]["chamber"]
        if idx < len(chamber):
            chamber[idx] = not chamber[idx]
            game_view.game_state["gun_config"]["loaded"] = sum(1 for shell in chamber if shell is True)
            game_view.game_state["gun_config"]["empty"] = sum(1 for shell in chamber if shell is False)
            return f"{interaction.user.mention} used Inverter. Current shell polarity swapped."

        else:
            return f"{interaction.user.mention} used Inverter, but there is no valid shell to invert."
    elif card == "Crowbar":
        opponent_hand = game_view.game_state["hands"].get(opponent_id, [])

        stealable = [c for c in opponent_hand if c != "Crowbar"]
        if stealable:
            stolen = random.choice(stealable)
            opponent_hand.remove(stolen)
            game_view.game_state["hands"][opponent_id] = opponent_hand
            game_view.game_state["hands"][active_id].append(stolen)

            return f"{interaction.user.mention} used {card} and stole **{stolen}** from opponent."
        else:

            return f"{interaction.user.mention} used {card} but opponent has no cards to steal."
    elif card == "Expired Medicine":
        if random.random() < 0.5:
            max_health = game_view.game_state["max_health"]
            current = game_view.game_state["health"][active_id]
            if current < max_health:
                game_view.game_state["health"][active_id] = min(current + 2, max_health)

                return f"{interaction.user.mention} used {card} and regained up to max health (now {game_view.game_state['health'][active_id]})."
            else:
                return f"{interaction.user.mention} used {card} but health is already full."
        else:
            game_view.game_state["health"][active_id] = max(0, game_view.game_state["health"][active_id] - 1)
            return f"{interaction.user.mention} used {card} but it backfired! Lost 1 health."
    else:
        return f"{interaction.user.mention} used an unimplemented card."


@bot.tree.command(name="buckshot_help", description="Learn how Buckshot Roulette works")
async def buckshot_help(interaction: discord.Interaction):
    embed = discord.Embed(title="Buckshot Roulette: How It Works", color=discord.Color.gold())

    embed.add_field(
        name="Game Overview",
        value=(
            "Buckshot Roulette is a turn-based duel between two players. Each round, a gun with a random shell configuration "
            "determines if a shot is loaded or empty. Players can choose to shoot themselves or their opponent, and use cards "
            "to affect the outcome. The goal is to deplete the opponent's health before yours reaches zero."),inline=False)

    embed.add_field(
        name="Actions",
        value=(
            "**Shoot Self:**\n"
            "• If the chamber is loaded, you lose 1 health and the turn passes to your opponent.\n"
            "• If the chamber is empty, you keep your turn.\n\n"
            "**Shoot Opponent:**\n"
            "• Whether the chamber is loaded or empty, the turn passes to your opponent."),inline=False)

    embed.add_field(
        name="Card Actions & Emoji",
        value=(
            "Both players receive the same number of cards each round. The available cards and their effects are:\n\n"
            "🍺 **Beer:** Ejects the current shell from the gun.\n"
            "🔍 **Magnifying Glass:** Reveals the status (Loaded/Empty) of the current shell.\n"
            "🚬 **Cigarette Pack:** Regains 1 health.\n"
            "🔒 **Handcuffs:** Blocks your opponent's next turn.\n"
            "🪚 **Hand Saw:** Your next shot deals double damage.\n"
            "📞 **Burner Phone:** Reveals the status of one upcoming shell.\n"
            "🔄 **Inverter:** Swaps the polarity of the current shell (loaded becomes empty, and vice versa).\n"
            "🔨 **Crowbar:** Steals one card from your opponent. (IMPORTANT: It can't steal another crowbar).\n"
            "💊 **Expired Medicine:** 50% chance to regain 2 health; otherwise, you lose 1 health."),inline=False)

    embed.add_field(
        name="Rounds & Flow",
        value=(
            "The game is divided into rounds. Each round starts with a fresh configuration of shells and a new set of cards "
            "dealt equally to both players. The current round is displayed on the game board so you always know which round you're in."),inline=False)

    embed.set_footer(text="Enjoy the game and may the best shooter win!")
    await interaction.response.send_message(embed=embed, ephemeral=True)






class Challenge(discord.ui.View):
    def __init__(self, challenger: discord.User, opponent: discord.User, timeout=120):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.opponent = opponent
        self.value = None  # Will be set to True (accept) or False (reject)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged user can accept!", ephemeral=True)
            return
        self.value = True
        self.stop()
        await interaction.response.defer()
        await interaction.message.delete()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged user can reject!", ephemeral=True)
            return
        self.value = False
        self.stop()
        await interaction.response.edit_message(content="Challenge rejected.", view=None)

class ColorWarView(discord.ui.View):
    def __init__(self, game_id):
        super().__init__(timeout=120)  # 2 minutes timeout (adjust as needed)
        self.game_id = game_id
        # Create a 5x5 grid, but replace the bottom-right cell with the Forfeit button.
        for x in range(5):
            for y in range(5):
                self.add_item(ColorWarButton(game_id, x, y))

    async def on_timeout(self):
        game = color_wars.get(self.game_id)
        if game:
            await game["message"].edit(content="Game Over! It's a tie due to timeout!", view=None)
            if "forfeit_message" in game:
                try:
                    await game["forfeit_message"].delete()
                except Exception:
                    pass
            color_wars.pop(self.game_id, None)

class ColorWarGame:
    def __init__(self, game_id, channel_id, player1, player2, starting_turn):
        self.game_id = game_id
        self.channel_id = channel_id
        self.player1 = player1
        self.player2 = player2
        self.current_turn = starting_turn
        self.grid = create_empty_grid()
        self.red_points = 0
        self.blue_points = 0
        self.view = ColorWarView(game_id)

    def get_embed(self):
        embed = discord.Embed(
            title="🔥 Color War Game 🔥",
            description=f"<@{self.player1}> challenged <@{self.player2}> to a battle of colors!",
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Current Turn: <@{self.current_turn}>")
        return embed

class ForfeitViewColorWars(discord.ui.View):
    def __init__(self, game_id, timeout=120):
        super().__init__(timeout=timeout)
        self.game_id = game_id
        self.add_item(ForfeitButtonColorWars(game_id))

class ForfeitButtonColorWars(discord.ui.Button):
    def __init__(self, game_id):
        super().__init__(label="Forfeit", style=discord.ButtonStyle.red)
        self.game_id = game_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        game = color_wars.get(self.game_id)
        if not game:
            await interaction.followup.send("Game not found.", ephemeral=True)
            return
        if interaction.user.id not in [game["player1"], game["player2"]]:
            await interaction.followup.send("You're not part of this game!", ephemeral=True)
            return
        # Determine the winner as the opponent of the forfeiting user.
        winner = game["player2"] if interaction.user.id == game["player1"] else game["player1"]
        await game["message"].edit(content=f"Game Over! <@{winner}> wins by forfeit!", view=None)
        if "forfeit_message" in game:
            try:
                await game["forfeit_message"].delete()
            except Exception as e:
                print(f"Error deleting forfeit message: {e}")
        color_wars.pop(self.game_id, None)
        await interaction.followup.send("You have forfeited the game.", ephemeral=True)

@bot.tree.command(name="colorwars", description="Challenge someone to a Color War battle!")
async def colorwars(interaction: discord.Interaction, opponent: discord.User):
    if await is_command_blocked(interaction.guild.id, interaction.user.id, "colorwars"):
        await interaction.response.send_message("You are blocked from using colorwars command.")
        return

    if opponent.bot or opponent.id == interaction.user.id:
        await interaction.response.send_message("Please choose a valid (non-bot) opponent!", ephemeral=True)
        return

    msg = f"**Color War Challenge**\n<@{interaction.user.id}> has challenged <@{opponent.id}> to a Color War battle! Do you accept?"

    view = Challenge(interaction.user, opponent)
    await interaction.response.send_message(msg, view=view)

    await view.wait()
    if view.value is None:
        try:
            await interaction.edit_original_response(content="Challenge timed out.", embed=None, view=None)
        except discord.NotFound:
            pass
        return
    if not view.value:
        return  # Challenge rejected

    # Challenge accepted: Create game instance
    game_id = f"game_{random.randint(1000, 9999999)}"
    starting_turn = random.choice([interaction.user.id, opponent.id])
    game_instance = ColorWarGame(game_id, interaction.channel.id, interaction.user.id, opponent.id, starting_turn)
    # Initialize first move flags so the first move can be an empty cell tap
    game_instance.first_move_done = {interaction.user.id: False, opponent.id: False}
    color_wars[game_id] = {
        "game_id": game_id,
        "channel_id": interaction.channel.id,
        "player1": interaction.user.id,
        "player2": opponent.id,
        "current_turn": starting_turn,
        "grid": game_instance.grid,
        "red_points": game_instance.red_points,
        "blue_points": game_instance.blue_points,
        "view": game_instance.view,
        "first_move_done": game_instance.first_move_done,
    }

    msg = await interaction.followup.send(content=f"**Color War Game**\n\nCurrent Turn: <@{starting_turn}>", view=game_instance.view)

    game_instance.message = msg
    game_instance.embed = None
    color_wars[game_id]["message"] = msg

    forfeit_message = await interaction.followup.send(content="Click here to forfeit the game if needed:", view=ForfeitViewColorWars(game_id))
    color_wars[game_id]["forfeit_message"] = forfeit_message

@bot.tree.command(name="colorwars_help", description="Displays help information for the Color War game.")
async def colorwarshelp(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Color War Game Help",
        description=(
            "**Welcome to Color War!**\n\n"
            "Color War is a fast-paced, two-player PvP game played on a 5x5 grid of buttons.\n\n"
            "**Gameplay Mechanics:**\n"
            "• **First Move:** Tapping an empty cell gives you a bubble with 3 dots.\n"
            "• **Subsequent Moves:** Tapping one of your own bubbles adds 1 dot.\n"
            "• **Bursting:** When a bubble reaches 4 dots, it bursts and spreads to adjacent cells, converting opponent bubbles as it goes.\n"
            "• **Winning:** The game ends when one player's bubbles are completely eliminated.\n\n"
            "**Additional Info:**\n"
            "• The grid is entirely represented by interactive buttons (no text grid).\n"
            "• Turn information and point counts (Red vs. Blue) are displayed in the game message.\n"
            "• A timeout is set for moves—if a player doesn’t respond in time, their opponent wins by default.\n\n"
            "Use `/colorwars` to start a game and challenge an opponent.\n"
            "Good luck and have fun!"
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Color War: Strategic, fast-paced, and fun!")
    await interaction.response.send_message(embed=embed, ephemeral=True)








class ChallengeMemory(discord.ui.View):
    def __init__(self, challenger: discord.User, opponent: discord.User, timeout=120):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.opponent = opponent
        self.value = None  # Will be set to True (accept) or False (reject)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged user can accept!", ephemeral=True)
            return
        self.value = True
        self.stop()
        await interaction.response.defer()
        await interaction.message.delete()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged user can reject!", ephemeral=True)
            return
        self.value = False
        self.stop()
        await interaction.response.edit_message(content="Challenge rejected.", view=None)

class MemoryGame:
    def __init__(self, game_id, channel_id, player1, player2, starting_turn):
        self.game_id = game_id
        self.channel_id = channel_id
        self.player1 = player1
        self.player2 = player2
        self.current_turn = starting_turn
        self.scores = {str(player1): 0, str(player2): 0}
        self.current_selections = []  # List of tuples (row, col)
        self.grid = self.create_grid()
        self.view = MemoryView(game_id)
        self.message = None

    def create_grid(self):
        # 6x4 grid => 24 cards, with 12 pairs.
        emojis = ["🍎", "🍌", "🍒", "🍇", "🍊", "🍉", "🍍", "🥝", "🍑", "🍓", "🍋", "🥭", "🦕","🌈","🍨","🍡","🥜","🏀","🏓","🥁","🎪","🎯","🧩","🎨","🎭","💸","🪔","💊","🧻","🎁","🎐","🎈","🏴","💡","⏰","🛕","🚦","🛺","🏅","🏆","🥅","🏉","🥋","🍙","🍞","🥑","⛄","🌚","🦧","🦓","🐪","🦜","🦚","🦔","🦦","🦄","💍","👑","🧶", "🎎","🎏","🎞","👓","⚽","🎱","🥇","🥈","🥉","🎮","🔒", "🍬","🛴","🚀","🚁","🏳‍🌈","🌏","🧭","⚡","🌊","☢"]
        chosen = random.sample(emojis, 12)
        deck = chosen * 2  # 24 cards
        random.shuffle(deck)
        grid = []
        dummy_position = (4, 4)  # Bottom-right cell as dummy.
        for r in range(5):
            row = []
            for c in range(5):
                if (r, c) == dummy_position:
                    # Dummy cell: always revealed & non-interactive.
                    row.append({"value": "Forfeit", "revealed": True, "matched": False, "dummy": True})
                else:
                    row.append({"value": deck.pop(), "revealed": False, "matched": False, "dummy": False})
            grid.append(row)
        return grid

class MemoryButton(discord.ui.Button):
    def __init__(self, game_id, row, col):
        self.row = row
        self.col = col
        self.game_id = game_id
        dummy_position = (4, 4)
        if (row, col) == dummy_position:
            # Create a disabled button for the dummy cell.
            super().__init__(style=discord.ButtonStyle.red, label="Forfeit", custom_id=f"{game_id}_{row}_{col}")
        else:
            super().__init__(style=discord.ButtonStyle.secondary, label="❓", custom_id=f"{game_id}_{row}_{col}")

    async def callback(self, interaction: discord.Interaction):
        try:
            parts = self.custom_id.split("_")
            # Get the last two parts as row and column.
            row = int(parts[-2])
            col = int(parts[-1])
        except Exception:
            await interaction.response.send_message("Internal error: invalid button data.", ephemeral=True)
            return

        game = memory_games.get(self.game_id)
        if not game:
            await interaction.response.send_message("Game not found.", ephemeral=True)
            return

        if (row, col) == (4, 4):
            if interaction.user.id not in [game["player1"], game["player2"]]:
                await interaction.response.send_message("You're not part of this game!", ephemeral=True)
                return
            winner = game["player2"] if interaction.user.id == game["player1"] else game["player1"]
            await game["message"].edit(content=f"Game Over! <@{winner}> wins by forfeit!", view=None)
            memory_games.pop(self.game_id, None)
            await interaction.response.send_message("You have forfeited the game.", ephemeral=True)
            return

        if interaction.user.id != game["current_turn"]:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return

        cell = game["grid"][row][col]
        if cell["matched"] or cell["revealed"]:
            await interaction.response.send_message("Card already revealed!", ephemeral=True)
            return

        # Reveal the card.
        cell["revealed"] = True
        self.label = cell["value"]
        game["current_selections"].append((row, col))
        await interaction.response.edit_message(content=update_game_content(game), view=game["view"])

        if len(game["current_selections"]) == 2:
            (r1, c1), (r2, c2) = game["current_selections"]
            val1 = game["grid"][r1][c1]["value"]
            val2 = game["grid"][r2][c2]["value"]
            if val1 == val2:
                # It's a match. Mark both as matched and add a point.
                game["grid"][r1][c1]["matched"] = True
                game["grid"][r2][c2]["matched"] = True
                game["scores"][str(interaction.user.id)] += 1
                # Keep the turn for the current player.
            else:
                # Not a match: wait then flip back.
                await asyncio.sleep(1.5)
                game["grid"][r1][c1]["revealed"] = False
                game["grid"][r2][c2]["revealed"] = False
                for btn in game["view"].children:
                    if isinstance(btn, MemoryButton):
                        parts = btn.custom_id.split("_")
                        btn_row = int(parts[-2])
                        btn_col = int(parts[-1])
                        if (btn_row, btn_col) in ((r1, c1), (r2, c2)):
                            btn.label = "❓"
                # Toggle turn after a mismatch.
                game["current_turn"] = game["player2"] if game["current_turn"] == game["player1"] else game["player1"]
            game["current_selections"] = []

        # Check if game is over.
        all_matched = all(cell["matched"] if not cell.get("dummy", False) else True for row in game["grid"] for cell in row)

        if all_matched:
            winner = determine_winner(game)
            if winner:
                content = f"Game Over! Winner: <@{winner}>"
            else:
                content = "Game Over! It's a tie!"
            await game["message"].edit(content=content, view=None)
            memory_games.pop(self.game_id, None)
        else:
            await game["message"].edit(content=update_game_content(game), view=game["view"])

class MemoryView(discord.ui.View):
    def __init__(self, game_id, timeout=120):
        super().__init__(timeout=timeout)
        self.game_id = game_id
        for r in range(5):        # 5 rows
            for c in range(5):    # 5 columns
                self.add_item(MemoryButton(game_id, r, c))

    async def on_timeout(self):
        game = memory_games.get(self.game_id)
        if game:
            loser = game["current_turn"]
            winner = game["player2"] if loser == game["player1"] else game["player1"]
            await game["message"].edit(content=f"Game Over! <@{winner}> wins due to timeout!", view=None)
            memory_games.pop(self.game_id, None)

@bot.tree.command(name="memory", description="Challenge someone to a Memory game!")
async def memory(interaction: discord.Interaction, opponent: discord.User):
    if await is_command_blocked(interaction.guild.id, interaction.user.id, "memory"):
        await interaction.response.send_message("You are blocked from using memory command.")
        return

    if opponent.bot or opponent.id == interaction.user.id:
        await interaction.response.send_message("Please choose a valid (non-bot) opponent!", ephemeral=True)
        return


    msg = f"**Memory Game Challenge**\n<@{interaction.user.id}> has challenged <@{opponent.id}> to a Memory game! Do you accept?"
    challenge_view = ChallengeMemory(interaction.user, opponent)
    await interaction.response.send_message(msg, view=challenge_view)
    await challenge_view.wait()
    if challenge_view.value is None:
         await interaction.edit_original_response(content="Challenge timed out.", embed=None, view=None)
         return
    if not challenge_view.value:
         return  # Challenge rejected

    # Challenge accepted; create game instance.
    game_id = f"memory_{random.randint(1000,9999999)}"
    starting_turn = random.choice([interaction.user.id, opponent.id])
    game_instance = MemoryGame(game_id, interaction.channel.id, interaction.user.id, opponent.id, starting_turn)
    memory_games[game_id] = {
        "game_id": game_id,
        "channel_id": interaction.channel.id,
        "player1": interaction.user.id,
        "player2": opponent.id,
        "player1_name": interaction.user.display_name,
        "player2_name": opponent.display_name,
        "current_turn": starting_turn,
        "scores": game_instance.scores,
        "current_selections": game_instance.current_selections,
        "grid": game_instance.grid,
        "view": game_instance.view,
    }

    msg = await interaction.followup.send(content=update_game_content(memory_games[game_id]), view=game_instance.view)
    game_instance.message = msg
    memory_games[game_id]["message"] = msg

@bot.tree.command(name="memory_help", description="Displays help information for the Memory game.")
async def memoryhelp(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Memory Game Help",
        description=(
            "**Welcome to Memory!**\n\n"
            "In Memory, two players compete to match pairs of cards hidden in a 6x4 grid (24 cards total).\n\n"
            "**How to Play:**\n"
            "• On your turn, click two cards to reveal them.\n"
            "• If they match, they stay open and you earn a point.\n"
            "• If they don't match, they'll flip back over after a short delay, and your turn ends.\n"
            "• The game continues until all pairs are found, and the player with the most points wins.\n\n"
            "**Additional Info:**\n"
            "• A 60-second timeout is in place. If you don't make a move in time, your opponent wins by default.\n"
            "• Use `/memory` to challenge another player and start a game.\n\n"
            "Good luck and have fun testing your memory!"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="Memory Game: Test your memory and win!")
    await interaction.response.send_message(embed=embed, ephemeral=True)























DICE_EMOJIS = {
    1: "<:dice1:1346110451276058655>",
    2: "<:dice2:1346110454258466938>",
    3: "<:dice3:1346110456473063477>",
    4: "<:dice4:1346110459111276574>",
    5: "<:dice5:1346110462067998782>",
    6: "<:dice6:1346110464639373374>",
}
CATEGORIES = [
    "Aces", "Deuces", "Threes", "Fours", "Fives", "Sixes",
    "Full House", "4 of a Kind", "Small Straight", "Big Straight",
    "Choice", "Yacht"]

def calculate_score(category, dice):
    if category == "Aces":
        return sum(d for d in dice if d == 1)
    elif category == "Deuces":
        return sum(d for d in dice if d == 2)
    elif category == "Threes":
        return sum(d for d in dice if d == 3)
    elif category == "Fours":
        return sum(d for d in dice if d == 4)
    elif category == "Fives":
        return sum(d for d in dice if d == 5)
    elif category == "Sixes":
        return sum(d for d in dice if d == 6)
    elif category == "Full House":
        counts = {x: dice.count(x) for x in set(dice)}
        if sorted(counts.values()) == [2, 3]:
            return sum(dice)
        return 0
    elif category == "4 of a Kind":
        for x in set(dice):
            if dice.count(x) >= 4:
                return sum(dice)
        return 0
    elif category == "Small Straight":
        if set([1, 2, 3, 4, 5]).issubset(dice):
            return 30
        return 0
    elif category == "Big Straight":
        if set([2, 3, 4, 5, 6]).issubset(dice):
            return 30
        return 0
    elif category == "Choice":
        return sum(dice)
    elif category == "Yacht":
        if len(set(dice)) == 1:
            return 50
        return 0
    return 0

class YazyGame:
    def __init__(self, player1: discord.User, player2: discord.User):
        self.players = [player1, player2]
        self.current_player_index = 0  # index of the player whose turn it is
        self.round = 1
        self.max_rounds = 12
        self.rerolls_remaining = 3  # up to 3 rolls per turn
        self.dice = [0] * 5  # five dice
        # Score sheet for each player: {category: score or None}
        self.score_sheets = {
            player1.id: {cat: None for cat in CATEGORIES},
            player2.id: {cat: None for cat in CATEGORIES}
        }

    @property
    def current_player(self):
        return self.players[self.current_player_index]

    @property
    def opponent(self):
        return self.players[1 - self.current_player_index]

    def roll_all_dice(self):
        self.dice = [random.randint(1, 6) for _ in range(5)]

    def get_dice_display(self):
        return " ".join(DICE_EMOJIS[val] for val in self.dice)

    def get_potential_scores(self):
        """For each category not yet chosen by the current player, calculate the potential score."""
        potentials = {}
        for cat in CATEGORIES:
            if self.score_sheets[self.current_player.id][cat] is None:
                potentials[cat] = calculate_score(cat, self.dice)
            else:
                potentials[cat] = self.score_sheets[self.current_player.id][cat]
        return potentials

    def set_score(self, category):
        """Lock in the score for the current player for the selected category."""
        if self.score_sheets[self.current_player.id][category] is None:
            score = calculate_score(category, self.dice)
            self.score_sheets[self.current_player.id][category] = score
            return score
        return None

    def end_turn(self):
        """Reset rerolls and switch turn; advance round if both players have played."""
        self.rerolls_remaining = 3
        self.current_player_index = 1 - self.current_player_index
        if self.current_player_index == 0:
            self.round += 1

    def game_over(self):
        return self.round > self.max_rounds

    def total_score(self, player: discord.User):
        return sum(score for score in self.score_sheets[player.id].values() if score is not None)

class YazyView(discord.ui.View):
    def __init__(self, game: YazyGame):
        # Set a timeout of 120 seconds for inactivity.
        super().__init__(timeout=120)
        self.game = game
        self.message = None  # to store the message reference once sent
        self.refresh_items()

    def refresh_items(self):
        self.clear_items()
        # Action buttons: Roll, Stay, Forfeit
        self.add_item(RollButton(self.game))
        self.add_item(StayButton(self.game))
        self.add_item(ForfeitButton(self.game))
        # Then add a score button for each category.
        potentials = self.game.get_potential_scores()
        for cat in CATEGORIES:
            disabled = self.game.score_sheets[self.game.current_player.id][cat] is not None
            label = f"{cat}: {potentials[cat]}"
            self.add_item(ScoreButton(cat, label, disabled, self.game))

    def generate_embed(self, final=False, winner: discord.User = None):
        embed = discord.Embed(title="Yazy Game", description=f"Round {self.game.round}/{self.game.max_rounds}")
        embed.add_field(name="Dice", value=self.game.get_dice_display(), inline=False)
        # Create a table with one header row and one row per category.
        header = f"**Category**{' ' * 5}| **{self.game.players[0].name}** | **{self.game.players[1].name}**\n"
        header += "---------------------------------------------\n"
        rows = ""
        for cat in CATEGORIES:
            score1 = self.game.score_sheets[self.game.players[0].id][cat]
            score2 = self.game.score_sheets[self.game.players[1].id][cat]
            score1_str = str(score1) if score1 is not None else "-"
            score2_str = str(score2) if score2 is not None else "-"
            rows += f"{cat:<15} | {score1_str:<8} | {score2_str:<8}\n"
        table = header + rows
        embed.add_field(name="Score Sheet", value=f"```{table}```", inline=False)
        if final:
            p1_total = self.game.total_score(self.game.players[0])
            p2_total = self.game.total_score(self.game.players[1])
            embed.add_field(name="Final Scores",
                            value=f"{self.game.players[0].name}: {p1_total}\n{self.game.players[1].name}: {p2_total}",
                            inline=False)
            winner_text = winner.name if winner else "Tie"
            embed.set_footer(text=f"Game Over! Winner: {winner_text}")
        else:
            embed.set_footer(text=f"Rerolls remaining: {self.game.rerolls_remaining}")
        return embed

    async def update_message(self, interaction: discord.Interaction):
        self.refresh_items()
        embed = self.generate_embed()
        content = f"Current Turn: {self.game.current_player.mention}"
        await interaction.response.edit_message(content=content, embed=embed, view=self)

    async def on_timeout(self):
        # When the view times out, disable all buttons and remove interactivity.
        if self.message:
            embed = self.generate_embed()
            embed.set_footer(text="Game expired due to inactivity.")
            await self.message.edit(embed=embed, view=None)

class RollButton(discord.ui.Button):
    def __init__(self, game: YazyGame):
        super().__init__(label="Roll Dice", style=discord.ButtonStyle.primary)
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.current_player.id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        if self.game.rerolls_remaining <= 0:
            await interaction.response.send_message("No rerolls left!", ephemeral=True)
            return
        self.game.roll_all_dice()
        self.game.rerolls_remaining -= 1
        view: YazyView = self.view
        await view.update_message(interaction)

class StayButton(discord.ui.Button):
    def __init__(self, game: YazyGame):
        super().__init__(label="Stay", style=discord.ButtonStyle.secondary)
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.current_player.id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        # Prompt the user to select a score category.
        await interaction.response.send_message("Please choose a category by clicking one of the score buttons.",
                                                ephemeral=True)

class ForfeitButton(discord.ui.Button):
    def __init__(self, game: YazyGame):
        super().__init__(label="Forfeit", style=discord.ButtonStyle.danger)
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.current_player.id:
            await interaction.response.send_message("You cannot forfeit on someone else's turn!", ephemeral=True)
            return
        # Forfeit: current player loses.
        winner = self.game.opponent
        embed = self.view.generate_embed(final=True, winner=winner)
        self.view.stop()
        await interaction.response.edit_message(embed=embed, view=None)

class ScoreButton(discord.ui.Button):
    def __init__(self, category: str, label: str, disabled: bool, game: YazyGame):
        super().__init__(label=label, style=discord.ButtonStyle.success, disabled=disabled)
        self.category = category
        self.game = game

    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game.current_player.id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        # Defer the response to avoid "already responded" error.
        await interaction.response.defer(ephemeral=True)
        score = self.game.set_score(self.category)
        if score is None:
            await interaction.followup.send("This category is already scored!", ephemeral=True)
            return
        # Immediately update results after clicking.
        self.game.end_turn()
        view: YazyView = self.view
        if self.game.game_over():
            p1_total = self.game.total_score(self.game.players[0])
            p2_total = self.game.total_score(self.game.players[1])
            if p1_total > p2_total:
                winner = self.game.players[0]
            elif p2_total > p1_total:
                winner = self.game.players[1]
            else:
                winner = None
            embed = view.generate_embed(final=True, winner=winner)
            view.stop()
            await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=None)
        else:
            await view.update_message(interaction)

class ChallengeYazy(discord.ui.View):
    def __init__(self, challenger: discord.User, opponent: discord.User):
        super().__init__(timeout=120)
        self.challenger = challenger
        self.opponent = opponent
        self.message = None

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged opponent can accept!", ephemeral=True)
            return
        # Delete the challenge message first.
        await interaction.delete_original_response()
        game = YazyGame(self.challenger, self.opponent)
        game.roll_all_dice()
        game_view = YazyView(game)
        embed = game_view.generate_embed()
        content = f"Current Turn: {game.current_player.mention}"
        msg = await interaction.channel.send(content=content, embed=embed, view=game_view)
        game_view.message = msg
        self.stop()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged opponent can reject!", ephemeral=True)
            return
        embed = discord.Embed(title="Yazy Challenge", description="Challenge rejected.")
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    async def on_timeout(self):
        if self.message:
            embed = discord.Embed(title="Yazy Challenge", description="Challenge expired due to no response.")
            await self.message.edit(embed=embed, view=None)

@bot.tree.command(name="yazy", description="Challenge someone to a game of Yazy!")
async def yazy(interaction: discord.Interaction, opponent: discord.User):

    await interaction.response.send_message("In development.")
    return

    if await is_command_blocked(interaction.guild.id, interaction.user.id, "memory"):
        await interaction.response.send_message("You are blocked from using memory command.")
        return
    
    if opponent.bot or opponent.id == interaction.user.id:
        await interaction.response.send_message("Please choose a valid (non-bot) opponent!", ephemeral=True)
        return
    msg = f"**Yazy Challenge!**\n{interaction.user.mention} has challenged {opponent.mention} to a game of Yazy! Do you accept?"

    view = ChallengeYazy(challenger=interaction.user, opponent=opponent)
    await interaction.response.send_message(msg, view=view)
    view.message = await interaction.original_response()









@bot.command(name="lb", aliases=["leaderboard"],
             help="View the top 10 Kero holders or Slave owners or Message senders in the Server.\n**Syntax**: lb kero or lb slave")
async def lb(ctx, leaderboard_type: str = "msg"):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "lb" or "leaderboard"):
        await ctx.reply("You are blocked from using `leaderboard`.")
        return

    if leaderboard_type.lower() not in ["kero", "slave", "msg"]:
        await ctx.send("Invalid leaderboard type! Use `kero` or `slave` or `msg`.")
        return

    await generate_leaderboard(ctx, leaderboard_type.lower(), "Today")









def get_all_commands():
    bot_commands = bot.commands
    slash_commands = bot.tree.get_commands()
    all_commands = list(bot_commands)
    for sc in slash_commands:
        if not any(sc.name.lower() == cmd.name.lower() for cmd in all_commands):
            all_commands.append(sc)
    return all_commands

CATEGORY_MAP = {
    "🛡️ Moderation": ['mute', 'unmute', 'ban', 'unban', 'massban', 'setrole', 'setperm', 'role', 'showperm',
                       'setnick', 'purge', 'modlogs', 'purgereaction', 'stealsticker', 'massunban'],
    "🛠️ Config": ["setprefix", 'botperm', 'giveperm', 'takeperm', 'setup', "selfprefix", 'ping'],
    "👻 Fun": ['say', 'spam', 'roleroulette', 'cf', 'diceroll', 'jackpot', 'tower', 'fetchwater', 'bakebread',
               'fanmaster', 'minerock', 'shinecrown', 'echo', 'buckshot', 'buckshot_help', 'hello', 'colorwars',
               'colorwars_help', 'memory', 'memory_help', 'waifu', 'wtags'],
    "💰 Economy": ['shop', 'daily', 'slbuy', 'beg', 'wallet', 'chkprice', 'lb', 'buycmd', 'auction', 'trade',
                   'give', 'tip', 'tribute'],
    "🤖 User": ['whois', 'av', 'afk', 'img', 'msgcount', 'bn', 'ping', 'help', 'slshow', 'slinfo', 'wish',
                'sljail', 'slunjail', 'slkick', 'slmute', 'slunmute', 'slsetnick', 'slrole',
                'slwhip', 'slrelease', 'slrefund', 'escape'],
}

def categorize_commands(all_commands):
    categories = {"🛡️ Moderation": [], "🤖 User": [], "👻 Fun": [], "💰 Economy": [], "🛠️ Config": [], "🎬 Actions": []}
    for command in all_commands:
        placed = False
        for cat, names in CATEGORY_MAP.items():
            if command.name in names:
                categories[cat].append(command)
                placed = True
                break
        if not placed and command.name in ACTIONS:
            categories["🎬 Actions"].append(command)
    return categories

def _thumbnail_file():
    try:
        return discord.File("thumbnail.png", filename="thumbnail.png")
    except (FileNotFoundError, OSError):
        return None

def build_category_embeds(categories, syntax_hint, use_thumbnail):
    embeds = {}
    for category, command_list in categories.items():
        if not command_list:
            continue
        commands_display = "  ".join(f"`{cmd.name}`" for cmd in command_list)
        embed = discord.Embed(
            title=f"{category} Commands",
            description=f"**🔎 To learn more about a specific command, type:** `{syntax_hint}`\n\n{commands_display}",
            color=discord.Color.random(),
        )
        if use_thumbnail:
            embed.set_thumbnail(url="attachment://thumbnail.png")
        embed.set_footer(text="Slickey Bot | Helping You Rule Your Server!")
        embeds[category] = embed
    return embeds

def build_command_embed(command, categories, fallback_prefix):
    command_help = getattr(command, "help", None) or getattr(command, "description", None) or "No description available."

    if "**Syntax**:" in command_help:
        description, syntax = command_help.split("**Syntax**:", 1)
    else:
        description, syntax = command_help, None
    description = description.strip() if description else "No description available."

    is_slash = isinstance(command, (discord.app_commands.Command, discord.app_commands.Group))
    cmd_prefix = "/" if is_slash else fallback_prefix
    syntax = f"`{cmd_prefix}{syntax.strip()}`" if syntax else "No syntax specified."

    embed = discord.Embed(
        title=f"🔍 Command: `{cmd_prefix}{command.name}`",
        description=description,
        color=discord.Color.green(),
    )
    embed.add_field(
        name="📂 Category",
        value=next((k for k, v in categories.items() if command in v), "Unknown"),
        inline=False,
    )
    embed.add_field(name="📖 Syntax", value=syntax, inline=False)

    cd = None
    try:
        if hasattr(command, "_buckets"):
            cooldown_obj = command._buckets._cooldown
            if cooldown_obj:
                cd = f"{cooldown_obj.rate} use(s) per {cooldown_obj.per}s"
        elif hasattr(command, "cooldown") and command.cooldown:
            cobj = command.cooldown
            cd = f"{cobj.rate} use(s) per {cobj.per}s"
    except Exception:
        cd = None
    embed.add_field(name="⏱️ Cooldown", value=cd or "None", inline=False)

    aliases = getattr(command, "aliases", [])
    embed.add_field(name="🔀 Aliases", value=", ".join(aliases) if aliases else "None", inline=False)
    return embed

@bot.command(name="help", aliases=["Help", "HELP"], help="Display all the commands organized by category.\n**Syntax**: help or help <command_name>")
@commands.guild_only()
async def help_command(ctx, command_name: str = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "help"):
        await ctx.reply("You are blocked from using help command.")
        return

    prefix = ctx.prefix

    all_commands = get_all_commands()
    categories = categorize_commands(all_commands)

    if command_name:
        command = bot.get_command(command_name) or bot.tree.get_command(command_name)
        if not command:
            await ctx.send(f"❌ Command `{command_name}` not found.")
            return
        await ctx.send(embed=build_command_embed(command, categories, prefix))
        return

    thumb_probe = _thumbnail_file()
    use_thumb = thumb_probe is not None
    embeds = build_category_embeds(categories, f"{prefix}help <command_name>", use_thumbnail=use_thumb)
    if not embeds:
        await ctx.send("No commands available to display.")
        return

    class CategoryDropdown(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=category, description=f"View commands in the {category} category.")
                for category in embeds.keys()
            ]
            super().__init__(placeholder="💡 Select a category to explore commands!", min_values=1, max_values=1,
                              options=options)

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message(
                    "⛔ Only the command invoker can interact with this menu.", ephemeral=True)
            thumb = _thumbnail_file()
            await interaction.response.edit_message(
                embed=embeds[self.values[0]], attachments=[thumb] if thumb else [])

    class HelpMenuView(discord.ui.View):
        def __init__(self, author):
            super().__init__(timeout=180)
            self.author = author
            self.add_item(CategoryDropdown())

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.author.id

    first_category = next(iter(embeds))
    initial_embed = embeds[first_category]
    if use_thumb:
        await ctx.send(embed=initial_embed, file=thumb_probe, view=HelpMenuView(ctx.author))
    else:
        await ctx.send(embed=initial_embed, view=HelpMenuView(ctx.author))
        
        
# @bot.command(name="help", aliases=["Help", "HELP"], help="Display all the commands organized by category.\n**Syntax**: help or help <command_name>")
# @commands.guild_only()
# async def help_command(ctx, command_name: str = None):
#     if await is_command_blocked(ctx.guild.id, ctx.author.id, "help"):
#         await ctx.reply("You are blocked from using help command.")
#         return

#     prefix = ctx.prefix
#     global prefixx
#     prefixx = ctx.prefix
#     bot_commands = bot.commands
#     slash_commands = bot.tree.get_commands()
#     all_commands = list(bot_commands)
#     for sc in slash_commands:
#         if not any(sc.name.lower() == cmd.name.lower() for cmd in all_commands):
#             all_commands.append(sc)

#     categories = {"🛡️ Moderation": [], "🤖 User": [], "👻 Fun": [], "💰 Economy": [], "🛠️ Config": [], "🎬 Actions": []}

#     for command in all_commands:
#         if command.name in ['mute', 'unmute', 'ban', 'unban', 'massban', 'setrole', 'setperm', 'role', 'showperm',
#                             'setnick', 'purge', 'modlogs', 'purgereaction', 'stealsticker', 'massunban']:
#             categories["🛡️ Moderation"].append(command)
#         elif command.name in ["setprefix", 'botperm', 'giveperm', 'takeperm', 'setup', "selfprefix", 'ping']:
#             categories["🛠️ Config"].append(command)
#         elif command.name in ['say', 'spam', 'roleroulette', 'cf', 'diceroll', 'jackpot', 'tower', 'fetchwater', 'bakebread',
#                               'fanmaster', 'minerock', 'shinecrown', 'echo', 'buckshot', 'buckshot_help', 'hello', 'colorwars', 'colorwars_help', 'memory', 'memory_help', 'waifu', 'wtags']:
#             categories["👻 Fun"].append(command)
#         elif command.name in ['shop', 'daily', 'slbuy', 'beg', 'wallet', 'chkprice', 'lb', 'buycmd', 'auction', 'trade',
#                               'give', 'tip', 'tribute']:
#             categories["💰 Economy"].append(command)
#         elif command.name in ['whois', 'av', 'afk', 'img', 'msgcount', 'bn', 'ping', 'help', 'slshow', 'slinfo', 'wish',
#                               'sljail', 'slunjail', 'slkick', 'slmute', 'slmute', 'slunmute', 'slsetnick', 'slrole',
#                               'slwhip', 'slrelease', 'slrefund', 'escape']:
#             categories["🤖 User"].append(command)
#         elif command.name in ACTIONS:
#             categories["🎬 Actions"].append(command)


#     if command_name:
#         command = bot.get_command(command_name)
#         if not command:
#             command = bot.tree.get_command(command_name)
#         if not command:
#             await ctx.send(f"❌ Command `{command_name}` not found.")
#             return

#         command_help = getattr(command, "help", None)
#         if not command_help:
#             command_help = getattr(command, "description", "No description available.")

#         if "**Syntax**:" in command_help:
#             description, syntax = command_help.split("**Syntax**:")
#         else:
#             description, syntax = command_help, None
#         description = description.strip() if description else "No description available."
#         cmd_prefix = "/" if isinstance(command,
#                                        (discord.app_commands.Command, discord.app_commands.Group)) else ctx.prefix
#         syntax = f"`{cmd_prefix}{syntax.strip()}`" if syntax else "No syntax specified."

#         embed = discord.Embed(
#             title=f"🔍 Command: `{cmd_prefix}{command.name}`",
#             description=description,
#             color=discord.Color.green(),)
        
#         embed.add_field(
#             name="📂 Category",
#             value=f"{next((k for k, v in categories.items() if command in v), 'Unknown')}",
#             inline=False, )
        
#         embed.add_field(name="📖 Syntax", value=syntax, inline=False)

#         try:
#             # for text commands
#             cd = None
#             if hasattr(command, "_buckets"):
#                 cooldown_obj = command._buckets._cooldown
#                 if cooldown_obj:
#                     cd = f"{cooldown_obj.rate} use(s) per {cooldown_obj.per}s"
#             # for slash commands
#             elif hasattr(command, "cooldown") and command.cooldown:
#                 cobj = command.cooldown
#                 cd = f"{cobj.rate} use(s) per {cobj.per}s"
#         except Exception:
#             cd = None
#         embed.add_field(
#             name="⏱️ Cooldown",
#             value=cd or "None",
#             inline=False
#         )
        
#         aliases = getattr(command, "aliases", [])
#         alias_str = ", ".join(aliases) if aliases else "None"
#         embed.add_field(name="🔀 Aliases", value=alias_str, inline=False)

#         await ctx.send(embed=embed)
#         return

#     embeds = {}
#     for category, command_list in categories.items():
#         if not command_list:
#             continue

#         commands_display = "  ".join(f"`{cmd.name}`" for cmd in command_list)

#         embed = discord.Embed(title=f"{category} Commands",
#                               description=f"**🔎 To learn more about a specific command, type:** `{prefix}help <command_name>`\n\n{commands_display}",
#                               color=discord.Color.random(), )

#         embed.set_thumbnail(url="attachment://thumbnail.png")
#         embed.set_footer(text="Slickey Bot | Helping You Rule Your Server!")
#         embeds[category] = embed

#     # Dropdown menu
#     class CategoryDropdown(discord.ui.Select):
#         def __init__(self):
#             options = [
#                 discord.SelectOption(label=category, description=f"View commands in the {category} category.")
#                 for category in categories.keys()
#             ]
#             super().__init__(placeholder="💡 Select a category to explore commands!", min_values=1, max_values=1,
#                              options=options)

#         async def callback(self, interaction: discord.Interaction):
#             if interaction.user.id != ctx.author.id:
#                 await interaction.response.send_message("⛔ Only the command invoker can interact with this menu.",
#                                                         ephemeral=True)
#                 return

#             selected_category = self.values[0]
#             embed = embeds[selected_category]
#             file = discord.File("thumbnail.png", filename="thumbnail.png")
#             await interaction.response.edit_message(embed=embed, attachments=[file])

#     # View with the dropdown menu
#     class HelpMenuView(discord.ui.View):
#         def __init__(self, author):
#             super().__init__(timeout=180)
#             self.author = author
#             self.add_item(CategoryDropdown())

#         async def interaction_check(self, interaction: discord.Interaction) -> bool:
#             return interaction.user.id == self.author.id

#     initial_embed = embeds[list(categories.keys())[0]]
#     initial_file = discord.File("thumbnail.png", filename="thumbnail.png")
#     await ctx.send(embed=initial_embed, file=initial_file, view=HelpMenuView(ctx.author))


@bot.tree.command(name="help", description="Display all commands organized by category.")
@discord.app_commands.guild_only()
@discord.app_commands.describe(command_name="(Optional) The specific command to get help for")
async def slash_help_command(interaction: discord.Interaction, command_name: str = None):
    if await is_command_blocked(interaction.guild.id, interaction.user.id, "help"):
        await interaction.response.send_message("You are blocked from using help command.", ephemeral=True)
        return

    prefix = await resolve_prefix(interaction.guild_id, interaction.user.id)
    
    all_commands = get_all_commands()
    categories = categorize_commands(all_commands)

    if command_name:
        command = bot.get_command(command_name) or bot.tree.get_command(command_name)
        if not command:
            await interaction.response.send_message(f"❌ Command `{command_name}` not found.", ephemeral=True)
            return
        await interaction.response.send_message(embed=build_command_embed(command, categories, prefix))
        return

    thumb_probe = _thumbnail_file()
    use_thumb = thumb_probe is not None
    embeds = build_category_embeds(categories, "/help command_name:<command>", use_thumbnail=use_thumb)
    if not embeds:
        await interaction.response.send_message("No commands available to display.", ephemeral=True)
        return

    class CategoryDropdown(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=category, description=f"View commands in the {category} category.")
                for category in embeds.keys()
            ]
            super().__init__(placeholder="💡 Select a category to explore commands!", min_values=1, max_values=1,
                              options=options)

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.view.author.id:
                return await interaction.response.send_message(
                    "⛔ Only the command invoker can interact with this menu.", ephemeral=True)
            thumb = _thumbnail_file()
            await interaction.response.edit_message(
                embed=embeds[self.values[0]], attachments=[thumb] if thumb else [])

    class HelpMenuView(discord.ui.View):
        def __init__(self, author):
            super().__init__(timeout=180)
            self.author = author
            self.add_item(CategoryDropdown())

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.author.id

    first_category = next(iter(embeds))
    initial_embed = embeds[first_category]
    if use_thumb:
        await interaction.response.send_message(embed=initial_embed, file=thumb_probe, view=HelpMenuView(interaction.user))
    else:
        await interaction.response.send_message(embed=initial_embed, view=HelpMenuView(interaction.user))
        
        
# @bot.tree.command(name="help",description="Display all commands organized by category.")
# @discord.app_commands.guild_only()
# @discord.app_commands.describe(command_name="(Optional) The specific command to get help for")
# async def slash_help_command(interaction: discord.Interaction, command_name: str = None):

#     await interaction.response.send_message("In Development", ephemeral=True)
#     return

#     if await is_command_blocked(interaction.guild.id, interaction.user.id, "help"):
#         await interaction.response.send_message("You are blocked from using help command.", ephemeral=True)
#         return

#     prefix = interaction.pref
#     bot_commands = bot.commands
#     slash_commands = bot.tree.get_commands()
#     all_commands = list(bot_commands)
#     for sc in slash_commands:
#         if not any(sc.name.lower() == cmd.name.lower() for cmd in all_commands):
#             all_commands.append(sc)

#     categories = {"🛡️ Moderation": [], "🤖 User": [], "👻 Fun": [], "💰 Economy": [], "🛠️ Config": [], "🎬 Actions": []}

#     for command in all_commands:
#         if command.name in ['mute', 'unmute', 'ban', 'unban', 'massban', 'setrole', 'setperm', 'role', 'showperm',
#                             'setnick', 'purge', 'modlogs', 'purgereaction', 'stealsticker', 'massunban']:
#             categories["🛡️ Moderation"].append(command)
#         elif command.name in ["setprefix", 'botperm', 'giveperm', 'takeperm', 'setup', "selfprefix", 'ping']:
#             categories["🛠️ Config"].append(command)
#         elif command.name in ['say', 'spam', 'roleroulette', 'cf', 'diceroll', 'jackpot', 'tower', 'fetchwater', 'bakebread',
#                               'fanmaster', 'minerock', 'shinecrown', 'echo', 'buckshot', 'buckshot_help', 'hello', 'colorwars', 'colorwars_help', 'memory', 'memory_help']:
#             categories["👻 Fun"].append(command)
#         elif command.name in ['shop', 'daily', 'slbuy', 'beg', 'wallet', 'chkprice', 'lb', 'buycmd', 'auction', 'trade',
#                               'give', 'tip', 'tribute']:
#             categories["💰 Economy"].append(command)
#         elif command.name in ['whois', 'av', 'afk', 'img', 'msgcount', 'bn', 'ping', 'help', 'slshow', 'slinfo', 'wish',
#                               'sljail', 'slunjail', 'slkick', 'slmute', 'slmute', 'slunmute', 'slsetnick', 'slrole',
#                               'slwhip', 'slrelease', 'slrefund', 'escape']:
#             categories["🤖 User"].append(command)
#         elif command.name in ACTIONS:
#             categories["🎬 Actions"].append(command)

#     if command_name:
#         command = bot.get_command(command_name)
#         if not command:
#             command = bot.tree.get_command(command_name)
#         if not command:
#             interaction.response.send_message(f"❌ Command `{command_name}` not found.", ephemeral=True)
#             return

#         command_help = getattr(command, "help", None)
#         if not command_help:
#             command_help = getattr(command, "description", "No description available.")

#         if "**Syntax**:" in command_help:
#             description, syntax = command_help.split("**Syntax**:")
#         else:
#             description, syntax = command_help, None
#         description = description.strip() if description else "No description available."
#         cmd_prefix = "/" if isinstance(command,
#                                        (discord.app_commands.Command, discord.app_commands.Group)) else ctx.prefix
#         syntax = f"`{cmd_prefix}{syntax.strip()}`" if syntax else "No syntax specified."

#         embed = discord.Embed(
#             title=f"🔍 Command: `{cmd_prefix}{command.name}`",
#             description=description,
#             color=discord.Color.green(),)
        
#         embed.add_field(
#             name="📂 Category",
#             value=f"{next((k for k, v in categories.items() if command in v), 'Unknown')}",
#             inline=False, )
        
#         embed.add_field(name="📖 Syntax", value=syntax, inline=False)

#         # ─── Cooldown field ─────────────────────────────────────────
        
        
#         aliases = getattr(command, "aliases", [])
#         alias_str = ", ".join(aliases) if aliases else "None"
#         embed.add_field(name="🔀 Aliases", value=alias_str, inline=False)

#         await interaction.response.send_message(embed=embed)
#         return

#     embeds = {}
#     for category, command_list in categories.items():
#         if not command_list:
#             continue

#         commands_display = "  ".join(f"`{cmd.name}`" for cmd in command_list)

#         embed = discord.Embed(title=f"{category} Commands",
#                               description=f"**🔎 To learn more about a specific command, type:** `{prefix}help <command_name>`\n\n{commands_display}",
#                               color=discord.Color.random(), )

#         embed.set_thumbnail(url="attachment://thumbnail.png")
#         embed.set_footer(text="Slickey Bot | Helping You Rule Your Server!")
#         embeds[category] = embed

#     # Dropdown menu
#     class CategoryDropdown(discord.ui.Select):
#         def __init__(self):
#             options = [
#                 discord.SelectOption(label=category, description=f"View commands in the {category} category.")
#                 for category in categories.keys()
#             ]
#             super().__init__(placeholder="💡 Select a category to explore commands!", min_values=1, max_values=1,
#                              options=options)

#         async def callback(self, interaction: discord.Interaction):
#             if interaction.user.id != self.view.author.id:
#                 await interaction.response.send_message("⛔ Only the command invoker can interact with this menu.", ephemeral=True)
#                 return

#             selected_category = self.values[0]
#             embed = embeds[selected_category]
#             file = discord.File("thumbnail.png", filename="thumbnail.png")
#             await interaction.response.edit_message(embed=embed, attachments=[file])

#     # View with the dropdown menu
#     class HelpMenuView(discord.ui.View):
#         def __init__(self, author):
#             super().__init__(timeout=180)
#             self.author = author
#             self.add_item(CategoryDropdown())

#         async def interaction_check(self, interaction: discord.Interaction) -> bool:
#             return interaction.user.id == self.author.id

#     initial_embed = embeds[list(categories.keys())[0]]
#     initial_file = discord.File("thumbnail.png", filename="thumbnail.png")
#     await interaction.response.send_message(embed=initial_embed, file=initial_file, view=HelpMenuView(interaction.user))


async def main():
    async with bot:
        await bot.load_extension("ai_cog")
        await bot.add_cog(permission_system.PermissionsCog(bot, lambda: utils.db_pool))
        Slickey_Secondary_.setup(bot)
        await bot.start(bada_wigu_bot_token)

asyncio.run(main())
