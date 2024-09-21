import requests
from os import getenv
from time import sleep
from web3 import Web3

class NoAPIKeyError(Exception):
    def __init__(self, message):
        super().__init__(message)


class OneInchAPI:
    def __init__(self, post_delay=1):
        """
        Debounce parameter is a delay in seconds to wait before executing the rest of the code.
        This may be needed in development purposes using a free API key due to the RPS limit.
        For now, each method will be in charge of implementing the debounce.
        """
        self.api_base_url = "https://api.1inch.dev"
        api_key = getenv('ONEINCH_API_KEY')
        if not api_key:
            raise NoAPIKeyError("Set up your ONEINCH_API_KEY to initialise this class!")
        self.headers = {
                "Authorization": f"Bearer {api_key}"
            }
        self.post_delay = post_delay

    def _build_api_url(self, api_name, version_number, chain_id, method_name):
        return f"{self.api_base_url}/{api_name}/v{version_number}/{chain_id}/{method_name}"

    def quoted_swap(self, chain_id, src_token_address, dst_token_address, amount) -> float:
        url = self._build_api_url("swap", 6.0, chain_id, "quote")
        params = {
            "src": src_token_address,
            "dst": dst_token_address,
            "amount": amount
        }
        response = requests.get(url, headers=self.headers, params=params)
        sleep(self.post_delay)
        try:
            return float(response.json().get("dstAmount"))
        except Exception as e:
            print(e)
            print(response)
            print(response.text)
            return 0.0

    def approve_swap_calldata(self, chain_id, token_address, amount):
        url = self._build_api_url("swap", 6.0, chain_id, "approve/transaction")
        params = {
            "tokenAddress": token_address,
            "amount": amount
        }
        response = requests.get(url, headers=self.headers, params=params)
        sleep(self.post_delay)
        try:
            # Clean up tx response to be sent onchain
            calldata = response.json()
            calldata["to"] = Web3.to_checksum_address(calldata["to"])
            calldata["gasPrice"] = int(calldata["gasPrice"])
            calldata["chainId"] = chain_id
            del calldata["value"]
            return calldata
        except Exception as e:
            print(e)
            print(response)
            print(response.text)

    def perform_swap_calldata(self, chain_id, src_token_address, dst_token_address, amount, from_origin, slippage):
        url = self._build_api_url("swap", 6.0, chain_id, "swap")
        params = {
            "src": src_token_address,
            "dst": dst_token_address,
            "amount": amount,
            "from": from_origin,
            "origin": from_origin,
            "slippage": slippage,
            "includeGas": "true",
            "disableEstimate": "false"
        }
        response = requests.get(url, headers=self.headers, params=params)
        sleep(self.post_delay)
        try:
            # Clean up tx response to be sent onchain
            calldata = response.json()
            calldata["tx"]["to"] = Web3.to_checksum_address(calldata["tx"]["to"])
            calldata["tx"]["from"] = Web3.to_checksum_address(calldata["tx"]["from"])
            calldata["tx"]["gasPrice"] = int(calldata["tx"]["gasPrice"])
            calldata["tx"]["chainId"] = chain_id
            del calldata["tx"]["value"]
            return calldata
        except Exception as e:
            print(e)
            print(response)
            print(response.text)

    def get_historical_chart_data(self, chain_id, token0, token1, period="24H"):
        assert period in ["24H", "1W", "1Y", "AllTime"], 'Please select period from ["24H", "1W", "1Y", "AllTime"]'
        url = f"{self.api_base_url}/charts/v1.0/chart/line/{token0}/{token1}/{period}/{chain_id}"
        response = requests.get(url, headers=self.headers)
        sleep(self.post_delay)
        try:
            return response.json()
        except Exception as e:
            print(e)
            print(response)
            print(response.text)

    def search_tokens(self, chain_id, token_query, include_unrated="true"):
        url = self._build_api_url("token", 1.2, chain_id, "search")
        params = {
            "query": token_query,
            "only_positive_rating": include_unrated
        }
        response = requests.get(url, headers=self.headers, params=params)
        sleep(self.post_delay)
        try:
           return response.json()
        except Exception as e:
            print(e)
            print(response)
            print(response.text)

    def get_token_balance(self, chain_id, wallet_address, token_addresses=[]):
        url = self._build_api_url("balance", 1.2, chain_id, "balances")
        url += f"/{wallet_address}"
        if token_addresses:
            response = requests.post(url, json={"tokens": token_addresses}, headers=self.headers)
        else:
            response = requests.get(url, headers=self.headers)
        sleep(self.post_delay)
        try:
            return response.json()
        except Exception as e:
            print(e)
            print(response)
            print(response.text)
    
    def get_token_info(self, chain_id, token_address: str) -> dict:
        url = self._build_api_url("token", 1.2, chain_id, f"custom")
        url += f"/{token_address}"
        response = requests.get(url, headers=self.headers)
        sleep(self.post_delay)
        try:
            return response.json()
        except Exception as e:
            print(e)
            print(response)
            print(response.text)
            return {}


if __name__ == '__main__':
    oneinch = OneInchAPI()
    # print(oneinch.get_token_balance(137, "0xB73f259E3d061e21b8725950d8aEFc8449A64c35"))  # Working
    print(oneinch.get_token_balance(137, "0xB73f259E3d061e21b8725950d8aEFc8449A64c35", ["0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"]))  # Working
    # print(oneinch.search_tokens(137, "XSGD"))  # Working
    # print(oneinch.approve_swap_calldata(137, "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 1000))  # Working
    # print(oneinch.get_historical_chart_data(137, "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "0xDC3326e71D45186F113a2F448984CA0e8D201995"))  # Working
    # print(oneinch.quoted_swap(137, "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "0xDC3326e71D45186F113a2F448984CA0e8D201995", 1000000000))  # Working


"""
const axios = require("axios");

async function httpCall() {

  const url = "https://api.1inch.dev/balance/v1.2/137/balances/{walletAddress}";

  const config = {
      headers: undefined,
      params: {},
      paramsSerializer: {
        indexes: null
      }
  };
       const body = {
  "tokens": [
    "0xdac17f958d2ee523a2206206994597c13d831ec7"
  ]
};

  try {
    const response = await axios.post(url, body, config);
    console.log(response.data);
  } catch (error) {
    console.error(error);
  }
}

"""