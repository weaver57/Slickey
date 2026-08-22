import React from "react";

const Icon = {
  overview: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M3 9.5 10 4l7 5.5M5 8.5V16a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V8.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  roles: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <circle cx="7" cy="7" r="2.6" stroke="currentColor" strokeWidth="1.6" />
      <path d="M2.5 16c.6-2.7 2.4-4.2 4.5-4.2s3.9 1.5 4.5 4.2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="14.5" cy="6.5" r="2.1" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12.7 11.6c1.8.2 3.2 1.6 3.8 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  policies: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M10 2.5 16 5v4.4c0 4-2.6 6.7-6 8.1-3.4-1.4-6-4.1-6-8.1V5l6-2.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M7.4 10 9.2 11.8 12.7 8.2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  catalog: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M4 5h12M4 10h12M4 15h7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  ),
  audit: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10 6v4.3l3 1.9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  chevron: (p) => (
    <svg viewBox="0 0 11 7" fill="none" {...p}>
      <path d="M1 1l4.5 4.5L10 1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  panel: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <rect x="3" y="4" width="14" height="12" rx="2.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8.3 4v12" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  menu: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M3 5.5h14M3 10h14M3 14.5h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  ),
  close: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M5 5l10 10M15 5 5 15" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  ),
  theme: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M10 3a7 7 0 1 0 7 7c0-.3 0-.6-.05-.9A5.2 5.2 0 0 1 10 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  ),
  simulator: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <circle cx="10" cy="7" r="3.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3.5 17c.6-2.8 2.8-4.5 6.5-4.5s5.9 1.7 6.5 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M14 3l2.5 2.5M16.5 3 14 5.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  autoassign: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <circle cx="8" cy="7" r="3" stroke="currentColor" strokeWidth="1.6" />
      <path d="M2 17c.6-2.8 2.7-4.5 6-4.5s5.4 1.7 6 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M16 8v6M13 11h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  ),
  rolesync: (p) => (
    <svg viewBox="0 0 20 20" fill="none" {...p}>
      <path d="M4 7h5.5M4 13h5.5M10.5 7H16M10.5 13H16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M7.75 5l-2 2 2 2M12.25 11l2 2-2 2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
};

export default Icon;
