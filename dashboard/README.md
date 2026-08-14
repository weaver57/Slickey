# Slickey Dashboard

1. Add `http://localhost:5173/auth/callback` as an OAuth2 redirect URL in Discord's Developer Portal.
2. Set `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `SUPABASE_DSN`, `DASHBOARD_ORIGIN`, and `DASHBOARD_REDIRECT_URI` for `dashboard_api.py`.
3. In the project root, run `python -m uvicorn dashboard_api:app --host 127.0.0.1 --port 8000`.
4. In this directory, run `npm install` once, then `npm run dev`. Open the local address Vite prints (normally `http://localhost:5173`).

For production, build the frontend with `npm run build`, host `dist/` over HTTPS, set the three dashboard URLs to their HTTPS production values, set `DASHBOARD_COOKIE_SECURE=true`, and run the API behind a reverse proxy. Sessions are already stored in Supabase PostgreSQL (`dashboard_sessions`), not in memory. Set `DISCORD_BOT_TOKEN` as well to enable the dashboard's member and channel pickers.
