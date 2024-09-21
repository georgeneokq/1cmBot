from os import getenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.exceptions import TransactionNotFound
from time import sleep
from constants import erc20_abi
from util import parse_decimal, format_decimal
from constants import networks

def initialise_w3(rpc):
    provider = rpc
    assert provider, "Please configure your ALCHEMY_API_KEY"
    w3 = Web3(Web3.HTTPProvider(provider))
    if not w3.is_connected():
        raise Exception("Failed to conenct to your configured RPC_PROVIDER")
    return w3


def execute_transaction(rpc, transaction, private_key):
    w3 = initialise_w3(rpc)
    account = w3.eth.account.from_key(private_key)

    # Estimate Gas
    transaction = {**transaction, "from":account.address, "nonce": w3.eth.get_transaction_count(str(account.address))}
    gas = w3.eth.estimate_gas(transaction)
    transaction = {
        **transaction,
        "nonce": w3.eth.get_transaction_count(str(account.address)),
        "gas": gas,
    }
    signed_tx = w3.eth.account.sign_transaction(transaction, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()
    for i in range(60):
        try:
            print(tx_receipt := w3.eth.get_transaction_receipt(tx_hash))
            print(tx_receipt.status)
            print(tx_receipt["status"])
            return tx_receipt.status
        except TransactionNotFound:
            print("tx not found onchain, waiting")
            sleep(1)
        except KeyboardInterrupt:
            print("quitting retries")
            return 0


def withdraw_tokens(rpc, chain_id, token_address, to_address, private_key, amount=0):
    w3 = initialise_w3(rpc)
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    oneinch = OneInchAPI()
    token_info = oneinch.get_token_info(chain_id, token_address)
    token_decimals = token_info["decimals"]
    account = w3.eth.account.from_key(private_key)
    token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
    if amount == 0:
        amount = token_contract.functions.balanceOf(account.address).call()
    else:
        amount = format_decimals(amount, token_decimals)
    # Get the nonce (transaction count) for the sending account
    nonce = w3.eth.get_transaction_count(account.address)
    transaction = token_contract.functions.transfer(
            to_address,
            amount
        ).build_transaction({
            "from": account.address,
            "nonce": nonce
    })
    print(transaction)
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    for i in range(60):
        try:
            print(tx_receipt := w3.eth.get_transaction_receipt(tx_hash))
            print(tx_receipt.status)
            print(tx_receipt["status"])
            return tx_receipt.status
        except TransactionNotFound:
            print("tx not found onchain, waiting")
            sleep(1)
        except KeyboardInterrupt:
            print("quitting retries")
            return 0




if __name__ == '__main__':
    from oneinch_api import OneInchAPI
    from util import parse_decimal, format_decimal
    oneinch = OneInchAPI()
    rpc = networks[137]["rpc"]
    withdraw_tokens(rpc, 137, "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "0xB73f259E3d061e21b8725950d8aEFc8449A64c35", getenv("PK"))
    # Example 1: Swapping 10cents USD to XSGD on polygon network
    # chain_id = 137
    # Find USDC and XSGD (simulate user searching using the search token function)
    # usdcoins = oneinch.search_tokens(chain_id, "USD Coin")
    # selected_usdc = usdcoins[1]["address"]     # (user selects option 2, get address of index 1)
    # sleep(2)
    # sgdcoins = oneinch.search_tokens(chain_id, "XSGD")
    # sleep(2)
    # selected_sgd = sgdcoins[0]["address"]  # (user selects option 1, get address of index 0)
    # print("selected:", selected_sgd, selected_usdc)
    # # Approve USDC for swap
    # calldata = oneinch.approve_swap_calldata(chain_id, selected_usdc, format_decimal(0.1, 6))
    # # Add nonce and gas to calldata
    # success = execute_transaction(calldata, getenv("PK"))
    # success = True
    # if success:
    #   w3 = initialise_w3()
    #   account = w3.eth.account.from_key(getenv("PK"))
    #   calldata = oneinch.perform_swap_calldata(
    #       chain_id,
    #       selected_usdc,
    #       selected_sgd,
    #       format_decimal(0.1, 6),
    #       account.address,
    #       1
    #   )
    #   print(calldata)
    #   receipt = execute_transaction(calldata["tx"], getenv("PK"))





"""
What token address should I use if I want to trade ETH or a chain's native asset?
Use the address 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE, this applies to the native asset of the chain, so MATIC on polygon, BNB on BNB chain, AVAX on Avalanche, etc.
"""