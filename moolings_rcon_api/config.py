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
    allow_edit_server_prop: bool = False
    allow_mcdr_private_api: bool = True
    use_asyncrcon_only: bool = True
    read_rcon_from_server_prop: bool = True


def get_config(psi: PluginServerInterface) -> DefaultConfig:
    config = psi.load_config_simple(file_name="config.yml", target_class=DefaultConfig)
    if not config:
        raise RuntimeError(tr(psi, "on_server_startup.on_load_config_failed", True))
    assert isinstance(config, DefaultConfig)
    return config


def get_rcon_info_from_mcdr(
    psi: PluginServerInterface,
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
    server_get_ip = server_properties.get("server-ip")
    mcdr_server_ip = psi.get_server_information().ip
    if mcdr_server_ip is not None and mcdr_server_ip != "":
        server_ip = mcdr_server_ip
    elif server_get_ip is not None and server_get_ip != "":
        server_ip = server_get_ip
    rcon_port = server_properties.get("rcon.port")
    rcon_password = server_properties.get("rcon.password")
    if rcon_port is None or rcon_password is None:
        missing_keys = [
            key
            for key, value in {
                "rcon.port": rcon_port,
                "rcon.password": rcon_password,
            }.items()
            if value is None
        ]
        raise KeyError(
            tr(psi, "server_properties_missing_key", True, ", ".join(missing_keys))
        )
    _rcon_info.host = server_ip
    _rcon_info.port = int(rcon_port)
    _rcon_info.password = rcon_password
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
    enable_rcon = server_properties.get("enable-rcon")
    if enable_rcon is None:
        raise KeyError(tr(psi, "server_properties_missing_key", True, "enable-rcon"))
    rcon_enabled: bool = json.loads(enable_rcon)
    if not rcon_enabled:
        if do_fix:
            psi.logger.info(tr(psi, "check_rcon.do_fix"))
            with open(file_path, "w") as f:
                server_properties["enable-rcon"] = "true"
                f.write(javaproperties.dumps(server_properties))
            rcon_enabled = True
        else:
            psi.logger.info(tr(psi, "check_rcon.need_edit_config"))
        psi.logger.info(tr(psi, "check_rcon.finish_fix"))
    return rcon_enabled
