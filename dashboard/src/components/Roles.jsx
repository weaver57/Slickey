import React, { useState } from "react";
import { api } from "../api.js";
import Icon from "../icons.jsx";
import Dropdown from "./Dropdown.jsx";

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

export default function Roles({ data, guild, mutate, searchMembers }) {
  const [detail, setDetail] = useState(null);
  const [member, setMember] = useState("");

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
            <button className="row" onClick={() => open(r.id)} key={r.id} type="button">
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
              onSearch={(query) =>
                searchMembers(guild.id, query).then((members) =>
                  members.map((m) => ({ value: m.id, label: m.name })),
                )
              }
            />
            <button
              disabled={!member}
              onClick={() =>
                mutate(
                  () =>
                    api(`/api/guilds/${guild.id}/roles/${role.id}/members`, {
                      method: "POST",
                      body: JSON.stringify({ user_id: member }),
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
