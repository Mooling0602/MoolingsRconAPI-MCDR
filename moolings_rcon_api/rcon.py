from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError

from asyncrcon import AsyncRCON
from mcdreforged.api.all import PluginServerInterface
from returns.maybe import Maybe, Nothing, Some
from returns.result import Failure, Result, Success, safe

_RCON_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_RCON_CLIENT: AsyncRCON | None = None


class RconError(RuntimeError):
    pass


async def rcon_get_from_mcdr(
    s: PluginServerInterface, cmd: str
) -> Result[Maybe[str], Exception]:
    if not s.is_rcon_running():
        return Failure(RconError("Rcon is not running with MCDR!"))

    @safe
    def on_query() -> Maybe[str]:
        future: Future[str | None] = _RCON_EXECUTOR.submit(s.rcon_query, cmd)

        try:
            raw_result = future.result(timeout=0.5)
        except TimeoutError:
            s.logger.warning(
                "Rcon query timeout, attempting reconnection with private mcdr api..."
            )
            s._mcdr_server.connect_rcon()
            raw_result = future.result(timeout=1.0)

        if raw_result is None or raw_result.strip() == "":
            return Nothing
        return Some(raw_result)

    try:
        loop = s.get_event_loop()
        result = await loop.run_in_executor(_RCON_EXECUTOR, on_query)
        return result
    except Exception as e:
        return Failure(e)


async def init_async_rcon_client(psi: PluginServerInterface):
    global _RCON_CLIENT
    if _RCON_CLIENT is None:
        rcon_address: str = psi.get_mcdr_config()["rcon"]["address"]
        rcon_port: int = psi.get_mcdr_config()["rcon"]["port"]
        rcon_password: str = psi.get_mcdr_config()["rcon"]["password"]
        rcon_host = f"{rcon_address}:{rcon_port}"
        _RCON_CLIENT = AsyncRCON(rcon_host, rcon_password)
        await _RCON_CLIENT.open_connection()
        psi.logger.info("Async rcon client initialized!")


async def close_async_rcon_client(psi: PluginServerInterface):
    global _RCON_CLIENT
    if _RCON_CLIENT is not None:
        _RCON_CLIENT.close()
        psi.logger.info("Async rcon client closed!")


async def rcon_get_from_async(cmd: str) -> Result[Maybe[str], Exception]:
    if _RCON_CLIENT is None:
        return Failure(RconError("Async rcon client is not initialized!"))
    try:
        result = await _RCON_CLIENT.command(cmd)
        if result is None or result.strip() == "":
            return Success(Nothing)
        return Success(Some(result))
    except Exception as e:
        return Failure(e)
