import React, { useState } from "react";
import { api } from "../api.js";
import Dropdown from "./Dropdown.jsx";

export default function Simulator({ data, guild, searchMembers }) {
  const [userId, setUserId] = useState("");
  const [channelId, setChannelId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [loading, setLoading] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const run = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const res = await api(`/api/guilds/${guild.id}/simulate`, {
        method: "POST",
        body: JSON.stringify({
          user_id: Number(userId),
          channel_id: channelId ? Number(channelId) : null,
          category_id: categoryId ? Number(categoryId) : null,
        }),
      });
      setSimResult(res);
      setExpanded(null);
    } catch {
      setSimResult(null);
    } finally {
      setLoading(false);
    }
  };

  const results = simResult?.results || [];
  const filtered = results.filter((r) => {
    if (filter === "allowed" && r.outcome !== "allowed") return false;
    if (filter === "denied" && r.outcome !== "denied") return false;
    if (filter === "default" && r.outcome !== "default") return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        r.command.includes(q) ||
        r.display_name.toLowerCase().includes(q) ||
        r.category.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const grouped = {};
  filtered.forEach((r) => {
    (grouped[r.category] ??= []).push(r);
  });

  return (
    <>
      <section className="glass form simulator-controls">
        <span className="eyebrow">Permission simulator</span>
        <h2>What can this user do?</h2>
        <p className="muted form-intro">
          Pick a member and optionally narrow the context to a specific
          channel or category. Every registered command is evaluated
          against the live policy engine.
        </p>

        <Dropdown
          required
          value={userId}
          onChange={setUserId}
          placeholder="Choose a member"
          options={data.members.map((m) => ({ value: m.id, label: m.name }))}
          onSearch={(q) =>
            searchMembers(guild.id, q).then((ms) =>
              ms.map((m) => ({ value: m.id, label: m.name })),
            )
          }
        />
        <Dropdown
          value={categoryId}
          onChange={(v) => { setCategoryId(v); setChannelId(""); }}
          placeholder="Any category"
          options={data.channels
            .filter((x) => x.type === 4)
            .map((x) => ({ value: x.id, label: `Category: ${x.name}` }))}
        />
        <Dropdown
          value={channelId}
          onChange={setChannelId}
          placeholder="Any channel"
          options={data.channels
            .filter((x) => x.type === 0)
            .map((x) => ({ value: x.id, label: `#${x.name}` }))}
        />
        <button disabled={!userId || loading} onClick={run}>
          {loading ? "Simulating…" : "Run simulation"}
        </button>
      </section>

      {simResult && (
        <>
          <div className="sim-summary">
            <div className="sim-stat sim-stat-allowed">
              <b>{simResult.summary.allowed}</b>
              <span>Allowed</span>
            </div>
            <div className="sim-stat sim-stat-denied">
              <b>{simResult.summary.denied}</b>
              <span>Denied</span>
            </div>
            <div className="sim-stat sim-stat-default">
              <b>{simResult.summary.default}</b>
              <span>No rule</span>
            </div>
            {simResult.user_roles.length > 0 && (
              <div className="sim-stat sim-stat-roles">
                <b>{simResult.user_roles.length}</b>
                <span>Custom roles</span>
              </div>
            )}
          </div>

          {simResult.user_roles.length > 0 && (
            <div className="sim-roles">
              {simResult.user_roles.map((r) => (
                <span className="pill" key={r.id}>
                  {r.name} <small>(rank {r.rank})</small>
                </span>
              ))}
            </div>
          )}

          <div className="sim-filters">
            <button className={filter === "all" ? "" : "ghost"} onClick={() => setFilter("all")}>
              All ({results.length})
            </button>
            <button className={filter === "allowed" ? "" : "ghost"} onClick={() => setFilter("allowed")}>
              Allowed ({simResult.summary.allowed})
            </button>
            <button className={filter === "denied" ? "" : "ghost"} onClick={() => setFilter("denied")}>
              Denied ({simResult.summary.denied})
            </button>
            <button className={filter === "default" ? "" : "ghost"} onClick={() => setFilter("default")}>
              No rule ({simResult.summary.default})
            </button>
            <input
              className="sim-search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter commands…"
            />
          </div>

          {Object.entries(grouped).map(([cat, items]) => (
            <section className="catalogue" key={cat}>
              <h3>{cat}</h3>
              {items.map((r) => (
                <div key={r.command}>
                  <button
                    className={`sim-row ${r.outcome}`}
                    onClick={() => setExpanded(expanded === r.command ? null : r.command)}
                    type="button"
                  >
                    <span className="sim-row-main">
                      <b>{r.display_name}</b>
                      <small>{r.command}</small>
                    </span>
                    <span className={`sim-badge ${r.outcome}`}>
                      {r.outcome === "allowed"
                        ? "✓ Allowed"
                        : r.outcome === "denied"
                          ? "✕ Denied"
                          : "— No rule"}
                    </span>
                  </button>
                  {expanded === r.command && (
                    <div className="sim-trace glass">
                      <p className="sim-reason">
                        <b>Reason:</b> {r.reason}
                      </p>
                      {r.matched_rule_id && (
                        <p className="sim-reason">
                          <b>Rule:</b> #{r.matched_rule_id}
                        </p>
                      )}
                      <ol className="sim-trace-list">
                        {r.trace.map((t, i) => (
                          <li key={i} className={t.selected ? "selected" : ""}>
                            {t.kind === "rule" ? (
                              <>
                                <span className={`sim-trace-effect ${t.effect}`}>
                                  {t.effect}
                                </span>{" "}
                                <code>{t.permission_key}</code>
                                {" "}
                                {t.subject_type}
                                {t.subject_id ? `:${t.subject_id}` : ""}
                                {" → "}
                                {t.scope_type}
                                {t.scope_id ? `:${t.scope_id}` : ""}
                                {t.priority ? ` (p${t.priority})` : ""}
                                {t.selected ? " ✓ USED" : " (skipped)"}
                              </>
                            ) : (
                              <>
                                {t.label}
                                {t.outcome ? ` → ${t.outcome}` : ""}
                              </>
                            )}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              ))}
            </section>
          ))}
        </>
      )}
    </>
  );
}
