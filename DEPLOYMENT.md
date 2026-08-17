# DebTab — everyday operations

Setting up for the first time? Use **`START_HERE.md`** instead. This file is for
after that.

---

## The three buttons

Everything routine is a double-click in your `debtab` folder.

| File | What it does |
|---|---|
| **`DEPLOY.bat`** | Pushes your changes live. Asks nothing. Closes itself when done. |
| **`BACKUP.bat`** | Saves a copy of the live database to `backups\`. Run after each tournament. |
| **`START SERVER.bat`** | Runs the site locally at `127.0.0.1:8000` for testing before you deploy. |

---

## Where everything lives

| Thing | Where | Plan | Cost |
|---|---|---|---|
| The website | Render — `debtab` service | Free | £0 |
| The database | Neon — `debtab` project | Free | £0 |
| The code | GitHub — `Ifeanyiuche/debtab` | Free | £0 |
| Monitoring | UptimeRobot | Free | £0 |

Nothing here expires. Neon's free plan has no time limit on projects or storage.

---

## Checking whether the site is healthy

<https://getdebtab.com/healthz>

| Response | Meaning |
|---|---|
| `{"status": "ok", "database": "ok"}` | Everything works. |
| `{"status": "unhealthy", ...}` | App is running, database is not reachable. The message says why. |
| `Server Error (500)` | App crashed. Render → **Logs** has the full traceback. |
| Nothing loads | Build failed. Render → **Events**. |

This URL is the fastest way to answer "is it me or is it the site?" — and it is
what UptimeRobot watches.

---

## When something breaks

**Always start here:** Render dashboard → **debtab** → **Logs**.

The single most important change made in August 2026 was adding logging config.
Before that, errors went nowhere — you got a blank error page and an empty log,
which is why the June outage went undiagnosed for seven weeks. Now every error
prints a full traceback in that tab. Read it, or send it to me.

**Common situations:**

| Symptom | Cause | Fix |
|---|---|---|
| First visit takes ~50s | Render free service was asleep | Normal. UptimeRobot reduces it. |
| 500 on login only | Database unreachable | Check `/healthz`, then `DATABASE_URL` in Render |
| 403 on every form | `CSRF_TRUSTED_ORIGINS` wrong or missing | Re-check that variable in Render |
| 400 on every page | `ALLOWED_HOSTS` does not include the domain | Re-check that variable in Render |
| "Invalid username or password" after a fresh database | Tables exist, no user yet | Render → Shell → `python manage.py ensure_superuser` |

---

## Backups

Neon keeps your data and does not delete it. But a backup you physically own is
the only one nobody else can lose.

**Run `BACKUP.bat` after every tournament.** It writes a timestamped file to
`backups\`, which is excluded from GitHub automatically.

First run asks you to add one line to your `.env` file — instructions appear on
screen.

**To restore a backup into an empty database:**

```
python manage.py loaddata backups\debtab-2026-08-06_1413.json
```

Copy at least one backup somewhere off this computer — OneDrive, Google Drive,
an external drive. A backup sitting on the same machine as the original is not
really a backup.

---

## Changing a setting on the live site

Render dashboard → **debtab** → **Environment** → edit → **Save changes**.
Render redeploys automatically, ~3–5 minutes. You do not need `DEPLOY.bat` for
environment variable changes — only for code changes.

**Never change `SECRET_KEY` on a working site.** It logs out every user and
invalidates outstanding password-reset links.

---

## Adding another Tab Master

Two ways:

1. **They register themselves** at <https://getdebtab.com/accounts/register/> —
   this already works and needs nothing from you.
2. **You create it** at <https://getdebtab.com/admin/> with your superuser
   login.

Each Tab Master only sees their own tournaments — `tournament_list` filters on
`tab_master=request.user`, so there is no cross-visibility between accounts.

---

## If you ever want to spend money

You do not need to. For reference only:

- **Render Starter, ~$7/mo** — removes the 15-minute sleep, so there is no
  cold-start delay. Also unlocks `preDeployCommand`; if you buy it, move
  `python manage.py migrate` out of `buildCommand` in `render.yaml`.
- **Neon Launch, ~$5/mo** — more compute hours. The free plan's 100 CU-hours per
  month is far more than DebTab will use.

The cold start is the only free-tier limitation you will actually notice, and it
only affects the first visitor after a quiet period.
