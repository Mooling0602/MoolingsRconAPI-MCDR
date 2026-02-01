from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError

from asyncrcon import AsyncRCON, AuthenticationException
from mcdreforged.api.all import PluginServerInterface
from returns.maybe import Maybe, Nothing, Some
from returns.result import Failure, Result, Success, safe

import moolings_rcon_api.runtime as rt
from moolings_rcon_api.config import (
    RconConnectionInfo,
    check_if_rcon_enabled,
    get_rcon_info_from_mcdr,
    get_rcon_info_from_server,
)
from moolings_rcon_api.utils import get_server_dir, tr

_RCON_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_RCON_CLIENT: AsyncRCON | None = None


class RconError(RuntimeError):
    pass


async def rcon_get_from_mcdr(
    psi: PluginServerInterface, cmd: str
) -> Result[Maybe[str], Exception]:
    if not psi.is_rcon_running():
        return Failure(
            RconError(tr(psi, f"#{rt._module}.rcon_api.on_error.built_in_down", True))
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
        return Failure(
            RconError(tr(psi, f"#{rt._module}.rcon_api.on_error.built_in_down", True))
        )

    @safe
    def on_query() -> Maybe[str]:
        future: Future[str | None] = _RCON_EXECUTOR.submit(psi.rcon_query, cmd)

        try:
            raw_result = future.result(timeout=0.5)
        except TimeoutError:
            psi.logger.warning(tr(psi, f"#{rt._module}.rcon_api.warn_built_in_timeout"))
            psi._mcdr_server.connect_rcon()
            raw_result = future.result(timeout=1.0)

        if raw_result is None or raw_result.strip() == "":
            return Nothing
        return Some(raw_result)

    return on_query()


async def detect_valid_rcon_info(
    psi: PluginServerInterface, rcon_info_list: list[RconConnectionInfo]
) -> bool:
    for i in rcon_info_list:
        try:
            await init_async_rcon_client(psi, i)
            return True
        except AuthenticationException:
            pass
        except Exception:
            return False
    return False


async def test_and_connect(psi: PluginServerInterface, rcon_info: RconConnectionInfo):
    try:
        await init_async_rcon_client(psi, rcon_info)
    except ConnectionRefusedError:
        rcon_enabled = check_if_rcon_enabled(psi, get_server_dir(psi))
        if rcon_enabled:
            psi.logger.error(tr(psi, f"#{rt._module}.rcon_api.on_connection_refused"))
        else:
            psi.logger.error(tr(psi, f"#{rt._module}.rcon_api.on_disabled_in_server"))
    except AuthenticationException:
        detection = await detect_valid_rcon_info(
            psi,
            [
                get_rcon_info_from_mcdr(psi),
                get_rcon_info_from_server(psi, get_server_dir(psi)),
            ],
        )
        if not detection:
            psi.logger.info(tr(psi, f"#{rt._module}.rcon_api.async_rcon_auth_failed"))
    except Exception as e:
        psi.logger.error(
            tr(psi, f"#{rt._module}.rcon_api.async_rcon_client_error", False, e)
        )


async def init_async_rcon_client(
    psi: PluginServerInterface, rcon_info: RconConnectionInfo
):
    global _RCON_CLIENT
    if _RCON_CLIENT is None:
        rcon_address: str = rcon_info.host
        rcon_port: int = rcon_info.port
        rcon_password: str = rcon_info.password
        rcon_host = f"{rcon_address}:{rcon_port}"
        _RCON_CLIENT = AsyncRCON(rcon_host, rcon_password)
        try:
            await _RCON_CLIENT.open_connection()
        except Exception as e:
            _RCON_CLIENT = None
            raise e
        psi.logger.info(
            tr(psi, f"#{rt._module}.rcon_api.async_rcon_client_initialized")
        )


async def close_async_rcon_client(psi: PluginServerInterface):
    global _RCON_CLIENT
    if _RCON_CLIENT is not None:
        _RCON_CLIENT.close()
        psi.logger.info(tr(psi, f"#{rt._module}.rcon_api.async_rcon_client_closed"))


async def rcon_get_from_async(cmd: str) -> Result[Maybe[str], Exception]:
    if _RCON_CLIENT is None:
        if not rt._PSI:
            return Failure(RconError("Async Rcon client has not been initialized yet!"))
        return Failure(RconError(tr(rt._PSI, "rcon_api.on_error.async_down", True)))
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
