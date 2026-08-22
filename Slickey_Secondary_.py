from discord.ext import commands
from discord import app_commands, AllowedMentions
import asyncio
import discord
import aiohttp
import random
import os, psutil, platform
from collections import deque
from datetime import datetime

# from anime_api.apis import NekosAPI
import utils
import permission_system
from utils import get_user_level, is_authorized_or_not, is_command_blocked, has_command_permission, operation_active, active_role_timers, get_top_slaves, ShopPaginationView, is_valid_url, WAIFU_IM_API, ALL_TAGS, ACTIONS, SFW_TAGS, NSFW_TAGS, GIFUKAI_API, GIFUKAI_ALIASES

BOT_START_TIME = datetime.utcnow()


safe = discord.AllowedMentions(
        users=True,      # let you ping the AFK user if you want
        roles=False,     # kill any @Role in the reason
        everyone=False)   # kill @everyone / @here)

_recent_waifu_im_pngs = []




ACTION_TEMPLATES = {
    "angry": {
        "title": "{user} is angry at {target}!",
        "footer": "Angry Count: {total}  •  {user} has been angry at {target} {specific} time(s) in this server."
    },
    "bite": {
        "title": "{user} bites {target}!",
        "footer": "Bite Count: {total}  •  {user} has bitten {target} {specific} time(s) in this server."
    },
    "bleh": {
        "title": "{user} sticks their tongue out at {target}!",
        "footer": "Bleh Count: {total}  •  {user} has stuck their tongue out at {target} {specific} time(s) in this server."
    },
    "blowkiss": {
        "title": "{user} blows a kiss to {target}!",
        "footer": "Blow Kiss Count: {total}  •  {user} has blown a kiss to {target} {specific} time(s) in this server."
    },
    "blush": {
        "title": "{user} blushes at {target}!",
        "footer": "Blush Count: {total}  •  {user} has blushed at {target} {specific} time(s) in this server."
    },
    "bonk": {
        "title": "{user} bonks {target}!",
        "footer": "Bonk Count: {total}  •  {user} has bonked {target} {specific} time(s) in this server."
    },
    "bored": {
        "title": "{user} bores {target}!",
        "footer": "Bore Count: {total}  •  {user} has bored {target} {specific} time(s) in this server."
    },
    "bye": {
        "title": "{user} says bye to {target}!",
        "footer": "Bye Count: {total}  •  {user} has said bye to {target} {specific} time(s) in this server."
    },
    "carry": {
        "title": "{user} carries {target}!",
        "footer": "Carry Count: {total}  •  {user} has carried {target} {specific} time(s) in this server."
    },
    "clap": {
        "title": "{user} claps for {target}!",
        "footer": "Clap Count: {total}  •  {user} has clapped for {target} {specific} time(s) in this server."
    },
    "confused": {
        "title": "{user} is confused!",
        "footer": "Confused Count: {total}  •  {user} has been confused {specific} time(s) in this server."
    },
    "cry": {
        "title": "{user} cries!",
        "footer": "Cry Count: {total}  •  {user} has cried {specific} time(s) in this server."
    },
    "cuddle": {
        "title": "{user} cuddles {target}!",
        "footer": "Cuddle Count: {total}  •  {user} has cuddled {target} {specific} time(s) in this server."
    },
    "dance": {
        "title": "{user} dances with {target}!",
        "footer": "Dance Count: {total}  •  {user} has danced with {target} {specific} time(s) in this server."
    },
    "eat": {
        "title": "{user} noms {target}!",
        "footer": "Nom Count: {total}  •  {user} has nommed {target} {specific} time(s) in this server."
    },
    "facepalm": {
        "title": "{user} facepalms at {target}!",
        "footer": "Facepalm Count: {total}  •  {user} has facepalmed at {target} {specific} time(s) in this server."
    },
    "feed": {
        "title": "{user} feeds {target}!",
        "footer": "Feed Count: {total}  •  {user} has fed {target} {specific} time(s) in this server."
    },
    "handhold": {
        "title": "{user} holds hands with {target}!",
        "footer": "Handhold Count: {total}  •  {user} has held hands with {target} {specific} time(s) in this server."
    },
    "handshake": {
        "title": "{user} shakes hands with {target}!",
        "footer": "Handshake Count: {total}  •  {user} has shaken hands with {target} {specific} time(s) in this server."
    },
    "happy": {
        "title": "{user} is happy!",
        "footer": "Happy Count: {total}  •  {user} has been happy {specific} time(s) in this server."
    },
    "hi": {
        "title": "{user} says hi to {target}!",
        "footer": "Hi Count: {total}  •  {user} has said hi to {target} {specific} time(s) in this server."
    },
    "highfive": {
        "title": "{user} high-fives {target}!",
        "footer": "High-Five Count: {total}  •  {user} has high-fived {target} {specific} time(s) in this server."
    },
    "hug": {
        "title": "{user} hugs {target}!",
        "footer": "Hug Count: {total}  •  {user} has hugged {target} {specific} time(s) in this server."
    },
    "kick": {
        "title": "{user} kicks {target}!",
        "footer": "Kick Count: {total}  •  {user} has kicked {target} {specific} time(s) in this server."
    },
    "kill": {
        "title": "{user} kills {target}!",
        "footer": "Kill Count: {total}  •  {user} has killed {target} {specific} time(s) in this server."
    },
    "kiss": {
        "title": "{user} kisses {target}!",
        "footer": "Kiss Count: {total}  •  {user} has kissed {target} {specific} time(s) in this server."
    },
    "lappillow": {
        "title": "{user} offers their lap as a pillow to {target}!",
        "footer": "Lap Pillow Count: {total}  •  {user} has offered their lap to {target} {specific} time(s) in this server."
    },
    "laugh": {
        "title": "{user} laughs!",
        "footer": "Laugh Count: {total}  •  {user} has laughed {specific} time(s) in this server."
    },
    "nod": {
        "title": "{user} nods at {target}!",
        "footer": "Nod Count: {total}  •  {user} has nodded at {target} {specific} time(s) in this server."
    },
    "nope": {
        "title": "{user} says nope!",
        "footer": "Nope Count: {total}  •  {user} has said nope {specific} time(s) in this server."
    },
    "nya": {
        "title": "{user} says nya!",
        "footer": "Nya Count: {total}  •  {user} has said nya {specific} time(s) in this server."
    },
    "pat": {
        "title": "{user} pats {target}!",
        "footer": "Pat Count: {total}  •  {user} has patted {target} {specific} time(s) in this server."
    },
    "peek": {
        "title": "{user} peeks at {target}!",
        "footer": "Peek Count: {total}  •  {user} has peeked at {target} {specific} time(s) in this server."
    },
    "poke": {
        "title": "{user} pokes {target}!",
        "footer": "Poke Count: {total}  •  {user} has poked {target} {specific} time(s) in this server."
    },
    "pout": {
        "title": "{user} pouts!",
        "footer": "Pout Count: {total}  •  {user} has pouted {specific} time(s) in this server."
    },
    "punch": {
        "title": "{user} punches {target}!",
        "footer": "Punch Count: {total}  •  {user} has punched {target} {specific} time(s) in this server."
    },
    "run": {
        "title": "{user} runs away!",
        "footer": "Run Count: {total}  •  {user} has run away {specific} time(s) in this server."
    },
    "salute": {
        "title": "{user} salutes {target}!",
        "footer": "Salute Count: {total}  •  {user} has saluted {target} {specific} time(s) in this server."
    },
    "shake": {
        "title": "{user} shakes {target}!",
        "footer": "Shake Count: {total}  •  {user} has shaken {target} {specific} time(s) in this server."
    },
    "shocked": {
        "title": "{user} is shocked by {target}!",
        "footer": "Shocked Count: {total}  •  {user} has been shocked by {target} {specific} time(s) in this server."
    },
    "shoot": {
        "title": "{user} shoots at {target}!",
        "footer": "Shoot Count: {total}  •  {user} has shot at {target} {specific} time(s) in this server."
    },
    "shrug": {
        "title": "{user} shrugs!",
        "footer": "Shrug Count: {total}  •  {user} has shrugged {specific} time(s) in this server."
    },
    "shy": {
        "title": "{user} is shy around {target}!",
        "footer": "Shy Count: {total}  •  {user} has been shy around {target} {specific} time(s) in this server."
    },
    "sip": {
        "title": "{user} sips their drink!",
        "footer": "Sip Count: {total}  •  {user} has sipped their drink {specific} time(s) in this server."
    },
    "slap": {
        "title": "{user} slaps {target}!",
        "footer": "Slap Count: {total}  •  {user} has slapped {target} {specific} time(s) in this server."
    },
    "sleep": {
        "title": "{user} is sleeping!",
        "footer": "Sleep Count: {total}  •  {user} has slept {specific} time(s) in this server."
    },
    "smile": {
        "title": "{user} smiles at {target}!",
        "footer": "Smile Count: {total}  •  {user} has smiled at {target} {specific} time(s) in this server."
    },
    "smug": {
        "title": "{user} smugs at {target}!",
        "footer": "Smug Count: {total}  •  {user} has smugged at {target} {specific} time(s) in this server."
    },
    "spin": {
        "title": "{user} spins around!",
        "footer": "Spin Count: {total}  •  {user} has spun around {specific} time(s) in this server."
    },
    "stare": {
        "title": "{user} stares at {target}!",
        "footer": "Stare Count: {total}  •  {user} has stared at {target} {specific} time(s) in this server."
    },
    "taunt": {
        "title": "{user} taunts {target}!",
        "footer": "Taunt Count: {total}  •  {user} has taunted {target} {specific} time(s) in this server."
    },
    "teehee": {
        "title": "{user} giggles!",
        "footer": "Teehee Count: {total}  •  {user} has giggled {specific} time(s) in this server."
    },
    "think": {
        "title": "{user} thinks about {target}!",
        "footer": "Think Count: {total}  •  {user} has thought about {target} {specific} time(s) in this server."
    },
    "thumbsup": {
        "title": "{user} gives a thumbs up to {target}!",
        "footer": "Thumbs Up Count: {total}  •  {user} has given a thumbs up to {target} {specific} time(s) in this server."
    },
    "tickle": {
        "title": "{user} tickles {target}!",
        "footer": "Tickle Count: {total}  •  {user} has tickled {target} {specific} time(s) in this server."
    },
    "wag": {
        "title": "{user} wags their tail!",
        "footer": "Wag Count: {total}  •  {user} has wagged their tail {specific} time(s) in this server."
    },
    "wallslam": {
        "title": "{user} pins {target} against the wall!",
        "footer": "Wall Slam Count: {total}  •  {user} has pinned {target} against the wall {specific} time(s) in this server."
    },
    "wave": {
        "title": "{user} waves at {target}!",
        "footer": "Wave Count: {total}  •  {user} has waved at {target} {specific} time(s) in this server."
    },
    "wink": {
        "title": "{user} winks at {target}!",
        "footer": "Wink Count: {total}  •  {user} has winked at {target} {specific} time(s) in this server."
    },
    "yawn": {
        "title": "{user} yawns!",
        "footer": "Yawn Count: {total}  •  {user} has yawned {specific} time(s) in this server."
    },
    "yeet": {
        "title": "{user} yeets {target}!",
        "footer": "Yeet Count: {total}  •  {user} has yeeted {target} {specific} time(s) in this server."
    },
    # alias-only entry — looked up separately via ctx.invoked_with / the type=="cheek" branch,
    # not by real action name, per the peck-lookup fix from the previous message
    "peck": {
        "title": "{user} pecks {target}!",
        "footer": "Peck Count: {total}  •  {user} has pecked {target} {specific} time(s) in this server."
    }
}

@commands.command(name='checkfunction', aliases=['chkfunc'], description='Testing...')
async def run_query(ctx):

    async with utils.db_pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM message_counts LIMIT 5;")
        await ctx.reply(f"Query result: {result}")

#SpawnAction = app_commands.Choice[str]

# --- Hybrid `spawn` (works as both !spawn and /spawn) ---
@commands.hybrid_command(name="spawn", description="Turn spawn ON/OFF for this server", help="Turn spawn ON/OFF for this server\n**Syntax**: spawn <enable|disable>")
@permission_system.slickey_command("configuration", "protected")
@app_commands.choices(action=[app_commands.Choice(name="Enable", value="enable"), app_commands.Choice(name="Disable", value="disable")])
async def spawn_hybrid(ctx: commands.Context, action: app_commands.Choice[str]):
    # This must match the registered command name and its policy key.
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "spawn"):
        return
    
    guild_id = str(ctx.guild.id)

    current = await utils.db_pool.fetchval("SELECT spawn_enabled FROM spawn_counters WHERE guild_id = $1", guild_id)

    want_on = (action.value == "enable")
    already = (current is None and want_on) or (current is True and want_on) or (current is False and not want_on)
    
    if already:
        msg = f"Spawn is already **{action.name.upper()}** on this server."
        if ctx.interaction:
            return await ctx.send(msg, ephemeral=True)
        else:
            return await ctx.send(msg)
    
    if current is None:
        sql = """
        INSERT INTO spawn_counters (guild_id, message_counter, target_messages, spawn_enabled)
        VALUES ($1, 0, 0, $2)
        """
        await utils.db_pool.execute(sql, guild_id, want_on)
    else:
        sql = "UPDATE spawn_counters SET spawn_enabled = $1 WHERE guild_id = $2"
        await utils.db_pool.execute(sql, want_on, guild_id)

    await ctx.send(f"Spawn has been **{action.name.upper()}D** for this server.")


# --- Hybrid `say` (works as both !say and /say) ---
@commands.hybrid_command(name="say", description="Send an anonymous DM to a user from this server.", help="Send an anonymous DM to a user from this server.\n**Syntax**: say @user Your message here")
@app_commands.describe(user="The user to send the DM to", prompt="The message to send")
async def say_hybrid(ctx: commands.Context, user: discord.Member, *, prompt: str):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "say"):
        return
    if not ctx.interaction:  # text invocation: delete the command message
        try:
            await ctx.message.delete()
        except Exception:
            pass
    server_name = ctx.guild.name if ctx.guild else "a server"
    dm_message = f"You got a message from someone in **{server_name}**: {prompt}"
    try:
        await user.send(dm_message)
        if ctx.interaction:
            await ctx.send("Message sent successfully.", ephemeral=True)
        else:
            await ctx.send("Message sent successfully.")
    except discord.Forbidden:
        msg = "I cannot send a DM to that user. They may have DMs disabled."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.send(msg)
    except Exception as e:
        msg = f"An error occurred while sending the DM: {e}"
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.send(msg)


# --- Hybrid `ping` (works as both !ping and /ping) ---
@commands.hybrid_command(name="ping", aliases=["Ping", "PING", "Pg", "pg", "PG"], description="Returns your ping along with a few stats.", help="Returns your ping along with a few stats.\n**Syntax**: ping")
async def ping_hybrid(ctx: commands.Context):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "ping"):
        msg = "You are blocked from using ping command."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    latency = ctx.bot.latency * 1000
    now = datetime.utcnow()
    delta = now - BOT_START_TIME
    days, remainder = divmod(int(delta.total_seconds()), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    total_guilds = len(ctx.bot.guilds)
    proc = psutil.Process(os.getpid())
    mem = proc.memory_info().rss / 1024**2
    cpu_pct = psutil.cpu_percent(interval=0.1)
    text_cmds = len(ctx.bot.commands)
    slash_cmds = len(ctx.bot.tree.get_commands())
    embed = discord.Embed(title="🏓 Pong! Bot Stats", color=discord.Color.blurple(), timestamp=now)
    embed.add_field(name="✨ Latency", value=f"`{latency:.2f} ms`", inline=True)
    embed.add_field(name="⏱️ Uptime",  value=f"`{uptime_str}`", inline=True)
    embed.add_field(name="🌐 Servers", value=f"`{total_guilds}`", inline=True)
    embed.add_field(name="📚 Text Cmds",  value=f"`{text_cmds}`", inline=True)
    embed.add_field(name="📜 Slash Cmds", value=f"`{slash_cmds}`", inline=True)
    embed.add_field(name="💾 Memory", value=f"`{mem:.1f} MB`", inline=True)
    embed.add_field(name="⚙️ CPU",    value=f"`{cpu_pct:.1f}%`", inline=True)
    requester = ctx.author if not ctx.interaction else ctx.interaction.user
    embed.set_footer(text=f"Requested by {requester}", icon_url=requester.display_avatar.url)
    await ctx.send(embed=embed)


# --- Hybrid `echo` (works as both !echo and /echo) ---
@commands.hybrid_command(name="echo", aliases=["Echo", "ECHO", "ec", "Ec", "EC"], description="Make the bot repeat your message anonymously", help="Make the bot repeat your message anonymously with an added functionality of using message ID for giving replied messages.\n**Syntax**: echo message <reply_to>")
@app_commands.describe(message="The message you want the bot to repeat", reply_to="The message ID to reply to")
async def echo_hybrid(ctx: commands.Context, message: str, reply_to: str = None):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "echo"):
        return
    if not ctx.interaction:  # text invocation
        try:
            await ctx.message.delete()
        except Exception:
            pass
        parts = message.split()
        if parts and parts[-1].isdigit():
            reply_to = parts[-1]
            message = " ".join(parts[:-1])
    if reply_to:
        try:
            target_message = await ctx.channel.fetch_message(int(reply_to))
            await ctx.send(message, reference=target_message, allowed_mentions=safe)
        except Exception:
            await ctx.send(message, allowed_mentions=safe)
    else:
        await ctx.send(message, allowed_mentions=safe)
    if ctx.interaction:
        await ctx.send("Message sent anonymously!", ephemeral=True)

# --- Hybrid `hello` (works as both !hello and /hello) ---
@commands.hybrid_command(name="hello", aliases=["Hello", "HELLO"], description="Says hello back to you!", help="Says hello back to you!")
async def hello_hybrid(ctx: commands.Context):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "hello"):
        msg = "You are blocked from using `hello` command."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.send(msg)
        return
    await ctx.send(f"Hello {ctx.author.mention}! :>")


# --- Hybrid `spam` (works as both !spam and /spam) ---
@commands.hybrid_command(name="spam", description="Spam a message a specified number of times anonymously.", help="Spam a message a specified number of times anonymously.\n**Syntax**: spam <message> <count> [channel]")
@permission_system.slickey_command("economy", "protected")
@app_commands.describe(
    message="The message to spam.",
    count="The number of times to spam (max limit 500).",
    channel="The channel where the spam should be sent. Defaults to the current channel."
)
async def spam_hybrid(ctx: commands.Context, message: str, count: int, channel: discord.TextChannel = None):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "spam"):
        return
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "spam"):
        msg = "You're blocked from using spam command."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return

    global operation_active
    operation_active = True

    if channel is None:
        channel = ctx.channel

    MAX_SPAM_COUNT = 500
    if count <= 0:
        msg = "The count must be greater than 0."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.send(msg)
        return
    if count > MAX_SPAM_COUNT:
        msg = f"You cannot spam more than {MAX_SPAM_COUNT} times."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.send(msg)
        return

    if ctx.interaction:
        await ctx.send("Spamming...", ephemeral=True)
    else:
        await ctx.send("Spamming...")

    for i in range(count):
        if not operation_active:
            msg = "Spamming halted due to stop command."
            if ctx.interaction:
                await ctx.followup.send(msg, ephemeral=False)
            else:
                await ctx.send(msg)
            return
        try:
            await channel.send(message)
            await asyncio.sleep(0.4)  # Delay to help prevent rate limiting
        except Exception as e:
            print(f"Error sending spam message: {e}")

    msg = "Spamming finished."
    if ctx.interaction:
        await ctx.followup.send(msg, ephemeral=True)
    else:
        await ctx.send(msg)



# --- Hybrid `stop` (works as both !stop and /stop) ---
@commands.hybrid_command(name="stop", description="Stop all ongoing bot operations.", help="Stop all ongoing bot operations.\n**Syntax**: stop")
@permission_system.slickey_command("economy", "protected")
async def stop_hybrid(ctx: commands.Context):
    if not await is_authorized_or_not(ctx, ctx.guild.id, ctx.author.id, "stop"):
        return
    global operation_active, active_role_timers
    operation_active = False

    for member_id, timer_data in list(active_role_timers.items()):
        role_id = timer_data.get("role_id")
        role = ctx.guild.get_role(role_id)
        member = ctx.guild.get_member(int(member_id))
        if member and role:
            try:
                await member.remove_roles(role)
            except discord.HTTPException:
                pass
        task = timer_data.get("task")
        if task:
            task.cancel()
        active_role_timers.pop(member_id, None)

    await ctx.send("All operations have been halted.")


# --- Hybrid `shop` (works as both !shop and /shop) ---
@commands.hybrid_command(name="shop", description="Browse and buy slaves with 💷 Kero", help="Browse and buy slaves with 💷 Kero\n**Syntax**: shop <asc|desc>")
@app_commands.describe(order="Choose price sort order: Ascending or Descending")
@app_commands.choices(order=[app_commands.Choice(name="Descending (highest first)", value="desc"), app_commands.Choice(name="Ascending (lowest first)",  value="asc")])
async def shop_hybrid(ctx: commands.Context, order: app_commands.Choice[str] = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "shop"):
        msg = "You are blocked from using `shop` command."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return

    sort_order = order.value if order else "desc"
    await ctx.defer()
    top_slaves = await get_top_slaves(ctx, ctx.guild.id, sort_order)
    non_bot_slaves = [
        slave for slave in top_slaves
        if not ctx.guild.get_member(slave[0]).bot
    ]

    if not non_bot_slaves:
        embed = discord.Embed(
            title="🌟 **The Grand Slave Market** 🌟",
            description="No slaves are currently available for purchase. Please check back later!",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    per_page = 5
    total_pages = (len(non_bot_slaves) - 1) // per_page + 1
    view = ShopPaginationView(ctx, non_bot_slaves, per_page, total_pages)
    embed = await view.create_embed()
    view.message = await ctx.send(embed=embed, view=view)



async def get_from_waifu_im(tag: str | None):
    """Single source of truth for all waifu image fetches. tag=None -> random SFW pool."""
    params = {"IncludedTags": tag} if tag else {}
    if tag in NSFW_TAGS:
        params["IsNsfw"] = "True"
    url = None
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as s:
            for _ in range(3):  # bounded retry against repeats; API returns one image per call, no batch to sample from
                async with s.get(WAIFU_IM_API, params=params) as r:
                    if r.status != 200:
                        return None
                    js = await r.json()
                candidates = [i["url"] for i in js.get("items", []) if i.get("url")]
                if not candidates:
                    return None
                url = random.choice(candidates)
                if url not in _recent_waifu_im_pngs:
                    break
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return None

    if url:
        _recent_waifu_im_pngs.append(url)
        if len(_recent_waifu_im_pngs) > 50:
            _recent_waifu_im_pngs.pop(0)
    return url

# --- Hybrid `waifu` (works as both !waifu and /waifu) ---
@commands.hybrid_command(name="waifu", description="🖼️ Get a random waifu PNG by tag (SFW by default).", help="🖼️ Get a random waifu PNG by tag (SFW by default)\n**Syntax**: waifu maid")
@commands.cooldown(1, 6, commands.BucketType.user)
@app_commands.describe(tag="Optional tag (e.g. neko, maid).")
@app_commands.choices(tag=[app_commands.Choice(name=t, value=t) for t in ALL_TAGS])
async def waifu_hybrid(ctx: commands.Context, tag: str = None):
    if await is_command_blocked(ctx.guild.id, ctx.author.id, "waifu"):
        msg = "You are blocked from using `waifu` command."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    tag = tag.strip().lower() if tag else None
    if tag and tag not in ALL_TAGS:
        msg = f"Unknown tag `{tag}`. Use `!wtags` to see valid tags."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    if tag in NSFW_TAGS and not ctx.channel.is_nsfw():
        msg = "🔞 Can't pull NSFW images in here!"
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    url = await get_from_waifu_im(tag)
    if not url:
        msg = "Couldn't fetch a waifu for you 😕"
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
        return
    embed = discord.Embed(title=f"🔸 Waifu: {tag or 'Random'}", description=f"[Download here]({url})", color=discord.Color.random())
    embed.set_image(url=url)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    try:
        await ctx.send(embed=embed)
    except Exception:
        msg = "⚠️ Oops, something went wrong sending the embed."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.send(msg)


@waifu_hybrid.error
async def waifu_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        msg = f"⏳ Slow down! Try again in {error.retry_after:.1f}s."
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.reply(msg)
    else:
        msg = f"An unexpected error occurred: {error}"
        if ctx.interaction:
            await ctx.send(msg, ephemeral=True)
        else:
            await ctx.send(msg)


@commands.command(name="wtags", aliases=['wtag'], help="📋 List all available waifu image tags\n**Syntax**: wtags")
async def waifu_tags(ctx):
    embed = discord.Embed(
        title="📋 Waifu Command Tags",
        description="Use these tags with `!waifu <tag>` (adding `nsfw` is necessary as `sfw` is default mode.)",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="SFW TAGS",
        value=", ".join(f"`{tag}`" for tag in SFW_TAGS),
        inline=False
    )
    embed.add_field(
        name="NSFW TAGS",
        value=", ".join(f"`{tag}`" for tag in NSFW_TAGS),
        inline=False
    )

    await ctx.reply(embed=embed)




async def add_interaction(guild_id: int, actor_id: int, receiver_id: int, activity: str):
    async with utils.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_interactions ( guild_id, actor_id, receiver_id, activity, count, last_updated ) VALUES ($1, $2, $3, $4, 1, NOW()) ON CONFLICT (guild_id, actor_id, receiver_id, activity) DO UPDATE SET count = user_interactions.count + 1, last_updated = NOW()
            """, guild_id, actor_id, receiver_id, activity)

async def get_per_user_activity_count(guild_id: int, actor_id: int, activity: str) -> int:
    async with utils.db_pool.acquire() as conn:
        val = await conn.fetchval("""
            SELECT COALESCE(SUM(count), 0) FROM user_interactions WHERE guild_id = $1 AND actor_id = $2 AND activity = $3""", guild_id, actor_id, activity)
    return val

async def get_interaction_count(guild_id: int, actor_id: int, receiver_id: int, activity: str) -> int:
    async with utils.db_pool.acquire() as conn:
        val = await conn.fetchval("""
            SELECT count FROM user_interactions WHERE guild_id = $1 AND actor_id = $2 AND receiver_id = $3 AND activity = $4""", guild_id, actor_id, receiver_id, activity)
    return val or 0





async def fetch_gifukai(action: str, pairing: str | None = None, nsfw: bool = False):
    params = {}
    if pairing:
        params["pairing"] = pairing
    if nsfw:
        params["nsfw"] = "true"

    url = f"{GIFUKAI_API}{action}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("url")
                return None  # 400/404/500 -> no gif this time
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        # ValueError covers resp.json() choking on a non-JSON body
        return None

async def get_gifs(tag: str, nsfw: bool = False, pairing: str | None = None):
    return await fetch_gifukai(tag, pairing=pairing, nsfw=nsfw)


# --- Hybrid GIF action factory (works as both !action and /action) ---

def make_hybrid_action(action: str):
    @commands.hybrid_command(name=action, aliases=GIFUKAI_ALIASES.get(action, []), description=f"Gives out a {action.capitalize()} GIF.", help=f"Gives out a {action.capitalize()} GIF.\n**Syntax**: {action} @user")
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def _hybrid_cmd(ctx: commands.Context, member: str = None):
        if await is_command_blocked(ctx.guild.id, ctx.author.id, action):
            msg = f"You are blocked from using `{action}` command."
            if ctx.interaction:
                await ctx.send(msg, ephemeral=True)
            else:
                await ctx.reply(msg)
            return

        # Resolve the target member
        target_member = None
        selff = False

        if ctx.interaction and member is not None and isinstance(member, discord.Member):
            # Slash command: discord.py auto-converts the parameter
            target_member = member
        elif member and isinstance(member, str):
            # Text command: parse string to member
            try:
                target_member = await commands.MemberConverter().convert(ctx, member)
            except commands.MemberNotFound:
                target_member = None

            if not target_member and ctx.message and ctx.message.reference:
                try:
                    replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    target_member = replied.author
                except Exception:
                    pass

            if not target_member:
                matched_member, confidence = await utils.find_closest_member(ctx, member)
                if matched_member and confidence > 70:
                    target_member = matched_member
                else:
                    msg = f"Could not find a user matching '{member}'."
                    if ctx.interaction:
                        await ctx.send(msg, ephemeral=True)
                    else:
                        await ctx.reply(msg)
                    return

        if not target_member:
            target_member = ctx.author

        if target_member.id == ctx.author.id:
            selff = True

        url = await get_gifs(action)
        if not url or not is_valid_url(url):
            msg = f"❌ Couldn't fetch a {action} gif."
            if ctx.interaction:
                await ctx.send(msg, ephemeral=True)
            else:
                await ctx.reply(msg)
            return

        # Record and counts
        await add_interaction(ctx.guild.id, ctx.author.id, target_member.id, action)
        specific = await get_interaction_count(ctx.guild.id, ctx.author.id, target_member.id, action)
        total = await get_per_user_activity_count(ctx.guild.id, ctx.author.id, action)

        template = ACTION_TEMPLATES.get(action)
        if template:
            title = template["title"].format(
                user=ctx.author.display_name,
                target=target_member.display_name if not selff else "themselves")
            footer = template["footer"].format(
                user=ctx.author.display_name,
                target=target_member.display_name if not selff else "themselves",
                specific=specific,
                total=total)
        else:
            title = f"{ctx.author.display_name} {action}s {target_member.display_name if not selff else 'themselves'}!"
            footer = f"{action.capitalize()} Count: {total}  •  {target_member.display_name} received from you: {specific}"

        emb = discord.Embed(title=title, color=discord.Color.random())
        emb.set_image(url=url)
        emb.set_footer(text=footer)
        await ctx.send(embed=emb)

    @_hybrid_cmd.error
    async def _hybrid_on_cooldown(ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            msg = f"Slow down! Try again in {error.retry_after:.1f}s."
            if ctx.interaction:
                await ctx.send(msg, ephemeral=True)
            else:
                await ctx.reply(msg, delete_after=error.retry_after)
        else:
            msg = f"An unexpected error occurred: {error}"
            if ctx.interaction:
                await ctx.send(msg, ephemeral=True)
            else:
                await ctx.reply(msg)
    _hybrid_cmd.__name__ = action
    return _hybrid_cmd


HIBRID_ACTION_COMMANDS = [make_hybrid_action(act) for act in ACTIONS]

def setup(bot: commands.Bot):
    bot.add_command(run_query)
    bot.add_command(say_hybrid)
    bot.add_command(ping_hybrid)
    bot.add_command(echo_hybrid)
    bot.add_command(hello_hybrid)
    bot.add_command(waifu_hybrid)
    bot.add_command(waifu_tags)
    bot.add_command(shop_hybrid)

    for cmd in HIBRID_ACTION_COMMANDS:
        bot.add_command(cmd)

    # <----REMOVE----> Old separate text/slash registrations
    # bot.add_command(say_text)
    # bot.add_command(ping_text)
    # bot.add_command(echo_text)
    # bot.add_command(hello_text)
    # bot.add_command(waifu)
    # for cmd in ACTION_COMMANDS:
    #     bot.add_command(cmd)
    # bot.tree.add_command(say)
    # bot.tree.add_command(ping)
    # bot.tree.add_command(hello)
    # bot.tree.add_command(echo)
    # bot.tree.add_command(shop_slash)
    # bot.tree.add_command(waifu_slash)
    # for cmd in SLASH_ACTION_COMMANDS:
    #     bot.tree.add_command(cmd)

    bot.add_command(spawn_hybrid)
    bot.add_command(spam_hybrid)
    bot.add_command(stop_hybrid)
