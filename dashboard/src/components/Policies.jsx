import React, { useState } from "react";
import { api } from "../api.js";
import Dropdown from "./Dropdown.jsx";

export function ruleSubject(r, data) {
  if (r.subject_type === "member") return "Everyone";
  if (r.subject_type === "role") {
    const role = data.roles.find((x) => x.id === String(r.subject_id));
    return role ? role.name : `Role ${r.subject_id}`;
  }
  if (r.subject_type === "user") {
    const user = data.members.find((x) => x.id === String(r.subject_id));
    return user ? user.name : `User ${r.subject_id}`;
  }
  return r.subject_type;
}

export function ruleScope(r, data) {
  if (r.scope_type === "guild") return "Server-wide";
  const channel = data.channels.find((x) => x.id === String(r.scope_id));
  const label = channel ? channel.name : r.scope_id;
  return r.scope_type === "category" ? `Category: ${label}` : `#${label}`;
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
        onSearch={(query) =>
          searchMembers(guild.id, query).then((members) =>
            members.map((m) => ({ value: m.id, label: m.name })),
          )
        }
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

export default function Policies({ data, guild, mutate, searchMembers }) {
  const [subjectType, setSubjectType] = useState("role");
  const [subjectTarget, setSubjectTarget] = useState("");
  const [controlKind, setControlKind] = useState("action");
  const [key, setKey] = useState("");
  const [effect, setEffect] = useState("allow");
  const [scopeType, setScopeType] = useState("guild");
  const [scopeTarget, setScopeTarget] = useState("");
  const [showBroadPopup, setShowBroadPopup] = useState(false);
  const [why, setWhy] = useState({ user: "", command: "", channel: "" });
  const [result, setResult] = useState(null);

  const isBroadDeny =
    effect === "deny" &&
    (scopeType === "guild" || ["*", "command.*", "category.*"].includes(key));

  const actionOptions = [
    ...data.catalog.map((x) => ({
      value: x.permission_key,
      label: `${x.display_name} · ${x.category}`,
    })),
    ...data.permissions
      .filter((x) => x.permission_kind === "category")
      .map((x) => ({ value: x.permission_key, label: x.display_name })),
    { value: "command.*", label: "All bot commands" },
  ];
  const policyOptions = data.permissions
    .filter((x) => x.permission_kind === "policy")
    .map((x) => ({ value: x.permission_key, label: x.display_name }));
  const selectedDefinition = data.permissions.find((x) => x.permission_key === key);

  const canSubmit =
    key &&
    (subjectType === "member" || subjectTarget) &&
    (scopeType === "guild" || scopeTarget);

  const doSubmit = (confirmedBroad) => {
    mutate(
      () =>
        api(`/api/guilds/${guild.id}/rules`, {
          method: "POST",
          body: JSON.stringify({
            subject_type: subjectType,
            subject_id: subjectType === "member" ? null : subjectTarget,
            permission_key: key,
            effect,
            scope_type: scopeType,
            scope_id: scopeType === "guild" ? null : scopeTarget,
            confirm_broad_deny: confirmedBroad,
          }),
        }),
      "Policy saved.",
    );
  };

  const submit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    if (isBroadDeny) {
      setShowBroadPopup(true);
      return;
    }
    doSubmit(false);
  };

  return (
    <>
      <section className="split">
        <form className="glass form" onSubmit={submit}>
          <span className="eyebrow">Fine-grained access</span>
          <h2>Create policy</h2>
          <p className="muted form-intro">
            Use allow rules as whitelists and deny rules as blacklists. More
            specific member, channel, and category rules can make exceptions.
          </p>

          <Dropdown
            required
            value={subjectType}
            onChange={(v) => { setSubjectType(v); setSubjectTarget(""); }}
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
              onSearch={
                subjectType === "user"
                  ? (query) =>
                      searchMembers(guild.id, query).then((members) =>
                        members.map((m) => ({ value: m.id, label: m.name })),
                      )
                  : undefined
              }
            />
          )}

          <div className="segmented" aria-label="Policy control type">
            <button
              type="button"
              className={controlKind === "action" ? "selected" : "ghost"}
              onClick={() => { setControlKind("action"); setKey(""); }}
            >
              Bot actions
            </button>
            <button
              type="button"
              className={controlKind === "policy" ? "selected" : "ghost"}
              onClick={() => { setControlKind("policy"); setKey(""); }}
            >
              Policy powers
            </button>
          </div>

          <Dropdown
            required
            value={key}
            onChange={setKey}
            placeholder={
              controlKind === "action"
                ? "Choose a command or command group"
                : "Choose a policy-management power"
            }
            options={controlKind === "action" ? actionOptions : policyOptions}
          />
          {selectedDefinition && (
            <p className="capability-note">{selectedDefinition.description}</p>
          )}
          {controlKind === "policy" && !selectedDefinition && (
            <p className="capability-note">
              Policy powers let a role manage only the actions, people, and
              scopes it is explicitly covered for.
            </p>
          )}

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
            onChange={(v) => { setScopeType(v); setScopeTarget(""); }}
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
                  label:
                    (scopeType === "category" ? "Category: " : "#") + x.name,
                }))}
            />
          )}

          <button disabled={!canSubmit}>Save policy</button>

          {showBroadPopup && (
            <div
              className="broad-popup-overlay"
              onClick={() => setShowBroadPopup(false)}
            >
              <div
                className="broad-popup"
                onClick={(e) => e.stopPropagation()}
              >
                <h3>Confirm broad deny</h3>
                <p>
                  This rule denies <code>{key}</code> across the{" "}
                  <b>entire server</b>. It may remove access for many members
                  at once.
                </p>
                <p className="muted">
                  Are you sure you want to save this policy?
                </p>
                <div className="broad-popup-actions">
                  <button
                    className="ghost"
                    onClick={() => setShowBroadPopup(false)}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      setShowBroadPopup(false);
                      doSubmit(true);
                    }}
                  >
                    Save anyway
                  </button>
                </div>
              </div>
            </div>
          )}
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
                  {ruleSubject(r, data)} · {ruleScope(r, data)}
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
