from os import getenv

ALCHEMY_API_KEY = getenv("ALCHEMY_API_KEY", "")
USDC_ADDRESS = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

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
