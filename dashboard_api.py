"""Authenticated API for Slickey's React permission dashboard.

Run separately from the bot: ``uvicorn dashboard_api:app --host 127.0.0.1 --port 8000``.
Both services use the same PostgreSQL database and permission tables.
"""
 
from __future__ import annotations

import os
import secrets
import json
import hashlib
from urllib.parse import urlencode
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

import asyncpg
import httpx
from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from permission_system import (BOT_CREATOR_ID, COMMAND_REGISTRY, ROLE_PRESETS, create_preset,
                               effective_rank, evaluate, evaluate_permission, initialize_permission_system,
                               actor_can_delegate_permission, actor_can_delegate_preset,
                               actor_can_administer_policy, is_broad_deny,
                               canonical_command_name, canonical_policy_key, dashboard_view_sections,
                               permission_key_is_registered, simulate_all,
                               validate_target_conditions, conditions_supported_for_permission)

# The bot and dashboard share the project-level configuration when run locally.
# Environment variables supplied by a host still take precedence over this file.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DISCORD_API = "https://discord.com/api/v10"
CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("DASHBOARD_REDIRECT_URI", "http://localhost:5173/auth/callback")
FRONTEND_ORIGIN = os.environ.get("DASHBOARD_ORIGIN", "http://localhost:5173")
COOKIE_SECURE = os.environ.get("DASHBOARD_COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = "none" if COOKIE_SECURE else "lax"
# The main bot starts with BOT_TOKEN_2.  The dashboard must use that same bot
# identity when asking Discord about guilds, channels, owners, and members.
# DASHBOARD_BOT_TOKEN remains available for deployments that intentionally use
# a different dashboard-capable bot.
BOT_TOKEN = os.environ.get("BOT_TOKEN_2") or os.environ.get("BOT_TOKEN_1")
CSRF_COOKIE = "slickey_csrf"


def _hash_session(token: str | None) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


@dataclass
class DashboardSession:
    user: dict[str, Any]
    guilds: dict[int, dict[str, Any]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    dsn = os.environ.get("SUPABASE_DSN")
    if not dsn:
        raise RuntimeError("SUPABASE_DSN must be set for the dashboard API")
    app.state.pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10, command_timeout=20)
    await initialize_permission_system(app.state.pool)
    await app.state.pool.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_sessions (
            token TEXT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            username TEXT NOT NULL,
            guilds JSONB NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_dashboard_sessions_expiry ON dashboard_sessions (expires_at);
    """)
    yield
    await app.state.pool.close()


app = FastAPI(title="Slickey Dashboard API", lifespan=lifespan)


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    """Cookie-authenticated writes require an unguessable double-submit token."""
    exempt = {"/api/auth/login", "/api/auth/callback", "/api/health", "/api/csrf"}
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path.startswith("/api/") and request.url.path not in exempt:
        cookie = request.cookies.get(CSRF_COOKIE, "")
        header = request.headers.get("X-CSRF-Token", "")
        if not cookie or not header or not secrets.compare_digest(cookie, header):
            return JSONResponse(status_code=403, content={"detail": "Your security token expired. Refresh the dashboard and try again."})
    return await call_next(request)


app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health(request: Request):
    """Small readiness endpoint used by local startup checks and deployments."""
    await request.app.state.pool.fetchval("SELECT 1")
    return {"ok": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    rank: int = Field(default=0, ge=-100_000, le=100_000)


class RoleAssignment(BaseModel):
    user_id: int


class RoleUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    rank: int = Field(default=0, ge=-100_000, le=100_000)


class RuleCreate(BaseModel):
    subject_type: Literal["member", "role", "user"]
    subject_id: int | None = None
    permission_key: str = Field(min_length=1, max_length=150)
    scope_type: Literal["guild", "category", "channel"] = "guild"
    scope_id: int | None = None
    effect: Literal["allow", "deny"]
    conditions: dict[str, Any] = Field(default_factory=dict)
    confirm_broad_deny: bool = False


class PresetCreate(BaseModel):
    preset: Literal["administrator", "moderator", "trial_moderator", "event_manager", "economy_manager"]


class AutoAssignCreate(BaseModel):
    role_id: int


class RoleSyncCreate(BaseModel):
    discord_role_id: int
    slickey_role_id: int
    on_remove: Literal["keep", "remove"] = "keep"


class ExplainRequest(BaseModel):
    user_id: int
    command_name: str
    channel_id: int | None = None
    category_id: int | None = None


class SimulateRequest(BaseModel):
    user_id: int
    channel_id: int | None = None
    category_id: int | None = None


def _canonical_permission_key(permission_key: str) -> str:
    key = permission_key.lower().strip()
    key = canonical_policy_key(key)
    if key.startswith("command.") and key != "command.*":
        return f"command.{canonical_command_name(key.removeprefix('command.'))}"
    return key


def _require_configuration() -> None:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(500, "Discord OAuth is not configured. Set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET.")


async def _session(request: Request, slickey_session: str | None) -> DashboardSession:
    await request.app.state.pool.execute("DELETE FROM dashboard_sessions WHERE expires_at <= NOW()")
    row = await request.app.state.pool.fetchrow(
        "SELECT user_id, username, guilds FROM dashboard_sessions WHERE token = $1 AND expires_at > NOW()", _hash_session(slickey_session)
    )
    if not row:
        raise HTTPException(401, "Sign in with Discord first.")
    guilds = row["guilds"] if isinstance(row["guilds"], dict) else json.loads(row["guilds"])
    return DashboardSession(user={"id": str(row["user_id"]), "username": row["username"]}, guilds={int(key): value for key, value in guilds.items()})


async def _can_open_guild(request: Request, session: DashboardSession, guild_id: int) -> dict[str, Any]:
    guild = session.guilds.get(guild_id)
    if not guild:
        raise HTTPException(403, "You are not a member of this Discord server.")
    user_id = int(session.user["id"])
    # This call is also the authoritative check that the configured dashboard
    # bot is currently in the server.  Even the Bot Creator only sees active
    # bot guilds in the dashboard.
    owner_id = await _live_guild_owner_id(request, guild_id)
    if user_id == BOT_CREATOR_ID:
        return guild
    # OAuth's guild-owner bit is a login-time snapshot.  Ownership can change,
    # so it must never grant dashboard access by itself.
    if owner_id == user_id:
        return guild
    await _require_live_membership(guild_id, user_id)
    decision = await evaluate_permission(
        request.app.state.pool, guild_id=guild_id, user_id=user_id, guild_owner_id=None,
        permission_key="policy.dashboard.access",
    )
    if not (decision.allowed and decision.matched_rule_id is not None):
        raise HTTPException(403, "The server owner has not given you dashboard access.")
    return guild


async def _require_below_rank(request: Request, session: DashboardSession, guild_id: int, target_rank: int) -> None:
    """Owners/creator are unrestricted; delegates manage only lower ranks."""
    await _can_open_guild(request, session, guild_id)
    user_id = int(session.user["id"])
    if user_id == BOT_CREATOR_ID or await _live_guild_owner_id(request, guild_id) == user_id:
        return
    actor_rank = await effective_rank(request.app.state.pool, guild_id, user_id)
    if actor_rank <= target_rank:
        raise HTTPException(403, "You may only manage custom roles and assignments below your own role rank.")


async def _discord_bot_get(path: str) -> Any:
    if not BOT_TOKEN:
        raise HTTPException(503, "Discord bot token is not configured for member/channel pickers.")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"{DISCORD_API}{path}", headers={"Authorization": f"Bot {BOT_TOKEN}"})
        if response.status_code == 401:
            raise HTTPException(503, "The configured Discord bot token is invalid.")
        if response.status_code == 403:
            raise HTTPException(403, "The bot lacks access to this server's channels or members. Give it View Channels permission; member lookup also requires the Guild Members intent.")
        if response.status_code == 404:
            if "/members" in path:
                raise HTTPException(
                    503,
                    "Discord did not expose this server's member list to the dashboard bot.",
                )
            raise HTTPException(404, "The bot cannot find that server.")
        response.raise_for_status()
        return response.json()


async def _live_guild_owner_id(request: Request, guild_id: int) -> int:
    """Read the present Discord owner once per request, never from OAuth data."""
    cache = getattr(request.state, "guild_owner_ids", None)
    if cache is None:
        cache = request.state.guild_owner_ids = {}
    if guild_id not in cache:
        guild = await _discord_bot_get(f"/guilds/{guild_id}")
        cache[guild_id] = int(guild["owner_id"])
    return cache[guild_id]


async def _validate_rule_targets(guild_id: int, body: RuleCreate) -> None:
    """Reject foreign/mistyped Discord scope IDs before writing a policy."""
    if body.scope_type != "guild":
        channels = await _discord_bot_get(f"/guilds/{guild_id}/channels")
        channel = next((item for item in channels if int(item["id"]) == body.scope_id), None)
        expected_type = 4 if body.scope_type == "category" else 0
        if not channel or channel["type"] != expected_type:
            raise HTTPException(422, "The selected channel/category does not belong to this server or has the wrong type.")
    if body.subject_type == "user":
        await _validate_member(guild_id, body.subject_id)


async def _validate_rule_conditions(pool, guild_id: int, permission_key: str, conditions: dict[str, Any]) -> dict[str, Any]:
    """Validate only target constraints that active command handlers enforce."""
    try:
        normalized = validate_target_conditions(conditions)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if normalized and not conditions_supported_for_permission(permission_key):
        raise HTTPException(422, "Target conditions are currently supported only for ban, mute, unmute, setnick, role, and roleroulette.")
    target = normalized.get("target", {})
    role_ids = target.get("custom_role_ids", []) + target.get("exclude_custom_role_ids", [])
    if role_ids:
        existing = await pool.fetch(
            "SELECT id FROM bot_permission_roles WHERE guild_id=$1 AND id = ANY($2::bigint[])", guild_id, role_ids
        )
        if {row["id"] for row in existing} != set(role_ids):
            raise HTTPException(422, "A target custom role does not belong to this server.")
    return normalized


async def _validate_member(guild_id: int, user_id: int) -> None:
    try:
        await _discord_bot_get(f"/guilds/{guild_id}/members/{user_id}")
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(422, "The selected user is not a current server member.") from exc
        raise


async def _require_live_membership(guild_id: int, user_id: int) -> None:
    """Session guild lists are stale after a member leaves; Discord is authoritative."""
    try:
        await _discord_bot_get(f"/guilds/{guild_id}/members/{user_id}")
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(403, "You are no longer a member of this Discord server. Sign in again after rejoining.") from exc
        raise


async def _rule_rank_guard(request: Request, session: DashboardSession, guild_id: int, subject_type: str, subject_id: int | None) -> None:
    if subject_type != "role":
        return
    rank = await request.app.state.pool.fetchval(
        "SELECT rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, subject_id
    )
    if rank is None:
        raise HTTPException(404, "The selected custom role does not belong to this server.")
    await _require_below_rank(request, session, guild_id, rank)


async def _member_rank_guard(request: Request, session: DashboardSession, guild_id: int, user_id: int) -> None:
    """Delegates may not alter a peer or superior through a direct rule/assignment."""
    target_rank = await effective_rank(request.app.state.pool, guild_id, user_id)
    await _require_below_rank(request, session, guild_id, target_rank)


async def _require_manager(
    request: Request, session: DashboardSession, guild_id: int, action: str,
    scope_type: str = "guild", scope_id: int | None = None,
) -> None:
    await _can_open_guild(request, session, guild_id)
    user_id = int(session.user["id"])
    allowed = await actor_can_administer_policy(
        request.app.state.pool, guild_id=guild_id, user_id=user_id,
        guild_owner_id=await _live_guild_owner_id(request, guild_id), action=action,
        scope_type=scope_type, scope_id=scope_id,
    )
    if not allowed:
        raise HTTPException(403, f"You need the custom {action} permission for this scope.")


async def _audit(
    request: Request, guild_id: int, actor_id: int, action: str,
    payload: dict[str, Any], *, actor_name: str = "",
    before: dict[str, Any] | None = None, after: dict[str, Any] | None = None,
) -> None:
    await request.app.state.pool.execute(
        """INSERT INTO bot_permission_audit_log
           (guild_id, actor_id, actor_name, action, payload, before_state, after_state)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb)""",
        guild_id, actor_id, actor_name, action,
        __import__("json").dumps(payload),
        __import__("json").dumps(before) if before else None,
        __import__("json").dumps(after) if after else None,
    )


def _clean_role_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise HTTPException(422, "Role name cannot be blank.")
    return name


@app.get("/api/auth/login")
async def login(response: Response):
    _require_configuration()
    state = secrets.token_urlsafe(32)
    response.set_cookie("slickey_oauth_state", state, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, max_age=600, path="/api/auth")
    url = "https://discord.com/oauth2/authorize?" + urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "response_type": "code", "scope": "identify guilds", "state": state,
    })
    return {"url": url}


@app.get("/api/auth/callback")
async def callback(request: Request, response: Response, code: str, state: str, slickey_oauth_state: str | None = Cookie(default=None)):
    _require_configuration()
    if not secrets.compare_digest(state, slickey_oauth_state or ""):
        print(f"OAuth state mismatch!")
        print(f"Received state: {state}")
        print(f"Cookie state:   {slickey_oauth_state}")
        raise HTTPException(status_code=400, detail="OAuth state mismatch")
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(f"{DISCORD_API}/oauth2/token", data={
            "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "authorization_code",
            "code": code, "redirect_uri": REDIRECT_URI,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        token_response.raise_for_status()
        token = token_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        user_response, guild_response = await __import__("asyncio").gather(
            client.get(f"{DISCORD_API}/users/@me", headers=headers), client.get(f"{DISCORD_API}/users/@me/guilds", headers=headers)
        )
        user_response.raise_for_status(); guild_response.raise_for_status()
    session_id = secrets.token_urlsafe(48)
    user = user_response.json()
    guilds = {str(g["id"]): g for g in guild_response.json()}
    await request.app.state.pool.execute(
        """INSERT INTO dashboard_sessions (token, user_id, username, guilds, expires_at)
           VALUES ($1, $2, $3, $4::jsonb, NOW() + INTERVAL '8 hours')""",
        _hash_session(session_id), int(user["id"]), user["username"], json.dumps(guilds),
    )
    
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie("slickey_session", session_id, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, max_age=8 * 3600, path="/")
    response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, max_age=8 * 3600, path="/")
    response.delete_cookie("slickey_oauth_state", path="/api/auth")
    return {"ok": True, "redirect": FRONTEND_ORIGIN, "csrf_token": csrf_token}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response, slickey_session: str | None = Cookie(default=None)):
    await request.app.state.pool.execute("DELETE FROM dashboard_sessions WHERE token = $1", _hash_session(slickey_session))
    response.delete_cookie("slickey_session", path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@app.post("/api/auth/logout-all")
async def logout_all(request: Request, response: Response, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session)
    await request.app.state.pool.execute("DELETE FROM dashboard_sessions WHERE user_id = $1", int(session.user["id"]))
    response.delete_cookie("slickey_session", path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@app.post("/api/auth/refresh")
async def refresh_session(request: Request, response: Response, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session)
    new_token = secrets.token_urlsafe(48)
    await request.app.state.pool.execute(
        "UPDATE dashboard_sessions SET token=$1, expires_at=NOW() + INTERVAL '8 hours' WHERE token=$2",
        _hash_session(new_token), _hash_session(slickey_session),
    )
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie("slickey_session", new_token, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, max_age=8 * 3600, path="/")
    response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, max_age=8 * 3600, path="/")
    return {"ok": True, "username": session.user["username"], "csrf_token": csrf_token}

@app.get("/api/csrf")
async def get_csrf_token(request: Request, slickey_session: str | None = Cookie(default=None), response: Response = None):
    await _session(request, slickey_session)  # just validates they're logged in
    token = secrets.token_urlsafe(32)
    response.set_cookie(CSRF_COOKIE, token, httponly=False, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, max_age=8 * 3600, path="/")
    return {"csrf_token": token}

@app.get("/api/me")
async def me(request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session)
    return {"id": session.user["id"], "username": session.user["username"]}


@app.get("/api/guilds")
async def guilds(request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session)
    visible = []
    for guild_id, guild in session.guilds.items():
        try:
            await _can_open_guild(request, session, guild_id)
            visible.append({"id": str(guild_id), "name": guild["name"], "icon": guild.get("icon"), "owner": guild["owner"]})
        except HTTPException:
            pass
    return visible


@app.get("/api/guilds/{guild_id}/roles")
async def roles(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.role.read")
    rows = await request.app.state.pool.fetch(
        """SELECT r.id, r.name, r.description, r.rank, COUNT(m.user_id) AS member_count
           FROM bot_permission_roles r LEFT JOIN bot_role_memberships m ON m.role_id = r.id
           WHERE r.guild_id = $1 GROUP BY r.id ORDER BY r.rank DESC, r.name""", guild_id)
    return [dict(row) for row in rows]


@app.post("/api/guilds/{guild_id}/roles")
async def create_role(guild_id: int, body: RoleCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.role.create")
    await _require_below_rank(request, session, guild_id, body.rank)
    try:
        role_id = await request.app.state.pool.fetchval(
            "INSERT INTO bot_permission_roles (guild_id,name,description,rank,created_by) VALUES ($1,$2,$3,$4,$5) RETURNING id",
            guild_id, _clean_role_name(body.name), body.description, body.rank, int(session.user["id"]))
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(409, "A custom role with that name already exists in this server.") from exc
    after_role = {"id": role_id, "name": _clean_role_name(body.name), "description": body.description, "rank": body.rank}
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.create",
                 {"role_id": role_id}, actor_name=session.user["username"], after=after_role)
    return {"id": role_id}


@app.delete("/api/guilds/{guild_id}/roles/{role_id}")
async def delete_role(guild_id: int, role_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.role.delete")
    before_role = dict(await request.app.state.pool.fetchrow("SELECT id,name,description,rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id) or {})
    if not before_role: raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, before_role.get("rank", 0))
    async with request.app.state.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM bot_permission_rules WHERE guild_id=$1 AND subject_type='role' AND subject_id=$2", guild_id, role_id)
            result = await conn.execute("DELETE FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if result.endswith("0"): raise HTTPException(404, "Role not found")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.delete",
                 {"role_id": role_id}, actor_name=session.user["username"], before=before_role)
    return {"ok": True}


@app.post("/api/guilds/{guild_id}/roles/{role_id}/members")
async def assign_role(guild_id: int, role_id: int, body: RoleAssignment, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.role.assign")
    rank = await request.app.state.pool.fetchval("SELECT rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if rank is None: raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, rank)
    await _validate_member(guild_id, body.user_id)
    await _member_rank_guard(request, session, guild_id, body.user_id)
    await request.app.state.pool.execute("INSERT INTO bot_role_memberships (guild_id,role_id,user_id,assigned_by,source) VALUES ($1,$2,$3,$4,'manual') ON CONFLICT DO NOTHING", guild_id, role_id, body.user_id, int(session.user["id"]))
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.assign",
                 {"role_id": role_id, "user_id": body.user_id},
                 actor_name=session.user["username"],
                 after={"role_id": role_id, "user_id": body.user_id})
    return {"ok": True}


@app.get("/api/guilds/{guild_id}/roles/{role_id}")
async def role_detail(guild_id: int, role_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.role.read")
    role = await request.app.state.pool.fetchrow("SELECT id,name,description,rank,created_by,created_at FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if not role: raise HTTPException(404, "Role not found")
    members = await request.app.state.pool.fetch("SELECT user_id,assigned_by,assigned_at FROM bot_role_memberships WHERE guild_id=$1 AND role_id=$2 ORDER BY assigned_at DESC", guild_id, role_id)
    rules = await request.app.state.pool.fetch("SELECT id,permission_key,scope_type,scope_id,effect FROM bot_permission_rules WHERE guild_id=$1 AND subject_type='role' AND subject_id=$2 ORDER BY id DESC", guild_id, role_id)
    return {"role": dict(role), "members": [dict(row) for row in members], "rules": [dict(row) for row in rules]}


@app.put("/api/guilds/{guild_id}/roles/{role_id}")
async def update_role(guild_id: int, role_id: int, body: RoleUpdate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.role.update")
    before_role = dict(await request.app.state.pool.fetchrow("SELECT id,name,description,rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id) or {})
    if not before_role: raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, max(before_role.get("rank", 0), body.rank))
    try:
        await request.app.state.pool.execute("UPDATE bot_permission_roles SET name=$3,description=$4,rank=$5 WHERE guild_id=$1 AND id=$2", guild_id, role_id, _clean_role_name(body.name), body.description, body.rank)
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(409, "A custom role with that name already exists in this server.") from exc
    after_role = {"id": role_id, "name": _clean_role_name(body.name), "description": body.description, "rank": body.rank}
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.update",
                 {"role_id": role_id}, actor_name=session.user["username"],
                 before=before_role, after=after_role)
    return {"ok": True}


@app.delete("/api/guilds/{guild_id}/roles/{role_id}/members/{user_id}")
async def remove_role_member(guild_id: int, role_id: int, user_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.role.assign")
    rank = await request.app.state.pool.fetchval("SELECT rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if rank is None: raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, rank)
    await _member_rank_guard(request, session, guild_id, user_id)
    await request.app.state.pool.execute("DELETE FROM bot_role_memberships WHERE guild_id=$1 AND role_id=$2 AND user_id=$3", guild_id, role_id, user_id)
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.remove_member",
                 {"role_id": role_id, "user_id": user_id},
                 actor_name=session.user["username"],
                 before={"role_id": role_id, "user_id": user_id})
    return {"ok": True}


# ── Auto-assign roles ─────────────────────────────────────────────────


@app.get("/api/guilds/{guild_id}/auto-assign")
async def list_auto_assign(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Return all auto-assign rules for this guild."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.read")
    rows = await request.app.state.pool.fetch(
        """SELECT a.id, a.role_id, a.enabled, a.created_by, a.created_at,
                  r.name AS role_name, r.rank AS role_rank, r.description AS role_description
           FROM bot_role_auto_assign a
           JOIN bot_permission_roles r ON r.id = a.role_id
           WHERE a.guild_id = $1
           ORDER BY r.rank DESC, r.name""",
        guild_id,
    )
    return [dict(row) for row in rows]


@app.post("/api/guilds/{guild_id}/auto-assign")
async def create_auto_assign(guild_id: int, body: AutoAssignCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Add an auto-assign rule for a role."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.assign")
    # Verify the role exists and user has rank clearance
    role = await request.app.state.pool.fetchrow(
        "SELECT id, rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2",
        guild_id, body.role_id,
    )
    if not role:
        raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, role["rank"])
    try:
        rule_id = await request.app.state.pool.fetchval(
            "INSERT INTO bot_role_auto_assign (guild_id, role_id, created_by)"
            " VALUES ($1, $2, $3) RETURNING id",
            guild_id, body.role_id, int(session.user["id"]),
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "This role already has an auto-assign rule.")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.auto_assign.create",
                 {"rule_id": rule_id, "role_id": body.role_id},
                 actor_name=session.user["username"],
                 after={"rule_id": rule_id, "role_id": body.role_id, "enabled": True})
    return {"id": rule_id}


@app.patch("/api/guilds/{guild_id}/auto-assign/{rule_id}")
async def toggle_auto_assign(guild_id: int, rule_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Toggle an auto-assign rule on/off."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.assign")
    row = await request.app.state.pool.fetchrow(
        "SELECT id, role_id, enabled FROM bot_role_auto_assign WHERE guild_id=$1 AND id=$2",
        guild_id, rule_id,
    )
    if not row:
        raise HTTPException(404, "Auto-assign rule not found")
    new_enabled = not row["enabled"]
    await request.app.state.pool.execute(
        "UPDATE bot_role_auto_assign SET enabled=$3 WHERE guild_id=$1 AND id=$2",
        guild_id, rule_id, new_enabled,
    )
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.auto_assign.toggle",
                 {"rule_id": rule_id, "role_id": row["role_id"], "enabled": new_enabled},
                 actor_name=session.user["username"],
                 before={"enabled": not new_enabled},
                 after={"enabled": new_enabled})
    return {"ok": True, "enabled": new_enabled}


@app.delete("/api/guilds/{guild_id}/auto-assign/{rule_id}")
async def delete_auto_assign(guild_id: int, rule_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Remove an auto-assign rule."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.assign")
    row = await request.app.state.pool.fetchrow(
        "SELECT id, role_id FROM bot_role_auto_assign WHERE guild_id=$1 AND id=$2",
        guild_id, rule_id,
    )
    if not row:
        raise HTTPException(404, "Auto-assign rule not found")
    await request.app.state.pool.execute(
        "DELETE FROM bot_role_auto_assign WHERE guild_id=$1 AND id=$2",
        guild_id, rule_id,
    )
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.auto_assign.delete",
                 {"rule_id": rule_id, "role_id": row["role_id"]},
                 actor_name=session.user["username"],
                 before={"rule_id": rule_id, "role_id": row["role_id"]})
    return {"ok": True}


# ── Discord role → Slickey role sync ──────────────────────────────────


@app.get("/api/guilds/{guild_id}/role-sync")
async def list_role_sync(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Return all Discord→Slickey sync rules for this guild."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.read")
    rows = await request.app.state.pool.fetch(
        """SELECT s.id, s.discord_role_id, s.slickey_role_id, s.on_remove,
                  s.enabled, s.created_by, s.created_at,
                  r.name AS slickey_role_name, r.rank AS slickey_role_rank
           FROM bot_role_discord_sync s
           JOIN bot_permission_roles r ON r.id = s.slickey_role_id
           WHERE s.guild_id = $1
           ORDER BY r.rank DESC, r.name""",
        guild_id,
    )
    return [dict(row) for row in rows]


@app.post("/api/guilds/{guild_id}/role-sync")
async def create_role_sync(guild_id: int, body: RoleSyncCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Create a Discord→Slickey sync rule."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.assign")
    role = await request.app.state.pool.fetchrow(
        "SELECT id, rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2",
        guild_id, body.slickey_role_id,
    )
    if not role:
        raise HTTPException(404, "Slickey role not found")
    await _require_below_rank(request, session, guild_id, role["rank"])
    # Verify the Discord role actually exists in the guild via the API
    try:
        roles_data = await _discord_bot_get(f"/guilds/{guild_id}/roles")
    except HTTPException:
        raise HTTPException(404, "Guild not found or bot lacks access")
    discord_role = next((r for r in roles_data if r["id"] == body.discord_role_id), None)
    if not discord_role:
        raise HTTPException(404, "Discord role not found in this server")
    try:
        rule_id = await request.app.state.pool.fetchval(
            "INSERT INTO bot_role_discord_sync"
            " (guild_id, discord_role_id, slickey_role_id, on_remove, created_by)"
            " VALUES ($1, $2, $3, $4, $5) RETURNING id",
            guild_id, body.discord_role_id, body.slickey_role_id,
            body.on_remove, int(session.user["id"]),
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "A sync rule for this Discord role and Slickey role already exists.")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role_sync.create",
                 {"rule_id": rule_id, "discord_role_id": body.discord_role_id,
                  "slickey_role_id": body.slickey_role_id},
                 actor_name=session.user["username"],
                 after={"rule_id": rule_id, "discord_role_id": body.discord_role_id,
                        "slickey_role_id": body.slickey_role_id,
                        "on_remove": body.on_remove, "enabled": True})
    return {"id": rule_id}


@app.patch("/api/guilds/{guild_id}/role-sync/{rule_id}")
async def update_role_sync(guild_id: int, rule_id: int, request: Request,
                           body: dict | None = None, slickey_session: str | None = Cookie(default=None)):
    """Toggle enabled or change on_remove policy for a sync rule."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.assign")
    row = await request.app.state.pool.fetchrow(
        "SELECT id, discord_role_id, slickey_role_id, on_remove, enabled"
        " FROM bot_role_discord_sync WHERE guild_id=$1 AND id=$2",
        guild_id, rule_id,
    )
    if not row:
        raise HTTPException(404, "Sync rule not found")
    body = body or {}
    new_enabled = body.get("enabled", row["enabled"])
    new_on_remove = body.get("on_remove", row["on_remove"])
    if new_on_remove not in ("keep", "remove"):
        raise HTTPException(422, "on_remove must be 'keep' or 'remove'")
    await request.app.state.pool.execute(
        "UPDATE bot_role_discord_sync SET enabled=$3, on_remove=$4"
        " WHERE guild_id=$1 AND id=$2",
        guild_id, rule_id, new_enabled, new_on_remove,
    )
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role_sync.update",
                 {"rule_id": rule_id, "discord_role_id": row["discord_role_id"],
                  "slickey_role_id": row["slickey_role_id"]},
                 actor_name=session.user["username"],
                 before={"enabled": row["enabled"], "on_remove": row["on_remove"]},
                 after={"enabled": new_enabled, "on_remove": new_on_remove})
    return {"ok": True, "enabled": new_enabled, "on_remove": new_on_remove}


@app.delete("/api/guilds/{guild_id}/role-sync/{rule_id}")
async def delete_role_sync(guild_id: int, rule_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Remove a sync rule."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.assign")
    row = await request.app.state.pool.fetchrow(
        "SELECT id, discord_role_id, slickey_role_id FROM bot_role_discord_sync"
        " WHERE guild_id=$1 AND id=$2",
        guild_id, rule_id,
    )
    if not row:
        raise HTTPException(404, "Sync rule not found")
    await request.app.state.pool.execute(
        "DELETE FROM bot_role_discord_sync WHERE guild_id=$1 AND id=$2",
        guild_id, rule_id,
    )
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role_sync.delete",
                 {"rule_id": rule_id, "discord_role_id": row["discord_role_id"],
                  "slickey_role_id": row["slickey_role_id"]},
                 actor_name=session.user["username"],
                 before={"rule_id": rule_id, "discord_role_id": row["discord_role_id"],
                         "slickey_role_id": row["slickey_role_id"]})
    return {"ok": True}


@app.get("/api/guilds/{guild_id}/discord-roles")
async def discord_roles(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Return the Discord roles in this guild for the sync picker."""
    session = await _session(request, slickey_session)
    await _require_manager(request, session, guild_id, "policy.role.read")
    # Fetch Discord roles via the API instead of the bot object
    roles_data = await _discord_bot_get(f"/guilds/{guild_id}/roles")
    # Exclude @everyone (id == guild_id) and managed bot roles
    return [
        {"id": r["id"], "name": r["name"], "color": str(r.get("color", 0)),
         "position": r.get("position", 0)}
        for r in sorted(roles_data, key=lambda r: -r.get("position", 0))
        if r["id"] != str(guild_id) and not r.get("managed", False)
    ]


@app.get("/api/guilds/{guild_id}/rules")
async def rules(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.rule.read")
    rows = await request.app.state.pool.fetch("SELECT id,subject_type,subject_id,permission_key,scope_type,scope_id,effect,conditions,priority,revision,updated_at FROM bot_permission_rules WHERE guild_id=$1 ORDER BY id DESC", guild_id)
    return [dict(row) for row in rows]


@app.post("/api/guilds/{guild_id}/rules")
async def create_rule(guild_id: int, body: RuleCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session)
    permission_key = _canonical_permission_key(body.permission_key)
    if (body.subject_type == "member") != (body.subject_id is None) or (body.scope_type == "guild") != (body.scope_id is None):
        raise HTTPException(422, "Subject/scope IDs do not match their selected types.")
    if is_broad_deny(permission_key, body.scope_type, body.effect) and not body.confirm_broad_deny:
        raise HTTPException(422, "This broad deny could lock down the server. Confirm it explicitly before saving.")
    if not await permission_key_is_registered(request.app.state.pool, permission_key):
        raise HTTPException(422, "Choose a command or category from the command catalogue.")
    conditions = await _validate_rule_conditions(request.app.state.pool, guild_id, permission_key, body.conditions)
    if not await actor_can_delegate_permission(
        request.app.state.pool, guild_id=guild_id, user_id=int(session.user["id"]),
        guild_owner_id=await _live_guild_owner_id(request, guild_id),
        permission_key=permission_key,
        scope_type=body.scope_type, scope_id=body.scope_id, effect=body.effect,
    ):
        raise HTTPException(403, "You can only create policies within your own permission and scope coverage.")
    await _validate_rule_targets(guild_id, body)
    await _rule_rank_guard(request, session, guild_id, body.subject_type, body.subject_id)
    if body.subject_type == "user":
        await _member_rank_guard(request, session, guild_id, body.subject_id)
    rule_id = await request.app.state.pool.fetchval("""INSERT INTO bot_permission_rules (guild_id,subject_type,subject_id,permission_key,scope_type,scope_id,effect,conditions,created_by) VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9) RETURNING id""", guild_id, body.subject_type, body.subject_id, permission_key, body.scope_type, body.scope_id, body.effect, json.dumps(conditions), int(session.user["id"]))
    after_rule = {"id": rule_id, "subject_type": body.subject_type, "subject_id": body.subject_id,
                  "permission_key": permission_key, "scope_type": body.scope_type, "scope_id": body.scope_id,
                  "effect": body.effect, "conditions": conditions}
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.rule.create",
                 {"rule_id": rule_id}, actor_name=session.user["username"], after=after_rule)
    return {"id": rule_id}


@app.get("/api/catalog")
async def catalog(request: Request):
    rows = await request.app.state.pool.fetch("SELECT command_path,permission_key,display_name,description,category,default_access,command_kind FROM bot_command_catalog ORDER BY category,display_name")
    if rows:
        return [dict(row) for row in rows]
    return [{"command_path": key, "permission_key": f"command.{key}", "display_name": key.replace("_", " ").title(), "description": "", "category": value[0], "default_access": value[1], "command_kind": "command"} for key, value in sorted(COMMAND_REGISTRY.items())]


@app.get("/api/permissions")
async def permission_definitions(request: Request):
    """Expose command and policy-management capabilities to the dashboard."""
    rows = await request.app.state.pool.fetch(
        """SELECT permission_key, display_name, description, category, default_access, permission_kind
           FROM bot_permission_definitions ORDER BY permission_kind, category, display_name"""
    )
    return [dict(row) for row in rows]


@app.get("/api/presets")
async def presets():
    return [{"key": key, "name": value["name"], "description": value["description"], "rank": value["rank"]} for key, value in ROLE_PRESETS.items()]


@app.post("/api/guilds/{guild_id}/roles/preset")
async def add_preset(guild_id: int, body: PresetCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.role.create")
    await _require_below_rank(request, session, guild_id, ROLE_PRESETS[body.preset]["rank"])
    if not await actor_can_delegate_preset(request.app.state.pool, guild_id=guild_id, user_id=int(session.user["id"]),
                                           guild_owner_id=await _live_guild_owner_id(request, guild_id), preset_key=body.preset):
        raise HTTPException(403, "You can only create a preset whose permissions you already hold.")
    try:
        role_id = await create_preset(request.app.state.pool, guild_id=guild_id, preset_key=body.preset, actor_id=int(session.user["id"]))
    except Exception as exc:
        raise HTTPException(409, f"Could not add preset: {exc}")
    preset_data = ROLE_PRESETS[body.preset]
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.preset",
                 {"preset": body.preset, "role_id": role_id},
                 actor_name=session.user["username"],
                 after={"role_id": role_id, "name": preset_data["name"],
                       "rank": preset_data["rank"], "permissions": preset_data["permissions"]})
    return {"id": role_id}


@app.get("/api/guilds/{guild_id}/channels")
async def channels(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    data = await _discord_bot_get(f"/guilds/{guild_id}/channels")
    return [{"id": item["id"], "name": item["name"], "type": item["type"], "parent_id": item.get("parent_id")} for item in data if item["type"] in (0, 4)]


@app.get("/api/guilds/{guild_id}/sections")
async def sections(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Return the dashboard sections this user can see in this server.

    The set is derived from existing ``policy.*`` capabilities so the engine
    remains the single source of truth.  The frontend uses it to filter the
    navigation; the per-endpoint checks stay in place as the authoritative
    defence.
    """
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    user_id = int(session.user["id"])
    guild_owner_id = await _live_guild_owner_id(request, guild_id)
    visible = await dashboard_view_sections(
        request.app.state.pool, guild_id=guild_id, user_id=user_id, guild_owner_id=guild_owner_id,
    )
    return {"sections": sorted(visible)}


@app.get("/api/guilds/{guild_id}/members")
async def members(guild_id: int, request: Request, query: str = "", limit: int = 100,
                  slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    query = query.lower().strip()
    limit = min(max(limit, 1), 100)
    # Discord's list endpoint is capped and ordered by ID.  Use its dedicated
    # search endpoint once the dashboard user types, so members beyond the
    # first page remain selectable in large servers.  Numeric IDs are resolved
    # directly, which is useful for an exact known member.
    if query.isdigit():
        data = [await _discord_bot_get(f"/guilds/{guild_id}/members/{query}")]
    elif query:
        data = await _discord_bot_get(f"/guilds/{guild_id}/members/search?{urlencode({'query': query, 'limit': limit})}")
    else:
        data = await _discord_bot_get(f"/guilds/{guild_id}/members?limit={limit}")
    return [{"id": item["user"]["id"], "name": item.get("nick") or item["user"]["username"]} for item in data]


@app.post("/api/guilds/{guild_id}/explain")
async def explain(guild_id: int, body: ExplainRequest, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.rule.read")
    decision = await evaluate(request.app.state.pool, guild_id=guild_id, user_id=body.user_id,
                              guild_owner_id=await _live_guild_owner_id(request, guild_id),
                              command_name=body.command_name, channel_id=body.channel_id, category_id=body.category_id)
    return {"allowed": decision.allowed, "reason": decision.reason, "matched_rule_id": decision.matched_rule_id,
            "trace": list(decision.trace)}


@app.post("/api/guilds/{guild_id}/simulate")
async def simulate(guild_id: int, body: SimulateRequest, request: Request, slickey_session: str | None = Cookie(default=None)):
    """Evaluate every registered command for a user in a given context.

    Returns the full permission matrix: which commands are allowed, denied,
    or at default, together with the decision trace for each.
    """
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.rule.read")
    result = await simulate_all(
        request.app.state.pool, guild_id=guild_id, user_id=body.user_id,
        guild_owner_id=await _live_guild_owner_id(request, guild_id),
        channel_id=body.channel_id, category_id=body.category_id,
    )
    return result


@app.delete("/api/guilds/{guild_id}/rules/{rule_id}")
async def delete_rule(guild_id: int, rule_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session)
    existing = await request.app.state.pool.fetchrow("SELECT subject_type,subject_id,scope_type,scope_id FROM bot_permission_rules WHERE guild_id=$1 AND id=$2", guild_id, rule_id)
    if not existing: raise HTTPException(404, "Rule not found")
    await _require_manager(request, session, guild_id, "policy.rule.delete", existing["scope_type"], existing["scope_id"])
    await _rule_rank_guard(request, session, guild_id, existing["subject_type"], existing["subject_id"])
    if existing["subject_type"] == "user":
        await _member_rank_guard(request, session, guild_id, existing["subject_id"])
    before_rule = dict(existing)
    before_rule["conditions"] = json.loads(before_rule.get("conditions") or "{}") if hasattr(before_rule.get("conditions"), "read") else (before_rule.get("conditions") or {})
    result = await request.app.state.pool.execute("DELETE FROM bot_permission_rules WHERE guild_id=$1 AND id=$2", guild_id, rule_id)
    if result.endswith("0"): raise HTTPException(404, "Rule not found")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.rule.delete",
                 {"rule_id": rule_id}, actor_name=session.user["username"], before=before_rule)
    return {"ok": True}


@app.put("/api/guilds/{guild_id}/rules/{rule_id}")
async def update_rule(guild_id: int, rule_id: int, body: RuleCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session)
    permission_key = _canonical_permission_key(body.permission_key)
    if (body.subject_type == "member") != (body.subject_id is None) or (body.scope_type == "guild") != (body.scope_id is None):
        raise HTTPException(422, "Subject/scope IDs do not match their selected types.")
    if is_broad_deny(permission_key, body.scope_type, body.effect) and not body.confirm_broad_deny:
        raise HTTPException(422, "Confirm this broad deny before saving.")
    if not await permission_key_is_registered(request.app.state.pool, permission_key):
        raise HTTPException(422, "Choose a command or category from the command catalogue.")
    conditions = await _validate_rule_conditions(request.app.state.pool, guild_id, permission_key, body.conditions)
    if not await actor_can_delegate_permission(
        request.app.state.pool, guild_id=guild_id, user_id=int(session.user["id"]),
        guild_owner_id=await _live_guild_owner_id(request, guild_id),
        permission_key=permission_key,
        scope_type=body.scope_type, scope_id=body.scope_id, effect=body.effect,
    ):
        raise HTTPException(403, "You can only create policies within your own permission and scope coverage.")
    await _validate_rule_targets(guild_id, body)
    before_row = await request.app.state.pool.fetchrow("SELECT * FROM bot_permission_rules WHERE guild_id=$1 AND id=$2", guild_id, rule_id)
    if not before_row: raise HTTPException(404, "Rule not found")
    before_rule = {"subject_type": before_row["subject_type"], "subject_id": before_row["subject_id"],
                   "permission_key": before_row["permission_key"], "scope_type": before_row["scope_type"],
                   "scope_id": before_row["scope_id"], "effect": before_row["effect"],
                   "conditions": before_row.get("conditions") or {}}
    await _require_manager(request, session, guild_id, "policy.rule.update", before_row["scope_type"], before_row["scope_id"])
    await _rule_rank_guard(request, session, guild_id, before_row["subject_type"], before_row["subject_id"])
    await _rule_rank_guard(request, session, guild_id, body.subject_type, body.subject_id)
    if before_row["subject_type"] == "user":
        await _member_rank_guard(request, session, guild_id, before_row["subject_id"])
    if body.subject_type == "user":
        await _member_rank_guard(request, session, guild_id, body.subject_id)
    after_rule = {"subject_type": body.subject_type, "subject_id": body.subject_id,
                  "permission_key": permission_key, "scope_type": body.scope_type,
                  "scope_id": body.scope_id, "effect": body.effect,
                  "conditions": conditions}
    result = await request.app.state.pool.execute("""UPDATE bot_permission_rules SET subject_type=$3,subject_id=$4,permission_key=$5,scope_type=$6,scope_id=$7,effect=$8,conditions=$9::jsonb,revision=revision+1,updated_at=NOW() WHERE guild_id=$1 AND id=$2""", guild_id, rule_id, body.subject_type, body.subject_id, permission_key, body.scope_type, body.scope_id, body.effect, json.dumps(conditions))
    if result.endswith("0"): raise HTTPException(404, "Rule not found")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.rule.update",
                 {"rule_id": rule_id}, actor_name=session.user["username"],
                 before=before_rule, after=after_rule)
    return {"ok": True}


@app.get("/api/guilds/{guild_id}/audit")
async def audit_log(guild_id: int, request: Request, limit: int = 100, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id, "policy.audit.read")
    rows = await request.app.state.pool.fetch(
        "SELECT id,actor_id,actor_name,action,payload,before_state,after_state,created_at"
        " FROM bot_permission_audit_log WHERE guild_id=$1 ORDER BY id DESC LIMIT $2",
        guild_id, min(max(limit, 1), 200),
    )
    return [dict(row) for row in rows]
