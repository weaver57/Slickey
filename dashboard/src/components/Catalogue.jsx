import React from "react";

export default function Catalogue({ groups }) {
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
