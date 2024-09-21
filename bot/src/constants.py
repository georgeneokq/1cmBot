from os import getenv

ALCHEMY_API_KEY = getenv("ALCHEMY_API_KEY", "")
USDC_ADDRESS = "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359"

# Map chain ID to more info
networks = {
    137: {
        "name": "Polygon",
        "rpc": f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    },
    8453: {
        "name": "Base",
        "rpc": f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    }
}

# erc20_abi = [
#     {
#         "constant": False,
#         "inputs": [
#             {"name": "to", "type": "address"},
#             {"name": "value", "type": "uint256"}
#         ],
#         "name": "transfer",
#         "outputs": [{"name": "", "type": "bool"}],
#         "type": "function"
#     }
# ]

erc20_abi = [
      {
        "constant": "false",
        "inputs": [
            {
                "name": "_to",
                "type": "address"
            },
            {
                "name": "_value",
                "type": "uint256"
            }
        ],
        "name": "transfer",
        "outputs": [
            {
                "name": "",
                "type": "bool"
            }
        ],
        "payable": "false",
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": "true",
        "inputs": [
            {
                "name": "_owner",
                "type": "address"
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "name": "balance",
                "type": "uint256"
            }
        ],
        "payable": "false",
        "stateMutability": "view",
        "type": "function"
    }
]
