from typing import TypedDict
from enum import Enum


# Enum for command names
class Command(Enum):
    WALLET = "WALLET"
    SET_CHAIN = "SET_CHAIN"
    SET_SLIPPAGE = "SET_SLIPPAGE"
    SET_TOKEN0 = "SET_TOKEN0"
    SET_TOKEN1 = "SET_TOKEN1"
    SHOW_CHART = "SHOW_CHART"
    BUY = "BUY"
    SELL = "SELL"
    REFRESH = "REFRESH"


class CommandStage(TypedDict):
    command: Command
    stage: int
