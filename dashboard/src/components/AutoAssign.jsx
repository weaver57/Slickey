import React, { useState } from "react";
import { api } from "../api.js";

export default function AutoAssign({ data, guild, mutate, roles }) {
  const [addOpen, setAddOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState("");
  const [saving, setSaving] = useState(false);

  const rules = data.autoAssign || [];
  const availableRoles = roles.filter(
    (r) => !rules.some((ar) => ar.role_id === r.id),
  );

  const handleCreate = async () => {
    if (!selectedRole) return;
    setSaving(true);
    try {
      await api(`/api/guilds/${guild.id}/auto-assign`, {
        method: "POST",
        body: JSON.stringify({ role_id: parseInt(selectedRole) }),
      });
      setSelectedRole("");
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
      await api(`/api/guilds/${guild.id}/auto-assign/${ruleId}`, {
        method: "PATCH",
      });
      mutate();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleDelete = async (ruleId) => {
    if (!confirm("Remove this auto-assign rule?")) return;
    try {
      await api(`/api/guilds/${guild.id}/auto-assign/${ruleId}`, {
        method: "DELETE",
      });
      mutate();
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <>
      <h2>Auto-assign roles</h2>
      <p className="muted">
        Configure Slickey roles that are automatically assigned to new members
        when they join the server.
      </p>

      <div className="row" style={{ justifyContent: "space-between", marginBottom: 16 }}>
        <span style={{ fontWeight: 600 }}>
          {rules.length} rule{rules.length !== 1 ? "s" : ""}
        </span>
        <button onClick={() => setAddOpen(!addOpen)}>
          {addOpen ? "Cancel" : "+ Add rule"}
        </button>
      </div>

      {addOpen && (
        <div className="glass form" style={{ marginBottom: 16 }}>
          <h3>New auto-assign rule</h3>
          <div>
            <label style={{ display: "block", marginBottom: 4, fontSize: 13, color: "var(--ink-soft)" }}>
              Role
            </label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
            >
              <option value="">Select a role…</option>
              {availableRoles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} (rank {r.rank})
                </option>
              ))}
            </select>
          </div>
          <button disabled={!selectedRole || saving} onClick={handleCreate}>
            {saving ? "Saving…" : "Add rule"}
          </button>
        </div>
      )}

      {rules.length === 0 && !addOpen && (
        <div className="empty-inline">
          No auto-assign rules configured. Click "+ Add rule" to get started.
        </div>
      )}

      {rules.map((rule) => (
        <div key={rule.id} className="row" style={{ gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600 }}>{rule.role_name}</div>
            <small>
              rank {rule.role_rank}
              {rule.role_description ? ` · ${rule.role_description}` : ""}
            </small>
          </div>
          <div className="row-meta" style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span
              className="tag"
              style={{
                background: rule.enabled ? "var(--green)" : "var(--bg-subtle)",
                color: rule.enabled ? "#fff" : "var(--ink-muted)",
              }}
            >
              {rule.enabled ? "Active" : "Disabled"}
            </span>
            <button
              title={rule.enabled ? "Disable" : "Enable"}
              onClick={() => handleToggle(rule.id)}
            >
              {rule.enabled ? "⏸" : "▶"}
            </button>
            <button title="Remove" onClick={() => handleDelete(rule.id)}>
              ✕
            </button>
          </div>
        </div>
      ))}
    </>
  );
}
