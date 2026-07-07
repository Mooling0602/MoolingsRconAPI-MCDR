import asyncio
from concurrent.futures import ThreadPoolExecutor

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
_RCON_CLIENT_LOCK = asyncio.Lock()


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


async def test_and_connect(
    psi: PluginServerInterface, rcon_info: RconConnectionInfo
) -> bool:
    rcon_enabled = check_if_rcon_enabled(
        psi, get_server_dir(psi), rt.config.allow_edit_server_prop
    )
    if not rcon_enabled:
        psi.logger.error(tr(psi, f"#{rt._module}.rcon_api.on_disabled_in_server"))
        return False
    try:
        await init_async_rcon_client(psi, rcon_info)
        return True
    except ConnectionRefusedError:
        psi.logger.error(tr(psi, f"#{rt._module}.rcon_api.on_connection_refused"))
        return False
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
        return detection
    except Exception as e:
        psi.logger.error(
            tr(psi, f"#{rt._module}.rcon_api.async_rcon_client_error", False, e)
        )
        if rcon_info.password == "":
            psi.logger.warning(
                tr(psi, f"#{rt._module}.rcon_api.async_rcon_no_passwd_warning")
            )
        return False


async def init_async_rcon_client(
    psi: PluginServerInterface, rcon_info: RconConnectionInfo
):
    global _RCON_CLIENT
    async with _RCON_CLIENT_LOCK:
        if _RCON_CLIENT is not None:
            _RCON_CLIENT.close()
            _RCON_CLIENT = None
        rcon_host = f"{rcon_info.host}:{rcon_info.port}"
        client = AsyncRCON(rcon_host, rcon_info.password)
        try:
            await client.open_connection()
        except Exception:
            raise
        _RCON_CLIENT = client
    psi.logger.info(tr(psi, f"#{rt._module}.rcon_api.async_rcon_client_initialized"))


async def close_async_rcon_client(psi: PluginServerInterface):
    global _RCON_CLIENT
    async with _RCON_CLIENT_LOCK:
        if _RCON_CLIENT is not None:
            _RCON_CLIENT.close()
            _RCON_CLIENT = None
            psi.logger.info(tr(psi, f"#{rt._module}.rcon_api.async_rcon_client_closed"))


async def rcon_get_from_async(cmd: str) -> Result[Maybe[str], Exception]:
    if _RCON_CLIENT is None:
        if not rt._PSI:
            return Failure(RconError("Async Rcon client has not been initialized yet!"))
        return Failure(RconError(tr(rt._PSI, "rcon_api.on_error.async_down", True)))

    async def on_query(client: AsyncRCON):
        result = await client.command(cmd)
        if result is None or result.strip() == "":
            return Success(Nothing)
        return Success(Some(result))

    try:
        async with _RCON_CLIENT_LOCK:
            client = _RCON_CLIENT
            if client is None:
                return Failure(
                    RconError(tr(rt._PSI, "rcon_api.on_error.async_down", True))
                )
            return await on_query(client)
    except ConnectionResetError:
        async with _RCON_CLIENT_LOCK:
            client = _RCON_CLIENT
            if client is None:
                return Failure(
                    RconError(tr(rt._PSI, "rcon_api.on_error.async_down", True))
                )
            await client.open_connection()
            return await on_query(client)
    except Exception as e:
        return Failure(e)


def shutdown_rcon_executor():
    global _RCON_EXECUTOR
    _RCON_EXECUTOR.shutdown(wait=True)
    _RCON_EXECUTOR = ThreadPoolExecutor(max_workers=1)
