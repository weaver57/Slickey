import React from "react";
import Icon from "../icons.jsx";

export default function Notice({ error, notice, clear }) {
  return (
    <>
      {error && (
        <div className="alert error">
          <span>{error}</span>
          <button onClick={clear}>
            <Icon.close width="14" height="14" />
          </button>
        </div>
      )}
      {notice && (
        <div className="alert notice">
          <span>{notice}</span>
          <button onClick={clear}>
            <Icon.close width="14" height="14" />
          </button>
        </div>
      )}
    </>
  );
}
