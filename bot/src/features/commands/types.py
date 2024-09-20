from typing import TypedDict
from enum import Enum


# Enum for command names
class Command(Enum):
    WALLET = "WALLET"
    SET_CHAIN = "SET_CHAIN"
    SET_SLIPPAGE = "SET_SLIPPAGE"
    SET_BUY_TOKEN = "SET_BUY_TOKEN"
    SET_SELL_TOKEN = "SET_SELL_TOKEN"
    SHOW_BUY_CHART = "SHOW_BUY_CHART"
    SHOW_SELL_CHART = "SHOW_SELL_CHART"
    BUY = "BUY"
    SELL = "SELL"


class CommandStage(TypedDict):
    command: Command
    stage: int
