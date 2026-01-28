# Woodhouse Runbook (Clawdbot workspace)

This document is the **portable state** for this assistant: what’s configured, where secrets live, and how to rehydrate the same capabilities on a new machine / new model backend.

> **Policy:** This file records **where** secrets are stored, not the secret values themselves.

---

## Identity / persona
- **Assistant name:** Woodhouse
- **Persona:** modeled after Woodhouse from *Archer* (dry, dutiful, unflappable; lightly sardonic when appropriate).
- **Primary user:** Ryan (Australia/Sydney)

Files to restore:
- `SOUL.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`, `memory/*.md`

---

## Messaging (WhatsApp)
- WhatsApp gateway is configured and in use.
- Allowed owner number: `+61466363840`

If WhatsApp breaks:
- Confirm gateway status in the Control UI / gateway logs.
- Re-link as needed (QR flow) using the gateway’s WhatsApp login tooling.

---

## Web search (Brave)
Web search and web fetch are enabled.

Config locations:
- Gateway config: `~/.clawdbot/clawdbot.json`
- Brave key is stored in config under:
  - `tools.web.search.apiKey` and
  - env var `BRAVE_API_KEY`

Notes:
- Free Brave plans can be rate-limited; prefer batching searches and using `web_fetch` once you have a good target URL.

**Do not commit keys** to git repos.

---

## X (Twitter) access
Tooling:
- Uses `bird` CLI (GraphQL + cookie auth).

Local credential storage:
- `~/.config/bird/creds.json` (chmod 600)
  - contains `auth_token` and `ct0`

Convenience wrapper:
- `~/.local/bin/bird-auth` (chmod 700)
  - reads `~/.config/bird/creds.json` and calls `bird ...`

Basic checks:
- `bird-auth whoami`
- `bird-auth following --all --json`

---

## Notion
- Notion integration token stored at: `~/.config/notion/api_key` (chmod 600)
- Note: Notion tokens typically start with `ntn_`.

---

## Todoist
- Todoist API token stored at: `~/.config/todoist/api_key` (chmod 600)

## Google Places
- Google Places API key configured in Gateway config under `skills.entries`.

## OpenAI Whisper
- OpenAI API key for Whisper configured in Gateway config under `skills.entries.openai-whisper-api`.

---

## Google Calendar (planned)
There are two paths available:

### Path A: CalDAV via vdirsyncer + khal (works on Linux)
Approach:
- CalDAV via `vdirsyncer` + `khal`.

Installed:
- `vdirsyncer`, `khal`, `python3-aiohttp-oauthlib` (apt)
- Workspace skill: `skills/caldav-calendar/`

Status:
- **OAuth not completed yet** (needs a browser on a computer).

Config files created:
- `~/.config/vdirsyncer/config`
- `~/.config/khal/config`
- Token file will be created after auth:
  - `~/.config/vdirsyncer/google_token.json` (chmod 600)

To complete auth (when a browser is available):
1) Run: `vdirsyncer discover google_calendar`
2) It will print a Google auth URL and start a local callback listener.
3) Open the URL in a desktop browser, approve access; the token is stored at `google_token.json`.
4) Run: `vdirsyncer sync`
5) Verify: `khal list today 7d`

### Path B: Google Workspace CLI (gog) — potentially easier, broader scope
- Skill installed: `skills/gog/` (Google Workspace CLI wrapper)
- `gog` binary installed at: `~/.local/bin/gog`
  - Install method (Linux): download release tarball from <https://github.com/steipete/gogcli/releases> and `install` the `gog` binary.

If you want to use this path, then:
- `gog auth credentials /path/to/client_secret.json`
- `gog auth add you@gmail.com --services gmail,calendar,drive,contacts,sheets,docs`

This can make Google integration more straightforward than CalDAV, once installed.

---

## Flights research notes (SYD ↔ Whitsundays)
Recent research pattern (useful later):
- Check both:
  - **SYD ↔ HTI (Hamilton Island)** direct (Qantas / Virgin)
  - **SYD ↔ PPP (Proserpine)** direct (Jetstar), then coach+ferry to Hamilton Island
- Jetstar vouchers are best applied to SYD↔PPP + transfers.

---

## System/bootstrap checklist (new machine)
1) Copy workspace folder (or git clone) to `/home/ubuntu/clawd`.
2) Restore secret files:
   - `~/.config/bird/creds.json`
   - `~/.config/notion/api_key`
   - `~/.config/todoist/api_key`
   - `~/.config/vdirsyncer/*` (and token file if already authorized)
   - `~/.clawdbot/clawdbot.json` (or re-apply settings)
3) Ensure packages installed:
   - `bird` (npm global)
   - `vdirsyncer`, `khal`, `python3-aiohttp-oauthlib`
4) Confirm web search:
   - `BRAVE_API_KEY` present (env or config)
5) Smoke tests:
   - `bird-auth whoami`
   - `khal list today` (after calendar auth)

---

## Things that should *not* be stored in this runbook
- Raw API keys, cookies, passwords.
- Anything you wouldn’t paste in a public repo.
