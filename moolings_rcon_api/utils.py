from mcdreforged.api.all import PluginServerInterface


def tr(server: PluginServerInterface, tr_key: str, return_str: bool = True, *args):
    plg_self = server.get_self_metadata()
    if tr_key.startswith(f"{plg_self.id}"):
        translation = server.rtr(f"{tr_key}")
    else:
        if tr_key.startswith("#"):
            translation = server.rtr(tr_key.replace("#", ""), *args)
        else:
            translation = server.rtr(f"{plg_self.id}.{tr_key}", *args)
    if return_str:
        tr_to_str: str = str(translation)
        return tr_to_str
    else:
        return translation
