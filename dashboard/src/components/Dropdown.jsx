import React, { useState, useRef, useEffect } from "react";
import Icon from "../icons.jsx";

export default function Dropdown({
  name,
  value,
  onChange,
  options = [],
  placeholder = "Select",
  required = false,
  disabled = false,
  onSearch,
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [remote, setRemote] = useState([]);
  const [searching, setSearching] = useState(false);
  const ref = useRef(null);

  const all = [...remote, ...options];
  const selected = all.find((o) => String(o.value) === String(value));
  const filtered = (onSearch && query.trim() ? remote : options).filter((o) =>
    String(o.label).toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  const pick = (v) => {
    onChange?.(v);
    setQuery("");
    setOpen(false);
  };

  useEffect(() => {
    if (!open || !onSearch || !query.trim()) return;
    const timer = setTimeout(async () => {
      try {
        setSearching(true);
        setRemote(await onSearch(query.trim()));
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [open, query]);

  return (
    <div className={`dd${disabled ? " dd-disabled" : ""}`} ref={ref}>
      {name && <input type="hidden" name={name} value={value ?? ""} />}
      <button
        type="button"
        className={`dd-trigger${open ? " open" : ""}${!selected ? " placeholder" : ""}`}
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
      >
        <span>{selected ? selected.label : placeholder}</span>
        <Icon.chevron className="dd-chevron" />
      </button>
      {open && (
        <div className="dd-menu">
          <input
            className="dd-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type to search…"
            autoFocus
          />
          {!required && (
            <div
              className={`dd-option${!selected ? " active" : ""}`}
              onClick={() => pick("")}
            >
              {placeholder}
            </div>
          )}
          {filtered.map((o) => (
            <div
              key={o.value}
              className={`dd-option${String(o.value) === String(value) ? " active" : ""}`}
              onClick={() => pick(o.value)}
            >
              {o.label}
            </div>
          ))}
          {searching && <div className="dd-option dd-empty">Searching…</div>}
          {!searching && !filtered.length && (
            <div className="dd-option dd-empty">Nothing found</div>
          )}
        </div>
      )}
    </div>
  );
}
