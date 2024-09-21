from os import getenv
from web3 import Web3


def initialise_w3():
	provider = getenv("RPC_PROVIDER")
	assert provider, "Please configure your RPC_PROVIDER"
	w3 = Web3(Web3.HTTPProvider(provider))
	if not w3.is_connected():
		raise Exception("Failed to conenct to your configured RPC_PROVIDER")
	return w3


def execute_transaction(transaction, private_key):
	w3 = initialise_w3()
	signed_tx = w3.eth.account.sign_transaction(transaction, private_key)
	return w3.eth.send_raw_transaction(signed_tx.raw_transaction)


if __name__ == '__main__':
	from oneinch_api import OneInchAPI
	oneinch = OneInchAPI()











"""
What token address should I use if I want to trade ETH or a chain's native asset?
Use the address 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE, this applies to the native asset of the chain, so MATIC on polygon, BNB on BNB chain, AVAX on Avalanche, etc.
"""