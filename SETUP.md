# Setup

Written for someone who has never used Google Cloud. Follow the
sections in order. Each one says what you're doing and why.

## 1. Clone the repo and install dependencies

```powershell
git clone https://github.com/<owner>/morning-briefing-bot.git
cd morning-briefing-bot
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

You'll fill in `.env` as you go through this guide.

## 2. Google Cloud: create a project and OAuth credentials

This lets the bot read your Calendar, Gmail, and Tasks on your behalf.
It never gets your Google password; you grant access through Google's
own consent screen.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
   and sign in with the Google account you want the bot to read.
2. Click the project dropdown at the top, then **New Project**. Give
   it any name (e.g. "morning-briefing"). Click **Create** and wait
   for it to finish, then select it from the dropdown.
3. In the left sidebar, go to **APIs & Services > Library**. Search
   for and enable, one at a time:
   - Google Calendar API
   - Gmail API
   - Google Tasks API
4. Go to **APIs & Services > OAuth consent screen**.
   - User type: **External** (unless you have a Google Workspace
     account and want Internal).
   - Fill in an app name and your email for the required fields.
   - Under **Scopes**, you don't need to add anything here; the code
     requests the specific scopes it needs.
   - Under **Test users**, add your own Google account's email. While
     the app is in "testing" status, only test users can authorize
     it — that's fine, since you're the only user.
   - Save through the remaining steps.
5. Go to **APIs & Services > Credentials**. Click **Create
   Credentials > OAuth client ID**.
   - Application type: **Desktop app**.
   - Name it anything.
   - Click **Create**, then **Download JSON**.
6. Save that downloaded file as `credentials.json` in the project
   root (same folder as this file). It's already in `.gitignore` —
   never commit it.

## 3. Run the one-time Google consent flow

This opens a browser once, asks you to approve access, and saves a
reusable token so the bot doesn't ask again.

```powershell
.venv\Scripts\python.exe tools/get_tasks.py
```

A browser window opens. Sign in, and when Google warns that the app
is unverified, click **Advanced > Go to (your app name) (unsafe)** —
this warning is expected for an app you created yourself that hasn't
gone through Google's full verification review. Approve the
requested Calendar/Gmail/Tasks (read-only) permissions.

This creates `token.json` in the project root. It's also gitignored —
never commit it. If the command then prints some tasks (or says you
have none), it worked.

## 4. Set your location and timezone in `.env`

Open `.env` and fill in:

- `LOCATION_NAME`, `LAT`, `LON` — your home city and its coordinates.
  You can get coordinates from any map site: right-click your
  location and copy the latitude/longitude shown.
- `HOME_TIMEZONE` — your IANA timezone name, e.g. `Europe/Paris`,
  `America/New_York`, `Asia/Tokyo`.
- `CALENDAR_ID` — leave as `primary` unless you want a different
  calendar.
- `EMAIL_COUNT` — how many unread emails to include (default 5 is
  fine to start).

## 5. Create a Telegram bot

1. In Telegram, open a chat with **@BotFather**.
2. Send `/newbot` and follow the prompts (pick a name and a username
   ending in `bot`).
3. BotFather replies with a token that looks like
   `123456789:AbCdEf...`. Copy it into `.env` as `TELEGRAM_BOT_TOKEN`.
4. Send your new bot any message (e.g. "hi") so it has a chat to
   reply to — bots can't message you first.
5. Find your chat ID: visit
   `https://api.telegram.org/bot<your-bot-token>/getUpdates` in a
   browser (replace `<your-bot-token>` with the real token), after
   sending the bot a message. Look for `"chat":{"id":...}` in the
   response and copy that number into `.env` as `TELEGRAM_CHAT_ID`.

## 6. Get a Claude Code OAuth token

This lets the automation use your existing Claude subscription instead
of a separate pay-per-token API key.

1. Install the Claude Code CLI if you haven't: see
   [claude.com/claude-code](https://claude.com/claude-code).
2. Run:

   ```powershell
   claude setup-token
   ```

3. Follow the prompts to authorize against your Claude account. Copy
   the resulting token into `.env` as `CLAUDE_CODE_OAUTH_TOKEN`.

## 7. First local test run

```powershell
.venv\Scripts\python.exe -m pytest
```

All tests should pass. Then try the interactive briefing — either
through Claude Code with `/briefing`, or the automated path end to
end:

```powershell
.venv\Scripts\python.exe tools/send_morning_briefing.py .tmp/test_state.json
```

This fetches real data and sends a real Telegram message. If it
works, you'll get the briefing on Telegram within a few seconds. Check
`.tmp/test_state.json` afterward; it should now show today as the
last sent date.

## 8. Push to your own GitHub repo

If you haven't already:

```powershell
git remote add origin https://github.com/<owner>/morning-briefing-bot.git
git push -u origin master
```

Also create the orphan state branch the automation needs:

```powershell
git checkout --orphan briefing-state
git rm -rf .
echo "{}" > briefing_state.json
git add briefing_state.json
git commit -m "Initialize briefing state"
git push -u origin briefing-state
git checkout master
```

## 9. Add GitHub Actions secrets

In your GitHub repo: **Settings > Secrets and variables > Actions >
New repository secret**. Add each of these:

| Secret | Value |
|---|---|
| `LOCATION_NAME` | Same as your `.env` |
| `LAT` | Same as your `.env` |
| `LON` | Same as your `.env` |
| `HOME_TIMEZONE` | Same as your `.env` |
| `TELEGRAM_BOT_TOKEN` | Same as your `.env` |
| `TELEGRAM_CHAT_ID` | Same as your `.env` |
| `CLAUDE_CODE_OAUTH_TOKEN` | Same as your `.env` |
| `GOOGLE_CREDENTIALS_JSON` | The full contents of your local `credentials.json` file |
| `GOOGLE_TOKEN_JSON` | The full contents of your local `token.json` file |

For the last two, open the file locally and paste its entire content
as the secret value.

## 10. Set up the trigger (Google Apps Script)

GitHub's built-in `schedule:` trigger is unreliable on low-activity
repos (see CLAUDE.md for why), so a small Google Apps Script pings the
workflow directly every 15 minutes instead. It runs free under the same
Google account you already use, with no billing account.

1. Create a fine-grained GitHub token: **Settings > Developer
   settings > Fine-grained tokens > Generate new token**. Repository
   access: this repo only. Permissions: **Actions: Read and write**.
2. Go to [script.google.com](https://script.google.com) > **New
   project**. Replace the editor's contents with
   [`scripts/apps_script_trigger.gs`](scripts/apps_script_trigger.gs)
   and save.
3. **Project Settings** (gear icon) > **Script properties** > add:
   - `GITHUB_TOKEN`: the token from step 1
   - `GITHUB_REPO`: `<owner>/<repo>`, e.g. `octocat/morning-briefing-bot`
   - `GITHUB_REF` (optional): branch name, default `master`
4. Back in the editor, pick `installTrigger` in the function dropdown
   and click **Run**. Google asks you to approve the script's access
   (connect to external services, run when you're not present); approve
   it. This creates the 15-minute timer.
5. Pick `pingBriefing` and click **Run** once. It should finish with
   no error, and a new "Morning Briefing" run should appear under
   **Actions** in your repo (it will just SKIP unless it's send time).

The ping never sets `force`, so it always goes through the normal "is
it actually time to send" check; at most one briefing a day is sent.
Failed runs show under **Executions** in Apps Script, and Google emails
you a summary of trigger failures.

## 11. Verify it's live

Wait for the next scheduled ping (or go to **Actions** in your repo
and manually run the "Morning Briefing" workflow with `force` checked
to test immediately). Check the Actions log for the run, and check
Telegram for the message.

Send `help` to your bot on Telegram at any point to see the full list
of commands (pause, resume, change timezone, change send time).

## Troubleshooting

- **"credentials.json not found"** — you skipped step 2/6, or saved
  the file under a different name.
- **Browser doesn't open during consent** — `tools/get_tasks.py` must
  be run on a machine with a browser available; it can't run
  headless for this one-time step.
- **GitHub Action fails at "Write Google OAuth credentials"** — one
  of the `GOOGLE_CREDENTIALS_JSON` / `GOOGLE_TOKEN_JSON` secrets is
  missing or wasn't pasted completely.
- **No Telegram message arrives but the Action succeeds** — double
  check `TELEGRAM_CHAT_ID`; it must be the numeric ID from step 5, not
  your username.
