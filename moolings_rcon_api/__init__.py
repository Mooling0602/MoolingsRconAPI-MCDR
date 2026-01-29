from mcdreforged.api.all import (
    CommandContext,
    CommandSource,
    GreedyText,
    PluginServerInterface,
    SimpleCommandBuilder,
)
from returns.maybe import Maybe, Some
from returns.result import Failure, Result, Success

import moolings_rcon_api.rcon as rcon_api
from moolings_rcon_api.config import DefaultConfig, get_config
from moolings_rcon_api.rcon import (
    close_async_rcon_client,
    init_async_rcon_client,
    rcon_get_from_async,
    rcon_get_from_mcdr,
)

config: DefaultConfig | None = None
builder = SimpleCommandBuilder()


async def on_load(psi: PluginServerInterface, _):
    psi.logger.info("Loading Mooling's Rcon API...")
    psi.logger.info("Registering commands to MCDR...")
    builder.arg("command", GreedyText)
    builder.register(psi)
    psi.logger.info("Commands registered.")
    psi.logger.info("Rcon connection info will be loaded after server startup.")
    if psi.is_server_startup():
        await on_server_startup(psi)


async def on_unload(psi: PluginServerInterface):
    if rcon_api._RCON_CLIENT is not None:  # type: ignore[reportPrivateUsage]
        await close_async_rcon_client(psi)


async def on_server_startup(psi: PluginServerInterface):
    global config
    config = get_config(psi)
    if config.use_asyncrcon_only:
        psi.logger.info(
            "Will try import and init rcon client from asyncrcon package first."
        )
        await init_async_rcon_client(psi)
        return
    if psi.is_rcon_running():
        psi.logger.info("Will try using built-in rcon client in MCDR first.")
    psi.logger.info("Configurations loaded successfully.")


async def rcon_get(
    psi: PluginServerInterface, cmd: str
) -> Result[Maybe[str], Exception]:
    if config is not None and config.use_asyncrcon_only:
        return await rcon_get_from_async(cmd)
    return await rcon_get_from_mcdr(psi, cmd)


@builder.command("!!rcon <command>")
async def on_rcon_get(src: CommandSource, ctx: CommandContext):
    if not src.has_permission_higher_than(3):
        src.reply("Permission denied!")
        return
    psi = src.get_server().psi()
    command = ctx["command"]
    result = await rcon_get(psi, command)
    match result:
        case Success(Some(content)):
            src.reply(content)
        case Success(_):
            src.reply("Command executed, no response.")
        case Failure(e):
            src.reply(f"Error: {e}")
