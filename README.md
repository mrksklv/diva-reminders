# Diva Reminders 🌸

A small [Telegram Serverless](https://core.telegram.org/bots/serverless) bot that
tracks posts in one configured public channel.

- New posts notify the configured recipients.
- Albums produce one immediate notification linking to the first received item.
- Every incoming message gets a reply with the latest post's age.
- At 22:00, reminders warn when tomorrow is the last day, then when two hours
  remain on the last day. At midnight afterward, the streak is lost.
  These deadlines use calendar dates in the configured timezone.

## Configure

The repository can be public. Store all real settings in GitHub Actions secrets,
under **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
| --- | --- |
| `BOT_CONFIG` | JSON matching `config.example.json`, with your channel, emoji, recipients, timezone, and streak length |
| `TGCLOUD_TOKEN` | Serverless CLI access token from BotFather, not the bot API token |

Copy `config.example.json`, replace its example values, and paste the JSON as
`BOT_CONFIG`. Use a public `@username` and a single emoji (plain Unicode or Telegram's
`<tg-emoji emoji-id="…">…</tg-emoji>` HTML). Do not commit your real
configuration. Sending the bot a message does not subscribe the sender. Each
configured recipient must message the bot first. Add the bot to the channel as
an administrator.

`scripts/configure.js` generates the ignored `tgcloud/lib/config.js` on the runner
before upload. Telegram's runtime cannot read GitHub environment variables, so
the configuration is uploaded as a backend module. The Bot API is authenticated
by Telegram; this project does not need the bot API token. Individual configuration
values are masked in Actions logs, and send errors omit recipient IDs and raw
error details. Logs and workflow definitions in a public repository remain public.
The bot's replies still show the channel username and notification emoji.

`initialLastPostAt` optionally seeds the last post using an ISO timestamp with a
UTC offset. To move Python state, copy `.state.json`'s `last_post_at` and `sent`
into `initialLastPostAt` and `initialSent` before first use. Otherwise leave the
baseline `null` and wait for a new post. Telegram does not replay channel history.
Changing the baseline later does not overwrite stored state.

## Deploy through GitHub Actions

1. Put this project at the root of the public repository on its default branch.
2. Stop the old Python bot before cutover. Enable Serverless in BotFather and get
   **CLI Access → Access token** (`app<id>:<secret>`).
3. Add both repository secrets above and enable GitHub Actions.
4. Open **Actions → Check reminders → Run workflow**, choose **deploy**, and run.

The workflow generates configuration, deploys the schema, applies additive
migrations with `--safe`, deploys the bot, and syncs the webhook. It does not
automatically deploy on commits or scheduled runs. Destructive/manual migrations
are not automatically applied. After changing `BOT_CONFIG`, run **deploy** again
so Telegram's handlers use the new settings too.

For optional local commands, use Node.js 22.13 or newer, run `npm ci`, and supply
`BOT_CONFIG` in the environment. `npm run configure` generates the runtime module;
`npm run deploy` and `npm run check-reminders` generate it automatically. Authenticate
with `npx tgcloud login` or set `TGCLOUD_TOKEN`. Never commit the generated module.
The previous Python version and its configuration examples are under `legacy/`.

## Schedule

The workflow in `.github/workflows/reminders.yml` checks daily at **22:00 and
midnight Moscow time** (`0 19,21 * * *` UTC). Put this project at a GitHub
repository's root on its default branch, configure the two secrets, and after
deployment run **Actions → Check reminders → Run workflow → check** to verify.

GitHub runs `npm run check-reminders`, executing the checked-out code on Telegram.
Keep the default branch synchronized with deployed code. If you change the
timezone in `BOT_CONFIG`, change the schedule too. This command sends real notifications.

GitHub schedules can run late or be skipped; public repositories' schedules can
be disabled after 60 days of inactivity. See [GitHub's scheduling docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
Missed close/final windows are skipped. Reminder checks also run after handled
messages and channel posts.

## Storage and limits

`channel_state` stores the latest post and three reminder flags. `albums` stores
album IDs so separate invocations notify once per album.
Newer posts reset the reminder flags; old updates cannot rewind the latest post.

Sends are best effort: failures are logged and are not queued or retried. Reminder
flags are claimed before sending to prevent concurrent duplicate checks; a crash
after claiming can skip that reminder. An interrupted album is not recovered.

Telegram's runtime has no `setTimeout`; albums notify immediately instead of
waiting for all items. Timezone support has been verified on Telegram.
There is no automated test suite in the project.
