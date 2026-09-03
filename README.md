# Stillward

A 3-minute guided spiritual practice app — a single-page HTML prototype.

## Deploying on Railway

1. Push this repo to GitHub.
2. In Railway: **New Project → Deploy from GitHub repo** → select this repo.
3. Railway auto-detects Node and runs `npm start`, which serves `index.html` via `serve`.
4. Go to **Settings → Networking → Generate Domain** to get a public URL.
5. Every push to the main branch auto-redeploys.

## Notes

- This is a fully static, client-side app. All user data (sessions, teacher
  selection, saved practices, name) is stored in the browser's `localStorage`
  — there is no backend, database, or API.
- Data does not sync across devices or browsers.
- No build step or dependencies to install locally — `package.json` only
  exists so Railway has a process to run.
