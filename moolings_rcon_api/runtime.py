from typing import Literal

from mcdreforged.api.all import PluginServerInterface

from moolings_rcon_api.config import DefaultConfig

config = DefaultConfig()
rcon_api_provider: Literal["mcdr", "asyncrcon"] = "mcdr"
_PSI: PluginServerInterface | None = None
_module = "moolings_rcon_api"


def set_psi(psi: PluginServerInterface):
    global _PSI
    _PSI = psi
