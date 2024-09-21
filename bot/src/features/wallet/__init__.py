from os import getenv
from eth_account import Account

def get_wallet_details(derivation_path_int: int, master_key: str | None = None):
    """
    Wallet address calculated from derivation path.
    Show balances of all tokens tied to this wallet.
    Show USD equivalent total of all tokens.
    """
    if not master_key:
        master_key = getenv('DERIVATION_MASTER_KEY')
    derivation_path_str = f"m/0'/{derivation_path_int}"
    account = Account.from_mnemonic(master_key, derivation_path_str)
    
    return {
        "address": account.address
    }
