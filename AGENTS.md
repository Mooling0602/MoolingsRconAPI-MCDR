**Ignore Issues**
Read AGENTS.IGNORE.md before dealing with the code.

**Project Shape**
- This is a small Python 3.11+ MCDReforged plugin; runtime code lives in `moolings_rcon_api/` and plugin metadata is `mcdreforged.plugin.json`.
- MCDR lifecycle hooks and command registration are in `moolings_rcon_api/__init__.py`; public stable async API is re-exported from `moolings_rcon_api/api.py`.
- `moolings_rcon_api/rcon.py` owns the global async RCON client and single-thread executor; be careful with plugin reload/unload lifecycle.

**Verification**
- Run Python-related commands through project wrappers such as `uv run`; better not use the default `PATH` Python directly.
- Use `ruff format --check` to check the code format.
- Use `ty check moolings_rcon_api/` to check the code syntax.
- Do not do any compile, so less `__pycache__/` will produce.

**Packaging And Metadata**
- Keep the version in `pyproject.toml` and `mcdreforged.plugin.json` synchronized.
- Keep MCDR/Python dependency floors synchronized across `pyproject.toml`, `requirements.txt`, and `mcdreforged.plugin.json` when changing support policy.
- `lang/` is declared as an MCDR resource in `mcdreforged.plugin.json` for i18n as in MCDR plugin package, it's not needed for python packaging or distribution.

**Runtime Gotchas**
- Default config reads RCON settings from the server `server.properties`; code expects keys like `enable-rcon`, `rcon.port`, `rcon.password`, and `server-ip`.
- Do not log full `RconConnectionInfo` unless password handling is intentionally reviewed; it contains the RCON password.
- Translation keys are under `lang/en_us.yml` and `lang/zh_cn.yml`; update both when adding user-visible messages.
