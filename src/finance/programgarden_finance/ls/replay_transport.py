"""Public stub: replay transport is platform-only; live HTTP is always used."""
def active_transport():
    return None
replay_client = None
def answer_request(*args, **kwargs):
    raise RuntimeError("replay transport is not available in the open-source build")
