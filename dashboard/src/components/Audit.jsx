import React from "react";

export default function Audit({ audit }) {
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
                by {x.actor_name || x.actor_id} · {new Date(x.created_at).toLocaleString()}
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
