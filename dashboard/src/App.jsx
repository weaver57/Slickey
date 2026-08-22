import React, { useEffect, useState } from "react";
import { api, setCsrfToken } from "./api.js";
import Icon from "./icons.jsx";
import Dropdown from "./components/Dropdown.jsx";
import Notice from "./components/Notice.jsx";
import Login from "./components/Login.jsx";
import Overview from "./components/Overview.jsx";
import Roles from "./components/Roles.jsx";
import Policies from "./components/Policies.jsx";
import Simulator from "./components/Simulator.jsx";
import AutoAssign from "./components/AutoAssign.jsx";
import RoleSync from "./components/RoleSync.jsx";
import Catalogue from "./components/Catalogue.jsx";
import Audit from "./components/Audit.jsx";

const NAV = [
  ["overview", "Overview", Icon.overview],
  ["roles", "Roles & members", Icon.roles],
  ["auto-assign", "Auto-assign", Icon.autoassign],
  ["role-sync", "Role sync", Icon.rolesync],
  ["policies", "Policies", Icon.policies],
  ["simulator", "Simulator", Icon.simulator],
  ["catalog", "Command catalogue", Icon.catalog],
  ["audit", "Activity", Icon.audit],
];

export default function App() {
  const [me, setMe] = useState(null);
  const [guilds, setGuilds] = useState([]);
  const [guild, setGuild] = useState(null);
  const [page, setPage] = useState("overview");
  const [data, setData] = useState({
    roles: [],
    rules: [],
    members: [],
    channels: [],
    audit: [],
    catalog: [],
    permissions: [],
    presets: [],
    autoAssign: [],
    roleSync: [],
    discordRoles: [],
  });
  const [sections, setSections] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("slickey_sidebar") === "collapsed",
  );
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dark, setDark] = useState(
    () => localStorage.getItem("slickey_theme") === "dark",
  );

  useEffect(() => {
    localStorage.setItem("slickey_sidebar", collapsed ? "collapsed" : "open");
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    localStorage.setItem("slickey_theme", dark ? "dark" : "light");
  }, [collapsed, dark]);

  const fail = (e) => setError(e.message || "Something went wrong.");
  const clear = () => { setError(""); setNotice(""); };

  const refresh = async (g = guild) => {
    if (!g) return;
    const sec = await api(`/api/guilds/${g.id}/sections`);
    const visible = new Set(sec.sections);
    setSections(visible);

    const [roles, rules, channels, audit, autoAssign, roleSync, discordRoles] = await Promise.all([
      visible.has("roles") ? api(`/api/guilds/${g.id}/roles`) : Promise.resolve([]),
      visible.has("policies") ? api(`/api/guilds/${g.id}/rules`) : Promise.resolve([]),
      api(`/api/guilds/${g.id}/channels`),
      visible.has("audit") ? api(`/api/guilds/${g.id}/audit`) : Promise.resolve([]),
      visible.has("auto-assign") ? api(`/api/guilds/${g.id}/auto-assign`).catch(() => []) : Promise.resolve([]),
      visible.has("role-sync") ? api(`/api/guilds/${g.id}/role-sync`).catch(() => []) : Promise.resolve([]),
      visible.has("role-sync") ? api(`/api/guilds/${g.id}/discord-roles`).catch(() => []) : Promise.resolve([]),
    ]);

    const members = visible.has("roles")
      ? await api(`/api/guilds/${g.id}/members`).catch((e) => {
          setError(`Member picker unavailable: ${e.message}`);
          return [];
        })
      : [];

    setData((d) => ({ ...d, roles, rules, members, channels, audit, autoAssign, roleSync, discordRoles }));
  };

  const searchMembers = async (guildId, query) =>
    api(`/api/guilds/${guildId}/members?query=${encodeURIComponent(query)}&limit=50`);

  // Auth + initial data load
  useEffect(() => {
    (async () => {
      try {
        const q = new URLSearchParams(location.search);
        if (q.has("code")) {
          const result = await api(`/api/auth/callback?${q}`);
          setCsrfToken(result.csrf_token);
          history.replaceState({}, "", location.pathname);
        } else {
          const { csrf_token } = await api("/api/csrf");
          setCsrfToken(csrf_token);
        }
        const [me, guilds, catalog, permissions, presets] = await Promise.all([
          api("/api/me"),
          api("/api/guilds"),
          api("/api/catalog"),
          api("/api/permissions"),
          api("/api/presets"),
        ]);
        setMe(me);
        setGuilds(guilds);
        setData((d) => ({ ...d, catalog, permissions, presets }));
        if (guilds[0]) setGuild(guilds[0]);
      } catch {
        setMe(false);
      }
    })();
  }, []);

  // Refresh data when guild changes
  useEffect(() => {
    refresh().catch(fail);
  }, [guild]);

  // Redirect to first visible section if current page is hidden
  useEffect(() => {
    if (!sections) return;
    if (!sections.has(page)) {
      const firstVisible = NAV.find(([id]) => sections.has(id));
      if (firstVisible) setPage(firstVisible[0]);
    }
  }, [sections]);

  // Loading state
  if (me === null)
    return (
      <main className="login">
        <div className="login-glow" />
        <div className="mark pulse">S</div>
        <p className="muted">Loading your workspace…</p>
      </main>
    );

  // Not authenticated
  if (me === false) return <Login />;

  const mutate = async (fn, message) => {
    try {
      if (fn) await fn();
      if (message) setNotice(message);
      refresh();
    } catch (e) {
      fail(e);
    }
  };

  const groups = data.catalog.reduce(
    (a, x) => ((a[x.category] ??= []).push(x), a),
    {},
  );

  const goTo = (id) => {
    setPage(id);
    setMobileOpen(false);
  };

  return (
    <div className={`app${collapsed ? " collapsed" : ""}`}>
      {mobileOpen && (
        <div className="backdrop" onClick={() => setMobileOpen(false)} />
      )}

      <aside className={mobileOpen ? "mobile-open" : ""}>
        <div className="aside-top">
          <div className="brand">
            <span className="mark small">S</span>
            {!collapsed && <b>Slickey</b>}
          </div>
          <button
            className="rail-toggle"
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <Icon.panel width="16" height="16" />
          </button>
          <button className="mobile-close" onClick={() => setMobileOpen(false)}>
            <Icon.close width="18" height="18" />
          </button>
          <button
            className="theme-toggle"
            onClick={() => setDark((d) => !d)}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            <Icon.theme width="15" height="15" />
          </button>
        </div>

        {!collapsed && (
          <div className="identity">
            Signed in as <b>{me.username}</b>
          </div>
        )}

        {!collapsed && (
          <Dropdown
            value={guild?.id || ""}
            onChange={(id) => setGuild(guilds.find((x) => x.id === id))}
            options={guilds.map((g) => ({ value: g.id, label: g.name }))}
            placeholder="Select a server"
            required
          />
        )}

        <nav>
          {NAV.filter(([id]) => !sections || sections.has(id)).map(
            ([id, label, IconCmp]) => (
              <button
                className={page === id ? "nav active" : "nav"}
                onClick={() => goTo(id)}
                key={id}
                title={collapsed ? label : undefined}
                type="button"
              >
                <IconCmp className="nav-icon" width="17" height="17" />
                {!collapsed && <span>{label}</span>}
              </button>
            ),
          )}
        </nav>

        {!collapsed && (
          <p className="aside-note">
            Only the owner, Bot Creator, and people granted dashboard access
            can enter.
          </p>
        )}
      </aside>

      <main>
        <button className="mobile-hamburger" onClick={() => setMobileOpen(true)}>
          <Icon.menu width="19" height="19" />
        </button>

        <Notice error={error} notice={notice} clear={clear} />

        {!guild ? (
          <section className="empty">
            <h1>No accessible servers</h1>
            <p>Ask the server owner to grant your role dashboard access.</p>
          </section>
        ) : (
          <>
            <header>
              <div>
                <span className="eyebrow">Server workspace</span>
                <h1>{guild.name}</h1>
              </div>
              <span className="pill">
                {guild.owner ? "Owner access" : "Delegated access"}
              </span>
            </header>

            <div className="page-enter" key={page}>
              {page === "overview" && (
                <Overview
                  data={data}
                  createPreset={(key) =>
                    mutate(
                      () =>
                        api(`/api/guilds/${guild.id}/roles/preset`, {
                          method: "POST",
                          body: JSON.stringify({ preset: key }),
                        }),
                      "Role created. Continue to members to assign it.",
                    )
                  }
                  go={goTo}
                />
              )}
              {page === "roles" && (
                <Roles data={data} guild={guild} mutate={mutate} searchMembers={searchMembers} />
              )}
              {page === "policies" && (
                <Policies data={data} guild={guild} mutate={mutate} searchMembers={searchMembers} />
              )}
              {page === "auto-assign" && (
                <AutoAssign data={data} guild={guild} mutate={mutate} roles={data.roles} />
              )}
              {page === "role-sync" && (
                <RoleSync data={data} guild={guild} mutate={mutate} roles={data.roles} discordRoles={data.discordRoles} />
              )}
              {page === "simulator" && (
                <Simulator data={data} guild={guild} searchMembers={searchMembers} />
              )}
              {page === "catalog" && <Catalogue groups={groups} />}
              {page === "audit" && <Audit audit={data.audit} />}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
