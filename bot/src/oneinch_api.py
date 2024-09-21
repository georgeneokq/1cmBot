from os import getenv
import requests


class NoAPIKeyError(Exception):
    def __init__(self, message):
        super().__init__(message)


class OneInchAPI:
    def __init__(self):
        self.api_base_url = "https://api.1inch.dev"
        api_key = getenv('ONEINCH_API_KEY')
        if not api_key:
            raise NoAPIKeyError("Set up your API key to initialise this class!")
        self.headers = {
                "Authorization": f"Bearer {api_key}"
            }
        

    def _build_api_url(self, api_name, version_number, chain_id, method_name):
        os.path
        return f"{self.api_base_url}/{api_name}/v{version_number}/{chain_id}/{method_name}"


    def approve_swap_calldata(self, chain_id, token_address, amount):
        url = self._build_api_url("swap", 6.0, chain_id, "approve/transaction")
        params = {
            "tokenAddress": token_address,
            "amount": amount
        }

        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

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
        return response.json()

    def get_historical_chart_data(self, chain_id, token0, token1, period="24H"):
        assert period in ["24H", "1W", "1Y", "AllTime"], 'Please select period from ["24H", "1W", "1Y", "AllTime"]'
        url = f"{self.api_base_url}/charts/v1.0/chart/line/{token0}/{token1}/{period}/{chain_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def search_tokens(self, chain_id, token_query, include_unrated="true"):
        url = self._build_api_url("token", 1.2, chain_id, "search")
        params = {
            "query": token_query,
            "only_positive_rating": include_unrated
        }
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

    def get_token_balance(self, chain_id, wallet_address):
        url = self._build_api_url("balance", 1.2, chain_id, "balances")
        url += f"/{wallet_address}"
        response = requests.get(url, headers=self.headers)
        return response.json()



if __name__ == '__main__':
    oneinch = OneInchAPI()
    # print(oneinch.get_token_balance(137, "0xB73f259E3d061e21b8725950d8aEFc8449A64c35"))  # Working
    # print(oneinch.search_tokens(137, "XSGD"))  # Working
    # print(oneinch.approve_swap_calldata(137, "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 1000))  # Working
    # print(oneinch.get_historical_chart_data(137, "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "0xDC3326e71D45186F113a2F448984CA0e8D201995"))  # Working
