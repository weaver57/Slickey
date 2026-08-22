# Slickey

A multi-feature Discord bot with a full web dashboard for server management. Built with discord.py, FastAPI, React, and PostgreSQL.

---

## Features

### Commands — 148 across 7 categories

| Category | Commands | Access |
|---|---|---|
| **Configuration** | `setprefix`, `selfprefix`, `setnick`, `showperm`, `setperm`, `whois`, `spawn`, `permissions` | Protected |
| **Moderation** | `ban`, `unban`, `mute`, `unmute`, `purge`, `purgereaction`, `spam`, `stop`, `role`, `setrole`, `roleroulette`, `setnick`, `modlogs`, `sljail`, `slunjail`, `slmute`, `slunmute`, `slkick`, `slwhip`, `slrole`, `slsetnick`, `massban`, `massunban`, `kick`, `setrole` | Protected |
| **Economy** | `daily`, `beg`, `give`, `tip`, `trade`, `tribute`, `wallet`, `bakebread`, `fetchwater`, `minerock`, `shinecrown`, `fanmaster`, `jackpot`, `escape`, `wish`, `shop`, `buycmd`, `chkprice`, `slinfo` | Public |
| **Games** | `buckshot`, `colorwars`, `memory`, `yazy`, `cf`, `diceroll`, `buckshot_help`, `colorwars_help`, `memory_help` | Public |
| **Social** | 61 reaction GIF commands (`hug`, `pat`, `slap`, `kiss`, `poke`, etc.) + `waifu`, `wtags`, `afk`, `msgcount`, `bn`, `lb` | Public |
| **Utility** | `help`, `echo`, `say`, `ping`, `hello`, `cmd`, `av`, `whois`, `run`, `kick` | Public (21 public, 1 protected) |
| **Creator** | `balance`, `debug`, `getmem`, `checkfunction`, `iw`, `dw` | Bot creator only |

- Hybrid commands work as both `!prefix` and `/slash` — no duplicate registrations.
- Every command is registered in the permission system with a category, access level, and policy key.

### Permission System

A multi-dimensional rule engine built on PostgreSQL. Every rule combines 5 axes:

- **Subject** — who: a specific member, a Discord role, or a Slickey role
- **Scope** — where: guild-wide, a specific channel, or a category
- **Key** — what: a single command (`command.ban`), a category (`category.moderation`), or a policy (`policy.role.assign`)
- **Effect** — allow or deny
- **Priority** — numeric, breaks ties. Deny wins at equal specificity.

Additional capabilities:
- Target conditions — restrict rules to specific users/roles as the *target* of a command (e.g., "can only mute members below rank X")
- Rule expiry — rules can have an `expires_at` timestamp
- Delegation scope — a user can only grant permissions they already hold, within their own scope
- Broad deny confirmation — guild-level or wildcard denies require explicit admin confirmation via a popup dialog
- Provenance tracking — every role membership row is tagged `source` as `manual`, `auto-assign`, or `discord-sync`. Automated systems only ever touch rows they created.

### Web Dashboard

A React SPA served by a FastAPI backend. Authenticates via Discord OAuth2.

**Pages:**

| Page | Description |
|---|---|
| **Overview** | Server stats, member/wizard setup guide |
| **Roles** | Create/edit/delete Slickey roles, assign members, rank management |
| **Auto-assign** | Configure roles automatically given to new members on join |
| **Role sync** | Map Discord roles to Slickey roles with configurable on-remove policy |
| **Policies** | Create/edit/delete permission rules with scope, conditions, and expiry |
| **Simulator** | "What can user X do in channel Y?" — shows every rule that was evaluated and why |
| **Catalogue** | Browse all 148 commands with their category, access level, and permission key |
| **Audit** | Full activity log with timestamps, actor info, and before/after state |

Dashboard visibility is section-gated — admins only see sections they have permission for (e.g., a user with only `policy.role.read` sees Overview and Roles, not Policies or Audit).

**Frontend:** 23 modular files — React components in `src/components/`, CSS split into variables, base, layout, components, pages, and responsive stylesheets. Responsive across desktop, laptop, tablet, and mobile.

**API:** 38 endpoints covering auth, guilds, roles, rules, auto-assign, role-sync, catalog, audit, simulation, and explain.

### Role Auto-assign

Configure Slickey roles that are automatically assigned to new members when they join the server. Managed entirely through the dashboard.

### Discord Role Sync

Map Discord roles to one or more Slickey roles. When a member gains or loses a Discord role, their Slickey roles update automatically. The `on-remove` policy controls whether losing the Discord role also removes the Slickey role (`keep` or `remove`). One Discord role can map to multiple Slickey roles.

### Permission Simulator

An explain/simulate endpoint that evaluates every rule against a given user + channel + command combination and returns the full decision trace — which rules matched, which won, and why. Exposed in the dashboard's Simulator page.

### Audit Log

Every policy change, role assignment, auto-assign toggle, and role-sync modification is logged with:
- Timestamp
- Actor (user ID + username)
- Action type
- Before/after state of the affected resource

---

## Architecture

```
Slickey_Main_.py          Bot entry point, event handlers, hybrid commands
Slickey_Secondary_.py     Additional commands (social GIFs, shop, spawn, etc.)
utils.py                  Shared utilities, DB helpers, game logic, caches
permission_system.py      Rule engine, schema, migrations, permission definitions
ai_cog.py                 AI chat integration (Google Gemini)
dashboard_api.py          FastAPI dashboard backend (OAuth2, REST API)
keep_alive.py             HTTP health check server for UptimeRobot/hosting

dashboard/
  src/
    App.jsx               Root component — auth, routing, sidebar, data fetching
    api.js                API helper with CSRF
    icons.jsx             SVG icon components
    components/           11 page components (Overview, Roles, Policies, etc.)
    styles/               7 CSS modules (variables, base, layout, components, etc.)

tests/
  test_permission_system.py   105 tests covering the rule engine, sections, auto-assign, sync, provenance, and integration scenarios
```

### Database (PostgreSQL)

| Table | Purpose |
|---|---|
| `bot_permission_rules` | Permission rules (subject, scope, key, effect, priority, conditions, expiry) |
| `bot_permission_roles` | Slickey roles (name, rank, description, created_by) |
| `bot_role_memberships` | Role assignments with provenance tracking (`source` column) |
| `bot_role_auto_assign` | Auto-assign rules (role, enabled) |
| `bot_role_discord_sync` | Discord→Slickey role mappings (on-remove policy) |
| `bot_command_catalog` | Command catalogue (synced from COMMAND_REGISTRY) |
| `bot_permission_definitions` | Registered permission keys and labels |
| `bot_permission_audit_log` | Audit trail for all policy and role changes |
| `bot_permission_migrations` | Schema migration tracking |

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for dashboard frontend)
- PostgreSQL database
- Discord bot application with OAuth2 credentials

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN_1` | Yes | Primary bot token |
| `BOT_TOKEN_2` | Optional | Secondary bot token (used by dashboard API if set) |
| `SUPABASE_DSN` | Yes | PostgreSQL connection string (`postgresql://...`) |
| `DISCORD_CLIENT_ID` | Yes | Discord OAuth2 client ID (for dashboard) |
| `DISCORD_CLIENT_SECRET` | Yes | Discord OAuth2 client secret |
| `DASHBOARD_REDIRECT_URI` | No | OAuth2 callback URL (default: `http://localhost:5173/auth/callback`) |
| `DASHBOARD_ORIGIN` | No | Frontend origin for CORS (default: `http://localhost:5173`) |
| `DASHBOARD_COOKIE_SECURE` | No | Set `true` for HTTPS deployments |
| `PORT` | No | Port for the health check server (default: `8080`) |

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/Slickey.git
cd Slickey

# Install Python dependencies
pip install -r requirements.txt

# Install dashboard frontend
cd dashboard
npm install
npm run build
cd ..
```

### Running

```bash
# Start the bot
python Slickey_Main_.py

# Start the dashboard API (separate terminal)
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000

# Or use the provided script (Windows)
.\start_dashboard.ps1
```

The bot and dashboard share the same PostgreSQL database. The dashboard reads the bot's permission rules directly.

---

## Development

```bash
# Run permission system tests
python -m unittest tests.test_permission_system -v

# Rebuild dashboard frontend
cd dashboard && npm run build

# Frontend dev server (hot reload)
cd dashboard && npm run dev
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | discord.py 2.x (hybrid commands) |
| Language | Python 3.10+ |
| Database | PostgreSQL via asyncpg |
| Dashboard backend | FastAPI + Uvicorn |
| Dashboard frontend | React 19 + Vite |
| Fuzzy matching | rapidfuzz (member name resolution) |
| AI integration | Google Gemini (ai_cog.py) |
| Image processing | Pillow |
| HTTP client | httpx |

---

## License

See [LICENSE](LICENSE) for details.
