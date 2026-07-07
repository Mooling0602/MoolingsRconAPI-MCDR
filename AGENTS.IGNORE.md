# Ignore Lists for Agents

Here are the issues you should ignore and avoid any changes for.

## Issue title template

Issue content template.

Do not remove this part, and follow the format then add new issues to the end of the file.

## `lang/` excluded from Python package builds

Ignore reports that `lang/` is excluded by Python packaging config while declared as an MCDReforged plugin resource. This plugin only runs inside MCDReforged, where resources are declared in `mcdreforged.plugin.json`; when imported into other projects as a dependency via UV, the translation files are not needed.

## Relaxed dependency versions in `requirements.txt`

Ignore reports that `requirements.txt` should mirror dependency lower bounds from `pyproject.toml`. The relaxed `requirements.txt` constraints are intentional so PIM, MCDR's built-in plugin manager, can install dependencies more easily; versions in `pyproject.toml` are managed by UV and are not necessarily the actual required minimums.
