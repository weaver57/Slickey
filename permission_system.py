"""Server-scoped, policy-based permissions for Slickey.

This module deliberately does not use Discord's permission model.  Discord is
used only to identify the current guild owner; Slickey permissions remain a
separate, fully configurable system.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands


# This account is the bot creator, not a guild role.  It is intentionally a
# permanent bypass and must be shown as "Bot Creator" in future dashboard UI.
BOT_CREATOR_ID = 1068465457910267975


def is_superuser(user_id: int, guild_owner_id: Optional[int] = None) -> bool:
    """The only two unconditional identities: Bot Creator and current owner."""
    return user_id == BOT_CREATOR_ID or (guild_owner_id is not None and user_id == guild_owner_id)


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str
    matched_rule_id: Optional[int] = None
    trace: tuple[dict[str, Any], ...] = ()


# Every command shipped by the bot is deliberately classified here.  Unknown
# commands fail closed at runtime, rather than silently becoming public.
# Values are (category, default access).  ``protected`` commands require an
# allow policy; ``public`` commands remain available unless a rule denies them.
COMMAND_REGISTRY: dict[str, tuple[str, str]] = {
    # Permission and server configuration
    **{name: ("configuration", "protected") for name in (
        "permissions", "dashboard", "setup", "setprefix", "selfprefix", "setperm", "showperm", "spawn",
    )},
    # Moderation and actions that affect another member or Discord role
    **{name: ("moderation", "protected") for name in (
        "mute", "unmute", "ban", "unban", "purge", "purgereaction", "setnick",
        "role", "setrole", "roleroulette", "role_roulette", "modlogs",
        "sljail", "slunjail", "slmute", "slunmute", "slkick", "slsetnick", "slrole", "slwhip",
        "massban", "massunban", "say", "echo", "spam", "stop",
    )},
    # Economy — all commands are publicly accessible by default
    **{name: ("economy", "public") for name in (
        "give", "tip", "tribute", "slbuy", "slrelease", "slrefund", "trade", "auction",
        "buycmd", "beg", "daily", "escape", "fetchwater", "bakebread", "fanmaster",
        "minerock", "shinecrown", "jackpot", "wish",
    )},
    # Safe, self-service and informational commands
    **{name: ("utility", "public") for name in (
        "afk", "msgcount", "av", "bn", "whois", "wallet", "chkprice",
        "shop", "slshow", "slinfo", "help", "ping", "hello", "waifu", "wtags", "lb",
        "ai_personality", "ai_forget", "ai",
    )},
    # Bot-creator only — these commands are invisible to everyone else
    **{name: ("creator", "protected") for name in (
        "balance", "debug", "getmem", "checkfunction", "iw", "dw",
    )},
    # Games — interactive games and their help subcommands
    **{name: ("games", "public") for name in (
        "cf", "diceroll", "buckshot", "colorwars", "memory",
        "buckshot_help", "colorwars_help", "memory_help", "yazy",
    )},
}
# Slickey_Secondary_ creates these commands dynamically from ``ACTIONS``.
# Keeping their source list here makes the registry complete without creating a
# circular import with utils.py (which imports this module).
PUBLIC_ACTION_COMMANDS = (
    "angry", "bite", "bleh", "blowkiss", "blush", "bonk", "bored", "bye", "carry", "clap",
    "confused", "cry", "cuddle", "dance", "eat", "facepalm", "feed", "handhold", "handshake",
    "happy", "hi", "highfive", "hug", "kick", "kill", "kiss", "lappillow", "laugh", "nod",
    "nope", "nya", "pat", "peek", "poke", "pout", "punch", "run", "salute", "shake",
    "shocked", "shoot", "shrug", "shy", "sip", "slap", "sleep", "smile", "smug", "spin",
    "stare", "taunt", "teehee", "think", "thumbsup", "tickle", "wag", "wallslam", "wave",
    "wink", "yawn", "yeet",
)
COMMAND_REGISTRY.update({name: ("social", "public") for name in PUBLIC_ACTION_COMMANDS})

# Compatibility aliases share one stable policy key.  The values, not the
# spellings users type, are persisted in new rules.
COMMAND_ALIASES = {"role_roulette": "roleroulette"}

# --- Auto-registration decorator ---
def slickey_command(category: str, access: str = "protected"):
    """Mark a command function with metadata for auto-registration.

    Apply this decorator *before* the discord.py command decorator::

        @commands.hybrid_command(name="mute")
        @slickey_command("moderation", "protected")
        async def mute(ctx, ...): ...

    At startup, ``build_registry()`` scans all registered bot commands and
    reads this metadata from ``cmd.callback`` to populate COMMAND_REGISTRY
    and CATEGORY_MAP automatically.
    """
    def decorator(func):
        if not hasattr(func, "_slickey_meta"):
            func._slickey_meta = {}
        func._slickey_meta["category"] = category
        func._slickey_meta["access"] = access
        return func
    return decorator


def build_registry(bot) -> None:
    """Scan every registered command and populate COMMAND_REGISTRY.

    Called once in ``main()`` after all cogs/commands are loaded.  Commands
    decorated with ``@slickey_command`` are placed in the registry by their
    metadata.  Any command *not* decorated falls back to the hardcoded values
    already present in COMMAND_REGISTRY (imported at module level).
    """
    for cmd in bot.commands:  # prefix + hybrid commands
        cb = getattr(cmd, "callback", None)
        meta = getattr(cb, "_slickey_meta", None) if cb else None
        if meta:
            COMMAND_REGISTRY[cmd.name] = (meta["category"], meta["access"])
    for cmd in bot.tree.get_commands():  # pure slash commands
        cb = getattr(cmd, "callback", None)
        meta = getattr(cb, "_slickey_meta", None) if cb else None
        if meta:
            COMMAND_REGISTRY[cmd.name] = (meta["category"], meta["access"])
    # Rebuild derived dicts
    global COMMAND_CATEGORIES, PROTECTED_COMMANDS
    COMMAND_CATEGORIES = {name: cat for name, (cat, _) in COMMAND_REGISTRY.items()}
    PROTECTED_COMMANDS = {name for name, (_, acc) in COMMAND_REGISTRY.items() if acc == "protected"}

# ``command.dashboard`` is the historical grant used to open the web dashboard.
# It is kept as an alias of ``policy.dashboard.access`` so existing server
# rules continue to grant dashboard access after the rename.  No engine code
# needs to special-case it; the alias is resolved when a rule is saved or when
# the evaluator looks up the policy catalogue.
DASHBOARD_POLICY_KEY = "policy.dashboard.access"
LEGACY_DASHBOARD_ALIAS = "command.dashboard"


def canonical_policy_key(permission_key: str) -> str:
    """Return the persisted policy key, mapping legacy aliases forward.

    This is the single place where ``command.dashboard`` is rewritten to its
    successor.  Callers should normalise before saving or evaluating.
    """
    key = permission_key.lower().strip()
    if key == LEGACY_DASHBOARD_ALIAS:
        return DASHBOARD_POLICY_KEY
    return key

COMMAND_CATEGORIES = {name: category for name, (category, _) in COMMAND_REGISTRY.items()}

# Friendly names used by the dashboard.  Keys not listed here remain fully
# supported as ``command.<name>`` policies; every prefix and slash command is
# still passed through ``install`` below.
COMMAND_DISPLAY_NAMES = {
    "permissions": "Permissions", "dashboard": "Dashboard access", "setprefix": "Set server prefix",
    "ban": "Ban member", "unban": "Unban member", "mute": "Mute member", "unmute": "Unmute member",
    "purge": "Purge messages", "setnick": "Set nickname", "role": "Manage Discord role",
    "modlogs": "View moderation logs", "wallet": "Wallet", "balance": "Balance",
    "give": "Give currency", "tip": "Tip", "daily": "Daily reward", "beg": "Beg",
}


def command_display_name(command_name: str) -> str:
    return COMMAND_DISPLAY_NAMES.get(
        command_name, command_name.replace("_", " ").replace("-", " ").title()
    )


@dataclass(frozen=True)
class PermissionDefinition:
    """A stable, documented permission the policy engine may later enforce."""
    key: str
    display_name: str
    description: str
    category: str
    default_access: str
    kind: str


def builtin_permission_definitions() -> tuple[PermissionDefinition, ...]:
    """Return the version-controlled catalogue used to seed the database.

    Command permissions remain compatible with existing ``command.<name>``
    rules.  The policy entries reserve a separate namespace for the upcoming
    fine-grained policy-administration layer; they are not command aliases.
    """
    definitions = [
        PermissionDefinition(
            key=f"command.{name}", display_name=command_display_name(name),
            description=f"Use the {name} command.", category=category,
            default_access=access, kind="command",
        )
        for name, (category, access) in COMMAND_REGISTRY.items()
    ]
    definitions.extend(
        PermissionDefinition(
            key=f"category.{category}", display_name=f"{category.title()} commands",
            description=f"Use all commands in the {category} category.",
            category=category, default_access="protected", kind="category",
        )
        for category in sorted(set(COMMAND_CATEGORIES.values()))
    )
    definitions.extend(
        PermissionDefinition(key, label, description, "policy", "protected", "policy")
        for key, label, description in (
            ("policy.dashboard.access", "Open the dashboard", "Open this server's Slickey web dashboard."),
            ("policy.rule.read", "View policies", "View this server's custom permission policies."),
            ("policy.rule.create", "Create policies", "Create scoped allow policies."),
            ("policy.rule.update", "Edit policies", "Edit existing permission policies."),
            ("policy.rule.delete", "Delete policies", "Delete existing permission policies."),
            ("policy.rule.create_deny", "Create deny policies", "Create scoped deny policies."),
            ("policy.role.read", "View custom roles", "View this server's Slickey custom roles."),
            ("policy.role.create", "Create custom roles", "Create Slickey custom roles."),
            ("policy.role.update", "Edit custom roles", "Rename or reprioritize Slickey custom roles."),
            ("policy.role.assign", "Assign custom roles", "Assign or remove Slickey custom roles."),
            ("policy.role.delete", "Delete custom roles", "Delete Slickey custom roles."),
            ("policy.role.auto_assign", "Auto-assign roles", "Configure roles that are automatically given to new members."),
            ("policy.audit.read", "View policy audit log", "View permission-policy change history."),
        )
    )
    return tuple(definitions)


BUILTIN_PERMISSION_DEFINITIONS = builtin_permission_definitions()
PERMISSION_DEFINITIONS_BY_KEY = {definition.key: definition for definition in BUILTIN_PERMISSION_DEFINITIONS}

# Presets are deliberately small and editable after creation.  Administrator
# means administrator of Slickey, not Discord's native Administrator bit.
ROLE_PRESETS: dict[str, dict[str, Any]] = {
    "administrator": {"name": "Administrator", "description": "Full Slickey administration", "rank": 50,
                      "permissions": ("command.*",)},
    "moderator": {"name": "Moderator", "description": "Standard moderation tools", "rank": 40,
                  "permissions": ("category.moderation", "command.dashboard")},
    "trial_moderator": {"name": "Trial Moderator", "description": "Limited moderation tools", "rank": 30,
                         "permissions": ("command.mute", "command.unmute", "command.purge")},
    "event_manager": {"name": "Event Manager", "description": "Event and game tools", "rank": 20,
                      "permissions": ("command.dashboard",)},
    "economy_manager": {"name": "Economy Manager", "description": "Economy-management tools", "rank": 10,
                        "permissions": ("category.economy", "command.dashboard")},
}

# These change server state, affect other members, or control the bot itself.
# They start denied to normal members; owners grant them deliberately.  Every
# other registered command defaults to public, and any command can still be
# explicitly allowed or denied by a rule.
PROTECTED_COMMANDS = {name for name, (_, access) in COMMAND_REGISTRY.items() if access == "protected"}


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bot_permission_roles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    rank INTEGER NOT NULL DEFAULT 0,
    created_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (guild_id, name)
);

CREATE TABLE IF NOT EXISTS bot_role_memberships (
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL REFERENCES bot_permission_roles(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    assigned_by BIGINT,
    source TEXT NOT NULL DEFAULT 'manual',
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_id, role_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_bot_role_memberships_user
    ON bot_role_memberships (guild_id, user_id);

CREATE TABLE IF NOT EXISTS bot_permission_rules (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('member', 'role', 'user')),
    subject_id BIGINT,
    permission_key TEXT NOT NULL,
    scope_type TEXT NOT NULL CHECK (scope_type IN ('guild', 'category', 'channel')),
    scope_id BIGINT,
    effect TEXT NOT NULL CHECK (effect IN ('allow', 'deny')),
    priority INTEGER NOT NULL DEFAULT 0,
    conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
    expires_at TIMESTAMPTZ,
    revision INTEGER NOT NULL DEFAULT 1,
    created_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK ((subject_type = 'member' AND subject_id IS NULL) OR
           (subject_type <> 'member' AND subject_id IS NOT NULL)),
    CHECK ((scope_type = 'guild' AND scope_id IS NULL) OR
           (scope_type <> 'guild' AND scope_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_bot_permission_rules_lookup
    ON bot_permission_rules (guild_id, subject_type, subject_id, scope_type, scope_id);

CREATE TABLE IF NOT EXISTS bot_permission_definitions (
    permission_key TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL,
    default_access TEXT NOT NULL CHECK (default_access IN ('public', 'protected', 'owner_only')),
    permission_kind TEXT NOT NULL CHECK (permission_kind IN ('command', 'category', 'policy')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_permission_audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    actor_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_permission_migrations (
    name TEXT PRIMARY KEY,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_role_auto_assign (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL REFERENCES bot_permission_roles(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS bot_role_discord_sync (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    discord_role_id BIGINT NOT NULL,
    slickey_role_id BIGINT NOT NULL REFERENCES bot_permission_roles(id) ON DELETE CASCADE,
    on_remove TEXT NOT NULL DEFAULT 'keep' CHECK (on_remove IN ('keep', 'remove')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (guild_id, discord_role_id, slickey_role_id)
);

CREATE TABLE IF NOT EXISTS bot_command_catalog (
    command_path TEXT PRIMARY KEY,
    permission_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL,
    default_access TEXT NOT NULL CHECK (default_access IN ('public', 'protected', 'owner_only')),
    command_kind TEXT NOT NULL,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def initialize_permission_system(pool) -> None:
    """Create tables and import the old internal roles exactly once per row."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(SCHEMA_SQL)
            # Existing installations already have this table, so add Phase 2
            # fields independently of CREATE TABLE IF NOT EXISTS.
            await conn.execute("""
                ALTER TABLE bot_permission_rules
                    ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
                    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
                    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1,
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_bot_permission_rules_evaluate
                    ON bot_permission_rules
                    (guild_id, permission_key, subject_type, subject_id,
                        scope_type, scope_id, expires_at);
            """)
            # Upgrade audit log schema: add human-readable actor name and
            # before/after state snapshots so the trail is reconstructable.
            await conn.execute("""
                ALTER TABLE bot_permission_audit_log
                    ADD COLUMN IF NOT EXISTS actor_name TEXT NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS before_state JSONB,
                    ADD COLUMN IF NOT EXISTS after_state JSONB;
            """)
            # Track provenance: distinguish manual grants from auto-assign
            # and Discord role sync so automated systems never overwrite
            # intentional human assignments.
            await conn.execute("""
                ALTER TABLE bot_role_memberships
                    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual';
            """)
            for definition in BUILTIN_PERMISSION_DEFINITIONS:
                await conn.execute(
                    """INSERT INTO bot_permission_definitions
                       (permission_key, display_name, description, category, default_access, permission_kind)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       ON CONFLICT (permission_key) DO UPDATE SET
                         display_name=EXCLUDED.display_name, description=EXCLUDED.description,
                         category=EXCLUDED.category, default_access=EXCLUDED.default_access,
                         permission_kind=EXCLUDED.permission_kind, updated_at=NOW()""",
                    definition.key, definition.display_name, definition.description,
                    definition.category, definition.default_access, definition.kind,
                )
            # Normalise policy keys introduced before canonical command aliases
            # existed.  This is idempotent and keeps existing real-server rules
            # effective after a command spelling is corrected.
            for old_name, canonical_name in COMMAND_ALIASES.items():
                await conn.execute(
                    "UPDATE bot_permission_rules SET permission_key = $1 WHERE permission_key = $2",
                    f"command.{canonical_name}", f"command.{old_name}",
                )
            # Migrate the historical ``command.dashboard`` grant to its successor
            # so existing rules continue to open the dashboard after the rename.
            await conn.execute(
                "UPDATE bot_permission_rules SET permission_key = $1 WHERE permission_key = $2",
                DASHBOARD_POLICY_KEY, LEGACY_DASHBOARD_ALIAS,
            )
            # Import existing data once.  The old tables are never consulted by
            # policy evaluation; this is a safe, reversible migration path.
            migrated = await conn.fetchval("SELECT 1 FROM bot_permission_migrations WHERE name = 'legacy-v1'")
            if migrated:
                return
            has_roles = await conn.fetchval("SELECT to_regclass('public.roles') IS NOT NULL")
            has_command_permissions = await conn.fetchval("SELECT to_regclass('public.command_permissions') IS NOT NULL")
            has_blocked_commands = await conn.fetchval("SELECT to_regclass('public.blocked_commands') IS NOT NULL")
            if not any((has_roles, has_command_permissions, has_blocked_commands)):
                await conn.execute("INSERT INTO bot_permission_migrations (name) VALUES ('legacy-v1')")
                return
            legacy_rows = await conn.fetch("SELECT guild_id, user_id, role, level FROM roles WHERE role IN ('moderator', 'admin', 'authorized')") if has_roles else ()
            for row in legacy_rows:
                role_id = await conn.fetchval(
                    """INSERT INTO bot_permission_roles (guild_id, name, description, rank)
                       VALUES ($1, $2, $3, $4)
                       ON CONFLICT (guild_id, name) DO UPDATE SET name = EXCLUDED.name
                       RETURNING id""",
                    row["guild_id"], row["role"].title(), "Migrated from Slickey's legacy permission system", row["level"],
                )
                await conn.execute(
                    """INSERT INTO bot_role_memberships (guild_id, role_id, user_id, source)
                       VALUES ($1, $2, $3, 'manual') ON CONFLICT DO NOTHING""",
                    row["guild_id"], role_id, row["user_id"],
                )
            command_permissions = await conn.fetch("SELECT guild_id, user_id, command_name FROM command_permissions") if has_command_permissions else ()
            for row in command_permissions:
                await conn.execute(
                    """INSERT INTO bot_permission_rules
                       (guild_id, subject_type, subject_id, permission_key, scope_type, scope_id, effect, created_by)
                       VALUES ($1, 'user', $2, $3, 'guild', NULL, 'allow', NULL)""",
                    row["guild_id"], row["user_id"], f"command.{canonical_command_name(row['command_name'])}",
                )
            blocked_commands = await conn.fetch("SELECT guild_id, user_id, command_name FROM blocked_commands") if has_blocked_commands else ()
            for row in blocked_commands:
                await conn.execute(
                    """INSERT INTO bot_permission_rules
                       (guild_id, subject_type, subject_id, permission_key, scope_type, scope_id, effect, created_by)
                       VALUES ($1, 'user', $2, $3, 'guild', NULL, 'deny', NULL)""",
                    row["guild_id"], row["user_id"], f"command.{canonical_command_name(row['command_name'])}",
                )
            await conn.execute("INSERT INTO bot_permission_migrations (name) VALUES ('legacy-v1')")


async def sync_command_catalog(pool, bot: commands.Bot) -> set[str]:
    """Register every loaded command and fail closed until it is classified."""
    if pool is None:
        return set()
    entries: dict[str, tuple[str, str, str, str, str]] = {}
    review_required: set[str] = set()
    # Collect names already seen via text/prefix commands so hybrid
    # commands (which appear in both bot.commands and bot.tree) are
    # recorded only once — as the prefix variant.
    text_names: set[str] = set()
    for command in bot.commands:
        if command.name == "help":
            continue
        text_names.add(command.name.lower())
        path = command.qualified_name.lower()
        name = command.name.lower()
        canonical = canonical_command_name(name)
        known = canonical in COMMAND_REGISTRY
        category, access = COMMAND_REGISTRY.get(canonical, ("unclassified", "protected"))
        if not known:
            review_required.add(name)
        entries[f"prefix:{path}"] = (f"command.{canonical}", command.name.replace("_", " ").title(), command.help or command.description or "", category, access)
    for command in bot.tree.walk_commands():
        if isinstance(command, app_commands.Group):
            continue
        path = command.qualified_name.lower()
        name = path.split()[-1]
        # Skip slash commands that are hybrids — they were already
        # captured in the text/prefix pass above.
        if name in text_names:
            continue
        root = path.split()[0]
        canonical = canonical_command_name(root)
        known = canonical in COMMAND_REGISTRY
        category, access = COMMAND_REGISTRY.get(canonical, ("unclassified", "protected"))
        if not known:
            review_required.add(root)
        entries[f"slash:{path}"] = (f"command.{canonical}", path.replace("_", " ").title(), command.description or "", category, access)
    async with pool.acquire() as conn:
        for path, (permission_key, label, description, category, access) in entries.items():
            await conn.execute(
                """INSERT INTO bot_command_catalog (command_path, permission_key, display_name, description, category, default_access, command_kind)
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT (command_path) DO UPDATE SET permission_key=EXCLUDED.permission_key, display_name=EXCLUDED.display_name,
                   description=EXCLUDED.description, category=EXCLUDED.category, default_access=EXCLUDED.default_access,
                   command_kind=EXCLUDED.command_kind, updated_at=NOW()""",
                path, permission_key, label, description[:500], category, access, path.split(":", 1)[0],
            )
        # Remove stale catalog rows left over from previous runs (e.g.
        # duplicate ``slash:`` entries created before the hybrid dedup).
        if entries:
            await conn.execute(
                "DELETE FROM bot_command_catalog WHERE command_path != ALL($1::text[])",
                list(entries.keys()),
            )
    bot._slickey_unclassified_commands = review_required
    return review_required


def is_broad_deny(permission_key: str, scope_type: str, effect: str) -> bool:
    """Broad denies can unexpectedly lock down a server, so require confirmation."""
    return effect == "deny" and (scope_type == "guild" or permission_key in {"*", "command.*", "category.*"})


async def create_preset(pool, *, guild_id: int, preset_key: str, actor_id: int) -> int:
    preset = ROLE_PRESETS.get(preset_key)
    if not preset:
        raise ValueError("Unknown role preset")
    async with pool.acquire() as conn:
        async with conn.transaction():
            role_id = await conn.fetchval(
                """INSERT INTO bot_permission_roles (guild_id, name, description, rank, created_by)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                guild_id, preset["name"], preset["description"], preset["rank"], actor_id,
            )
            for permission_key in preset["permissions"]:
                await conn.execute(
                    """INSERT INTO bot_permission_rules
                       (guild_id, subject_type, subject_id, permission_key, scope_type, scope_id, effect, created_by)
                       VALUES ($1, 'role', $2, $3, 'guild', NULL, 'allow', $4)""",
                    guild_id, role_id, permission_key, actor_id,
                )
    return role_id


def canonical_command_name(command_name: str) -> str:
    """Return the persisted root command key for prefix and slash commands."""
    name = command_name.lower().strip().replace("/", "").split()[0]
    return COMMAND_ALIASES.get(name, name)


def command_keys(command_name: str, category: Optional[str] = None) -> tuple[str, ...]:
    name = canonical_command_name(command_name)
    category = category or COMMAND_CATEGORIES.get(name, "general")
    return (f"command.{name}", f"category.{category}", "command.*", "category.*", "*")


def policy_keys(permission_key: str) -> tuple[str, ...]:
    """Return a policy key and its namespace wildcards, most specific first."""
    parts = permission_key.lower().strip().split(".")
    if not permission_key or any(not part for part in parts):
        return ()
    keys = [".".join(parts)]
    keys.extend(".".join(parts[:index] + ["*"]) for index in range(len(parts) - 1, 0, -1))
    keys.append("*")
    return tuple(dict.fromkeys(keys))


def default_allowed(command_name: str) -> bool:
    return COMMAND_REGISTRY.get(canonical_command_name(command_name), ("unclassified", "protected"))[1] == "public"


def _scope_candidates(channel_id: Optional[int], category_id: Optional[int]) -> tuple[tuple[str, Optional[int]], ...]:
    candidates: list[tuple[str, Optional[int]]] = []
    if channel_id is not None:
        candidates.append(("channel", channel_id))
    if category_id is not None:
        candidates.append(("category", category_id))
    candidates.append(("guild", None))
    return tuple(candidates)


def _rule_is_expired(rule: Any, now: Optional[datetime] = None) -> bool:
    """Return whether a stored rule is no longer effective.

    ``asyncpg`` returns a timezone-aware datetime.  The defensive naive-value
    branch keeps policy evaluation predictable for imports and unit tests.
    """
    expires_at = rule.get("expires_at") if hasattr(rule, "get") else rule["expires_at"]
    if expires_at is None:
        return False
    now = now or datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now


TARGET_CONDITION_KEYS = frozenset({
    "max_custom_role_rank", "member_ids", "exclude_member_ids",
    "custom_role_ids", "exclude_custom_role_ids",
})


def validate_target_conditions(conditions: Any) -> dict[str, Any]:
    """Validate the small, intentional condition language used for member targets.

    Conditions are currently limited to target protection.  Keeping this format
    closed avoids storing a pretend-general expression language that commands
    cannot safely evaluate.  A rule without conditions remains unchanged.
    """
    if conditions in (None, {}):
        return {}
    if not isinstance(conditions, dict) or set(conditions) != {"target"}:
        raise ValueError("Conditions may only contain a target object.")
    target = conditions["target"]
    if not isinstance(target, dict) or not target or set(target) - TARGET_CONDITION_KEYS:
        raise ValueError("Unsupported target condition.")
    normalized: dict[str, Any] = {}
    for key, value in target.items():
        if key == "max_custom_role_rank":
            if type(value) is not int or not -100_000 <= value <= 100_000:
                raise ValueError("target.max_custom_role_rank must be an integer between -100000 and 100000.")
            normalized[key] = value
            continue
        if not isinstance(value, list) or not value or len(value) > 100 or any(type(item) is not int or item <= 0 for item in value):
            raise ValueError(f"target.{key} must be a non-empty list of up to 100 positive IDs.")
        normalized[key] = sorted(set(value))
    if {"member_ids", "exclude_member_ids"} <= normalized.keys() or {"custom_role_ids", "exclude_custom_role_ids"} <= normalized.keys():
        raise ValueError("A target condition cannot include both an allow-list and deny-list for the same target type.")
    return {"target": normalized}


def target_conditions_match(conditions: Any, *, target_user_id: Optional[int], target_rank: int,
                            target_role_ids: set[int]) -> bool:
    """Return whether a rule is applicable to this member target.

    A condition never grants access by itself: it only narrows the rule on
    which it is written.  ``member_ids``/``custom_role_ids`` create allow
    lists; the ``exclude_*`` variants create protected target lists.
    """
    if not conditions:
        return True
    try:
        if isinstance(conditions, str):
            conditions = json.loads(conditions)
        target = validate_target_conditions(conditions).get("target", {})
    except ValueError:
        return False
    if target and target_user_id is None:
        return False
    if "max_custom_role_rank" in target and target_rank > target["max_custom_role_rank"]:
        return False
    if "member_ids" in target and target_user_id not in target["member_ids"]:
        return False
    if "exclude_member_ids" in target and target_user_id in target["exclude_member_ids"]:
        return False
    if "custom_role_ids" in target and not target_role_ids.intersection(target["custom_role_ids"]):
        return False
    if "exclude_custom_role_ids" in target and target_role_ids.intersection(target["exclude_custom_role_ids"]):
        return False
    return True


TARGET_CONDITION_COMMANDS = frozenset({"ban", "mute", "unmute", "setnick", "role", "roleroulette"})


def conditions_supported_for_permission(permission_key: str) -> bool:
    """Target rules are safe only for commands routed through the shared guard."""
    return permission_key in {f"command.{name}" for name in TARGET_CONDITION_COMMANDS}


async def evaluate(
    pool, *, guild_id: int, user_id: int, guild_owner_id: Optional[int], command_name: str,
    channel_id: Optional[int] = None, category_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    preflight_target_conditions: bool = False,
    strict_unclassified: bool = False, permission_keys_override: Optional[tuple[str, ...]] = None,
) -> PermissionDecision:
    """Evaluate a policy.  Specific deny wins; otherwise specific allow wins.

    A command with no matching policy stays available. This preserves existing
    public-command behaviour while servers progressively add their own rules.
    """
    if user_id == BOT_CREATOR_ID:
        return PermissionDecision(True, "Bot Creator bypass", trace=({"kind": "bypass", "label": "Bot Creator has permanent access."},))
    if guild_owner_id is not None and user_id == guild_owner_id:
        # The guild owner still cannot use creator-category commands.
        _owner_cat = COMMAND_CATEGORIES.get(command_name, "")
        if _owner_cat != "creator":
            return PermissionDecision(True, "Current Discord server owner", trace=({"kind": "bypass", "label": "Current Discord server owner has permanent access."},))
    if pool is None:
        allowed = default_allowed(command_name) and not strict_unclassified
        return PermissionDecision(allowed, "Permission database unavailable; protected commands fail closed", trace=({"kind": "fallback", "label": "Permission database unavailable.", "outcome": "Allowed public command" if allowed else "Denied protected command"},))

    keys = permission_keys_override or command_keys(command_name)
    async with pool.acquire() as conn:
        role_ids = await conn.fetch(
            "SELECT role_id FROM bot_role_memberships WHERE guild_id = $1 AND user_id = $2", guild_id, user_id
        )
        target_role_ids = await conn.fetch(
            "SELECT role_id FROM bot_role_memberships WHERE guild_id = $1 AND user_id = $2", guild_id, target_user_id
        ) if target_user_id is not None else ()
        subject_pairs = [("member", None), ("user", user_id)]
        subject_pairs.extend(("role", row["role_id"]) for row in role_ids)
        # The evaluator still makes the final matching decision in Python so
        # its trace remains complete, but this query avoids loading unrelated
        # rules from the rest of a large server.
        rules = await conn.fetch(
            """SELECT id, subject_type, subject_id, permission_key, scope_type,
                      scope_id, effect, priority, conditions, expires_at
               FROM bot_permission_rules
               WHERE guild_id = $1
                 AND permission_key = ANY($2::text[])
                 AND (expires_at IS NULL OR expires_at > NOW())
                 AND (
                    (subject_type = 'member' AND subject_id IS NULL)
                    OR (subject_type = 'user' AND subject_id = $3)
                    OR (subject_type = 'role' AND subject_id = ANY($4::bigint[]))
                 )
                 AND (
                    (scope_type = 'guild' AND scope_id IS NULL)
                    OR (scope_type = 'category' AND scope_id = $5)
                    OR (scope_type = 'channel' AND scope_id = $6)
                 )""",
            guild_id, list(keys), user_id, [row["role_id"] for row in role_ids], category_id, channel_id,
        )

    scope_rank = {"guild": 0, "category": 1, "channel": 2}
    subject_rank = {"member": 0, "role": 1, "user": 2}
    key_rank = {key: len(keys) - index for index, key in enumerate(keys)}
    candidates = []
    allowed_subjects = set(subject_pairs)
    allowed_scopes = set(_scope_candidates(channel_id, category_id))
    target_roles = {row["role_id"] for row in target_role_ids}
    target_rank = await effective_rank(pool, guild_id, target_user_id) if target_user_id is not None else 0
    for rule in rules:
        if (rule["subject_type"], rule["subject_id"]) not in allowed_subjects:
            continue
        if (rule["scope_type"], rule["scope_id"]) not in allowed_scopes or rule["permission_key"] not in key_rank:
            continue
        if _rule_is_expired(rule):
            continue
        conditions = rule.get("conditions", {})
        # The universal command gate runs before handlers have parsed a target.
        # It may admit a target-limited allow so the shared target guard can
        # make the final decision, but it must never turn a target-limited deny
        # into a blanket command denial.
        if target_user_id is None and preflight_target_conditions and conditions and rule["effect"] == "deny":
            continue
        if not (target_user_id is None and preflight_target_conditions and conditions) and not target_conditions_match(
            conditions, target_user_id=target_user_id, target_rank=target_rank, target_role_ids=target_roles,
        ):
            continue
        # More concrete key/scope/subject always wins. At the same specificity,
        # a higher explicit priority wins.  A deny is safer only when every
        # specificity dimension, including priority, is tied.  Exact duplicate
        # effects resolve to the newest rule, which makes imports and manual
        # conflict recovery deterministic until rule editing is added.
        rank = (
            scope_rank[rule["scope_type"]], key_rank[rule["permission_key"]],
            subject_rank[rule["subject_type"]], rule.get("priority", 0),
            1 if rule["effect"] == "deny" else 0, rule["id"],
        )
        candidates.append((rank, rule))
    if not candidates:
        if default_allowed(command_name) and not strict_unclassified:
            return PermissionDecision(True, "Public command default", trace=({"kind": "default", "label": "No matching policy. This command is public by default."},))
        label = "This command has not yet been classified in the catalogue." if strict_unclassified else "No matching allow policy. This command is protected by default."
        return PermissionDecision(False, "Protected command; no allow rule", trace=({"kind": "default", "label": label},))
    ordered = sorted(candidates, key=lambda item: item[0], reverse=True)
    _, rule = ordered[0]
    trace = tuple({
        "kind": "rule", "id": item[1]["id"], "effect": item[1]["effect"],
        "permission_key": item[1]["permission_key"], "subject_type": item[1]["subject_type"],
        "subject_id": item[1]["subject_id"], "scope_type": item[1]["scope_type"],
        "scope_id": item[1]["scope_id"], "priority": item[1].get("priority", 0),
        "conditions": item[1].get("conditions", {}),
        "expires_at": item[1].get("expires_at"), "selected": index == 0,
    } for index, item in enumerate(ordered))
    return PermissionDecision(rule["effect"] == "allow", f"{rule['effect'].title()} rule #{rule['id']}", rule["id"], trace)


async def evaluate_permission(
    pool, *, guild_id: int, user_id: int, guild_owner_id: Optional[int], permission_key: str,
    channel_id: Optional[int] = None, category_id: Optional[int] = None,
) -> PermissionDecision:
    """Evaluate a non-command permission using the same policy precedence."""
    keys = policy_keys(permission_key)
    if not keys:
        return PermissionDecision(False, "Invalid permission key")
    return await evaluate(
        pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
        command_name="__policy_permission__", channel_id=channel_id, category_id=category_id,
        strict_unclassified=True, permission_keys_override=keys,
    )


async def actor_can_manage(pool, *, guild_id: int, user_id: int, guild_owner_id: Optional[int], action: str) -> bool:
    """Compatibility gateway for the original ``command.permissions`` grant."""
    if is_superuser(user_id, guild_owner_id):
        return True
    decision = await evaluate(pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id, command_name="permissions")
    return decision.allowed and decision.matched_rule_id is not None


# Sections the dashboard may expose.  Each section is gated by an existing
# ``policy.*`` capability so the engine is the single source of truth.
# ``overview`` is always visible to anyone who can open the dashboard.
DASHBOARD_SECTIONS: tuple[str, ...] = ("overview", "roles", "policies", "simulator", "auto-assign", "role-sync", "audit", "catalog")

_DASHBOARD_SECTION_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "overview": (DASHBOARD_POLICY_KEY,),
    "roles": ("policy.role.read",),
    "policies": ("policy.rule.read",),
    "simulator": ("policy.rule.read",),
    "audit": ("policy.audit.read",),
    # The command catalogue is a read-only reference that anyone who can open
    # the dashboard may browse; it inherits the access key.
    "auto-assign": ("policy.role.assign",),
    "role-sync": ("policy.role.assign",),
    # The command catalogue is a read-only reference that anyone who can open
    # the dashboard may browse; it inherits the access key.
    "catalog": (DASHBOARD_POLICY_KEY,),
}


async def dashboard_view_sections(
    pool, *, guild_id: int, user_id: int, guild_owner_id: Optional[int],
    channel_id: Optional[int] = None, category_id: Optional[int] = None,
) -> set[str]:
    """Return the set of dashboard sections the user can see.

    A user who can open the dashboard at all always sees ``overview`` and the
    read-only ``catalog``.  Other sections appear exactly when the user holds
    the corresponding ``policy.*`` capability.  This function only derives; it
    introduces no new grant model.
    """
    visible: set[str] = set()
    if pool is None:
        return visible
    if is_superuser(user_id, guild_owner_id):
        return set(DASHBOARD_SECTIONS)
    for section in DASHBOARD_SECTIONS:
        requirements = _DASHBOARD_SECTION_REQUIREMENTS[section]
        for key in requirements:
            decision = await evaluate_permission(
                pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
                permission_key=key, channel_id=channel_id, category_id=category_id,
            )
            if not (decision.allowed and decision.matched_rule_id is not None):
                break
        else:
            visible.add(section)
    return visible


# ── Auto-assign roles ────────────────────────────────────────────────


async def apply_auto_assign_roles(pool, guild_id: int, user_id: int) -> list[int]:
    """Assign all enabled auto-assign roles to a new member.

    Returns the list of role IDs that were assigned.
    """
    if pool is None:
        return []
    rows = await pool.fetch(
        "SELECT id, role_id FROM bot_role_auto_assign"
        " WHERE guild_id = $1 AND enabled = TRUE",
        guild_id,
    )
    if not rows:
        return []
    assigned: list[int] = []
    for row in rows:
        try:
            await pool.execute(
                "INSERT INTO bot_role_memberships"
                " (guild_id, role_id, user_id, assigned_by, source)"
                " VALUES ($1, $2, $3, $4, 'auto-assign') ON CONFLICT DO NOTHING",
                guild_id, row["role_id"], user_id, 0,  # 0 = system auto-assign
            )
            assigned.append(row["role_id"])
        except Exception:
            pass  # role may have been deleted between query and insert
    return assigned


# ── Discord role sync ────────────────────────────────────────────────


async def process_discord_role_sync(pool, guild_id: int, user_id: int,
                                    added_role_ids: list[int],
                                    removed_role_ids: list[int]) -> dict:
    """Process Discord role changes and apply/remove Slickey roles accordingly.

    Returns a dict with ``assigned`` and ``removed`` lists of Slickey role IDs.
    """
    if pool is None or (not added_role_ids and not removed_role_ids):
        return {"assigned": [], "removed": []}
    result = {"assigned": [], "removed": []}

    # ── Roles added on Discord → assign Slickey roles ──
    if added_role_ids:
        rows = await pool.fetch(
            "SELECT id, slickey_role_id FROM bot_role_discord_sync"
            " WHERE guild_id = $1 AND discord_role_id = ANY($2::bigint[]) AND enabled = TRUE",
            guild_id, added_role_ids,
        )
        for row in rows:
            try:
                await pool.execute(
                    "INSERT INTO bot_role_memberships"
                    " (guild_id, role_id, user_id, assigned_by, source)"
                    " VALUES ($1, $2, $3, $4, 'discord-sync') ON CONFLICT DO NOTHING",
                    guild_id, row["slickey_role_id"], user_id, 0,
                )
                result["assigned"].append(row["slickey_role_id"])
            except Exception:
                pass

    # ── Roles removed on Discord → handle on_remove policy ──
    # Only touch rows with source='discord-sync' so manually granted
    # Slickey roles are never yanked by sync automation.
    if removed_role_ids:
        rows = await pool.fetch(
            "SELECT id, slickey_role_id, on_remove FROM bot_role_discord_sync"
            " WHERE guild_id = $1 AND discord_role_id = ANY($2::bigint[]) AND enabled = TRUE",
            guild_id, removed_role_ids,
        )
        for row in rows:
            if row["on_remove"] == "remove":
                try:
                    await pool.execute(
                        "DELETE FROM bot_role_memberships"
                        " WHERE guild_id = $1 AND role_id = $2 AND user_id = $3"
                        " AND source = 'discord-sync'",
                        guild_id, row["slickey_role_id"], user_id,
                    )
                    result["removed"].append(row["slickey_role_id"])
                except Exception:
                    pass
    return result


# ── Permission simulator ──────────────────────────────────────────────


async def simulate_all(
    pool, *, guild_id: int, user_id: int, guild_owner_id: Optional[int],
    channel_id: Optional[int] = None, category_id: Optional[int] = None,
) -> dict[str, Any]:
    """Evaluate every registered command for a user in a given context.

    Returns a dict with:
    - ``user_id``, ``channel_id``, ``category_id``
    - ``user_roles``: list of custom Slickey role IDs the user holds
    - ``results``: list of ``{command, display_name, category, access,
      allowed, reason, matched_rule_id, trace}`` for each command
    - ``summary``: ``{allowed, denied, default}`` counts

    This is the backend for the permission simulator / "why" explainer.
    """
    if pool is None:
        return {"user_id": user_id, "channel_id": channel_id,
                "category_id": category_id, "user_roles": [],
                "results": [], "summary": {"allowed": 0, "denied": 0, "default": 0}}

    # Fetch the user's custom Slickey roles for display.
    async with pool.acquire() as conn:
        role_rows = await conn.fetch(
            "SELECT r.id, r.name, r.rank FROM bot_permission_roles r"
            " JOIN bot_role_memberships m ON m.role_id = r.id"
            " WHERE m.guild_id = $1 AND m.user_id = $2"
            " ORDER BY r.rank DESC, r.name",
            guild_id, user_id,
        )
    user_roles = [{"id": row["id"], "name": row["name"], "rank": row["rank"]} for row in role_rows]

    # Build the list of commands to evaluate.  Use the catalog if populated;
    # fall back to the in-memory COMMAND_REGISTRY.
    async with pool.acquire() as conn:
        catalog = await conn.fetch(
            "SELECT DISTINCT permission_key, display_name, category, default_access"
            " FROM bot_command_catalog ORDER BY category, display_name",
        )
    if not catalog:
        catalog = [
            {"permission_key": f"command.{name}", "display_name": command_display_name(name),
             "category": cat, "default_access": acc}
            for name, (cat, acc) in sorted(COMMAND_REGISTRY.items())
        ]

    results: list[dict[str, Any]] = []
    allowed_count = 0
    denied_count = 0
    default_count = 0

    for entry in catalog:
        perm_key = entry["permission_key"]
        cmd_name = perm_key.removeprefix("command.")
        decision = await evaluate(
            pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
            command_name=cmd_name, channel_id=channel_id, category_id=category_id,
        )
        # Classify the outcome.
        outcome = "allowed" if decision.allowed else "denied"
        if decision.matched_rule_id is None and not decision.allowed:
            outcome = "default"
            default_count += 1
        elif decision.allowed:
            allowed_count += 1
        else:
            denied_count += 1

        results.append({
            "command": cmd_name,
            "display_name": entry["display_name"],
            "category": entry["category"],
            "access": entry["default_access"],
            "allowed": decision.allowed,
            "outcome": outcome,
            "reason": decision.reason,
            "matched_rule_id": decision.matched_rule_id,
            "trace": list(decision.trace),
        })

    return {
        "user_id": user_id,
        "channel_id": channel_id,
        "category_id": category_id,
        "user_roles": user_roles,
        "results": results,
        "summary": {"allowed": allowed_count, "denied": denied_count, "default": default_count},
    }


async def actor_can_administer_policy(
    pool, *, guild_id: int, user_id: int, guild_owner_id: Optional[int], action: str,
    scope_type: str = "guild", scope_id: Optional[int] = None,
    context_category_id: Optional[int] = None,
) -> bool:
    """Check a scoped policy-management capability, with legacy compatibility."""
    if is_superuser(user_id, guild_owner_id):
        return True
    category_id = scope_id if scope_type == "category" else context_category_id
    channel_id = scope_id if scope_type == "channel" else None
    decision = await evaluate_permission(
        pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
        permission_key=action, channel_id=channel_id, category_id=category_id,
    )
    if decision.allowed and decision.matched_rule_id is not None:
        return True
    return await actor_can_manage(
        pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id, action=action,
    )


def _delegation_probes(permission_key: str) -> tuple[tuple[str, str], ...]:
    """Expand a requested grant into every capability it would cover."""
    key = permission_key.lower().strip()
    if key.startswith("command."):
        name = key.removeprefix("command.")
        if name == "*":
            return tuple(("command", command) for command in COMMAND_REGISTRY)
        return (("command", canonical_command_name(name)),)
    if key.startswith("category."):
        category = key.removeprefix("category.")
        categories = set(COMMAND_CATEGORIES.values()) if category == "*" else {category}
        return tuple(("command", name) for name, value in COMMAND_CATEGORIES.items() if value in categories)
    if key.startswith("policy."):
        if key.endswith(".*"):
            prefix = key[:-1]
            return tuple(("policy", definition.key) for definition in BUILTIN_PERMISSION_DEFINITIONS if definition.key.startswith(prefix))
        return (("policy", key),)
    return ()


async def actor_can_delegate_permission(
    pool, *, guild_id: int, user_id: int, guild_owner_id: Optional[int], permission_key: str,
    scope_type: str = "guild", scope_id: Optional[int] = None, effect: str = "allow",
) -> bool:
    """Delegates may grant only authority and scope they personally cover."""
    if not await actor_can_administer_policy(
        pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
        action="policy.rule.create_deny" if effect == "deny" else "policy.rule.create",
        scope_type=scope_type, scope_id=scope_id,
    ):
        return False
    if is_superuser(user_id, guild_owner_id):
        return True
    category_id = scope_id if scope_type == "category" else None
    channel_id = scope_id if scope_type == "channel" else None
    probes = _delegation_probes(permission_key)
    if not probes:
        return False
    for kind, key in probes:
        decision = (
            await evaluate(pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
                           command_name=key, channel_id=channel_id, category_id=category_id)
            if kind == "command" else
            await evaluate_permission(pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
                                      permission_key=key, channel_id=channel_id, category_id=category_id)
        )
        if not decision.allowed:
            return False
    return True


async def actor_can_delegate_preset(pool, *, guild_id: int, user_id: int, guild_owner_id: Optional[int], preset_key: str) -> bool:
    """A preset is a bundle of grants, so it must obey the same ceiling as a rule."""
    preset = ROLE_PRESETS.get(preset_key)
    if not preset:
        return False
    return all(await actor_can_delegate_permission(
        pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
        permission_key=permission,
    ) for permission in preset["permissions"])


async def permission_key_is_registered(pool, permission_key: str) -> bool:
    """Allow only catalogue-backed keys plus intentional global wildcards."""
    key = permission_key.lower().strip()
    if key in {"*", "command.*", "category.*"}:
        return True
    # Legacy ``command.dashboard`` is accepted on the way in and rewritten to
    # ``policy.dashboard.access`` before the rule is persisted.
    if key == LEGACY_DASHBOARD_ALIAS:
        return True
    if key.startswith("policy.") and key.endswith(".*"):
        return any(definition.key.startswith(key[:-1]) for definition in BUILTIN_PERMISSION_DEFINITIONS)
    if key in PERMISSION_DEFINITIONS_BY_KEY:
        return True
    # Command aliases are accepted at the UI edge but persisted canonically by
    # the caller before insertion.
    if key.startswith("command."):
        return f"command.{canonical_command_name(key.removeprefix('command.'))}" in PERMISSION_DEFINITIONS_BY_KEY
    return False


async def effective_rank(pool, guild_id: int, user_id: int) -> int:
    """Highest custom-role rank. Rank only protects targets; it grants nothing."""
    if pool is None:
        return 0
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """SELECT COALESCE(MAX(r.rank), 0) FROM bot_permission_roles r
               JOIN bot_role_memberships m ON m.role_id = r.id
               WHERE m.guild_id = $1 AND m.user_id = $2""", guild_id, user_id
        ) or 0


class PermissionsCog(commands.Cog):
    """The Discord management surface for the policy system.

    Rule subjects use role IDs (shown after creation) or Discord user IDs.  This
    keeps policy records stable when a role's display name changes.
    """

    permissions = app_commands.Group(name="permissions", description="Manage Slickey's custom permissions")

    def __init__(self, bot: commands.Bot, pool_getter):
        self.bot = bot
        self.pool_getter = pool_getter

    async def _manager(
        self, interaction: discord.Interaction, action: str,
        scope_type: str = "channel", scope_id: Optional[int] = None,
    ) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False
        allowed = await actor_can_administer_policy(
            self.pool_getter(), guild_id=interaction.guild.id, user_id=interaction.user.id,
            guild_owner_id=interaction.guild.owner_id, action=action,
            scope_type=scope_type,
            scope_id=getattr(interaction.channel, "id", None) if scope_id is None and scope_type == "channel" else scope_id,
            context_category_id=getattr(interaction.channel, "category_id", None) if scope_type == "channel" else None,
        )
        if not allowed:
            await interaction.response.send_message(
                f"You need the custom `{action}` permission here to do that.", ephemeral=True
            )
        return allowed

    async def _can_manage_rank(self, interaction: discord.Interaction, target_rank: int) -> bool:
        """Delegates may only change roles and people below their own rank."""
        if is_superuser(interaction.user.id, interaction.guild.owner_id):
            return True
        actor_rank = await effective_rank(self.pool_getter(), interaction.guild.id, interaction.user.id)
        if actor_rank > target_rank:
            return True
        await interaction.response.send_message(
            "You can only manage custom roles and members below your own role rank.", ephemeral=True
        )
        return False

    async def _can_manage_member(self, interaction: discord.Interaction, member: discord.Member) -> bool:
        return await self._can_manage_rank(
            interaction, await effective_rank(self.pool_getter(), interaction.guild.id, member.id)
        )

    @permissions.command(name="role-create", description="Create a server-specific Slickey role")
    async def role_create(self, interaction: discord.Interaction, name: str, description: str = "", rank: int = 0):
        if not await self._manager(interaction, "policy.role.create", "guild"):
            return
        if not await self._can_manage_rank(interaction, rank):
            return
        name = name.strip()
        if not name or len(name) > 80:
            await interaction.response.send_message("Role names must be 1–80 characters.", ephemeral=True)
            return
        try:
            role_id = await self.pool_getter().fetchval(
                """INSERT INTO bot_permission_roles (guild_id, name, description, rank, created_by)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                interaction.guild.id, name, description[:500], rank, interaction.user.id,
            )
        except Exception as exc:
            await interaction.response.send_message(f"Could not create that role: {exc}", ephemeral=True)
            return
        await self._audit(interaction, "role.create", {"role_id": role_id, "name": name})
        await interaction.response.send_message(f"Created `{name}` (role ID: `{role_id}`).", ephemeral=True)

    @permissions.command(name="role-list", description="List this server's custom Slickey roles")
    async def role_list(self, interaction: discord.Interaction):
        if not await self._manager(interaction, "policy.role.read", "guild"):
            return
        rows = await self.pool_getter().fetch(
            """SELECT r.id, r.name, r.rank, COUNT(m.user_id) AS members
               FROM bot_permission_roles r
               LEFT JOIN bot_role_memberships m ON m.role_id = r.id
               WHERE r.guild_id = $1
               GROUP BY r.id, r.name, r.rank ORDER BY r.rank DESC, r.name LIMIT 50""", interaction.guild.id
        )
        if not rows:
            await interaction.response.send_message("No custom Slickey roles yet.", ephemeral=True)
            return
        lines = [f"`{row['id']}` — **{row['name']}** (rank {row['rank']}, {row['members']} members)" for row in rows]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @permissions.command(name="role-delete", description="Delete a custom Slickey role and its role rules")
    async def role_delete(self, interaction: discord.Interaction, role_id: int):
        if not await self._manager(interaction, "policy.role.delete", "guild"):
            return
        target_rank = await self.pool_getter().fetchval("SELECT rank FROM bot_permission_roles WHERE id = $1 AND guild_id = $2", role_id, interaction.guild.id)
        if target_rank is None or not await self._can_manage_rank(interaction, target_rank):
            return
        async with self.pool_getter().acquire() as conn:
            async with conn.transaction():
                exists = await conn.fetchval("SELECT 1 FROM bot_permission_roles WHERE id = $1 AND guild_id = $2", role_id, interaction.guild.id)
                if not exists:
                    await interaction.response.send_message("That custom role does not exist in this server.", ephemeral=True)
                    return
                await conn.execute("DELETE FROM bot_permission_rules WHERE guild_id = $1 AND subject_type = 'role' AND subject_id = $2", interaction.guild.id, role_id)
                await conn.execute("DELETE FROM bot_permission_roles WHERE id = $1 AND guild_id = $2", role_id, interaction.guild.id)
        await self._audit(interaction, "role.delete", {"role_id": role_id})
        await interaction.response.send_message(f"Deleted role `{role_id}` and its rules.", ephemeral=True)

    @permissions.command(name="role-assign", description="Assign a custom Slickey role to a member")
    async def role_assign(self, interaction: discord.Interaction, member: discord.Member, role_id: int):
        if not await self._manager(interaction, "policy.role.assign", "guild"):
            return
        target_rank = await self.pool_getter().fetchval(
            "SELECT rank FROM bot_permission_roles WHERE id = $1 AND guild_id = $2", role_id, interaction.guild.id
        )
        if target_rank is None:
            await interaction.response.send_message("That custom role does not exist in this server.", ephemeral=True)
            return
        if not await self._can_manage_rank(interaction, target_rank):
            return
        if not await self._can_manage_member(interaction, member):
            return
        await self.pool_getter().execute(
            """INSERT INTO bot_role_memberships (guild_id, role_id, user_id, assigned_by, source)
               VALUES ($1, $2, $3, $4, 'manual') ON CONFLICT DO NOTHING""",
            interaction.guild.id, role_id, member.id, interaction.user.id,
        )
        await self._audit(interaction, "role.assign", {"role_id": role_id, "user_id": member.id})
        await interaction.response.send_message(f"Assigned role `{role_id}` to {member.mention}.", ephemeral=True)

    @permissions.command(name="role-remove", description="Remove a custom Slickey role from a member")
    async def role_remove(self, interaction: discord.Interaction, member: discord.Member, role_id: int):
        if not await self._manager(interaction, "policy.role.assign", "guild"):
            return
        target_rank = await self.pool_getter().fetchval("SELECT rank FROM bot_permission_roles WHERE id = $1 AND guild_id = $2", role_id, interaction.guild.id)
        if target_rank is None or not await self._can_manage_rank(interaction, target_rank):
            return
        if not await self._can_manage_member(interaction, member):
            return
        await self.pool_getter().execute(
            "DELETE FROM bot_role_memberships WHERE guild_id = $1 AND role_id = $2 AND user_id = $3",
            interaction.guild.id, role_id, member.id,
        )
        await self._audit(interaction, "role.remove", {"role_id": role_id, "user_id": member.id})
        await interaction.response.send_message(f"Removed role `{role_id}` from {member.mention}.", ephemeral=True)

    @permissions.command(name="rule-add", description="Add an allow or deny rule")
    @app_commands.choices(
        subject_type=[app_commands.Choice(name="Everyone (Member)", value="member"), app_commands.Choice(name="Custom role", value="role"), app_commands.Choice(name="Specific user", value="user")],
        effect=[app_commands.Choice(name="Allow", value="allow"), app_commands.Choice(name="Deny", value="deny")],
        scope_type=[app_commands.Choice(name="Entire server", value="guild"), app_commands.Choice(name="Discord category", value="category"), app_commands.Choice(name="Discord channel", value="channel")],
    )
    async def rule_add(self, interaction: discord.Interaction, subject_type: app_commands.Choice[str], permission: str,
                       effect: app_commands.Choice[str], scope_type: app_commands.Choice[str], subject_id: Optional[str] = None,
                       scope_id: Optional[str] = None, confirm_broad_deny: bool = False):
        permission = permission.lower().strip()
        permission = canonical_policy_key(permission)
        if permission.startswith("command.") and permission != "command.*":
            permission = f"command.{canonical_command_name(permission.removeprefix('command.'))}"
        if not permission or len(permission) > 150 or any(char.isspace() for char in permission):
            await interaction.response.send_message("Permission must be a short key such as `command.ban`, `category.moderation`, or `command.*`.", ephemeral=True)
            return
        try:
            parsed_subject = None if subject_type.value == "member" else int(subject_id or "")
            parsed_scope = None if scope_type.value == "guild" else int(scope_id or "")
        except ValueError:
            await interaction.response.send_message("A role/user ID or category/channel ID is missing or invalid.", ephemeral=True)
            return
        management_action = "policy.rule.create_deny" if effect.value == "deny" else "policy.rule.create"
        if not await self._manager(interaction, management_action):
            return
        if is_broad_deny(permission, scope_type.value, effect.value) and not confirm_broad_deny:
            await interaction.response.send_message("This broad deny can lock down a server. Run it again with `confirm_broad_deny: True` if that is intentional.", ephemeral=True)
            return
        if not await permission_key_is_registered(self.pool_getter(), permission):
            await interaction.response.send_message("That permission is not in the command catalogue. Sync the bot first or choose a listed command/category.", ephemeral=True)
            return
        if not await actor_can_delegate_permission(
            self.pool_getter(), guild_id=interaction.guild.id, user_id=interaction.user.id,
            guild_owner_id=interaction.guild.owner_id, permission_key=permission,
            scope_type=scope_type.value, scope_id=parsed_scope, effect=effect.value,
        ):
            await interaction.response.send_message(
                "You can only create rules within your own permission and scope coverage.", ephemeral=True
            )
            return
        if subject_type.value == "role":
            target_rank = await self.pool_getter().fetchval("SELECT rank FROM bot_permission_roles WHERE id = $1 AND guild_id = $2", parsed_subject, interaction.guild.id)
            if target_rank is None or not await self._can_manage_rank(interaction, target_rank):
                return
        if subject_type.value == "user" and interaction.guild.get_member(parsed_subject) is None:
            await interaction.response.send_message("That user is not a member of this server.", ephemeral=True)
            return
        if subject_type.value == "user" and not await self._can_manage_member(
            interaction, interaction.guild.get_member(parsed_subject)
        ):
            return
        if scope_type.value != "guild":
            scope = interaction.guild.get_channel(parsed_scope)
            valid_scope = scope is not None and ((scope_type.value == "category" and isinstance(scope, discord.CategoryChannel)) or (scope_type.value == "channel" and not isinstance(scope, discord.CategoryChannel)))
            if not valid_scope:
                await interaction.response.send_message("The selected scope does not exist in this server or has the wrong type.", ephemeral=True)
                return
        rule_id = await self.pool_getter().fetchval(
            """INSERT INTO bot_permission_rules
               (guild_id, subject_type, subject_id, permission_key, scope_type, scope_id, effect, created_by)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id""",
            interaction.guild.id, subject_type.value, parsed_subject, permission, scope_type.value, parsed_scope, effect.value, interaction.user.id,
        )
        await self._audit(interaction, "rule.add", {"rule_id": rule_id, "permission": permission, "effect": effect.value})
        await interaction.response.send_message(f"Created {effect.value} rule `{rule_id}` for `{permission}`.", ephemeral=True)

    @permissions.command(name="role-preset", description="Create an editable Slickey role from a safe preset")
    @app_commands.choices(preset=[app_commands.Choice(name=value["name"], value=key) for key, value in ROLE_PRESETS.items()])
    async def role_preset(self, interaction: discord.Interaction, preset: app_commands.Choice[str]):
        if not await self._manager(interaction, "policy.role.create", "guild"):
            return
        preset_data = ROLE_PRESETS[preset.value]
        if not await self._can_manage_rank(interaction, preset_data["rank"]):
            return
        if not await actor_can_delegate_preset(
            self.pool_getter(), guild_id=interaction.guild.id, user_id=interaction.user.id,
            guild_owner_id=interaction.guild.owner_id, preset_key=preset.value,
        ):
            await interaction.response.send_message("You can only create a preset whose permissions you already hold.", ephemeral=True)
            return
        try:
            role_id = await create_preset(self.pool_getter(), guild_id=interaction.guild.id, preset_key=preset.value, actor_id=interaction.user.id)
        except Exception as exc:
            await interaction.response.send_message(f"Could not create preset: {exc}", ephemeral=True)
            return
        await self._audit(interaction, "role.preset", {"preset": preset.value, "role_id": role_id})
        await interaction.response.send_message(f"Created the **{preset_data['name']}** preset (role ID: `{role_id}`).", ephemeral=True)

    @permissions.command(name="rule-remove", description="Remove an allow or deny rule")
    async def rule_remove(self, interaction: discord.Interaction, rule_id: int):
        rule = await self.pool_getter().fetchrow(
            "SELECT subject_type, subject_id, scope_type, scope_id FROM bot_permission_rules WHERE guild_id = $1 AND id = $2",
            interaction.guild.id, rule_id,
        )
        if not rule:
            await interaction.response.send_message("That rule was not found.", ephemeral=True)
            return
        if not await self._manager(interaction, "policy.rule.delete", rule["scope_type"], rule["scope_id"]):
            return
        if rule["subject_type"] == "role":
            target_rank = await self.pool_getter().fetchval(
                "SELECT rank FROM bot_permission_roles WHERE guild_id = $1 AND id = $2", interaction.guild.id, rule["subject_id"]
            )
            if target_rank is None or not await self._can_manage_rank(interaction, target_rank):
                return
        result = await self.pool_getter().execute(
            "DELETE FROM bot_permission_rules WHERE guild_id = $1 AND id = $2", interaction.guild.id, rule_id
        )
        await self._audit(interaction, "rule.remove", {"rule_id": rule_id})
        await interaction.response.send_message("Rule removed." if result.endswith("1") else "That rule was not found.", ephemeral=True)

    @permissions.command(name="rule-list", description="List this server's custom permission rules")
    async def rule_list(self, interaction: discord.Interaction):
        if not await self._manager(interaction, "policy.rule.read"):
            return
        rows = await self.pool_getter().fetch(
            """SELECT id, subject_type, subject_id, effect, permission_key, scope_type, scope_id
               FROM bot_permission_rules WHERE guild_id = $1 ORDER BY id DESC LIMIT 50""", interaction.guild.id
        )
        if not rows:
            await interaction.response.send_message("No custom rules yet.", ephemeral=True)
            return
        lines = []
        for row in rows:
            subject = "everyone" if row["subject_type"] == "member" else f"{row['subject_type']}:{row['subject_id']}"
            scope = "server" if row["scope_type"] == "guild" else f"{row['scope_type']}:{row['scope_id']}"
            lines.append(f"`{row['id']}` — **{row['effect']}** `{row['permission_key']}` for {subject} in {scope}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @permissions.command(name="test", description="Explain whether a member can use a command here")
    async def test(self, interaction: discord.Interaction, member: discord.Member, command: str):
        if not await self._manager(interaction, "policy.rule.read"):
            return
        channel = interaction.channel
        decision = await evaluate(
            self.pool_getter(), guild_id=interaction.guild.id, user_id=member.id, guild_owner_id=interaction.guild.owner_id,
            command_name=command, channel_id=getattr(channel, "id", None), category_id=getattr(channel, "category_id", None),
        )
        verdict = "Allowed" if decision.allowed else "Denied"
        await interaction.response.send_message(f"**{verdict}** for {member.mention}: {decision.reason}.", ephemeral=True)

    async def _audit(self, interaction: discord.Interaction, action: str, payload: dict,
                      *, before: dict | None = None, after: dict | None = None) -> None:
        await self.pool_getter().execute(
            """INSERT INTO bot_permission_audit_log
               (guild_id, actor_id, actor_name, action, payload, before_state, after_state)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb)""",
            interaction.guild.id, interaction.user.id, str(interaction.user), action,
            __import__("json").dumps(payload),
            __import__("json").dumps(before) if before else None,
            __import__("json").dumps(after) if after else None,
        )


def install(bot: commands.Bot, pool_getter) -> None:
    """Install universal checks once, so every command honours deny policies."""
    if getattr(bot, "_slickey_permission_system_installed", False):
        return
    bot._slickey_permission_system_installed = True

    async def prefix_check(ctx: commands.Context) -> bool:
        if ctx.guild is None or ctx.command is None:
            return True
        command_path = getattr(ctx.command, "qualified_name", ctx.command.name)
        command_name = canonical_command_name(command_path)
        decision = await evaluate(
            pool_getter(), guild_id=ctx.guild.id, user_id=ctx.author.id, guild_owner_id=ctx.guild.owner_id,
            command_name=command_name, channel_id=getattr(ctx.channel, "id", None), category_id=getattr(ctx.channel, "category_id", None),
            preflight_target_conditions=command_name in TARGET_CONDITION_COMMANDS,
            strict_unclassified=command_name in getattr(bot, "_slickey_unclassified_commands", set()),
        )
        if decision.allowed:
            return True
        await ctx.reply(f"You cannot use `{ctx.command.name}` here. {decision.reason}.")
        return False

    async def slash_check(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.command is None:
            return True
        command_path = getattr(interaction.command, "qualified_name", interaction.command.name)
        command_name = canonical_command_name(command_path)
        # The permission-management group authorizes each subcommand against
        # its own ``policy.*`` capability below.  Treating the group itself as
        # one protected command would make a narrowly delegated policy manager
        # obtain the old, all-purpose ``command.permissions`` grant first.
        if command_name == "permissions":
            return True
        decision = await evaluate(
            pool_getter(), guild_id=interaction.guild.id, user_id=interaction.user.id, guild_owner_id=interaction.guild.owner_id,
            command_name=command_name, channel_id=getattr(interaction.channel, "id", None),
            category_id=getattr(interaction.channel, "category_id", None),
            preflight_target_conditions=command_name in TARGET_CONDITION_COMMANDS,
            strict_unclassified=command_name in getattr(bot, "_slickey_unclassified_commands", set()),
        )
        if decision.allowed:
            return True
        await interaction.response.send_message(f"You cannot use `/{interaction.command.name}` here. {decision.reason}.", ephemeral=True)
        return False

    bot.add_check(prefix_check)
    # discord.py's CommandTree exposes one global interaction_check hook (it
    # does not provide Bot.add_check's multi-check API).
    bot.tree.interaction_check = slash_check
