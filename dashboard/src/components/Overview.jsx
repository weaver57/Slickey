import React, { useState } from "react";

export default function Overview({ data, createPreset, go }) {
  const [step, setStep] = useState(0);
  const [chosen, setChosen] = useState("");
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
            ["Choose a starting role", "Confirm the access level", "Put it to work"][step]
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
                  type="button"
                >
                  <b>{p.name}</b>
                  <small>{p.description} · rank {p.rank}</small>
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
