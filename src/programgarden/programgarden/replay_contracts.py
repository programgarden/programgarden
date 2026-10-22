"""Public stub (replay contracts are platform-only)."""
class ContractViolation(Exception):
    pass
def check_contract(*args, **kwargs):
    return None
def check_codenode_ports(*args, **kwargs):
    return None
