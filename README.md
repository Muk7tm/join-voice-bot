# Join Voice Bot (Discord)

A Discord bot that watches a selected voice channel, plays a welcome audio clip when users join, sends join notifications with a `سحب` (Bring) button, and provides configurable embed-based logs.

## Features
- Monitors one configured voice channel (`/setchannel`).
- Plays a welcome audio file (`voice.mp3` by default) when a user joins that channel.
- Sends join notifications to a configured text channel (`/setnotifychannel`).
- Adds a blue `سحب` button to each join notification.
- Moves the joined user to the clicker's voice channel when `سحب` is used.
- Restricts `سحب` usage to:
  - Administrators (always allowed), and
  - Extra roles configured by admins.
- Uses embed-based notifications and logs from `embed_settings.json`.
- Supports optional log channel routing (`/setlogchannel`).

## Role Access For `سحب`
Admins can manage which roles are allowed to use the `سحب` button:
- `/addbringrole <role>`: allow a role.
- `/removebringrole <role>`: remove a role.
- `/listbringroles`: list allowed roles.
- `/clearbringroles`: clear all extra allowed roles.

Notes:
- Administrators are always allowed, even if no roles are configured.
- Allowed roles are stored in `bring_roles.json`.

## Slash Commands
- `/setchannel <voice channel>`: set monitored voice channel.
- `/setnotifychannel <text channel>`: set join notification channel.
- `/setlogchannel <text channel>`: set log channel.
- `/addbringrole <role>`: allow role to use `سحب`.
- `/removebringrole <role>`: remove role from `سحب` access.
- `/listbringroles`: show allowed `سحب` roles.
- `/clearbringroles`: clear non-admin `سحب` role access.
- `/reloadaudio`: check/reload audio file availability.
- `/togglebot`: enable/disable automatic behavior.
- `/leave`: disconnect bot from voice.
- `/reloadembeds`: reload embed config from `embed_settings.json`.

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env`:
```env
DISCORD_TOKEN=your-bot-token
```

3. Ensure FFmpeg is installed and available in your system `PATH`.

4. Put your welcome audio in the project root (default file: `voice.mp3`), or set `WELCOME_AUDIO_PATH` in your environment.

5. Start the bot:
```bash
python app.py
```

6. In Discord (admin):
- Run `/setchannel`
- Run `/setnotifychannel`
- Optionally run `/setlogchannel`

## Data Files
- `target_channel.txt`: monitored voice channel ID.
- `notify_channel.txt`: join notification text channel ID.
- `log_channel.txt`: log text channel ID.
- `bring_roles.json`: per-guild allowed role IDs for `سحب`.
- `embed_settings.json`: embed styles and message templates.

## Requirements
- Python 3.8+
- FFmpeg in `PATH`

## Security
- Keep `.env` private.
- Never share your bot token.
