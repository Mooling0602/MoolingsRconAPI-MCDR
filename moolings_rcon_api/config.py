import json
import os

import javaproperties
from mcdreforged.api.all import PluginServerInterface, Serializable

from moolings_rcon_api.utils import tr


class RconConnectionInfo(Serializable):
    host: str = "127.0.0.1"
    port: int = 25575
    password: str = "password"


class DefaultConfig(Serializable):
    rcon: RconConnectionInfo = RconConnectionInfo()
    allow_mcdr_private_api: bool = True
    use_asyncrcon_only: bool = True


def get_config(psi: PluginServerInterface) -> DefaultConfig:
    config = psi.load_config_simple(file_name="config.yml", target_class=DefaultConfig)
    if not config:
        raise RuntimeError(tr(psi, "on_server_startup.on_load_config_failed", True))
    assert isinstance(config, DefaultConfig)
    return config


def get_rcon_info_from_mcdr(
    psi: PluginServerInterface, sync_to_server: bool = False
) -> RconConnectionInfo:
    _rcon_info = RconConnectionInfo()
    _rcon_info.host = psi.get_mcdr_config()["rcon"]["address"]
    _rcon_info.port = psi.get_mcdr_config()["rcon"]["port"]
    _rcon_info.password = psi.get_mcdr_config()["rcon"]["password"]
    return _rcon_info


def get_rcon_info_from_server(
    psi: PluginServerInterface,
    server_dir: str,
) -> RconConnectionInfo:
    _rcon_info = RconConnectionInfo()
    server_properties: dict | None = None
    file_path: str = os.path.join(server_dir, "server.properties")
    if not os.path.exists(file_path):
        raise FileNotFoundError(tr(psi, "server_properties_not_found", True, file_path))
    with open(file_path, "r") as f:
        cache = f.read()
        server_properties = javaproperties.loads(cache)
    server_ip: str = "127.0.0.1"
    server_get_ip = server_properties["server-ip"]
    mcdr_server_ip = psi.get_server_information().ip
    psi.logger.info(mcdr_server_ip)
    if mcdr_server_ip is not None and mcdr_server_ip != "":
        server_ip = mcdr_server_ip
    elif server_get_ip is not None and server_get_ip != "":
        server_ip = server_get_ip
    _rcon_info.host = server_ip
    _rcon_info.port = int(server_properties["rcon.port"])
    _rcon_info.password = server_properties["rcon.password"]
    return _rcon_info


def check_if_rcon_enabled(
    psi: PluginServerInterface, server_dir: str, do_fix: bool = False
) -> bool:
    server_properties: dict | None = None
    file_path: str = os.path.join(server_dir, "server.properties")
    if not os.path.exists(file_path):
        raise FileNotFoundError(tr(psi, "server_properties_not_found", True, file_path))
    with open(file_path, "r") as f:
        cache = f.read()
        server_properties = javaproperties.loads(cache)
    rcon_enabled: bool = json.loads(server_properties["enable-rcon"])
    if not rcon_enabled:
        psi.logger.info(tr(psi, "check_rcon.do_fix"))
        if do_fix:
            with open(file_path, "w") as f:
                server_properties["enable-rcon"] = "true"
                f.write(javaproperties.dumps(server_properties))
        psi.logger.info(tr(psi, "check_rcon.finish_fix"))
    return rcon_enabled
