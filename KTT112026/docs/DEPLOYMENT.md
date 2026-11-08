# Deployment

## Docker

Build from the project root:

```bash
docker build -t ktt112026 .
docker run --env-file .env ktt112026
```

The Docker image installs FFmpeg at OS level and Python packages from `requirements.txt`.

## Nixpacks

The included `nixpacks.toml` installs Python 3.11 and FFmpeg, installs requirements, then runs `python -m ktt112026`.

## Host environment

Set `DISCORD_TOKEN` and any optional `KTT_*` settings in the deployment provider's secret/environment panel. Keep one active bot process per token unless you intentionally implement sharding. For 24/7 voice presence, ensure the hosting platform does not suspend or frequently restart the process.

## Required Discord permissions

At minimum: View Channel, Connect and Speak in the target voice channel. Enable Message Content Intent in the Developer Portal only if the `.tts` prefix compatibility command is required. Slash commands are the primary interface.
