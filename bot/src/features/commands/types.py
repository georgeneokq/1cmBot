from typing import TypedDict
from enum import Enum


# Enum for command names
class Command(Enum):
    WALLET = "WALLET"
    SET_CHAIN = "SET_CHAIN"
    SET_SLIPPAGE = "SET_SLIPPAGE"
    SET_TOKEN0 = "SET_BUY_TOKEN"
    SET_TOKEN1 = "SET_SELL_TOKEN"
    SHOW_TOKEN0_CHART = "SHOW_BUY_CHART"
    SHOW_TOKEN1_CHART = "SHOW_SELL_CHART"
    BUY = "BUY"
    SELL = "SELL"


class CommandStage(TypedDict):
    command: Command
    stage: int
