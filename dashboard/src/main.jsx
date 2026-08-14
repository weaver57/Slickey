import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_DASHBOARD_API || "http://localhost:8000";
const csrf = () =>
  document.cookie
    .split("; ")
    .find((x) => x.startsWith("slickey_csrf="))
    ?.split("=")[1] || "";
async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase(),
    headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
  if (!["GET", "HEAD", "OPTIONS"].includes(method))
    headers["X-CSRF-Token"] = csrf();
  const r = await fetch(`${API}${path}`, {
    credentials: "include",
    headers,
    ...options,
  });
  if (!r.ok)
    throw new Error(
      (await r.json().catch(() => ({}))).detail || "Something went wrong.",
    );
  return r.status === 204 ? null : r.json();
}

/* ---------- Icons ---------- */
const Icon = {
  overview: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M3 9.5 10 4l7 5.5M5 8.5V16a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V8.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  roles: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <circle cx="7" cy="7" r="2.6" stroke="currentColor" strokeWidth="1.6" />
      <path d="M2.5 16c.6-2.7 2.4-4.2 4.5-4.2s3.9 1.5 4.5 4.2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="14.5" cy="6.5" r="2.1" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12.7 11.6c1.8.2 3.2 1.6 3.8 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  policies: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M10 2.5 16 5v4.4c0 4-2.6 6.7-6 8.1-3.4-1.4-6-4.1-6-8.1V5l6-2.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M7.4 10 9.2 11.8 12.7 8.2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  catalog: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M4 5h12M4 10h12M4 15h7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  ),
  audit: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10 6v4.3l3 1.9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  chevron: (p) => (
    <svg viewBox="0 0 11 7" fill="none" {...p}>
      <path d="M1 1l4.5 4.5L10 1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  panel: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <rect x="3" y="4" width="14" height="12" rx="2.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8.3 4v12" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  menu: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M3 5.5h14M3 10h14M3 14.5h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  ),
  close: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M5 5l10 10M15 5 5 15" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  ),
  theme: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M10 3a7 7 0 1 0 7 7c0-.3 0-.6-.05-.9A5.2 5.2 0 0 1 10 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  ),
};

/* ---------- Dropdown (replaces every native <select>) ---------- */
function Dropdown({
  name,
  value,
  onChange,
  options = [],
  placeholder = "Select",
  required = false,
  disabled = false,
  onSearch,
}) {
  const [open, setOpen] = useState(false),
    [query, setQuery] = useState(""),
    [remote, setRemote] = useState([]),
    [searching, setSearching] = useState(false);
  const ref = useRef(null);
  const selected = [...remote, ...options].find(
    (o) => String(o.value) === String(value),
  );
  const filtered = (onSearch && query.trim() ? remote : options).filter((o) =>
    String(o.label).toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const pick = (v) => {
    onChange?.(v);
    setQuery("");
    setOpen(false);
  };

  useEffect(() => {
    if (!open || !onSearch || !query.trim()) return;
    const timer = setTimeout(async () => {
      try {
        setSearching(true);
        setRemote(await onSearch(query.trim()));
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [open, query]);

  return (
    <div className={`dd${disabled ? " dd-disabled" : ""}`} ref={ref}>
      {name && <input type="hidden" name={name} value={value ?? ""} />}
      <button
        type="button"
        className={`dd-trigger${open ? " open" : ""}${!selected ? " placeholder" : ""}`}
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
      >
        <span>{selected ? selected.label : placeholder}</span>
        <Icon.chevron className="dd-chevron" />
      </button>
      {open && (
        <div className="dd-menu">
          <input
            className="dd-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type to search…"
            autoFocus
          />
          {!required && (
            <div
              className={`dd-option${!selected ? " active" : ""}`}
              onClick={() => pick("")}
            >
              {placeholder}
            </div>
          )}
          {filtered.map((o) => (
            <div
              key={o.value}
              className={`dd-option${String(o.value) === String(value) ? " active" : ""}`}
              onClick={() => pick(o.value)}
            >
              {o.label}
            </div>
          ))}
          {searching && <div className="dd-option dd-empty">Searching…</div>}
          {!searching && !filtered.length && <div className="dd-option dd-empty">Nothing found</div>}
        </div>
      )}
    </div>
  );
}

const Notice = ({ error, notice, clear }) => (
  <>
    {error && (
      <div className="alert error">
        <span>{error}</span>
        <button onClick={clear}><Icon.close width="14" height="14" /></button>
      </div>
    )}
    {notice && (
      <div className="alert notice">
        <span>{notice}</span>
        <button onClick={clear}><Icon.close width="14" height="14" /></button>
      </div>
    )}
  </>
);

function Login() {
  const [error, setError] = useState("");
  const login = async () => {
    try {
      location.assign((await api("/api/auth/login")).url);
    } catch {
      setError(
        "The dashboard service is offline. Start the API, then try again.",
      );
    }
  };
  return (
    <main className="login">
      <div className="login-glow" />
      <div className="mark">S</div>
      <h1>Slickey</h1>
      <p>Clear, powerful permissions for your Discord community.</p>
      {error && <div className="alert error"><span>{error}</span></div>}
      <button onClick={login}>Continue with Discord</button>
    </main>
  );
}

const NAV = [
  ["overview", "Overview", Icon.overview],
  ["roles", "Roles & members", Icon.roles],
  ["policies", "Policies", Icon.policies],
  ["catalog", "Command catalogue", Icon.catalog],
  ["audit", "Activity", Icon.audit],
];

function App() {
  const [me, setMe] = useState(null),
    [guilds, setGuilds] = useState([]),
    [guild, setGuild] = useState(null),
    [page, setPage] = useState("overview"),
    [data, setData] = useState({
      roles: [],
      rules: [],
      members: [],
      channels: [],
      audit: [],
      catalog: [],
      presets: [],
    }),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [collapsed, setCollapsed] = useState(
      () => localStorage.getItem("slickey_sidebar") === "collapsed",
    ),
    [mobileOpen, setMobileOpen] = useState(false),
    [dark, setDark] = useState(
  () => localStorage.getItem("slickey_theme") === "dark",);

  useEffect(() => {
    localStorage.setItem("slickey_sidebar", collapsed ? "collapsed" : "open");
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  localStorage.setItem("slickey_theme", dark ? "dark" : "light");
  }, [collapsed, dark]);

  const fail = (e) => setError(e.message || "Something went wrong.");
  const clear = () => {
    setError("");
    setNotice("");
  };
  const refresh = async (g = guild) => {
    if (!g) return;
    const [roles, rules, channels, audit] = await Promise.all([
      api(`/api/guilds/${g.id}/roles`),
      api(`/api/guilds/${g.id}/rules`),
      api(`/api/guilds/${g.id}/channels`),
      api(`/api/guilds/${g.id}/audit`),
    ]);
    const members = await api(`/api/guilds/${g.id}/members`).catch((e) => {
      setError(`Member picker unavailable: ${e.message}`);
      return [];
    });
    setData((d) => ({ ...d, roles, rules, members, channels, audit }));
  };
  const searchMembers = async (guildId, query) =>
    api(`/api/guilds/${guildId}/members?query=${encodeURIComponent(query)}&limit=50`);
  useEffect(() => {
    (async () => {
      try {
        const q = new URLSearchParams(location.search);
        if (q.has("code")) {
          await api(`/api/auth/callback?${q}`);
          history.replaceState({}, "", location.pathname);
        }
        const [me, guilds, catalog, presets] = await Promise.all([
          api("/api/me"),
          api("/api/guilds"),
          api("/api/catalog"),
          api("/api/presets"),
        ]);
        setMe(me);
        setGuilds(guilds);
        setData((d) => ({ ...d, catalog, presets }));
        if (guilds[0]) setGuild(guilds[0]);
      } catch {
        setMe(false);
      }
    })();
  }, []);
  useEffect(() => {
    refresh().catch(fail);
  }, [guild]);

  if (me === null)
    return (
      <main className="login">
        <div className="login-glow" />
        <div className="mark pulse">S</div>
        <p className="muted">Loading your workspace…</p>
      </main>
    );
  if (me === false) return <Login />;

  const mutate = async (fn, message) => {
    try {
      await fn();
      setNotice(message);
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
      {mobileOpen && <div className="backdrop" onClick={() => setMobileOpen(false)} />}
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
          <button className="theme-toggle" onClick={() => setDark((d) => !d)} title={dark ? "Switch to light mode" : "Switch to dark mode"}>
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
          {NAV.map(([id, label, IconCmp]) => (
            <button
              className={page === id ? "nav active" : "nav"}
              onClick={() => goTo(id)}
              key={id}
              title={collapsed ? label : undefined}
            >
              <IconCmp className="nav-icon" width="17" height="17" />
              {!collapsed && <span>{label}</span>}
            </button>
          ))}
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
            <p>
              Ask the server owner to grant your custom role{" "}
              <code>command.dashboard</code>.
            </p>
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
              {page === "catalog" && <Catalogue groups={groups} />}
              {page === "audit" && <Audit audit={data.audit} />}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function Overview({ data, createPreset, go }) {
  const [step, setStep] = useState(0),
    [chosen, setChosen] = useState("");
  const preset = data.presets.find((x) => x.key === chosen);
  return (
    <>
      <section className="hero glass">
        <div>
          <h2>Permission control, without the maze.</h2>
          <p>
            Set your team up safely, then make narrow policies only when your
            server needs them.
          </p>
        </div>
        <button onClick={() => go("policies")}>Create a policy</button>
      </section>
      <div className="stats">
        <div>
          <b>{data.roles.length}</b>
          <span>Custom roles</span>
        </div>
        <div>
          <b>{data.rules.length}</b>
          <span>Active policies</span>
        </div>
        <div>
          <b>Live</b>
          <span>Owner access</span>
        </div>
      </div>
      <section className="glass wizard">
        <span className="eyebrow">Guided setup</span>
        <h2>
          {
            [
              "Choose a starting role",
              "Confirm the access level",
              "Put it to work",
            ][step]
          }
        </h2>
        {step === 0 && (
          <>
            <p className="muted">
              Presets are editable. Start with the closest fit for your team.
            </p>
            <div className="preset-grid">
              {data.presets.map((p) => (
                <button
                  className={chosen === p.key ? "preset selected" : "preset"}
                  onClick={() => setChosen(p.key)}
                  key={p.key}
                >
                  <b>{p.name}</b>
                  <small>
                    {p.description} · rank {p.rank}
                  </small>
                </button>
              ))}
            </div>
            <button disabled={!chosen} onClick={() => setStep(1)}>
              Continue
            </button>
          </>
        )}
        {step === 1 && (
          <>
            <p>
              {preset?.name} can be changed after creation. Delegated
              managers can only create a preset when they already hold each
              included permission.
            </p>
            <div className="wizard-actions">
              <button className="ghost" onClick={() => setStep(0)}>
                Back
              </button>
              <button
                onClick={() => {
                  createPreset(chosen);
                  setStep(2);
                }}
              >
                Create {preset?.name}
              </button>
            </div>
          </>
        )}
        {step === 2 && (
          <>
            <p>
              Your role is ready. Assign people from the Roles & members
              page, then use Policies to limit commands to specific channels
              if needed.
            </p>
            <div className="wizard-actions">
              <button onClick={() => go("roles")}>Assign members</button>
              <button className="ghost" onClick={() => go("policies")}>
                Create a policy
              </button>
            </div>
          </>
        )}
      </section>
    </>
  );
}

function Roles({ data, guild, mutate, searchMembers }) {
  const [detail, setDetail] = useState(null),
    [member, setMember] = useState("");
  const open = async (id) =>
    setDetail(await api(`/api/guilds/${guild.id}/roles/${id}`));
  const role = detail?.role;
  return (
    <section className="split">
      <div>
        <h2>Roles</h2>
        <p className="muted">
          Roles group people. Policies decide what they can do.
        </p>
        <div className="list">
          {data.roles.map((r) => (
            <button className="row" onClick={() => open(r.id)} key={r.id}>
              <span>
                <b>{r.name}</b>
                <small>{r.description || "No description"}</small>
              </span>
              <span className="row-meta">
                {r.member_count} members · rank {r.rank}
              </span>
            </button>
          ))}
          {!data.roles.length && (
            <p className="empty-inline">
              No roles yet. Start with guided setup.
            </p>
          )}
        </div>
      </div>
      <RoleCreate guild={guild} mutate={mutate} />
      {role && (
        <section className="drawer glass">
          <button className="close" onClick={() => setDetail(null)}>
            <Icon.close width="18" height="18" />
          </button>
          <h2>{role.name}</h2>
          <form
            className="form compact"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              mutate(
                () =>
                  api(`/api/guilds/${guild.id}/roles/${role.id}`, {
                    method: "PUT",
                    body: JSON.stringify({
                      name: f.get("name"),
                      description: f.get("description"),
                      rank: Number(f.get("rank")),
                    }),
                  }),
                "Role updated.",
              ).then(() => open(role.id));
            }}
          >
            <input name="name" defaultValue={role.name} />
            <input name="description" defaultValue={role.description} />
            <input name="rank" type="number" defaultValue={role.rank} />
            <button>Save role</button>
          </form>
          <h3>Members</h3>
          <div className="assign">
            <Dropdown
              value={member}
              onChange={setMember}
              options={data.members.map((m) => ({ value: m.id, label: m.name }))}
              placeholder="Choose a member"
              onSearch={(query) => searchMembers(guild.id, query).then((members) => members.map((m) => ({ value: m.id, label: m.name })))}
            />
            <button
              disabled={!member}
              onClick={() =>
                mutate(
                  () =>
                    api(`/api/guilds/${guild.id}/roles/${role.id}/members`, {
                      method: "POST",
                      body: JSON.stringify({ user_id: Number(member) }),
                    }),
                  "Member assigned.",
                ).then(() => open(role.id))
              }
            >
              Assign
            </button>
          </div>
          <div className="chips">
            {detail.members.map((m) => {
              const p = data.members.find((x) => x.id === String(m.user_id));
              return (
                <span key={m.user_id}>
                  {p?.name || m.user_id}
                  <button
                    onClick={() =>
                      mutate(
                        () =>
                          api(
                            `/api/guilds/${guild.id}/roles/${role.id}/members/${m.user_id}`,
                            { method: "DELETE" },
                          ),
                        "Member removed.",
                      ).then(() => open(role.id))
                    }
                  >
                    <Icon.close width="10" height="10" />
                  </button>
                </span>
              );
            })}
            {!detail.members.length && <small>No members assigned.</small>}
          </div>
          <h3>Role policies</h3>
          {detail.rules.map((r) => (
            <p key={r.id} className="rule-line">
              <b className={r.effect}>{r.effect}</b>{" "}
              <code>{r.permission_key}</code> in {r.scope_type}
            </p>
          ))}
          <button
            className="danger"
            onClick={() =>
              mutate(
                () =>
                  api(`/api/guilds/${guild.id}/roles/${role.id}`, {
                    method: "DELETE",
                  }),
                "Role deleted.",
              ).then(() => setDetail(null))
            }
          >
            Delete role
          </button>
        </section>
      )}
    </section>
  );
}

function RoleCreate({ guild, mutate }) {
  return (
    <form
      className="glass form"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        mutate(
          () =>
            api(`/api/guilds/${guild.id}/roles`, {
              method: "POST",
              body: JSON.stringify({
                name: f.get("name"),
                description: f.get("description"),
                rank: Number(f.get("rank") || 0),
              }),
            }),
          "Role created.",
        );
        e.currentTarget.reset();
      }}
    >
      <h3>Create a role</h3>
      <input name="name" required placeholder="Event Manager" />
      <input name="description" placeholder="What this role is for" />
      <input name="rank" type="number" placeholder="Rank" />
      <button>Create role</button>
    </form>
  );
}

function Policies({ data, guild, mutate, searchMembers }) {
  const [subjectType, setSubjectType] = useState("role"),
    [subjectTarget, setSubjectTarget] = useState(""),
    [key, setKey] = useState(""),
    [effect, setEffect] = useState("allow"),
    [scopeType, setScopeType] = useState("guild"),
    [scopeTarget, setScopeTarget] = useState(""),
    [confirmBroad, setConfirmBroad] = useState(false),
    [why, setWhy] = useState({ user: "", command: "", channel: "" }),
    [result, setResult] = useState(null);

  const canSubmit =
    key &&
    (subjectType === "member" || subjectTarget) &&
    (scopeType === "guild" || scopeTarget);

  const submit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    mutate(
      () =>
        api(`/api/guilds/${guild.id}/rules`, {
          method: "POST",
          body: JSON.stringify({
            subject_type: subjectType,
            subject_id: subjectType === "member" ? null : Number(subjectTarget),
            permission_key: key,
            effect,
            scope_type: scopeType,
            scope_id: scopeType === "guild" ? null : Number(scopeTarget),
            confirm_broad_deny: confirmBroad,
          }),
        }),
      "Policy saved.",
    );
  };

  return (
    <>
      <section className="split">
        <form className="glass form" onSubmit={submit}>
          <h2>Create policy</h2>

          <Dropdown
            required
            value={subjectType}
            onChange={(v) => {
              setSubjectType(v);
              setSubjectTarget("");
            }}
            options={[
              { value: "role", label: "A custom role" },
              { value: "user", label: "A specific member" },
              { value: "member", label: "Everyone" },
            ]}
          />

          {subjectType !== "member" && (
            <Dropdown
              required
              value={subjectTarget}
              onChange={setSubjectTarget}
              placeholder="Choose target"
              options={(subjectType === "role" ? data.roles : data.members).map(
                (x) => ({ value: x.id, label: x.name }),
              )}
              onSearch={subjectType === "user" ? (query) => searchMembers(guild.id, query).then((members) => members.map((m) => ({ value: m.id, label: m.name }))) : undefined}
            />
          )}

          <Dropdown
            required
            value={key}
            onChange={setKey}
            placeholder="Choose command or category"
            options={[
              ...data.catalog.map((x) => ({
                value: x.permission_key,
                label: `${x.display_name} · ${x.category}`,
              })),
              { value: "command.*", label: "All commands" },
            ]}
          />

          <Dropdown
            required
            value={effect}
            onChange={setEffect}
            options={[
              { value: "allow", label: "Allow" },
              { value: "deny", label: "Deny" },
            ]}
          />

          <Dropdown
            required
            value={scopeType}
            onChange={(v) => {
              setScopeType(v);
              setScopeTarget("");
            }}
            options={[
              { value: "guild", label: "Entire server" },
              { value: "category", label: "One category" },
              { value: "channel", label: "One channel" },
            ]}
          />

          {scopeType !== "guild" && (
            <Dropdown
              required
              value={scopeTarget}
              onChange={setScopeTarget}
              placeholder="Choose scope"
              options={data.channels
                .filter((x) =>
                  scopeType === "category" ? x.type === 4 : x.type === 0,
                )
                .map((x) => ({
                  value: x.id,
                  label: (scopeType === "category" ? "Category: " : "#") + x.name,
                }))}
            />
          )}

          <label className="check">
            <input
              type="checkbox"
              checked={confirmBroad}
              onChange={(e) => setConfirmBroad(e.target.checked)}
            />
            Confirm broad deny
          </label>

          <button disabled={!canSubmit}>Save policy</button>
        </form>

        <WhyPanel
          data={data}
          why={why}
          setWhy={setWhy}
          result={result}
          setResult={setResult}
          guild={guild}
          searchMembers={searchMembers}
        />
      </section>

      <section>
        <h2>Active policies</h2>
        <div className="list">
          {data.rules.map((r) => (
            <div className="row static" key={r.id}>
              <span>
                <b className={r.effect}>{r.effect}</b>{" "}
                <code>{r.permission_key}</code>
                <small>
                  {r.subject_type} · {r.scope_type}
                </small>
              </span>
              <button
                className="danger"
                onClick={() =>
                  mutate(
                    () =>
                      api(`/api/guilds/${guild.id}/rules/${r.id}`, {
                        method: "DELETE",
                      }),
                    "Policy removed.",
                  )
                }
              >
                Remove
              </button>
            </div>
          ))}
          {!data.rules.length && (
            <p className="empty-inline">No policies yet.</p>
          )}
        </div>
      </section>
    </>
  );
}

function WhyPanel({ data, why, setWhy, result, setResult, guild, searchMembers }) {
  const explain = async () =>
    setResult(
      await api(`/api/guilds/${guild.id}/explain`, {
        method: "POST",
        body: JSON.stringify({
          user_id: Number(why.user),
          command_name: why.command,
          channel_id: why.channel ? Number(why.channel) : null,
        }),
      }),
    );
  return (
    <section className="glass explain">
      <h2>Why?</h2>
      <p className="muted">
        Preview the exact decision and the rules that were considered.
      </p>
      <Dropdown
        value={why.user}
        onChange={(user) => setWhy({ ...why, user })}
        options={data.members.map((m) => ({ value: m.id, label: m.name }))}
        placeholder="Select member"
        onSearch={(query) => searchMembers(guild.id, query).then((members) => members.map((m) => ({ value: m.id, label: m.name })))}
      />
      <Dropdown
        value={why.command}
        onChange={(command) => setWhy({ ...why, command })}
        placeholder="Select command"
        options={data.catalog.map((x) => ({
          value: x.permission_key.replace("command.", ""),
          label: x.display_name,
        }))}
      />
      <Dropdown
        value={why.channel}
        onChange={(channel) => setWhy({ ...why, channel })}
        placeholder="Any channel"
        options={data.channels
          .filter((x) => x.type === 0)
          .map((x) => ({ value: x.id, label: `#${x.name}` }))}
      />
      <button disabled={!why.user || !why.command} onClick={explain}>
        Explain access
      </button>
      {result && (
        <div className={result.allowed ? "decision allow" : "decision deny"}>
          <b>{result.allowed ? "Allowed" : "Denied"}</b>
          <span>{result.reason}</span>
          <ol>
            {result.trace.map((x, i) => (
              <li className={x.selected ? "selected" : ""} key={i}>
                {x.kind === "rule" ? (
                  <>
                    {x.selected ? "Used" : "Considered"}:{" "}
                    <code>
                      {x.effect} {x.permission_key}
                    </code>{" "}
                    for {x.subject_type} in {x.scope_type}
                  </>
                ) : (
                  x.label
                )}
                {x.outcome && ` ${x.outcome}`}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}

function Catalogue({ groups }) {
  return (
    <>
      <h2>Command catalogue</h2>
      <p className="muted">
        Protected commands need an allow policy. Public commands are
        available until restricted.
      </p>
      {Object.entries(groups).map(([category, items]) => (
        <section className="catalogue" key={category}>
          <h3>{category}</h3>
          {items.map((x) => (
            <article className="catalog-row" key={x.command_path}>
              <span>
                <b>{x.display_name}</b>
                <small>
                  {x.command_path} ·{" "}
                  {x.description || "No description supplied"}
                </small>
              </span>
              <span
                className={
                  x.default_access === "public"
                    ? "badge public"
                    : "badge protected"
                }
              >
                {x.default_access}
              </span>
            </article>
          ))}
        </section>
      ))}
    </>
  );
}

function Audit({ audit }) {
  return (
    <>
      <h2>Activity</h2>
      <p className="muted">Recent permission changes in this server.</p>
      <div className="list">
        {audit.map((x) => (
          <div className="row static" key={x.id}>
            <span>
              <b>{x.action}</b>
              <small>
                by {x.actor_id} · {new Date(x.created_at).toLocaleString()}
              </small>
            </span>
          </div>
        ))}
        {!audit.length && (
          <p className="empty-inline">
            No permission activity has been recorded yet.
          </p>
        )}
      </div>
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);
