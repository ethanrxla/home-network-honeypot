# Cowrie overlay — SSH honeypot

This isn't a full Cowrie install, just the pieces layered on top of stock
[Cowrie](https://github.com/cowrie/cowrie) for this project.

## Setup

```bash
git clone https://github.com/cowrie/cowrie.git
cd cowrie
python -m venv cowrie-env
source cowrie-env/bin/activate
pip install --upgrade -r requirements.txt

# drop in the overlay from this repo
cp -r ../cowrie/src/cowrie/commands/sensor_agent src/cowrie/commands/
cp ../cowrie/src/cowrie/commands/sensor_agent_hook.py src/cowrie/commands/
cp ../cowrie/etc/cowrie.cfg etc/cowrie.cfg
cp ../cowrie/etc/userdb.txt etc/userdb.txt
```

Then register the hook by adding `"sensor_agent_hook",` as the **last** entry
in `command_modules` in `src/cowrie/commands/__init__.py` — it needs to be
last so it wins the `commands.update()` merge and overrides the built-in
emulated handlers for the commands it covers.

`etc/cowrie.cfg`'s `[output_discord]` section has a placeholder
`url = https://discord.com/api/webhooks/id/token` — swap in your own webhook
URL, or delete/comment the section to skip Discord alerts.

## What `sensor_agent/` does

Replaces Cowrie's static command emulation with a tiered dispatcher
(`dispatch.py`): known commands hit a fast static lookup, unknown ones fall
through to stateful shell emulation (`node_runtime.py`, `shell_layer.py`,
`node_context.py`), and anything still unhandled escalates to an LLM
(`edge_inference.py` / `upstream_sync.py`, reads AWS credentials from the
environment — never hardcoded) to generate a plausible response. This is
independent of the wifi-side `collector/`; it only affects what an attacker
sees after connecting to Cowrie's fake SSH server on port 2222.

`telemetry_cache.py` holds the fake bait content (decoy `/etc/shadow`
hashes, fake `wp-config.php`, fake AWS credentials file, etc.) served up if
an attacker goes looking for files on the fake filesystem — all fabricated,
not real credentials.
