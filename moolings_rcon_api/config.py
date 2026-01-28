from mcdreforged.api.all import PluginServerInterface, Serializable


class RconConnectionInfo(Serializable):
    host: str = "127.0.0.1"
    port: int = 25575
    password: str = "password"


rcon_info: RconConnectionInfo | None = None


class IgnoreOptions(Serializable):
    mcdr_config: bool = False
    server_properties: bool = False
    plg_config: bool = True


class DefaultConfig(Serializable):
    rcon: RconConnectionInfo = RconConnectionInfo()
    ignore: IgnoreOptions = IgnoreOptions()
    allow_mcdr_private_api: bool = True
    use_asyncrcon_only: bool = False


def get_config(psi: PluginServerInterface) -> DefaultConfig:
    config = psi.load_config_simple(file_name="config.yml", target_class=DefaultConfig)
    assert isinstance(config, DefaultConfig)
    if rcon_info is not None:
        config.rcon = rcon_info  # TODO: will prepare for the support of reading from `server.properties`
    return config  # type: ignore[reportReturnType]


def get_rcon_info(psi: PluginServerInterface):
    pass  # TODO: will support reading from `server.properties`
