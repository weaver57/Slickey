import React, { useState } from "react";
import { api } from "../api.js";

export default function Login() {
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
      {error && (
        <div className="alert error">
          <span>{error}</span>
        </div>
      )}
      <button onClick={login}>Continue with Discord</button>
    </main>
  );
}
