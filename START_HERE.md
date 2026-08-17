# START HERE — get DebTab live

**Time needed: about 15 minutes, once. After this you never do it again.**

Do these in order. Parts 1, 2 and 3 all have to happen before login will work —
the database and the code are two separate halves of the same fix, and neither
one works without the other. Do not skip Part 5; that is what stops this from
repeating.

When you are done, log in at <https://getdebtab.com/accounts/login/> and it will work.

---

# PART 1 — Create the Neon database (4 minutes)

**1.1** Open <https://neon.com> and click **Sign up**.

**1.2** Choose **Continue with GitHub**. You already have a GitHub account
(`Ifeanyiuche`), so this is one click and no new password to remember.

**1.3** Neon asks you to create your first project. Fill it in like this:

| Field | What to enter |
|---|---|
| Project name | `debtab` |
| Postgres version | leave the default |
| Cloud service provider | **AWS** |
| Region | **Europe (Frankfurt)** — or whichever is closest to you |

Click **Create**.

> Region matters a little: your Render service runs in Frankfurt, so picking
> Frankfurt keeps the database next door and the site feels faster. Any region
> will work, it will just be slightly slower.

**1.4** Neon opens your project dashboard and shows a **Connect to your
database** box with a connection string in it. **Do not copy it yet** — there
is one toggle to change first.

**1.5** Find the **Connection pooling** toggle in that box and switch it
**OFF**.

> Why: with pooling on, the hostname gets `-pooler` added to it and the
> connection runs through PgBouncer in transaction mode, which cannot handle
> some of the things Django does during migrations. With it off you get a plain
> direct connection, which is what Django wants. Your site is small enough that
> pooling buys you nothing.

**1.6** Now click the **copy** icon to copy the connection string.

It looks like this — one long line, and it already contains your password:

```
postgresql://neondb_owner:npg_AbC123xyz@ep-cool-name-12345678.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

**1.7** Paste it somewhere safe for the next two minutes — Notepad is fine.
Check that the hostname does **not** contain the word `pooler`. If it does, go
back to 1.5.

✅ **Part 1 done.** You now have a database that never expires and wakes itself
up automatically.

---

# PART 2 — Point Render at it (5 minutes)

**2.1** Open <https://dashboard.render.com> and sign in.

**2.2** Click the service named **debtab** in your list.

**2.3** In the left sidebar, click **Environment**.

**2.4** You will see a list of environment variables. Add or update each row
below. For each one: click **Add Environment Variable**, type the key on the
left and the value on the right.

**Copy these exactly.**

| # | Key | Value |
|---|---|---|
| 1 | `DATABASE_URL` | *paste the Neon string from step 1.6* |
| 2 | `ALLOWED_HOSTS` | `getdebtab.com,www.getdebtab.com,debtab.onrender.com,.onrender.com` |
| 3 | `CSRF_TRUSTED_ORIGINS` | `https://getdebtab.com,https://www.getdebtab.com,https://*.onrender.com` |
| 4 | `DEBUG` | `False` |
| 5 | `DB_SSL_REQUIRE` | `True` |
| 6 | `DISABLE_SERVER_SIDE_CURSORS` | `False` |
| 7 | `LOG_LEVEL` | `INFO` |
| 8 | `DJANGO_SUPERUSER_USERNAME` | *the username you want to log in with* |
| 9 | `DJANGO_SUPERUSER_EMAIL` | `godswillifeanyi1996@gmail.com` |
| 10 | `DJANGO_SUPERUSER_PASSWORD` | *a strong password you choose — this becomes your login* |

> Rows 8, 9 and 10 create your login account automatically on the next deploy.
> Pick the password now and write it down. You can change it later from inside
> the site.

**2.5** Check whether a variable called `SECRET_KEY` already exists in the list.

- **If it exists** — leave it completely alone. Do not edit it, do not
  regenerate it. Changing it logs out every existing user and invalidates any
  outstanding password-reset links.
- **If it does not exist** — click **Add Environment Variable**, type
  `SECRET_KEY` as the key, then click the **Generate** button that Render shows
  next to the value box. Render creates a strong random value for you.

> Never paste a `SECRET_KEY` that you found in a file, a chat, or a web page.
> Anyone who has seen that value can forge a login session on your site. The
> Generate button produces one that only Render has ever seen.

**2.6** Click **Save changes** at the bottom.

Render will start a deploy on its own. **Ignore it** — it is still building the
old code and it will not fix login. Part 3 is the one that matters. You do not
need to wait for this one to finish.

**2.7** While you are here, check the **Build Command**. Left sidebar →
**Settings** → scroll to **Build & Deploy**.

It must read exactly:

```
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py ensure_superuser
```

If it says anything else, replace it with the line above and click **Save**.

> Why this matters: Render Free has no Shell tab, so there is no way to create
> your login account by hand. That last command does it during the build
> instead. Without it you will get "Invalid username or password" forever, on a
> site that is otherwise working perfectly.

✅ **Part 2 done.**

---

# PART 3 — Deploy the fixed code (2 minutes)

**None of the fixes are on the live site yet.** They are on your computer,
waiting. This is the step that ships them.

**3.1** Go to your `debtab` folder and **double-click `DEPLOY.bat`**.

**3.2** Leave it running. It pushes the code, then waits for the site and tells
you when it is live. Expect 3–5 minutes.

If a GitHub sign-in window appears, sign in — it only happens once.

**3.3** Your login account is created automatically during this deploy, using
the username and password you set in step 2.4 (rows 8 and 10).

✅ **Part 3 done.**

---

# PART 4 — Confirm it works (2 minutes)

**4.1** Open <https://getdebtab.com/healthz> in your browser.

You are looking for exactly this:

```json
{"status": "ok", "database": "ok"}
```

**If that is what you see, you are live. Go to step 4.2.**

If you see something else, here is what each one means:

| What you see | What it means | What to do |
|---|---|---|
| `{"status": "unhealthy", ...}` | App is fine, database string is wrong | Re-check `DATABASE_URL` in step 2.4. The message on screen says what failed. |
| `Server Error (500)` | App crashed | Render → **Logs**. The full error is printed there now. Send it to me. |
| Page never loads | Build failed | Render → **Events**. Send me what it says. |
| Loads slowly the first time | Normal | Free tier waking up. Refresh once. |

**4.2** Go to <https://getdebtab.com/accounts/login/> and log in with the
username and password you chose in step 2.4 (rows 8 and 10).

✅ **Part 4 done. The site is working.**

---

# PART 5 — Make sure it never breaks again (3 minutes)

**Do not skip this.** Neon keeps your data safe and wakes itself up, so the
database will not repeat what happened. But this step is how *you find out*
if anything else ever goes wrong — instead of discovering it the night before
a tournament.

**5.1** Go to <https://uptimerobot.com> and click **Register for FREE**.
No card required.

**5.2** Confirm your email, then click **+ New monitor**.

**5.3** Fill it in exactly like this:

| Field | Value |
|---|---|
| Monitor Type | **HTTP(s)** |
| Friendly Name | `DebTab` |
| URL | `https://getdebtab.com/healthz` |
| Monitoring Interval | **5 minutes** |

**5.4** Under **Alert Contacts To Notify**, tick your email address.

**5.5** Click **Create Monitor**.

That is it. From now on, if the site or the database goes down for any reason,
you get an email within five minutes. It also keeps the Render service warm, so
visitors stop hitting the slow 50-second cold start.

✅ **Part 5 done. You are finished.**

---

# From now on: how to deploy

Double-click **`DEPLOY.bat`** in your `debtab` folder.

That is the entire process. It asks you nothing. It saves your changes, pushes
them to GitHub, waits for the site to come back, opens it in your browser, and
closes itself.

The first time you run it, a GitHub sign-in window may appear. Sign in once and
it never asks again.

If a deploy ever fails, the window stays open and tells you exactly what went
wrong instead of closing.

---

# What this costs

Nothing. Permanently.

| Service | Plan | Cost | Expires? |
|---|---|---|---|
| Render (web) | Free | £0 | No |
| Neon (database) | Free | £0 | **No — data is permanent** |
| UptimeRobot | Free | £0 | No |

The only free-tier behaviour left is that the Render web service sleeps after
15 minutes of no visitors, so the first person to arrive waits about 50 seconds.
The UptimeRobot monitor in Part 4 largely fixes that too, by pinging the site
every 5 minutes.

If that last 50 seconds ever bothers you during a live tournament, Render
Starter at about $7/month removes it. Nothing else needs upgrading, ever.
