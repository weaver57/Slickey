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

from permission_system import (BOT_CREATOR_ID, COMMAND_CATALOG, ROLE_PRESETS, create_preset,
                               effective_rank, evaluate, initialize_permission_system,
                               actor_can_delegate_permission, actor_can_delegate_preset,
                               is_broad_deny, is_superuser, permission_key_is_registered)

# The bot and dashboard share the project-level configuration when run locally.
# Environment variables supplied by a host still take precedence over this file.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DISCORD_API = "https://discord.com/api/v10"
CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("DASHBOARD_REDIRECT_URI", "http://localhost:5173/auth/callback")
FRONTEND_ORIGIN = os.environ.get("DASHBOARD_ORIGIN", "http://localhost:5173")
COOKIE_SECURE = os.environ.get("DASHBOARD_COOKIE_SECURE", "false").lower() == "true"
BOT_TOKEN = os.environ.get("BOT_TOKEN_1") or os.environ.get("BOT_TOKEN_2")
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
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    """Cookie-authenticated writes require an unguessable double-submit token."""
    exempt = {"/api/auth/login", "/api/auth/callback", "/api/health"}
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path.startswith("/api/") and request.url.path not in exempt:
        cookie = request.cookies.get(CSRF_COOKIE, "")
        header = request.headers.get("X-CSRF-Token", "")
        if not cookie or not header or not secrets.compare_digest(cookie, header):
            return JSONResponse(status_code=403, content={"detail": "Your security token expired. Refresh the dashboard and try again."})
    return await call_next(request)


@app.get("/api/health")
async def health(request: Request):
    """Small readiness endpoint used by local startup checks and deployments."""
    await request.app.state.pool.fetchval("SELECT 1")
    return {"ok": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    rank: int = 0


class RoleAssignment(BaseModel):
    user_id: int


class RoleUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    rank: int = 0


class RuleCreate(BaseModel):
    subject_type: Literal["member", "role", "user"]
    subject_id: int | None = None
    permission_key: str = Field(min_length=1, max_length=150)
    scope_type: Literal["guild", "category", "channel"] = "guild"
    scope_id: int | None = None
    effect: Literal["allow", "deny"]
    confirm_broad_deny: bool = False


class PresetCreate(BaseModel):
    preset: Literal["administrator", "moderator", "trial_moderator", "event_manager", "economy_manager"]


class ExplainRequest(BaseModel):
    user_id: int
    command_name: str
    channel_id: int | None = None
    category_id: int | None = None


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
    if user_id == BOT_CREATOR_ID or guild["owner"]:
        return guild
    decision = await evaluate(request.app.state.pool, guild_id=guild_id, user_id=user_id, guild_owner_id=None,
                              command_name="dashboard")
    if not (decision.allowed and decision.matched_rule_id is not None):
        raise HTTPException(403, "The server owner has not given you dashboard access.")
    return guild


async def _require_below_rank(request: Request, session: DashboardSession, guild_id: int, target_rank: int) -> None:
    """Owners/creator are unrestricted; delegates manage only lower ranks."""
    guild = await _can_open_guild(request, session, guild_id)
    user_id = int(session.user["id"])
    if is_superuser(user_id, user_id if guild["owner"] else None):
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
            raise HTTPException(404, "The bot cannot find that server.")
        response.raise_for_status()
        return response.json()


async def _validate_rule_targets(guild_id: int, body: RuleCreate) -> None:
    """Reject foreign/mistyped Discord scope IDs before writing a policy."""
    if body.scope_type != "guild":
        channels = await _discord_bot_get(f"/guilds/{guild_id}/channels")
        channel = next((item for item in channels if int(item["id"]) == body.scope_id), None)
        expected_type = 4 if body.scope_type == "category" else 0
        if not channel or channel["type"] != expected_type:
            raise HTTPException(422, "The selected channel/category does not belong to this server or has the wrong type.")
    if body.subject_type == "user":
        members = await _discord_bot_get(f"/guilds/{guild_id}/members?limit=1000")
        if not any(int(item["user"]["id"]) == body.subject_id for item in members):
            raise HTTPException(422, "The selected user is not a current server member.")


async def _validate_member(guild_id: int, user_id: int) -> None:
    members = await _discord_bot_get(f"/guilds/{guild_id}/members?limit=1000")
    if not any(int(item["user"]["id"]) == user_id for item in members):
        raise HTTPException(422, "The selected user is not a current server member.")


async def _rule_rank_guard(request: Request, session: DashboardSession, guild_id: int, subject_type: str, subject_id: int | None) -> None:
    if subject_type != "role":
        return
    rank = await request.app.state.pool.fetchval(
        "SELECT rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, subject_id
    )
    if rank is None:
        raise HTTPException(404, "The selected custom role does not belong to this server.")
    await _require_below_rank(request, session, guild_id, rank)


async def _require_manager(request: Request, session: DashboardSession, guild_id: int) -> None:
    guild = await _can_open_guild(request, session, guild_id)
    user_id = int(session.user["id"])
    if is_superuser(user_id, user_id if guild["owner"] else None):
        return
    decision = await evaluate(request.app.state.pool, guild_id=guild_id, user_id=user_id, guild_owner_id=None,
                              command_name="permissions")
    if not (decision.allowed and decision.matched_rule_id is not None):
        raise HTTPException(403, "You have dashboard access but not permission-management access.")


async def _audit(request: Request, guild_id: int, actor_id: int, action: str, payload: dict[str, Any]) -> None:
    await request.app.state.pool.execute(
        "INSERT INTO bot_permission_audit_log (guild_id, actor_id, action, payload) VALUES ($1, $2, $3, $4::jsonb)",
        guild_id, actor_id, action, __import__("json").dumps(payload),
    )


@app.get("/api/auth/login")
async def login(response: Response):
    _require_configuration()
    state = secrets.token_urlsafe(32)
    response.set_cookie("slickey_oauth_state", state, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=600, path="/api/auth")
    url = "https://discord.com/oauth2/authorize?" + urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "response_type": "code", "scope": "identify guilds", "state": state,
    })
    return {"url": url}


@app.get("/api/auth/callback")
async def callback(request: Request, response: Response, code: str, state: str, slickey_oauth_state: str | None = Cookie(default=None)):
    _require_configuration()
    if not secrets.compare_digest(state, slickey_oauth_state or ""):
        raise HTTPException(400, "Invalid OAuth state.")
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
    response.set_cookie("slickey_session", session_id, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=8 * 3600, path="/")
    response.set_cookie(CSRF_COOKIE, secrets.token_urlsafe(32), httponly=False, secure=COOKIE_SECURE, samesite="lax", max_age=8 * 3600, path="/")
    response.delete_cookie("slickey_oauth_state", path="/api/auth")
    return {"ok": True, "redirect": FRONTEND_ORIGIN}


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
    response.set_cookie("slickey_session", new_token, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=8 * 3600, path="/")
    response.set_cookie(CSRF_COOKIE, secrets.token_urlsafe(32), httponly=False, secure=COOKIE_SECURE, samesite="lax", max_age=8 * 3600, path="/")
    return {"ok": True, "username": session.user["username"]}


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
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    rows = await request.app.state.pool.fetch(
        """SELECT r.id, r.name, r.description, r.rank, COUNT(m.user_id) AS member_count
           FROM bot_permission_roles r LEFT JOIN bot_role_memberships m ON m.role_id = r.id
           WHERE r.guild_id = $1 GROUP BY r.id ORDER BY r.rank DESC, r.name""", guild_id)
    return [dict(row) for row in rows]


@app.post("/api/guilds/{guild_id}/roles")
async def create_role(guild_id: int, body: RoleCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    await _require_below_rank(request, session, guild_id, body.rank)
    role_id = await request.app.state.pool.fetchval(
        "INSERT INTO bot_permission_roles (guild_id,name,description,rank,created_by) VALUES ($1,$2,$3,$4,$5) RETURNING id",
        guild_id, body.name.strip(), body.description, body.rank, int(session.user["id"]))
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.create", {"role_id": role_id})
    return {"id": role_id}


@app.delete("/api/guilds/{guild_id}/roles/{role_id}")
async def delete_role(guild_id: int, role_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    rank = await request.app.state.pool.fetchval("SELECT rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if rank is None: raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, rank)
    await _validate_member(guild_id, body.user_id)
    async with request.app.state.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM bot_permission_rules WHERE guild_id=$1 AND subject_type='role' AND subject_id=$2", guild_id, role_id)
            result = await conn.execute("DELETE FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if result.endswith("0"): raise HTTPException(404, "Role not found")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.delete", {"role_id": role_id})
    return {"ok": True}


@app.post("/api/guilds/{guild_id}/roles/{role_id}/members")
async def assign_role(guild_id: int, role_id: int, body: RoleAssignment, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    rank = await request.app.state.pool.fetchval("SELECT rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if rank is None: raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, rank)
    await request.app.state.pool.execute("INSERT INTO bot_role_memberships (guild_id,role_id,user_id,assigned_by) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING", guild_id, role_id, body.user_id, int(session.user["id"]))
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.assign", {"role_id": role_id, "user_id": body.user_id})
    return {"ok": True}


@app.get("/api/guilds/{guild_id}/roles/{role_id}")
async def role_detail(guild_id: int, role_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    role = await request.app.state.pool.fetchrow("SELECT id,name,description,rank,created_by,created_at FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if not role: raise HTTPException(404, "Role not found")
    members = await request.app.state.pool.fetch("SELECT user_id,assigned_by,assigned_at FROM bot_role_memberships WHERE guild_id=$1 AND role_id=$2 ORDER BY assigned_at DESC", guild_id, role_id)
    rules = await request.app.state.pool.fetch("SELECT id,permission_key,scope_type,scope_id,effect FROM bot_permission_rules WHERE guild_id=$1 AND subject_type='role' AND subject_id=$2 ORDER BY id DESC", guild_id, role_id)
    return {"role": dict(role), "members": [dict(row) for row in members], "rules": [dict(row) for row in rules]}


@app.put("/api/guilds/{guild_id}/roles/{role_id}")
async def update_role(guild_id: int, role_id: int, body: RoleUpdate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    current = await request.app.state.pool.fetchval("SELECT rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if current is None: raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, max(current, body.rank))
    await request.app.state.pool.execute("UPDATE bot_permission_roles SET name=$3,description=$4,rank=$5 WHERE guild_id=$1 AND id=$2", guild_id, role_id, body.name.strip(), body.description, body.rank)
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.update", {"role_id": role_id})
    return {"ok": True}


@app.delete("/api/guilds/{guild_id}/roles/{role_id}/members/{user_id}")
async def remove_role_member(guild_id: int, role_id: int, user_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    rank = await request.app.state.pool.fetchval("SELECT rank FROM bot_permission_roles WHERE guild_id=$1 AND id=$2", guild_id, role_id)
    if rank is None: raise HTTPException(404, "Role not found")
    await _require_below_rank(request, session, guild_id, rank)
    await request.app.state.pool.execute("DELETE FROM bot_role_memberships WHERE guild_id=$1 AND role_id=$2 AND user_id=$3", guild_id, role_id, user_id)
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.remove_member", {"role_id": role_id, "user_id": user_id})
    return {"ok": True}


@app.get("/api/guilds/{guild_id}/rules")
async def rules(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    rows = await request.app.state.pool.fetch("SELECT id,subject_type,subject_id,permission_key,scope_type,scope_id,effect FROM bot_permission_rules WHERE guild_id=$1 ORDER BY id DESC", guild_id)
    return [dict(row) for row in rows]


@app.post("/api/guilds/{guild_id}/rules")
async def create_rule(guild_id: int, body: RuleCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    if (body.subject_type == "member") != (body.subject_id is None) or (body.scope_type == "guild") != (body.scope_id is None):
        raise HTTPException(422, "Subject/scope IDs do not match their selected types.")
    if is_broad_deny(body.permission_key, body.scope_type, body.effect) and not body.confirm_broad_deny:
        raise HTTPException(422, "This broad deny could lock down the server. Confirm it explicitly before saving.")
    if not await permission_key_is_registered(request.app.state.pool, body.permission_key):
        raise HTTPException(422, "Choose a command or category from the command catalogue.")
    if body.effect == "allow" and not await actor_can_delegate_permission(
        request.app.state.pool, guild_id=guild_id, user_id=int(session.user["id"]), guild_owner_id=None,
        permission_key=body.permission_key,
    ):
        raise HTTPException(403, "You can only grant permissions you currently hold yourself.")
    await _validate_rule_targets(guild_id, body)
    await _rule_rank_guard(request, session, guild_id, body.subject_type, body.subject_id)
    rule_id = await request.app.state.pool.fetchval("""INSERT INTO bot_permission_rules (guild_id,subject_type,subject_id,permission_key,scope_type,scope_id,effect,created_by) VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id""", guild_id, body.subject_type, body.subject_id, body.permission_key.lower().strip(), body.scope_type, body.scope_id, body.effect, int(session.user["id"]))
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.rule.create", {"rule_id": rule_id})
    return {"id": rule_id}


@app.get("/api/catalog")
async def catalog(request: Request):
    rows = await request.app.state.pool.fetch("SELECT command_path,permission_key,display_name,description,category,default_access,command_kind FROM bot_command_catalog ORDER BY category,display_name")
    if rows:
        return [dict(row) for row in rows]
    return [{"command_path": key, "permission_key": f"command.{key}", "display_name": value[0], "description": "", "category": value[1], "default_access": "public", "command_kind": "legacy"} for key, value in sorted(COMMAND_CATALOG.items())]


@app.get("/api/presets")
async def presets():
    return [{"key": key, "name": value["name"], "description": value["description"], "rank": value["rank"]} for key, value in ROLE_PRESETS.items()]


@app.post("/api/guilds/{guild_id}/roles/preset")
async def add_preset(guild_id: int, body: PresetCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    await _require_below_rank(request, session, guild_id, ROLE_PRESETS[body.preset]["rank"])
    if not await actor_can_delegate_preset(request.app.state.pool, guild_id=guild_id, user_id=int(session.user["id"]), guild_owner_id=None, preset_key=body.preset):
        raise HTTPException(403, "You can only create a preset whose permissions you already hold.")
    try:
        role_id = await create_preset(request.app.state.pool, guild_id=guild_id, preset_key=body.preset, actor_id=int(session.user["id"]))
    except Exception as exc:
        raise HTTPException(409, f"Could not add preset: {exc}")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.role.preset", {"preset": body.preset, "role_id": role_id})
    return {"id": role_id}


@app.get("/api/guilds/{guild_id}/channels")
async def channels(guild_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    data = await _discord_bot_get(f"/guilds/{guild_id}/channels")
    return [{"id": item["id"], "name": item["name"], "type": item["type"], "parent_id": item.get("parent_id")} for item in data if item["type"] in (0, 4)]


@app.get("/api/guilds/{guild_id}/members")
async def members(guild_id: int, request: Request, query: str = "", slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    data = await _discord_bot_get(f"/guilds/{guild_id}/members?limit=1000")
    query = query.lower().strip()
    return [{"id": item["user"]["id"], "name": item.get("nick") or item["user"]["username"]} for item in data if not query or query in (item.get("nick") or item["user"]["username"]).lower()]


@app.post("/api/guilds/{guild_id}/explain")
async def explain(guild_id: int, body: ExplainRequest, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    decision = await evaluate(request.app.state.pool, guild_id=guild_id, user_id=body.user_id, guild_owner_id=None,
                              command_name=body.command_name, channel_id=body.channel_id, category_id=body.category_id)
    return {"allowed": decision.allowed, "reason": decision.reason, "matched_rule_id": decision.matched_rule_id,
            "trace": list(decision.trace)}


@app.delete("/api/guilds/{guild_id}/rules/{rule_id}")
async def delete_rule(guild_id: int, rule_id: int, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    existing = await request.app.state.pool.fetchrow("SELECT subject_type,subject_id FROM bot_permission_rules WHERE guild_id=$1 AND id=$2", guild_id, rule_id)
    if not existing: raise HTTPException(404, "Rule not found")
    await _rule_rank_guard(request, session, guild_id, existing["subject_type"], existing["subject_id"])
    result = await request.app.state.pool.execute("DELETE FROM bot_permission_rules WHERE guild_id=$1 AND id=$2", guild_id, rule_id)
    if result.endswith("0"): raise HTTPException(404, "Rule not found")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.rule.delete", {"rule_id": rule_id})
    return {"ok": True}


@app.put("/api/guilds/{guild_id}/rules/{rule_id}")
async def update_rule(guild_id: int, rule_id: int, body: RuleCreate, request: Request, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _require_manager(request, session, guild_id)
    if (body.subject_type == "member") != (body.subject_id is None) or (body.scope_type == "guild") != (body.scope_id is None):
        raise HTTPException(422, "Subject/scope IDs do not match their selected types.")
    if is_broad_deny(body.permission_key, body.scope_type, body.effect) and not body.confirm_broad_deny:
        raise HTTPException(422, "Confirm this broad deny before saving.")
    if not await permission_key_is_registered(request.app.state.pool, body.permission_key):
        raise HTTPException(422, "Choose a command or category from the command catalogue.")
    if body.effect == "allow" and not await actor_can_delegate_permission(
        request.app.state.pool, guild_id=guild_id, user_id=int(session.user["id"]), guild_owner_id=None,
        permission_key=body.permission_key,
    ):
        raise HTTPException(403, "You can only grant permissions you currently hold yourself.")
    await _validate_rule_targets(guild_id, body)
    existing = await request.app.state.pool.fetchrow("SELECT subject_type,subject_id FROM bot_permission_rules WHERE guild_id=$1 AND id=$2", guild_id, rule_id)
    if not existing: raise HTTPException(404, "Rule not found")
    await _rule_rank_guard(request, session, guild_id, existing["subject_type"], existing["subject_id"])
    await _rule_rank_guard(request, session, guild_id, body.subject_type, body.subject_id)
    result = await request.app.state.pool.execute("""UPDATE bot_permission_rules SET subject_type=$3,subject_id=$4,permission_key=$5,scope_type=$6,scope_id=$7,effect=$8 WHERE guild_id=$1 AND id=$2""", guild_id, rule_id, body.subject_type, body.subject_id, body.permission_key.lower().strip(), body.scope_type, body.scope_id, body.effect)
    if result.endswith("0"): raise HTTPException(404, "Rule not found")
    await _audit(request, guild_id, int(session.user["id"]), "dashboard.rule.update", {"rule_id": rule_id})
    return {"ok": True}


@app.get("/api/guilds/{guild_id}/audit")
async def audit_log(guild_id: int, request: Request, limit: int = 100, slickey_session: str | None = Cookie(default=None)):
    session = await _session(request, slickey_session); await _can_open_guild(request, session, guild_id)
    rows = await request.app.state.pool.fetch("SELECT id,actor_id,action,payload,created_at FROM bot_permission_audit_log WHERE guild_id=$1 ORDER BY id DESC LIMIT $2", guild_id, min(max(limit, 1), 200))
    return [dict(row) for row in rows]
