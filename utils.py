import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timezone
from discord import app_commands
from rapidfuzz import process, fuzz
import json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests
import random
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Select, Button, View
import math
import statistics
import asyncpg
#import psycopg2
#from psycopg2 import pool
import os
import re
from typing import Optional
from dotenv import load_dotenv
from permission_system import BOT_CREATOR_ID, effective_rank, evaluate, initialize_permission_system
load_dotenv()


supabase_dsn = os.getenv("SUPABASE_DSN")

if not supabase_dsn:
    raise ValueError("SUPABASE_DSN environment variable not set!")

db_pool = None

async def init_db_pool():
    global db_pool
    print("SUPABASE_DSN is:", supabase_dsn)
    try:
        db_pool = await asyncpg.create_pool(
            dsn=os.environ["SUPABASE_DSN"],
            min_size=1, max_size=20,
            statement_cache_size=0,
            max_inactive_connection_lifetime=120.0,
            command_timeout=20.0)
        await initialize_permission_system(db_pool)
        print("Postgres pool initialized!")
    except Exception as e:
        print(f"Pool creation failed: {e}")
        db_pool = None



# @bot.command(name='sltransfer')
# async def transferkero(ctx, amount: int, target: discord.Member = None, source: discord.Member = None):
# if is_master(ctx.author.id, ctx.guild.id):
# if not await has_permission_for_slave(ctx, ctx.author.id, target.id, "Transfer"):
# await ctx.send(f"You don't have the authority to use Transfer Kero command on {target.id}.")
# return
# if not await has_permission_for_slave(ctx, ctx.author.id, source.id, "Transfer"):
# await ctx.send(f"You don't have the authority to use Transfer Kero command on {target.id}.")
# return

# If both target and source are provided, check if they are slaves and proceed with the transfer
# if target != ctx.author.id and source != ctx.author.id:
# if await is_slave(source.id, ctx.guild.id) and await is_slave(target.id, ctx.guild.id):
# Transfer Kero between two slaves
# target_balance = await get_user_balance(target.id)
# if target_balance < amount:
# await ctx.send(f"{target.display_name} doesn't have enough Kero to transfer.")
# return
# Deduct from source, add to target
# await update_user_balance(source.id, amount)
# await update_user_balance(target.id, -amount)
# await ctx.send(
# f"**{amount} Kero** has been transferred from {target.display_name} to {source.display_name}.")
# else:
# await ctx.send("Both users must be your slaves.")
# return

# If only target is provided, check if it's a slave, and transfer from master to slave
# elif target == ctx.author.id and source != ctx.author.id:
# if #await is_slave(source.id, ctx.guild.id):

# master_balance = await get_user_balance(ctx.author.id)
# if master_balance < amount:
# await ctx.send(f"You don't have enough Kero to transfer to your slave {source.display_name}.")
# return
# Deduct from master, add to slave
# await update_user_balance(ctx.author.id, -amount)
# await update_user_balance(source.id, amount)
# await ctx.send(f"{amount} Kero has been transferred from your account to {source.display_name}.")
# else:
# await ctx.send(f"{source.display_name} is not your slave.")

# elif target != ctx.author.id and source == ctx.author.id:
# if await is_slave(target.id, ctx.guild.id):
# slave_balance = await get_user_balance(target.id)
# if slave_balance < amount:
# await ctx.send(f"{target.display_name} doesn't have enough Kero to transfer.")
# return
# Deduct from slave, add to master
# await update_user_balance(target.id, -amount)
# await update_user_balance(ctx.author.id, amount)
# await ctx.send(f"{amount} Kero has been transferred from {target.display_name} to your account.")
# else:
# await ctx.send("This user is not your slave.")
# else:
# await ctx.reply(
# "Nigga, you must have atleast one slave yourself to use this command. Go buy some slaves from `shop` and then come back.")



# @bot.command(name="slban")
# async def ban(ctx, slave: discord.Member):
#    master_id = ctx.author.id
#    slave_id = slave.id
#
#    if await is_master(ctx.author.id, ctx.guild.id):
#        if not await has_permission_for_slave(ctx, master_id, slave_id, "Ban"):
#            await ctx.send("You don't have the authority to ban this slave.")
#            return
#        await slave.ban()
#
#    else:
#        await ctx.send("You are not a master.")
#
#    await ctx.send(
#        f"Some faggot named {slave.display_name} got banned by it's master {ctx.author.mention}. Good Job bro!!")


# @bot.command(name="slunban")
# async def unban(ctx, slave_id: int):
#    master_id = ctx.author.id

#    if not await is_master(ctx.author.id, ctx.guild.id):
#        await ctx.send("You are not a master.")
#        return

#    if await is_slave(master_id, ctx.guild.id):
#        await ctx.reply("You are a slave, you cannot use that command.")
#        return

#    if not await has_permission_for_slave(ctx, master_id, slave_id, "Unban"):
#        await ctx.send("You don't have the authority to unban this slave.")
#        return

# Fetch the guild's ban list
#    banned_users = await ctx.guild.bans()
#    slave_entry = discord.utils.find(lambda entry: entry.user.id == slave_id, banned_users)

#    if not slave_entry:
#        await ctx.send("The specified user is not banned.")
#        return

#    await ctx.guild.unban(slave_entry)
#    await ctx.send(f"Your slave **{slave_entry.display_name}** has been unbanned by **{ctx.author.mention}**.")


# Compatibility alias used by legacy command handlers.  This is the Bot
# Creator bypass, not a server owner; the real owner is resolved from Discord.
BOT_OWNER_ID = BOT_CREATOR_ID

active_role_timers = {}
role_list_for_command = {}
active_begging_requests = {}
jackpot_game = {}
modified_permissions_dict = {}
active_auctions = {}
responded_messages = {}
tower_games = {}
jailed_users_data = {}
active_games = {}
color_wars = {}
memory_games = {}

key_permissions = {
    'administrator': 'Administrator',
    'manage_guild': 'Manage Server',
    'manage_channels': 'Manage Channels',
    'manage_roles': 'Manage Roles',
    'ban_members': 'Ban Members',
    'kick_members': 'Kick Members',
    'manage_emojis': 'Manage Expressions',
    'view_audit_log': 'View Audit Log',
    'manage_webhooks': 'Manage Webhooks',
    'manage_nicknames': 'Manage Nicknames',
    'moderate_members': 'Timeout Members',
    'manage_messages': 'Manage Messages',
    'mention_everyone': 'Mention Everyone',
    'mute_members': 'Mute Members',
    'deafen_members': 'Deafen Members',
    'move_members': 'Move Members'
}
mod_perms = [
    'Kick Members',
    'Ban Members',
    'Manage Roles',
    'Manage Channels',
    'Manage Messages',
    'Timeout Members',
    'Manage Nicknames',
    'Mention Everyone',
    'View Audit Log',
    'Mute Members',
    'Manage Webhooks'
]
admin_perms = [
    'Manage Server',
    'Manage Channels',
    'Manage Roles',
    'Ban Members',
    'Kick Members',
    'Manage Expressions',
    'View Audit Log',
    'Manage Webhooks',
    'Manage Nicknames',
    'Timeout Members',
    'Manage Messages',
    'Mention Everyone',
    'Mute Members',
    'Deafen Members',
    'Move Members'
]

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
PERMISSIONS_DICT = {str(i + 1): perm[0] for i, perm in enumerate(PERMISSIONS_LIST)}

db_connection = None
#setup_perm = None
masterslave_connection = None
automod_setup = None
operation_active = True



#                ------------------------------------------------------------------------------------------------------------


def is_valid_url(u: str) -> bool:
    return bool(u and re.match(r"^https?://", u))

GIFUKAI_API = "https://api.gifukai.com/v1/"



#  -----------------images-----------------
WAIFU_IM_API = "https://api.waifu.im/images"

WAIFU_IM_SFW_PNG = ["maid", "waifu", "marin-kitagawa", "mori-calliope", "raiden-shogun", "oppai", "selfies", "uniform", "kamisato-ayaka"]
WAIFU_IM_NSFW_PNG = ["ass", "hentai", "milf", "oral", "paizuri", "ecchi", "ero"]

ALL_TAGS = WAIFU_IM_SFW_PNG + WAIFU_IM_NSFW_PNG
SFW_TAGS = WAIFU_IM_SFW_PNG
NSFW_TAGS = WAIFU_IM_NSFW_PNG




GIFUKAI_ACTIONS = [
    "angry", "bite", "bleh", "blowkiss", "blush", "bonk", "bored", "bye",
    "carry", "clap", "confused", "cry", "cuddle", "dance", "eat", "facepalm",
    "feed", "handhold", "handshake", "happy", "hi", "highfive", "hug", "kick",
    "kill", "kiss", "lappillow", "laugh", "nod", "nope", "nya", "pat", "peek",
    "poke", "pout", "punch", "run", "salute", "shake", "shocked", "shoot",
    "shrug", "shy", "sip", "slap", "sleep", "smile", "smug", "spin", "stare",
    "taunt", "teehee", "think", "thumbsup", "tickle", "wag", "wallslam",
    "wave", "wink", "yawn", "yeet",
]

GIFUKAI_ALIASES = {
    "angry": ["mad", "rage"], "blowkiss": ["mwah"], "blush": ["flustered"],
    "bye": ["cya", "goodbye"], "clap": ["claps"], "cry": ["sob"],
    "cuddle": ["snuggle"], "eat": ["nom"], "hi": ["hey"],
    "kill": ["murder"], "kiss": ["peck"], "laugh": ["lmao", "lol"],
    "nod": ["agree", "yes"], "nope": ["deny", "no"], "nya": ["meow", "neko"],
    "pat": ["headpat"], "poke": ["boop"], "shocked": ["surprised"],
    "shoot": ["bang"], "shrug": ["dunno", "idk"], "sip": ["drink"],
    "sleep": ["nap", "zzz"], "stare": ["gaze"], "think": ["thinking"],
    "thumbsup": ["like"], "wallslam": ["kabedon"],
}


ACTIONS = GIFUKAI_ACTIONS  # keeps the rest of the file's `for act in ACTIONS` loops untouched

# ACTIONS = NEKOS_BEST_SFW_GIFS + WAIFU_PICS_SFW_GIFS


# ------------------------------------------------------------------------------------------------------------------------






async def find_closest_role(ctx, role_name: str):
    roles = [role.name for role in ctx.guild.roles]
    best_match = process.extractOne(role_name, roles, score_cutoff=60)

    if best_match:
        matched_role_name = best_match[0]
        confidence = best_match[1]
        matched_role = discord.utils.get(ctx.guild.roles, name=matched_role_name)
        return matched_role, confidence
    return None, 0

async def find_closest_member(ctx: commands.Context, query: str):
    name_map = {}
    for m in ctx.guild.members:
        name_map[m.display_name.lower()] = m
        name_map[m.name.lower()] = m

    best = process.extractOne(
        query.lower(),
        name_map.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=70
    )
    if not best:
        return None, 0

    # Find which member had this matching name
    matched_name, confidence, *_ = best  # best is like ("someusername", 82)
    return name_map[matched_name], confidence

async def memname_choice(action: discord.Interaction, current: str):
    guild = action.guild
    if not guild:
        return []
    members = guild.members

    filtered_members = [app_commands.Choice(name=member.display_name, value=str(member.id))
        for member in members if current.lower() in member.display_name.lower()]

    return filtered_members[:25]







def create_gun_config():
    total = random.randint(3, 10)

    lower_bound = max(1, math.ceil(total * 0.3))
    upper_bound = min(total - 1, math.floor(total * 0.7))
    if lower_bound > upper_bound:
        lower_bound, upper_bound = 1, total - 1
    loaded = random.randint(lower_bound, upper_bound)
    empty = total - loaded

    chamber = [True] * loaded + [False] * empty
    random.shuffle(chamber)
    return {"total": total, "loaded": loaded, "empty": empty, "chamber": chamber, "current_index": 0}

def deal_cards(hand_size=None):
    allowed_cards = ["Beer", "Magnifying Glass", "Cigarette Pack", "Handcuffs", "Hand Saw", "Burner Phone", "Inverter", "Crowbar", "Expired Medicine"]
    if hand_size is None:
        hand_size = random.randint(2, 5)
    return random.choices(allowed_cards, k=hand_size)

def calculate_hand_size(total):
    base = total * 0.4
    hand_size = round(base) + random.choice([-1, 0, 0, 1])
    return max(1, min(5, hand_size))

def create_initial_game_state(challenger_id, challenged_id):
    max_health = random.randint(4, 8)
    gun_config = create_gun_config()
    hand_size = calculate_hand_size(gun_config["total"])
    return {
        "challenger": str(challenger_id),
        "challenged": str(challenged_id),
        "max_health": max_health,
        "health": {str(challenger_id): max_health, str(challenged_id): max_health},
        "gun_config": gun_config,
        "hands": {str(challenger_id): deal_cards(hand_size), str(challenged_id): deal_cards(hand_size)},
        "turn": random.choice([challenger_id, challenged_id]),
        "round": 1,
        "skip_turn": {str(challenger_id): 0, str(challenged_id): 0},
        "damage_multiplier": {}
    }

async def create_game_board_embed(guild: discord.Guild, game_state: dict):
    challenger = guild.get_member(int(game_state["challenger"]))
    challenged = guild.get_member(int(game_state["challenged"]))

    gun = game_state["gun_config"]
    chamber = gun["chamber"]
    gun_status = f"Total:  {gun['total']}   |  Loaded:  **{gun['loaded']}**  🔴  |  Empty: **{gun['empty']}**  ⚪"
    current_index = gun["current_index"]

    shell_emojis = []
    for i, loaded in enumerate(chamber):
        if i < current_index:
            shell_emojis.append("❌")
        else:
            shell_emojis.append("🟤")
    shell_display = "  ".join(shell_emojis)

    card_emojis = {
        "Beer": "🍺",
        "Magnifying Glass": "🔍",
        "Cigarette Pack": "🚬",
        "Handcuffs": "🔒",
        "Hand Saw": "🪚",
        "Burner Phone": "📞",
        "Inverter": "🔄",
        "Crowbar": "🔨",
        "Expired Medicine": "💊"
    }

    def format_hand(hand):
        return "   ".join(card_emojis.get(card, card) for card in hand) if hand else "None"

    challenger_hand = format_hand(game_state["hands"].get(str(challenger.id), []))
    challenged_hand = format_hand(game_state["hands"].get(str(challenged.id), []))

    embed = discord.Embed(title="Buckshot Roulette", color=discord.Color.dark_gold())
    embed.add_field(
        name="🔫 Gun Status\n\n\n",
        value=f"{gun_status}\n\nShells:  {shell_display}\n\n\n",
        inline=False
    )
    embed.add_field(
        name=f"👤 {challenger.display_name}",
        value=f"\n\n\n**Health: {game_state['health'][str(challenger.id)]}**\n\n**Cards:** {challenger_hand}",
        inline=True
    )
    embed.add_field(
        name=f"👤 {challenged.display_name}",
        value=f"**Health: {game_state['health'][str(challenged.id)]}**\n\n**Cards:** {challenged_hand}",
        inline=True
    )

    if game_state.get("action_log"):
        embed.add_field(name="\n\n📜 Actions", value="\n".join(game_state["action_log"][-4:]), inline=False)

    embed.set_footer(text=f" Round: {game_state['round']}")

    return embed







class ColorWarButton(discord.ui.Button):
    def __init__(self, game_id, x, y):
        empty_emoji = discord.PartialEmoji(name="⬜")  # Or simply leave label for text
        super().__init__(style=discord.ButtonStyle.secondary, label="", emoji=empty_emoji, custom_id=f"{game_id}_{x}_{y}")
        self.x = x
        self.y = y
        self.game_id = game_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        game = color_wars.get(self.game_id)
        if not game:
            await interaction.followup.send("Game not found.", ephemeral=True)
            return

        if interaction.user.id not in [game["player1"], game["player2"]]:
            await interaction.followup.send("You're not in this game!", ephemeral=True)
            return

        if interaction.user.id != game["current_turn"]:
            await interaction.followup.send("Not your turn!", ephemeral=True)
            return

        if game.get("processing"):
            await interaction.followup.send("Still resolving the last move, hang on!", ephemeral=True)
            return
        game["processing"] = True

        player_color = "red" if interaction.user.id == game["player1"] else "blue"
        grid = game["grid"]
        try:
            parts = self.custom_id.split("_")
            row = int(parts[-2])
            col = int(parts[-1])
        except Exception:
            await interaction.followup.send("Internal error: invalid button data.", ephemeral=True)
            return

        cell = grid[row][col]

        # First move: allow tapping an empty cell or own bubble.
        if not game["first_move_done"][interaction.user.id]:
            if cell is not None and cell["color"] != player_color:
                await interaction.followup.send("For your first move, you must tap an empty cell or your own bubble!", ephemeral=True)
                return
            if cell is None:
                grid[row][col] = {"color": player_color, "dots": 3}
            else:
                grid[row][col]["dots"] += 1
            game["first_move_done"][interaction.user.id] = True
        else:
            # Subsequent moves: Only allow tapping your own bubble.
            if cell is None or cell["color"] != player_color:
                await interaction.followup.send("You can only tap a square with your own bubble!", ephemeral=True)
                return
            grid[row][col]["dots"] += 1

        if grid[row][col]["dots"] >= 4:
            await process_chain_reactions(game, interaction)

        red_points, blue_points = update_points(game)

        for item in game["view"].children:
            if isinstance(item, ColorWarButton):
                xi, yj = item.x, item.y
                new_emoji = get_cell_emoji(game["grid"][xi][yj])
                if new_emoji.startswith("<:"):
                    parts = new_emoji.strip("<>").split(":")
                    item.emoji = discord.PartialEmoji(name=parts[1], id=int(parts[2]))
                else:
                    item.emoji = new_emoji

        # Check win condition only if both have moved.
        if game["first_move_done"][game["player1"]] and game["first_move_done"][game["player2"]]:
            winner_color = check_win_condition(grid)
            if winner_color:
                for item in game["view"].children:
                    item.disabled = True
                if winner_color == "draw":
                    await game["message"].edit(content="Game Over! Mutual annihilation — it's a **draw**!", view=game["view"])
                else:
                    win_id = game["player1"] if winner_color == "red" else game["player2"]
                    await game["message"].edit(content=f"Game Over! **<@{win_id}> wins!**", view=game["view"])
                if "forfeit_message" in game:
                    try:
                        await game["forfeit_message"].delete()
                    except Exception:
                        pass
                color_wars.pop(self.game_id, None)
                return

        # Toggle turn.
        game["current_turn"] = game["player2"] if game["current_turn"] == game["player1"] else game["player1"]

        for item in game["view"].children:
            if isinstance(item, ColorWarButton):
                xi, yj = item.x, item.y
                new_emoji = get_cell_emoji(game["grid"][xi][yj])
                # Convert new_emoji string to a PartialEmoji if it's custom. For example:
                if new_emoji.startswith("<:"):
                    # Extract name and id from format "<:name:id>"
                    parts = new_emoji.strip("<>").split(":")
                    item.emoji = discord.PartialEmoji(name=parts[1], id=int(parts[2]))
                else:
                    item.emoji = new_emoji  # For standard emoji


        new_content = f"**Color War Game**\n\nRed Points: **{red_points}** | Blue Points: **{blue_points}**\n\nCurrent Turn: <@{game['current_turn']}>"
        game["processing"] = False
        await game['message'].edit(content=new_content, view=game["view"])


def create_empty_grid():
    return [[None for _ in range(5)] for _ in range(5)]

def get_cell_emoji(cell):
    if cell is None:
        return "⬜"  # empty cell
    else:
        if cell["color"] == "red":
            if cell["dots"] == 1:
                return "<:red1:1345132322709573682>"
            elif cell["dots"] == 2:
                return "<:red2:1345132324806852690>"
            elif cell["dots"] == 3:
                return "<:red3:1345132327621234828>"
            else:
                return "<:red4:1345132330901180518>"
        else:
            if cell["dots"] == 1:
                return "<:blue1:1345124821557706792>"
            elif cell["dots"] == 2:
                return "<:blue2:1345124824367890552>"
            elif cell["dots"] == 3:
                return "<:blue3:1345124193586647050>"
            else:
                return "<:blue4:1345124482595160176>"


def check_win_condition(grid):
    red_exists = any(cell is not None and cell["color"] == "red" for row in grid for cell in row)
    blue_exists = any(cell is not None and cell["color"] == "blue" for row in grid for cell in row)
    if not red_exists and not blue_exists:
        return "draw"
    if not red_exists:
        return "blue"
    if not blue_exists:
        return "red"
    return None

async def process_chain_reactions(game, interaction):
    grid = game["grid"]
    chain_active = True
    while chain_active:
        chain_active = False
        burst_cells = []
        for i in range(5):
            for j in range(5):
                cell = grid[i][j]
                if cell is not None and cell["dots"] >= 4:
                    burst_cells.append((i, j))
        if burst_cells:
            chain_active = True
            for i, j in burst_cells:
                bubble_color = grid[i][j]["color"]
                grid[i][j] = None  # Original cell becomes empty
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < 5 and 0 <= nj < 5:
                        neighbor = grid[ni][nj]
                        if neighbor is None:
                            grid[ni][nj] = {"color": bubble_color, "dots": 1}
                        else:
                            grid[ni][nj] = {"color": bubble_color, "dots": neighbor["dots"] + 1}
            red_points = sum(1 for row in grid for cell in row if cell and cell["color"] == "red")
            blue_points = sum(1 for row in grid for cell in row if cell and cell["color"] == "blue")
            new_content = f"**Color War Game**\n\nRed Points: **{red_points}** | Blue Points: **{blue_points}**\n\nCurrent Turn: <@{game['current_turn']}>"
            for item in game["view"].children:
                if isinstance(item, ColorWarButton):
                    xi, yj = item.x, item.y
                    new_emoji = get_cell_emoji(game["grid"][xi][yj])
                    if new_emoji.startswith("<:"):
                        parts = new_emoji.strip("<>").split(":")
                        item.emoji = discord.PartialEmoji(name=parts[1], id=int(parts[2]))
                    else:
                        item.emoji = new_emoji
            await game["message"].edit(content=new_content, view=game["view"])

            await asyncio.sleep(0.5)
    game["grid"] = grid

def update_points(game):
    grid = game["grid"]
    red_points = sum(1 for row in grid for cell in row if cell is not None and cell["color"] == "red")
    blue_points = sum(1 for row in grid for cell in row if cell is not None and cell["color"] == "blue")
    game["red_points"] = red_points
    game["blue_points"] = blue_points
    return red_points, blue_points




def update_game_content(game):
    current_turn = f"<@{game['current_turn']}>"
    return (
        f"**Memory Game**\n"
        f"Current Turn: {current_turn}\n"
        f"**{game['player1_name']}**: {game['scores'][str(game['player1'])]}\n"
        f"**{game['player2_name']}**: {game['scores'][str(game['player2'])]}")

def determine_winner(game):
    score1 = game["scores"][str(game["player1"])]
    score2 = game["scores"][str(game["player2"])]
    if score1 > score2:
        return game["player1"]
    elif score2 > score1:
        return game["player2"]
    else:
        return None  # tie








# <---REMOVE---> Superseded permission compatibility block; the active v2
# helpers are defined near the end of this module.
PERM_LEVELS = {
    'normal': 0,
    'command': 1,
    'moderator': 2,
    'admin': 3,
    'authorized': 4,
    'owner': 5
}

async def get_user_level(guild_id: int, user_id: int):
    """Compatibility helper returning custom-role rank, never a legacy level."""
    return await effective_rank(db_pool, guild_id, user_id)


async def only_for_setprefix(guild_id: int, user_id: int) -> bool:
    level = await get_user_level(guild_id, user_id)
    
    
    #roles = await get_user_level(guild_id, user_id)
    #if not isinstance(roles, (list, tuple)):
    #    roles = [roles]

    #allowed_roles = [3, 4, 5]
    #if any(role in allowed_roles for role in roles):
    return True if level >= 3 else False


async def is_authorized_or_not(context, guild_id: int, user_id: int, command_name: str) -> bool:
    if hasattr(context, 'user'):  # Interaction
        author = context.user
        guild = context.guild
        reply = lambda message: context.response.send_message(message, ephemeral=True)
    elif hasattr(context, 'author'):  # Context
        author = context.author
        guild = context.guild
        reply = context.reply
    else:
        raise ValueError("Invalid object passed: must be a Context or Interaction.")

    decision = await evaluate(
        db_pool, guild_id=guild_id, user_id=user_id, guild_owner_id=getattr(guild, "owner_id", None),
        command_name=command_name, channel_id=getattr(context.channel, "id", None),
        category_id=getattr(context.channel, "category_id", None),
    )
    if not decision.allowed:
        await reply(f"You are blocked from using {command_name} command. {decision.reason}.")
        return False

    # An explicit new-policy allow is authoritative.  Otherwise, retain the
    # historical ladder until every command has been migrated from it.
    if decision.matched_rule_id is not None or decision.reason in {"Bot Creator bypass", "Current Discord server owner"}:
        return True

    if await is_command_blocked(guild_id, user_id, command_name):
        await reply(f"You are blocked from using {command_name} command.")
        return False

    level = await get_user_level(guild_id, user_id)

    if level >= 2:
        return True

    if level == 1:
        has_perm = await has_command_permission(guild.id, author.id, command_name)
        if not has_perm:
            await reply(f"You don’t have permission to run `{command_name}`.")
            return False
        return True

    await reply(f"You don't have perms to execute {command_name} command.")
    return False


async def is_command_blocked(guild_id: int, user_id: int, command_name: str) -> bool:
    if db_pool is None:
        return False

    sql = """
    SELECT EXISTS(
      SELECT 1
        FROM blocked_commands
       WHERE guild_id = $1
         AND user_id = $2
         AND command_name= $3
    );
    """

    return await db_pool.fetchval(sql, guild_id, user_id, command_name)


async def has_command_permission(guild_id: int, user_id: int, command_name: str) -> bool:

    if db_pool is None:
        return False
    
    sql = """
    SELECT EXISTS(
      SELECT 1
        FROM command_permissions
       WHERE guild_id = $1
         AND user_id = $2
         AND command_name = $3
    );"""

    return await db_pool.fetchval(sql, guild_id, user_id, command_name)


async def permissions_check_decorator(context, target, command_name):
    if hasattr(context, 'user'):  # Interaction
        author = context.user
        guild = context.guild
        reply_method = lambda message: context.response.send_message(message, ephemeral=True)
    elif hasattr(context, 'author'):  # Context
        author = context.author
        guild = context.guild
        reply_method = context.reply
    else:
        raise ValueError("Invalid object passed: must be a Context or Interaction.")

    decision = await evaluate(
        db_pool, guild_id=guild.id, user_id=author.id, guild_owner_id=getattr(guild, "owner_id", None),
        command_name=command_name, channel_id=getattr(context.channel, "id", None),
        category_id=getattr(context.channel, "category_id", None),
    )
    if not decision.allowed:
        await reply_method(f"You are blocked from using `{command_name}`. {decision.reason}.")
        return False

    if author.id == BOT_OWNER_ID or decision.matched_rule_id is not None or decision.reason == "Current Discord server owner":
        return True

    author_level = await get_user_level(guild.id, author.id)
    target_level = await get_user_level(guild.id, target.id)

    if await is_command_blocked(guild.id, author.id, command_name):
        await reply_method(f"You are blocked from using `{command_name}` command.")
        return False

    if author_level == 1:
        has_perm = await has_command_permission(guild.id, author.id, command_name)
        if not has_perm:
            await reply_method(f"You don't have `{command_name}` permission to execute this command.")
            return False
        
        if target_level > 1:
            await reply_method(f"You cannot use `{command_name}` command on {target.display_name} because they outrank you in bot hierarchy.")
            return False
        
        if has_perm and await has_command_permission(guild.id, target.id, command_name):
            await reply_method(f"You can't use `{command_name}` on {target.display_name} because they have the same command permission as you.")
            return False

    for lvl in (2, 3, 4):
        if author_level == lvl:
            if target_level > lvl:
                await reply_method(f"You can't use `{command_name}` on {target.display_name} because they outrank you.")
                return False
            if target_level == lvl:
                name = PERM_LEVELS[lvl]
                await reply_method(f"You can't use `{command_name}` on {target.display_name} because they are also a/an {name}.")
                return False
            break

    return True
# <---REMOVE--->

def format_timedelta(td):
    """Formats a timedelta into a user-friendly string."""
    total_seconds = int(td.total_seconds())
    weeks, remainder = divmod(total_seconds, 604800)  # 604800 seconds in a week
    days, remainder = divmod(remainder, 86400)  # 86400 seconds in a day
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if weeks > 0:
        parts.append(f"{weeks} week{'s' if weeks > 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0 or not parts:  # Include seconds if no other units
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    return ', '.join(parts)


def convert_to_seconds(duration: int, unit: str):
    if unit == "s":
        return duration
    elif unit == "m":
        return duration * 60
    elif unit == "h":
        return duration * 3600
    elif unit == "d":
        return duration * 86400
    else:
        return None

async def unmute_member(ctx, member, duration, unit):
    # Wait for the specified mute duration
    dm_message = f"You have been unmuted in **{ctx.guild.name}** after serving your mute term of **{duration}{unit}**.\nYou can now participate in chats and have fun again :)"
    time = convert_to_seconds(duration, unit)
    try:
        await asyncio.sleep(time - 1.5)
    except asyncio.CancelledError:
        # Handle if the task is cancelled, you may want to log or skip the unmute process.
        return
    # Check if still muted
    if member.is_timed_out():
        try:
            await member.timeout(None)  # Remove the mute
            unmute_embed = discord.Embed(
                title=f"Unmuted **{member.display_name}**",
                description=f"**{member.display_name}** has been unmuted after serving their mute of **{duration}{unit}**.",
                color=discord.Color.blue()
            )
            await member.send(embed=discord.Embed(title=f"You've been Unmuted!!", description=dm_message,
                                                  color=discord.Color.random()))
            await ctx.send(embed=unmute_embed)
        except Exception as e:
            await ctx.send(f"An error occurred while unmuting **{member.display_name}**: {e}")




async def get_message_count(user_id: int, guild_id: int):
    if db_pool is None:
        return 0

    sql = """SELECT message_count FROM message_counts WHERE user_id  = $1 AND guild_id = $2"""
    count = await db_pool.fetchval(sql, user_id, guild_id)
    return count or 0


async def get_num_slaves_owned(user_id: int, guild_id: int):
    if db_pool is None:
        return 0
    
    sql = """ SELECT COUNT(*) FROM ownerships WHERE master_id = $1 AND guild_id  = $2"""
    count = await db_pool.fetchval(sql, user_id, guild_id)
    return count or 0

async def get_days_on_server(user_id: str, guild_id: str):
    
    if db_pool is None:
        return 0
    
    row = await db_pool.fetchval(
        "SELECT joined_at FROM users WHERE user_id = $1 AND guild_id = $2",
        user_id, guild_id
    )
    
    joined = row
    if joined is None:
         return 0
    
    try:
        if isinstance(joined, datetime):
            joined_at = joined
        else:
            joined_at = datetime.fromisoformat(joined)

        if joined_at.tzinfo is None:
            joined_at = joined_at.replace(tzinfo=datetime.timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - joined_at).days
    except Exception as e:
        print(f"Error parsing joined_at for user {user_id}: {e}")
        return 0


async def get_hours_since_message(user_id: int, guild_id: int) -> Optional[int]:
    async with db_pool.acquire() as conn:
        ts = await conn.fetchval("""SELECT last_message_at FROM message_counts WHERE user_id  = $1::bigint AND guild_id = $2::bigint """, user_id, guild_id)

    if not ts:
        return 0
    # ensure UTC
    now = datetime.now(timezone.utc)
    delta = now - ts
    hours = int(delta.total_seconds() // 3600)
    return min(hours, 2400)




async def dynamic_base_price(guild_id):
    # pull the last N sold prices from your DB
    rows = await db_pool.fetch("SELECT purchase_price FROM ownerships WHERE guild_id = $1 ORDER BY timestamp DESC LIMIT 10", int(guild_id))
    prices = [r["purchase_price"] for r in rows]
    if not prices:
        return None
    median = statistics.median(prices)
    return median * 0.7


async def get_100d_total(user_id: int, guild_id: int) -> int:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(""" SELECT COALESCE(SUM(count), 0) AS total FROM message_hourly_counts WHERE user_id = $1 AND guild_id = $2
              AND hour_ts >= NOW() - INTERVAL '100 days'; """, user_id, guild_id)
        return row['total']


async def get_active_days(user_id: int, guild_id: int) -> int:
    async with db_pool.acquire() as conn:
        return await conn.fetchval("""SELECT COUNT(*) FROM (SELECT date_trunc('day', hour_ts) AS day_bucket, SUM(count) AS msgs_that_day
                FROM message_hourly_counts WHERE user_id  = $1 AND guild_id = $2 AND hour_ts  >= NOW() - INTERVAL '100 days'
                GROUP BY day_bucket HAVING SUM(count) >= 10) AS active_days """, user_id, guild_id)



async def get_reactions_received(author_id: int, guild_id: int) -> int:
    async with db_pool.acquire() as conn:
        return await conn.fetchval("""SELECT COALESCE(COUNT(*), 0) FROM message_reactions
            WHERE author_id  = $1 AND guild_id   = $2 AND reactor_id <> $1 AND reacted_at >= NOW() - INTERVAL '100 days'""", author_id, guild_id)


async def get_voice_minutes_100d(user_id: int, guild_id: int) -> float:
    async with db_pool.acquire() as conn:
        total = await conn.fetchval("""SELECT COALESCE(SUM(EXTRACT(EPOCH FROM duration)/3600), 0) FROM voice_sessions
            WHERE user_id  = $1 AND guild_id = $2 AND leave_ts >= NOW() - INTERVAL '100 days' """, user_id, guild_id)
        
        return total



async def get_user_transaction_volume(user_id: int, guild_id: int) -> float:
    async with db_pool.acquire() as conn:
        return await conn.fetchval("""SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE guild_id = $1 AND receiver_id  = $2 AND timestamp >= NOW() - INTERVAL '100 days' AND amount < 1e10 AND type <> 'trade'""", guild_id, user_id)


def logistic(x, L, k, x0):
    #if isinstance(x, decimal.Decimal):
    x = float(x or 0)

    return L / (1 + math.exp(-k * (x - x0)))

def linear_score(x, m=300, b=0):
    return m * x + b
# N is L, k is the steepness of the curve, x0 is the midpoint which is y0

async def calculate_slave_price(ctx, user_id, guild_id):
    try:
        try:
            member = ctx.guild.get_member(user_id)
            if member is None:
                print(f"Member not found for user_id: {user_id}")
                return None

        except Exception as e:
            print(f"Error calculating slave price for user_id {user_id}: {e}")
            return None
        
        base_price = await dynamic_base_price(guild_id) or 10000


        # 1) how many messages in last 100d
        msg_100d         = await get_100d_total(user_id, guild_id)
        # 2) how many active days (>=10 msgs)
        active_days      = await get_active_days(user_id, guild_id)
        # 3) how many hours since last msg (0–2400)
        hours_since_msg  = await get_hours_since_message(user_id, guild_id)
        # 4) voice minutes in last 100d
        voice_mins       = await get_voice_minutes_100d(user_id, guild_id)
        # 5) reactions received last 100d
        reactions_recv   = await get_reactions_received(user_id, guild_id)
        # 6) transaction volume received last 100d
        tx_volume        = await get_user_transaction_volume(user_id, guild_id)
        # 7) Kero Balance
        balance = await get_user_balance(user_id)

        num_slaves_owned = await db_pool.fetchval("SELECT COUNT(DISTINCT slave_id) FROM ownerships WHERE master_id = $1 AND guild_id = $2", user_id, guild_id)

        


        m1 = logistic(msg_100d, L=200000, k=0.00006, x0=68000)
        m2 = linear_score(active_days)
        m3 = logistic(voice_mins, L=150000, k=0.005, x0=750)
        m4 = logistic(reactions_recv, L=35000, k=0.01, x0=300)
        m5 = logistic(tx_volume, L=75000, k=0.00006, x0=65000)
        m6 = logistic(balance, L=125000, k=0.000018, x0=210000)

        recency_penalty = logistic(hours_since_msg, L=100000, k=0.004, x0=660)

        score = (m1 + m2 + m3 + m4 + m5 + m6) - recency_penalty

        price = (base_price / 3) + score

        # discounts & adjustments
        discount = max(1 - 0.02 * num_slaves_owned, 0.1)
        price = price * discount
        if num_slaves_owned > 3:
            price *= (1 + 0.05 * (num_slaves_owned - 3))
            
        return int(price)
    
    except ValueError as e:
        print(f"Error in calculate_slave_price: {e}")
        await ctx.send(f"Error calculating slave price: {e}")
        return None




async def get_user_balance(user_id):
    async with db_pool.acquire() as conn:
        bal = await conn.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)
        return bal or 0

async def update_user_balance(user_id, amount):
    async with db_pool.acquire() as cursor:
        
        current_balance = await get_user_balance(user_id)
        new_balance = current_balance + amount

        if new_balance <= 0:
            await cursor.execute("UPDATE users SET balance = 0 WHERE user_id = $1", user_id)
        else:
            await cursor.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", amount, user_id)


async def add_transaction(sender, receiver, amount, type_, guild_id):
    if db_pool is None:
        raise RuntimeError("DB pool not initialized")
    
    sql = """ INSERT INTO transactions (sender_id, receiver_id, amount, type, timestamp, guild_id) VALUES ($1, $2, $3, $4, $5, $6) """
    await db_pool.execute(sql, sender, receiver, amount, type_, datetime.now(timezone.utc), guild_id)

    print(f"Transaction added: {sender} -> {receiver}, Amount: {amount}, Type: {type_}, Guild: {guild_id}")

async def is_slave(user_id: int, guild_id: int) -> bool:
    if db_pool is None:
        return False

    return await db_pool.fetchval("SELECT EXISTS(SELECT 1 FROM ownerships WHERE slave_id = $1 AND guild_id = $2)", user_id, guild_id)

async def is_master(user_id: int, guild_id: int) -> bool:
    if db_pool is None:
        return False

    return await db_pool.fetchval("SELECT EXISTS(SELECT 1 FROM ownerships WHERE master_id = $1 AND guild_id = $2)", user_id, guild_id)

async def get_master_of_slave(ctx, slave_id: int, guild_id: int):
    if db_pool is None:
        return False
    
    row = await db_pool.fetchrow("SELECT master_id FROM ownerships WHERE slave_id = $1 AND guild_id = $2", slave_id, guild_id)
    if not row:
        return None
    
    master_id = row["master_id"]
    master = ctx.guild.get_member(master_id)

    if master is None:
        try:
            master = await ctx.bot.fetch_user(master_id)
        except discord.NotFound:
            return None

    return master


async def fetch_all_slave_data(guild_id: int):
    sql = """
    WITH
    -- 1) messages per user
    msg AS (
      SELECT user_id,
             SUM(count) AS msg_100d,
             COUNT(DISTINCT date_trunc('day', hour_ts)) 
               FILTER (WHERE count >= 10) AS active_days
      FROM message_hourly_counts
      WHERE guild_id = $1
        AND hour_ts >= NOW() - INTERVAL '100 days'
      GROUP BY user_id
    ),
    -- 2) recency per user
    rec AS (
      SELECT user_id,
             EXTRACT(EPOCH FROM (NOW() - last_message_at))/3600 AS hours_since_msg
      FROM message_counts
      WHERE guild_id = $1
    ),
    -- 3) voice mins per user
    vc AS (
      SELECT user_id,
             SUM(EXTRACT(EPOCH FROM duration)/3600) AS voice_mins
      FROM voice_sessions
      WHERE guild_id = $1
        AND leave_ts >= NOW() - INTERVAL '100 days'
      GROUP BY user_id
    ),
    -- 4) reactions per user
    rx AS (
      SELECT author_id AS user_id,
             COUNT(*) AS reactions_recv
      FROM message_reactions
      WHERE guild_id = $1
        AND reacted_at >= NOW() - INTERVAL '100 days'
        AND reactor_id <> author_id
      GROUP BY author_id
    ),
    -- 5) transactions per user
    tx AS (
      SELECT receiver_id AS user_id,
             SUM(amount) AS tx_volume
      FROM transactions
      WHERE guild_id = $1
        AND timestamp >= NOW() - INTERVAL '100 days'
        AND amount < 1e10
        AND type <> 'trade'
      GROUP BY receiver_id
    ),
    -- 6) how many slaves they own
    slave_cnt AS (
      SELECT master_id AS user_id,
             COUNT(DISTINCT slave_id) AS num_slaves_owned
      FROM ownerships
      WHERE guild_id = $1
      GROUP BY master_id
    ),
    -- 7) which users are slaves (to filter out)
    slaves AS (
      SELECT slave_id AS user_id
      FROM ownerships
      WHERE guild_id = $1
    )
    SELECT
      u.user_id,
      COALESCE(msg.msg_100d,         0) AS msg_100d,
      COALESCE(msg.active_days,      0) AS active_days,
      COALESCE(rec.hours_since_msg,  0) AS hours_since_msg,
      COALESCE(vc.voice_mins,        0) AS voice_mins,
      COALESCE(rx.reactions_recv,    0) AS reactions_recv,
      COALESCE(tx.tx_volume,         0) AS tx_volume,
      COALESCE(u.balance,            0) AS balance,
      COALESCE(slave_cnt.num_slaves_owned, 0) AS num_slaves_owned
    FROM users u
    LEFT JOIN msg       ON u.user_id = msg.user_id
    LEFT JOIN rec       ON u.user_id = rec.user_id
    LEFT JOIN vc        ON u.user_id = vc.user_id
    LEFT JOIN rx        ON u.user_id = rx.user_id
    LEFT JOIN tx        ON u.user_id = tx.user_id
    LEFT JOIN slave_cnt ON u.user_id = slave_cnt.user_id

    LEFT JOIN ownerships o_current
  ON u.user_id = o_current.slave_id
  AND o_current.guild_id = $1

WHERE u.guild_id = $1
  AND o_current.slave_id IS NULL
    ;
    """
    
    return await db_pool.fetch(sql, guild_id)


async def get_top_slaves(ctx, guild_id: int, order: str = "desc"):
    if db_pool is None:
        await ctx.reply("DB pool not initialized in get_top_slaves.")
        return []
    
    print(f"Starting get_top_slaves for guild_id: {guild_id}")

    base_price = await dynamic_base_price(guild_id) or 10000

    rows = await fetch_all_slave_data(guild_id)
    print("DEBUG: fetched IDs:", [r["user_id"] for r in rows])
    


    #rows = await db_pool.fetch("""
    #    SELECT u.user_id
    #      FROM users u
    # LEFT JOIN ownerships o
    #        ON u.user_id = o.slave_id
    #       AND o.guild_id = $1
    #     WHERE u.guild_id = $1
    #       AND o.slave_id IS NULL
    #""", guild_id)

    await ctx.guild.chunk()
    member_map = {m.id: m for m in ctx.guild.members}

    top_list = []

    for r in rows:
        uid = r["user_id"]
        member = member_map.get(uid)
        if not member:
            #try:
            #    member = await ctx.guild.fetch_member(uid)
            #except discord.NotFound:
                continue

        msg_100d        = r['msg_100d']
        #print(f"DEBUG: Dynamic Base Price: {base_price}")
        #print(f"DEBUG: msg_100d for {uid}: {msg_100d}")
        active_days     = r['active_days']
        #print(f"DEBUG: active_days for {uid}: {active_days}")
        hours_since_msg = min(int(r.get('hours_since_msg') or 0), 2400)
        #print(f"DEBUG: hours_since_msg for {uid}: {hours_since_msg}")
        voice_mins      = r['voice_mins']
        #print(f"DEBUG: voice_mins for {uid}: {voice_mins}")
        reactions_recv  = r['reactions_recv']
        #print(f"DEBUG: reactions_recv for {uid}: {reactions_recv}")
        tx_volume       = r['tx_volume']
        #print(f"DEBUG: tx_volume for {uid}: {tx_volume}")
        balance         = r['balance']
        #print(f"DEBUG: balance for {uid}: {balance}")
        num_slaves_owned      = r['num_slaves_owned']
        #print(f"DEBUG: num_slaves_owned for {uid}: {num_slaves_owned}")

        m1 = logistic(msg_100d, L=200000, k=0.00006, x0=68000)
        m2 = linear_score(active_days)
        m3 = logistic(voice_mins, L=150000, k=0.005, x0=750)
        m4 = logistic(reactions_recv, L=35000, k=0.01, x0=300)
        m5 = logistic(tx_volume, L=75000, k=0.00006, x0=65000)
        m6 = logistic(balance, L=125000, k=0.000018, x0=210000)

        recency_penalty = logistic(hours_since_msg, L=100000, k=0.004, x0=660)

        score = (m1 + m2 + m3 + m4 + m5 + m6) - recency_penalty

        score += (base_price / 5)

        # discounts & adjustments
        discount = max(1 - 0.02 * num_slaves_owned, 0.1)
        score = score * discount
        if num_slaves_owned > 3:
            score *= (1 + 0.05 * (num_slaves_owned - 3))
        
        score = max(score, 0)  # cap the score to prevent overflow

        top_list.append((uid, int(score), balance, msg_100d))

    # no sorting needed—SQL gave us DESC balance already; 
    # if you need to re‑sort by price, do it now in Python:
    
    if order.lower() == "asc" or order.lower() == "ascending" or order.lower() == "ascend" or order.lower() == "a":
        top_list.sort(key=lambda x: x[1])
    else:
        top_list.sort(key=lambda x: x[1], reverse=True)
    #MY_ID = 1068465457910267975
    #for idx, (uid, price, balance, msg100) in enumerate(top_list, start=1):
    #    if uid == MY_ID:
    #        print(f"DEBUG: My ID {MY_ID} is ranked #{idx} with price {price}")
    #        break
    #else:
    #    print(f"DEBUG: My ID {MY_ID} not in full top_list of {len(top_list)} users")
    
    return top_list[:50]


async def get_slaves_of_master(master_id: int, guild_id: int) -> list[int]:
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(""" SELECT slave_id FROM ownerships WHERE master_id = $1 AND guild_id  = $2""", master_id, guild_id)
    
    return [record["slave_id"] for record in rows]

async def has_permission_for_slave(ctx, master_id: int, slave_id: int, command: str) -> bool:
    async with db_pool.acquire() as conn:
        val = await conn.fetchval(""" SELECT 1 FROM purchased_slave_commands WHERE master_id = $1 AND slave_id = $2 AND command = $3 AND guild_id = $4""", master_id, slave_id, command, ctx.guild.id)
    
    return val is not None

async def purchase_command_for_slave(ctx, master_id: int, slave_id: int, command: str) -> None:
    async with db_pool.acquire() as conn:
        await conn.execute("""INSERT INTO purchased_slave_commands (master_id, slave_id, command, guild_id) VALUES ($1, $2, $3, $4) """, master_id, slave_id, command, ctx.guild.id)

async def get_unpurchased_commands(ctx, slave_id: int, master_id: int, guild_id: int) -> dict[str, float]:

    available_commands = {
        "Jail": 1.412,
        "Unjail": 1.028,
        "Mute": 2.247,
        "Unmute": 1.789,
        "Kick": 3.3627,
        "Setnick": 1.915,
        "Whip": 0.751,
        "Role": 2.987
    }

    price = await calculate_slave_price(ctx, slave_id, guild_id)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch( """SELECT command FROM purchased_slave_commands WHERE master_id = $1 AND slave_id  = $2 AND guild_id  = $3 """, master_id, slave_id, guild_id)

    
    purchased_commands = [record["command"] for record in rows]
    print(f"Purchased Commands: {purchased_commands}")

    # Filter out the commands that have already been purchased
    unpurchased_commands: dict[str, float] = {}

    num_slaves_owned = await get_num_slaves_owned(master_id, guild_id)

    print(f"Master {master_id} owns {num_slaves_owned} slaves.")

    for cmd, factor in available_commands.items():
        if cmd not in purchased_commands:
            base_command_price = price * 0.125
            print(f"Base Command Price for {cmd}: {base_command_price}")

            command_price = base_command_price * factor
            print(f"Command Price before discount for {cmd}: {command_price}")

            print(f"Final Command Price for {cmd}: {command_price}")
            unpurchased_commands[cmd] = command_price

    return unpurchased_commands



def random_emojis():
    emoji_list = [
        "😀", "🍎", "🌟", "💎", "🎉", "🔥", "🌹", "🎵", "⚽", "🚀", "🐱", "🐶", "🍕", "🎤", "🦄", "💼", "🍔", "🌈", "🌙", "🦋", "🍦", "🌼",
        "🎮", "🌻", "🔮", "🥑", "🧠", "👑", "🍿", "💋", "🌸", "💡", "🎬", "🍉", "🥝", "🍍", "🍓", "🍇", "🍊", "🍋", "🍒", "🍑", "🥭", "🥥",
        "🧁", "🍰", "🍮", "🥧", "🧃", "🍾", "🥂", "🍻", "🍷", "🥃", "🍸", "🍺", "🧉", "🥤", "🥛", "🍫", "🍬", "🍭", "🍪", "🍩", "🍧", "🍨", "🍦", "🍪", "🥖", "🥨",
        "🍠", "🍙", "🍚", "🍜", "🍲", "🥗", "🥘", "🍛", "🍕", "🥪", "🍩", "🍮", "🍰", "🍴", "🍳", "🥓", "🥩", "🥚", "🍗", "🍖", "🌯", "🍿",
        "🍚", "🍞", "🍪"
    ]
    return random.sample(emoji_list, 3)






class CategorySelect(discord.ui.Select):
    def __init__(self, view):
        options = [
            discord.SelectOption(label="Slaves", description="View available slaves"),
            discord.SelectOption(label="Slave Commands", description="View commands available for your slaves"),
            discord.SelectOption(label="Buff", description="View available buffs (coming soon)")
        ]
        super().__init__(placeholder="Choose a category", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        if interaction.user != self.view.ctx.author:
            await interaction.response.send_message("Only the command invoker can change categories.", ephemeral=True)
            return
        self.view.current_category = self.values[0]
        await self.view.update_embed(interaction)


class ShopPaginationView(discord.ui.View):
    def __init__(self, ctx, non_bot_slaves, per_page, total_pages, timeout=150):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.non_bot_slaves = non_bot_slaves
        self.per_page = per_page
        self.total_pages = total_pages
        self.current_page = 0
        self.current_category = 'Slaves'
        self.message = None

        self.add_item(CategorySelect(self))

    async def get_permissions_description(self):
        available_permissions = {
            "Jail": "Jail the slave and restrict some of its permissions indefinitely.",
            "Unjail": "Unjail the jailed slave.",
            "Mute": "Timeout the slave for a duration.",
            "Unmute": "Removes timeout from the slave.",
            "Kick": "Kick the slave from the server.",
            "Set Nickname": "Change the slave's nickname.",
            "Role": "Toggle roles to the slave.",
            "Whip": "Whips your slave.", }

        prefix = getattr(self.ctx, "prefix", "/")
        description = f"**To buy a respective command of a slave, type {prefix}buycmd <slave> <command_name>**\n\n**Available Permissions for your slaves:**\n"
        for command, description_text in available_permissions.items():
            description += f"- **{command}**: {description_text}\n"
        return description

    async def create_embed(self):
        embed = discord.Embed(color=discord.Color.gold())
        prefix = getattr(self.ctx, "prefix", "/")
        if self.current_category == 'Slaves':
            embed.title = "🌟 **The Grand Slave Market** 🌟"
            embed.description = f"**Browse top slaves and make your purchase using Kero!**\nTo buy a slave, type {prefix}slbuy <slave>"
            start = self.current_page * self.per_page
            end = start + self.per_page
            guild = self.ctx.guild
            for user_id, price, balance, message_count in self.non_bot_slaves[start:end]:
                member = guild.get_member(user_id)
                if member:
                    embed.add_field(
                        name=f"💎 **{member.display_name} [{member.name}]**",
                        value=(f"**Price:** 🪙 {price} Kero\n"
                            f"**Balance:** 💷 {balance} Kero\n"
                            f"**Messages Sent:** {message_count}\n"
                        ),
                        inline=False)

        elif self.current_category == 'Slave Commands':
            embed.title = "⚔️ **Commands for Your Slaves** ⚔️"
            embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages}")
            embed.color = discord.Color.purple()

            # Page 1: List of permissions
            if self.current_page == 0:
                embed.description = await self.get_permissions_description()
            else:
                master_id = self.ctx.author.id
                guild_id = self.ctx.guild.id
                owned_slaves = await get_slaves_of_master(master_id, guild_id)

                # Determine the index of the slave based on the page number (first page of slaves starts at 1)
                slave_index = self.current_page - 1

                # Only show if there are owned slaves and the index is within range
                if slave_index < len(owned_slaves):
                    slave_id = owned_slaves[slave_index]
                    embed.description = await self.get_slave_commands_description(slave_id)
                else:
                    embed.description = "No more slaves to display."

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages}")
        return embed

    async def get_slave_commands_description(self, slave_id):
        commands = []
        available_permissions = {
            "Jail": "Jail the slave and restrict some of its permissions indefinitely.",
            "Unjail": "Unjail the jailed slave.",
            "Mute": "Timeout the slave for a duration.",
            "Unmute": "Removes timeout from the slave.",
            "Kick": "Kick the slave from the server.",
            "Set Nickname": "Change the slave's nickname.",
            "Role": "Toggle roles to the slave.",
            "Whip": "Whips your slave.",
        }

        # Fetch unpurchased commands for the slave
        available_commands = await get_unpurchased_commands(self.ctx, slave_id, self.ctx.author.id, self.ctx.guild.id)

        if available_commands:
            slave_name = (await self.ctx.guild.fetch_member(slave_id)).display_name
            commands.append(f"👤 **{slave_name}**:\n")

            for index, (command, price) in enumerate(available_commands.items(), start=1):
                commands.append(f"{index}. **{command}**: 🪙 {round(price)} Kero")

        if not commands:
            commands.append("No commands available.")

        return "\n".join(commands)

    async def update_total_pages(self):
        if self.current_category == 'Slave Commands':
            # Page 1 is reserved for permissions
            master_id = self.ctx.author.id
            guild_id = self.ctx.guild.id
            owned_slaves = await get_slaves_of_master(master_id, guild_id)
            self.total_pages = 1 + len(owned_slaves)
        else:
            # Keep the total pages for 'Slaves' as calculated by the initial setup
            self.total_pages = (len(self.non_bot_slaves) + self.per_page - 1) // self.per_page

    async def update_embed(self, interaction):
        await self.update_total_pages()
        embed = await self.create_embed()
        if interaction.response.is_done():
            return
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction, button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Only the command invoker can navigate the shop.", ephemeral=True)
            return
        await self.update_embed(interaction)
        if self.current_page > 0:
            self.current_page -= 1

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction, button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Only the command invoker can navigate the shop.", ephemeral=True)
            return
        await self.update_embed(interaction)
        if self.current_page < self.total_pages - 1:
            self.current_page += 1









class LeaderboardView(View):
    def __init__(self, ctx, leaderboard_type, current_mode):
        super().__init__()
        self.ctx = ctx
        self.leaderboard_type = leaderboard_type
        self.current_mode = current_mode

        # Define modes
        modes = ["Today", "7d", "30d", "All Time"]
        for mode in modes:
            if mode == current_mode:
                self.add_item(Button(label=mode, style=discord.ButtonStyle.primary, disabled=True))
            else:
                self.add_item(
                    Button(label=mode, style=discord.ButtonStyle.secondary, custom_id=f"{leaderboard_type}:{mode}"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

async def generate_leaderboard(ctx, leaderboard_type, mode):
    waiting_message = await ctx.send("Fetching Leaderboard Data...")

    # Fetch leaderboard data and historical data
    data = await fetch_leaderboard_data(ctx.guild.id, leaderboard_type, mode)
    prev_data = await fetch_historical_data(ctx.guild.id, leaderboard_type, mode)

    if not data:
        await waiting_message.delete()
        await ctx.send(f"No data available for {leaderboard_type.capitalize()} leaderboard in {mode}.")
        return

    await update_historical_rankings(ctx.guild.id, leaderboard_type, data)

    # Generate leaderboard image
    image = await generate_leaderboard_image(ctx, ctx.guild, leaderboard_type, data, prev_data, mode)

    # Create view with buttons
    view = LeaderboardView(ctx, leaderboard_type, mode)

    with BytesIO() as image_binary:
        image.save(image_binary, format="PNG")
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename="leaderboard.png"), view=view)

    await waiting_message.delete()

async def fetch_leaderboard_data(guild_id, leaderboard_type, mode):
    
    async with db_pool.acquire() as cursor:
        if leaderboard_type == "kero":
            return await cursor.fetch("""SELECT user_id, balance FROM users WHERE guild_id = $1 ORDER BY balance DESC LIMIT 10""", guild_id)
        elif leaderboard_type == "slave":
            return await cursor.fetch("""SELECT master_id, COUNT(DISTINCT slave_id) AS slave_count FROM ownerships WHERE guild_id = $1 GROUP BY master_id ORDER BY slave_count DESC LIMIT 10 """, guild_id)
        elif leaderboard_type == "msg":
            return await cursor.fetch("""SELECT user_id, message_count AS value FROM message_counts WHERE guild_id = $1 ORDER BY message_count DESC LIMIT 10""", guild_id)

async def fetch_historical_data(guild_id, leaderboard_type, mode):
    timeframes = {
        "7d": "30d",
        "30d": "All Time",
        "All Time": None,
        "Today": "7d"
    }
    base_mode = timeframes.get(mode, None)  # Get the appropriate base timeframe
    days = {"7d": 7, "30d": 30, "All Time": None}.get(base_mode, None)  # Get days based on the base mode


    async with db_pool.acquire() as cursor:
        if days:
            return await cursor.fetch( """ SELECT user_id, rank FROM historical_rankings WHERE guild_id = $1 AND leaderboard_type = $2 AND timestamp >= now() - ($3 || ' days')::interval ORDER BY timestamp DESC LIMIT 10 """, guild_id, leaderboard_type, f"-{days}")
        else:
            return await cursor.fetch(""" SELECT user_id, rank FROM historical_rankings WHERE guild_id = $1 AND leaderboard_type = $2 ORDER BY timestamp DESC LIMIT 10 """, guild_id, leaderboard_type)

async def update_historical_rankings(guild_id, leaderboard_type, data):
    async with db_pool.acquire() as cursor:
        for rank, (user_id, value) in enumerate(data, start=1):
            await cursor.execute("""INSERT INTO historical_rankings (guild_id, user_id, leaderboard_type, rank, value, timestamp) VALUES ($1, $2, $3, $4, $5, now()) ON CONFLICT (guild_id, user_id, leaderboard_type) DO UPDATE SET rank = EXCLUDED.rank, value = EXCLUDED.value, timestamp = EXCLUDED.timestamp """, guild_id, user_id, leaderboard_type, rank, value)


async def generate_leaderboard_image(ctx, guild, leaderboard_type, data, prev_data, mode):
    img_path = ("lb.png" if leaderboard_type == "kero" 
      else "lb_slave.png" if leaderboard_type == "slave"
      else "lb_message.png")
    base_img = Image.open(img_path)
    draw = ImageDraw.Draw(base_img)
    width, height = base_img.size

    try:
        font_large = ImageFont.truetype("Montserrat-Bold.ttf", 40)
        font_small = ImageFont.truetype("Montserrat-Bold.ttf", 20)
    except IOError:
        font_large = font_small = ImageFont.load_default()

    avatar_size = 32
    y_start = 95
    spacing = 43.75

    for rank, (user_id, value) in enumerate(data, start=1):
        y_position = y_start + (rank - 1) * spacing

        user = await ctx.bot.fetch_user(user_id)
        if user and not user.bot:  # Make sure it's not a bot
            nickname = user.name if user else f"User {user_id}"
            avatar_url = user.avatar.url if user and user.avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
        else:
            nickname = f"User {user_id}"
            avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

        response = requests.get(avatar_url)
        avatar = Image.open(BytesIO(response.content)).resize((avatar_size, avatar_size))
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

        amount_text = f"{value} {leaderboard_type.capitalize()}"
        text_width, _ = draw.textbbox((0, 0), amount_text, font=font_small)[2:4]

        base_img.paste(avatar, (115, int(y_position + 1.5)), mask)
        draw.text((167, y_position + 8), nickname, font=font_small, fill=(255, 255, 255))
        right_padding = 10
        draw.text((width - right_padding - text_width - 100, y_position + 8),
                  f"{round(value)} {leaderboard_type.capitalize()}", font=font_small, fill=(255, 255, 255))

        prev_rank = next((r for u, r in prev_data if u == user_id), None)
        if prev_rank is not None:
            if prev_rank > rank:
                icon_path = "green_arrow.png"
            elif prev_rank < rank:
                icon_path = "red_arrow.png"
            else:
                icon_path = "equal.png"
            icon = Image.open(icon_path).resize((20, 20))
            base_img.paste(icon, (int(25), int(y_position + 8.18)), icon)

    draw.text((10, 10), mode, font=font_large, fill=(255, 255, 255))
    return base_img


# Permission-system v2 compatibility overrides. Legacy tables remain only as
# historical data; all active command decisions now use permission_system.py.
async def get_user_level(guild_id: int, user_id: int):
    return await effective_rank(db_pool, guild_id, user_id)


async def only_for_setprefix(guild_id: int, user_id: int) -> bool:
    return await effective_rank(db_pool, guild_id, user_id) > 0


async def is_command_blocked(guild_id: int, user_id: int, command_name: str) -> bool:
    return False


async def has_command_permission(guild_id: int, user_id: int, command_name: str) -> bool:
    return False


async def is_authorized_or_not(context, guild_id: int, user_id: int, command_name: str) -> bool:
    guild = context.guild
    reply = (lambda message: context.response.send_message(message, ephemeral=True)) if hasattr(context, "user") else context.reply
    decision = await evaluate(db_pool, guild_id=guild_id, user_id=user_id, guild_owner_id=getattr(guild, "owner_id", None), command_name=command_name, channel_id=getattr(context.channel, "id", None), category_id=getattr(context.channel, "category_id", None))
    if decision.allowed:
        return True
    await reply(f"You cannot use `{command_name}` here. {decision.reason}.")
    return False


async def permissions_check_decorator(context, target, command_name: str) -> bool:
    author = context.user if hasattr(context, "user") else context.author
    guild = context.guild
    reply = (lambda message: context.response.send_message(message, ephemeral=True)) if hasattr(context, "user") else context.reply
    decision = await evaluate(db_pool, guild_id=guild.id, user_id=author.id, guild_owner_id=getattr(guild, "owner_id", None), command_name=command_name, channel_id=getattr(context.channel, "id", None), category_id=getattr(context.channel, "category_id", None))
    if not decision.allowed:
        await reply(f"You cannot use `{command_name}`. {decision.reason}.")
        return False
    if author.id == BOT_OWNER_ID or author.id == getattr(guild, "owner_id", None):
        return True
    target_rank = await effective_rank(db_pool, guild.id, target.id)
    if target_rank > 0 and await effective_rank(db_pool, guild.id, author.id) <= target_rank:
        await reply(f"You cannot use `{command_name}` on {target.display_name}; their custom-role rank is equal to or above yours.")
        return False
    return True
