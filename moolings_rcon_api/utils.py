from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from mcdreforged.api.all import PluginServerInterface, RTextMCDRTranslation

P = ParamSpec("P")
T = TypeVar("T")
condition_error_message = "Condition must be satisfied!"


class ConditionError(RuntimeError):
    pass


def edit_condition_error_message(content: str):
    global condition_error_message
    condition_error_message = content


def execute_if(condition: bool | Callable[[], bool], raise_error: bool = False):
    def decorator(func: Callable[P, T]) -> Callable[P, T | None]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            _condition: bool = condition() if callable(condition) else condition
            if _condition:
                return func(*args, **kwargs)
            else:
                if raise_error:
                    raise ConditionError(condition_error_message)
                return None

        return wrapper

    return decorator


def tr(
    server: PluginServerInterface, tr_key: str, return_str: bool = False, *args
) -> str | RTextMCDRTranslation:
    plg_id = server.get_self_metadata().id
    if tr_key.startswith(f"{plg_id}"):
        translation = server.rtr(f"{tr_key}")
    else:
        if tr_key.startswith("#"):
            translation = server.rtr(tr_key.replace("#", ""), *args)
        else:
            translation = server.rtr(f"{plg_id}.{tr_key}", *args)
    if return_str:
        tr_to_str: str = str(translation)
        return tr_to_str
    else:
        return translation


def tr_to_str(server: PluginServerInterface, tr_key: str, *args) -> str:
    return str(tr(server, tr_key, return_str=True, *args))


def get_server_dir(psi: PluginServerInterface, return_default: bool = True) -> str:
    default_value: str = "server"
    if return_default:
        return psi.get_mcdr_config().get("working_directory", default_value)
    return psi.get_mcdr_config()["working_directory"]
