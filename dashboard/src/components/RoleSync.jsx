import React, { useState } from "react";
import { api } from "../api.js";

export default function RoleSync({ data, guild, mutate, roles, discordRoles }) {
  const [addOpen, setAddOpen] = useState(false);
  const [selectedDiscord, setSelectedDiscord] = useState("");
  const [selectedSlickey, setSelectedSlickey] = useState("");
  const [onRemove, setOnRemove] = useState("keep");
  const [saving, setSaving] = useState(false);

  const rules = data.roleSync || [];
  const dRoles = discordRoles || [];
  const sRoles = roles || [];
  const usedPairs = new Set(rules.map((r) => `${r.discord_role_id}:${r.slickey_role_id}`));
  const availableSlickey = sRoles.filter((r) => !usedPairs.has(`${selectedDiscord}:${r.id}`));

  const handleCreate = async () => {
    if (!selectedDiscord || !selectedSlickey) return;
    setSaving(true);
    try {
      await api(`/api/guilds/${guild.id}/role-sync`, {
        method: "POST",
        body: JSON.stringify({
          discord_role_id: parseInt(selectedDiscord),
          slickey_role_id: parseInt(selectedSlickey),
          on_remove: onRemove,
        }),
      });
      setSelectedDiscord("");
      setSelectedSlickey("");
      setOnRemove("keep");
      setAddOpen(false);
      mutate();
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (ruleId) => {
    try {
      await api(`/api/guilds/${guild.id}/role-sync/${ruleId}`, {
        method: "PATCH",
        body: JSON.stringify({}),
      });
      mutate();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleOnRemove = async (ruleId, newOnRemove) => {
    try {
      await api(`/api/guilds/${guild.id}/role-sync/${ruleId}`, {
        method: "PATCH",
        body: JSON.stringify({ on_remove: newOnRemove }),
      });
      mutate();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleDelete = async (ruleId) => {
    if (!confirm("Remove this sync rule?")) return;
    try {
      await api(`/api/guilds/${guild.id}/role-sync/${ruleId}`, {
        method: "DELETE",
      });
      mutate();
    } catch (e) {
      alert(e.message);
    }
  };

  const getDiscordRoleName = (id) => {
    const r = dRoles.find((d) => d.id === id);
    return r ? r.name : `Unknown (${id})`;
  };

  const getSlickeyRoleName = (id) => {
    const r = sRoles.find((s) => s.id === id);
    return r ? r.name : `Unknown (${id})`;
  };

  return (
    <>
      <h2>Discord → Slickey role sync</h2>
      <p className="muted">
        When a Discord role is added or removed from a member, automatically
        assign or remove the corresponding Slickey roles. One Discord role can
        map to multiple Slickey roles.
      </p>

      <div className="row" style={{ justifyContent: "space-between", marginBottom: 16 }}>
        <span style={{ fontWeight: 600 }}>
          {rules.length} sync rule{rules.length !== 1 ? "s" : ""}
        </span>
        <button onClick={() => setAddOpen(!addOpen)}>
          {addOpen ? "Cancel" : "+ Add rule"}
        </button>
      </div>

      {addOpen && (
        <div className="glass form" style={{ marginBottom: 16 }}>
          <h3>New sync rule</h3>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, color: "var(--ink-soft)" }}>
                Discord role
              </label>
              <select
                value={selectedDiscord}
                onChange={(e) => { setSelectedDiscord(e.target.value); setSelectedSlickey(""); }}
              >
                <option value="">Select a Discord role…</option>
                {dRoles.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, color: "var(--ink-soft)" }}>
                Slickey role
              </label>
              <select
                value={selectedSlickey}
                onChange={(e) => setSelectedSlickey(e.target.value)}
                disabled={!selectedDiscord}
              >
                <option value="">Select a Slickey role…</option>
                {availableSlickey.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} (rank {r.rank})
                  </option>
                ))}
              </select>
            </div>
            <div style={{ minWidth: 160 }}>
              <label style={{ display: "block", marginBottom: 4, fontSize: 13, color: "var(--ink-soft)" }}>
                When Discord role removed
              </label>
              <select value={onRemove} onChange={(e) => setOnRemove(e.target.value)}>
                <option value="keep">Keep Slickey role</option>
                <option value="remove">Remove Slickey role</option>
              </select>
            </div>
          </div>
          <button disabled={!selectedDiscord || !selectedSlickey || saving} onClick={handleCreate}>
            {saving ? "Saving…" : "Add rule"}
          </button>
        </div>
      )}

      {rules.length === 0 && !addOpen && (
        <div className="empty-inline">
          No sync rules configured. Click "+ Add rule" to get started.
        </div>
      )}

      {rules.map((rule) => (
        <div key={rule.id} className="row" style={{ gap: 12, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ color: "var(--accent)" }}>{getDiscordRoleName(rule.discord_role_id)}</span>
              <span style={{ color: "var(--ink-muted)" }}>→</span>
              <span style={{ color: "var(--green)" }}>{getSlickeyRoleName(rule.slickey_role_id)}</span>
            </div>
            <small style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 2 }}>
              <span>On remove: {rule.on_remove === "remove" ? "Remove Slickey role" : "Keep Slickey role"}</span>
            </small>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
            <span
              className="tag"
              style={{
                background: rule.enabled ? "var(--green)" : "var(--bg-subtle)",
                color: rule.enabled ? "#fff" : "var(--ink-muted)",
              }}
            >
              {rule.enabled ? "Active" : "Disabled"}
            </span>
            <select
              value={rule.on_remove}
              onChange={(e) => handleOnRemove(rule.id, e.target.value)}
              style={{ fontSize: 12, padding: "4px 6px", borderRadius: "var(--r-sm)", width: "auto" }}
            >
              <option value="keep">Keep</option>
              <option value="remove">Remove</option>
            </select>
            <button onClick={() => handleToggle(rule.id)}>
              {rule.enabled ? "⏸" : "▶"}
            </button>
            <button onClick={() => handleDelete(rule.id)}>✕</button>
          </div>
        </div>
      ))}
    </>
  );
}
