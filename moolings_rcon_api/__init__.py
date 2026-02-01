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
import moolings_rcon_api.runtime as rt
import moolings_rcon_api.utils as utils
from moolings_rcon_api.config import (
    get_config,
    get_rcon_info_from_mcdr,
)
from moolings_rcon_api.rcon import (
    close_async_rcon_client,
    rcon_get_from_async,
    rcon_get_from_mcdr,
    test_and_connect,
)
from moolings_rcon_api.utils import tr, tr_to_str

builder = SimpleCommandBuilder()
_DEBUG_ASYNC_RCON_CLOSE: bool = False


async def on_load(psi: PluginServerInterface, _):
    psi.logger.info(tr(psi, "on_load.loading"))
    rt.set_psi(psi)
    utils.edit_condition_error_message(tr_to_str(psi, "condition_error_message"))
    psi.logger.info(tr(psi, "on_load.register_command.registering"))
    builder.arg("command", GreedyText)
    builder.register(psi)
    psi.logger.info(tr(psi, "on_load.register_command.registered"))
    psi.logger.info(tr(psi, "on_load.finish"))
    if psi.is_server_startup():
        await on_server_startup(psi)


async def on_unload(psi: PluginServerInterface):
    if rcon_api._RCON_CLIENT is not None:  # type: ignore[reportPrivateUsage]
        await close_async_rcon_client(psi)
        rcon_api._RCON_EXECUTOR.shutdown(wait=True)
        rcon_api._RCON_EXECUTOR = None


async def on_server_startup(psi: PluginServerInterface):
    rt.config = get_config(psi)
    if psi.is_rcon_running() and not rt.config.use_asyncrcon_only:
        psi.logger.info(tr(psi, "on_server_startup.when_use_builtin"))
        rt.config.rcon = get_rcon_info_from_mcdr(psi)
        rt.rcon_api_provider = "mcdr"
    else:
        psi.logger.info(tr(psi, "on_server_startup.when_use_asyncrcon_only"))
        await test_and_connect(psi, rt.config.rcon)
        rt.rcon_api_provider = "asyncrcon"
    psi.logger.info(tr(psi, "on_server_startup.on_config_loaded"))


async def rcon_get(
    psi: PluginServerInterface, cmd: str
) -> Result[Maybe[str], Exception]:
    if rt.rcon_api_provider == "asyncrcon":
        return await rcon_get_from_async(cmd)
    return await rcon_get_from_mcdr(psi, cmd)


@builder.command("!!asyncrcon")
@builder.command("!!asyncrcon <command>")
@builder.command("!!asyncrcon open_connection")
@builder.command("!!asyncrcon close")
@builder.command("!!asyncrcon close --confirm")
async def on_command_asyncrcon(src: CommandSource, ctx: CommandContext):
    psi = src.get_server().psi()
    if not src.has_permission_higher_than(3):
        src.reply(tr(psi, "on_server_startup.on_command.permission_denied"))
        return

    async def on_close():
        global _DEBUG_ASYNC_RCON_CLOSE
        if not _DEBUG_ASYNC_RCON_CLOSE and "--confirm" not in ctx.command:
            src.reply(tr(psi, "on_command.on_debug.on_close_confirm"))
            _DEBUG_ASYNC_RCON_CLOSE = True
        else:
            await rcon_api.close_async_rcon_client(psi)
            _DEBUG_ASYNC_RCON_CLOSE = False
            src.reply(tr(psi, "rcon_api.async_rcon_client_closed"))

    async def on_open_connection():
        if rt.config is None:
            raise RuntimeError(tr(psi, "on_command.on_debug.on_config_empty", True))
        await rcon_api.init_async_rcon_client(psi, rt.config.rcon)
        src.reply(tr(psi, "rcon_api.async_rcon_client_opened"))

    if "close" in ctx.command:
        await on_close()
    elif "open_connection" in ctx.command:
        await on_open_connection()
    else:
        help_message = f"""{tr(psi, "on_command.on_debug.help_message.description")}
{tr(psi, "on_command.on_debug.help_message.valid_usage")}
    !!asyncrcon open_connection
    !!asyncrcon close
    !!asyncrcon close --confirm"""
        src.reply(help_message)


@builder.command("!!rcon <command>")
async def on_rcon_get(src: CommandSource, ctx: CommandContext):
    psi = src.get_server().psi()
    if not src.has_permission_higher_than(3):
        src.reply(tr(psi, "on_server_startup.on_command.permission_denied"))
        return
    command = ctx["command"]
    result = await rcon_get(psi, command)
    match result:
        case Success(Some(content)):
            src.reply(content)
        case Success(_):
            src.reply(tr(psi, "on_server_startup.on_command.no_response"))
        case Failure(e):
            src.reply(tr(psi, "on_server_startup.on_command.on_error", True, e))
