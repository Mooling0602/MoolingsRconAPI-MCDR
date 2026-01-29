from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError

from asyncrcon import AsyncRCON
from mcdreforged.api.all import PluginServerInterface
from returns.maybe import Maybe, Nothing, Some
from returns.result import Failure, Result, Success, safe

from moolings_rcon_api.utils import tr

_RCON_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_RCON_CLIENT: AsyncRCON | None = None
_PSI: PluginServerInterface | None = None


def set_psi(psi: PluginServerInterface):
    global _PSI
    _PSI = psi


class RconError(RuntimeError):
    pass


async def rcon_get_from_mcdr(
    psi: PluginServerInterface, cmd: str
) -> Result[Maybe[str], Exception]:
    if not psi.is_rcon_running():
        if _PSI is not None:
            return Failure(RconError(tr(_PSI, "rcon_api.on_error.built_in_down", True)))
        else:
            return Failure(
                RconError(
                    tr(psi, "moolings_rcon_api.rcon_api.on_error.built_in_down", True)
                )
            )

    @safe
    def on_query() -> Maybe[str]:
        raw_result = psi.rcon_query(cmd)

        if raw_result is None or raw_result.strip() == "":
            return Nothing
        return Some(raw_result)

    try:
        loop = psi.get_event_loop()
        result = await loop.run_in_executor(_RCON_EXECUTOR, on_query)
        return result
    except Exception as e:
        return Failure(e)


def rcon_get_from_mcdr_non_async(
    psi: PluginServerInterface, cmd: str
) -> Result[Maybe[str], Exception]:
    if not psi.is_rcon_running():
        if _PSI is not None:
            return Failure(RconError(tr(_PSI, "rcon_api.on_error.built_in_down", True)))
        else:
            return Failure(
                RconError(
                    tr(psi, "moolings_rcon_api.rcon_api.on_error.built_in_down", True)
                )
            )

    @safe
    def on_query() -> Maybe[str]:
        future: Future[str | None] = _RCON_EXECUTOR.submit(psi.rcon_query, cmd)

        try:
            raw_result = future.result(timeout=0.5)
        except TimeoutError:
            if _PSI is not None:
                _PSI.logger.warning(tr(_PSI, "rcon_api.warn_built_in_timeout"))
            else:
                psi.logger.warning(
                    tr(psi, "moolings_rcon_api.rcon_api.warn_built_in_timeout")
                )
            psi._mcdr_server.connect_rcon()
            raw_result = future.result(timeout=1.0)

        if raw_result is None or raw_result.strip() == "":
            return Nothing
        return Some(raw_result)

    return on_query()


async def init_async_rcon_client(psi: PluginServerInterface):
    global _RCON_CLIENT
    if _RCON_CLIENT is None:
        rcon_address: str = psi.get_mcdr_config()["rcon"]["address"]
        rcon_port: int = psi.get_mcdr_config()["rcon"]["port"]
        rcon_password: str = psi.get_mcdr_config()["rcon"]["password"]
        rcon_host = f"{rcon_address}:{rcon_port}"
        _RCON_CLIENT = AsyncRCON(rcon_host, rcon_password)
        await _RCON_CLIENT.open_connection()
        if _PSI is not None:
            _PSI.logger.info(tr(_PSI, "rcon_api.async_rcon_client_initialized"))
        else:
            psi.logger.info(
                tr(psi, "moolings_rcon_api.rcon_api.async_rcon_client_initialized")
            )


async def close_async_rcon_client(psi: PluginServerInterface):
    global _RCON_CLIENT
    if _RCON_CLIENT is not None:
        _RCON_CLIENT.close()
        if _PSI is not None:
            _PSI.logger.info(tr(_PSI, "rcon_api.async_rcon_client_closed"))
        else:
            psi.logger.info(
                tr(psi, "moolings_rcon_api.rcon_api.async_rcon_client_closed")
            )


async def rcon_get_from_async(cmd: str) -> Result[Maybe[str], Exception]:
    if _RCON_CLIENT is None:
        if not _PSI:
            return Failure(RconError("Async Rcon client has not been initialized yet!"))
        return Failure(RconError(tr(_PSI, "rcon_api.on_error.async_down", True)))
    client = _RCON_CLIENT

    async def on_query():
        result = await client.command(cmd)
        if result is None or result.strip() == "":
            return Success(Nothing)
        return Success(Some(result))

    try:
        return await on_query()
    except ConnectionResetError:
        await client.open_connection()
        return await on_query()
    except Exception as e:
        return Failure(e)
