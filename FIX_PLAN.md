# DebTab — what was broken and what I changed

Worked through 6 August 2026. Start here: **`DEPLOYMENT.md`** has the one manual step
left. This file is the record of what changed and why.

---

## The actual fault

The login page rendered fine. Submitting it returned 500.

Every page that worked was a page that never opened a database connection — the
homepage is a bare `render()` call, and an unauthenticated GET of the login form
builds an empty form object. The first request that touched Postgres was the login
POST, and that was the one that broke. The app was healthy; the database was gone.

The Render free Postgres instance expired. Render free databases expire 30 days after
creation and are deleted after a further 14-day grace period. `render.yaml` was
committed 12 June, so the database expired around 12 July and was deleted around
26 July.

The 504 was the same root cause in a different disguise: Render free web services spin
down after 15 minutes idle, and a cold start that also hangs waiting on a dead database
exceeds the gateway timeout.

**A note on what I found while fixing it:** there is a Supabase project named "DebTab"
in your account, created 4 June. It was paused. I restored it — but its schema is
completely empty, which means it was set up and never actually used. Your data was on
Render, not Supabase. See the last section of `DEPLOYMENT.md`.

---

## Fixes

### 1. No error visibility — `debtab/settings.py`
There was no `LOGGING` block. With `DEBUG=False`, Django writes tracebacks to the
`django.request` logger, which had no handler attached, so they went nowhere. That
produced a blank 500 page *and* an empty Render log — which is the real reason a
one-line database problem stayed unsolved for weeks.

Added a full `LOGGING` config sending everything to stderr, where Render captures it.

*Verified:* with a deliberately unreachable database, the log now emits
`ERROR django.request Internal Server Error: /accounts/login/` followed by the complete
`OperationalError` traceback. Previously: silence.

### 2. Stale database connections — `debtab/settings.py`
`conn_max_age=600` held connections open for ten minutes with no health check, so
whenever the database or a pooler closed an idle connection, Django handed the dead
socket to the next request. On a free tier that idles out, this alone causes
intermittent 500s that look random.

Added `conn_health_checks=True`.

### 3. TLS hardcoded off — `debtab/settings.py`
`ssl_require=False`, carried over from the Railway deploy in commit `2546871` and never
revisited. Managed Postgres providers require TLS. Now defaults to on, overridable via
`DB_SSL_REQUIRE`.

### 4. `ALLOWED_HOSTS` did not include your domain — `render.yaml`
The blueprint said `.onrender.com`, which does not match `getdebtab.com`. The live site
only worked because the value had been overridden by hand in the dashboard, meaning the
committed file no longer described the running service — a redeploy from it would have
produced a site returning 400 on every request. Fixed in the file, with the real domain.

### 5. `CSRF_TRUSTED_ORIGINS` was missing entirely — `debtab/settings.py`
Django 4+ requires it for HTTPS form posts from a custom domain. It had not yet caused
a visible failure only because `SECURE_PROXY_SSL_HEADER` was *also* missing — Django
believed every request was plain HTTP and skipped the referer check. Fixing either one
alone would have broken every form on the site with a 403. Both are now set together,
which is the only safe way to do it.

### 6. `DEBUG` defaulted to `True` — `debtab/settings.py`
One missing or misspelled env var away from running production with debug on, publicly
exposing settings, environment variables and stack traces. Now defaults to `False`.

### 7. `SECRET_KEY` had a committed fallback — `debtab/settings.py`
`'dev-secret-key-change-in-production-abc123xyz'` was in git. Same failure mode as #6:
one missing variable and every session cookie on the site becomes forgeable. Now raises
a clear `RuntimeError` at startup in production rather than falling back.

### 8. Open redirect — `apps/accounts/views.py`
`redirect(request.GET.get("next", ...))` with no validation. A link like
`/accounts/login/?next=https://evil.example` would log a tab master in and then hand
them to an attacker's copy of the site. Now validated with Django's
`url_has_allowed_host_and_scheme`.

*Verified:* the malicious `next` is discarded and the user lands on `/tournaments/`;
a legitimate internal `next` still works.

### 9. Migrations ran in the build step — `render.yaml`
`preDeployCommand` is the correct hook, but Render only offers it on paid instance
types and this service is on Free. Migrations therefore stay in `buildCommand`, now
with `--noinput` and explicit `&&` chaining so a failure stops the build loudly instead
of half-deploying. Documented so it can be moved if you ever upgrade.

### 10. No way to create a login account — new file
`apps/accounts/management/commands/ensure_superuser.py`. After a database is recreated,
`migrate` gives you empty tables and no user, so login stops returning 500 and starts
saying "Invalid username or password" — which looks like a brand new bug. Render Free
has no interactive shell, so `createsuperuser` was not usable. This command reads env
vars, is safe to run on every deploy, and never overwrites an existing account.

### Also fixed along the way

**`STATICFILES_STORAGE` was silently dead.** The setting was removed in Django 5.1, and
`requirements.txt` allowed anything up to Django 7, so WhiteNoise's compression was
simply never applied. Replaced with the supported `STORAGES` dict, plus
`WHITENOISE_MANIFEST_STRICT = False` so one missing icon can never take the whole site
down with a 500.

**Unbounded dependencies.** `Django>=5.0,<7.0` would have pulled Django 6.x into a
production build and broken it without a single line of code changing. All pins now
have upper bounds.

**72 files permanently showing as modified.** Editing on Windows had rewritten every
source file with CRLF endings, so `git status` was unusable and any real change would
have been buried in whitespace noise. Added `.gitattributes` to normalise.

**No health signal.** Added `/healthz` (`debtab/health.py`), which runs `SELECT 1` and
returns 503 with a diagnostic message when the database is unreachable. This is what
makes the failure detectable from outside instead of only by a logged-in user.

---

## Verification

Ran against a real Django 5.2.17 install with migrations applied:

```
[PASS]  homepage 200                     200
[PASS]  healthz 200                      200
[PASS]  healthz json ok                  {'status': 'ok', 'database': 'ok'}
[PASS]  login GET 200                    200
[PASS]  login POST redirects (not 500)   302     <- the original bug
[PASS]  login lands on /tournaments/     /tournaments/
[PASS]  tournaments 200 when logged in   200
[PASS]  bad password re-renders form     200
[PASS]  open redirect blocked            /tournaments/
[PASS]  internal next= honoured          /tournaments/
[PASS]  anon redirected to login         /accounts/login/?next=/tournaments/

11/11 checks passed
```

`manage.py check --deploy` reports no errors.

Separately, with a deliberately dead database: `/healthz` returns 503 with a readable
reason, and the login 500 produces a full traceback in the log.

---

## What is left

One step, in `DEPLOYMENT.md` — paste the Supabase connection string into Render. It is
a password that exists only in your dashboard, so it is the one thing that could not be
automated. About 3 minutes.

Then set up the free uptime monitor described in the same file. That is what stops this
from happening again: the Supabase free tier pauses after roughly a week of inactivity,
and a paused database produces exactly the 500 you reported.
