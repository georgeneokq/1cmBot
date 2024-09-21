from os import getenv

ALCHEMY_API_KEY = getenv("ALCHEMY_API_KEY", "")

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
