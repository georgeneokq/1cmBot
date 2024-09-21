from os import getenv
from typing import Callable, TypedDict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from features.database import get_connection
from eth_account import Account
from features.database.user import get_user, add_user
from wallet import withdraw_tokens, execute_transaction, get_wallet_details
from features.commands.types import Command
from cache.user import (
    get_user_current_stage,
    set_user_current_stage,
    unset_user_current_stage,
)
from oneinch_api import OneInchAPI
from charts import generate_chart
from constants import networks
from util import parse_decimal, format_decimal

Account.enable_unaudited_hdwallet_features()


class WithdrawInfo(TypedDict):
    withdraw_wallet_address: str
    withdraw_token_address: str
    withdraw_amount: float


# Stores withdrawal data input by the user
# Map user id to withdrawal info
withdrawal: dict[int, WithdrawInfo] = {}


# Define the main menu keyboard layout
def main_menu_keyboard(user: dict):
    """
    Args:
        user (dict): Result from get_user
    """
    buttons: list[list[InlineKeyboardButton]] = []

    # Get the chain name
    chain_id = user.get("chain_id", -1)
    chain_info = networks.get(chain_id)
    chain_name = chain_info["name"] if chain_info else chain_id

    # Populate current configuration into button text
    if chain_name:
        buttons.append(
            [InlineKeyboardButton("Withdraw", callback_data=Command.WITHDRAW.value)]
        )

    slippage = user["slippage"]
    buttons.append(
        [
            InlineKeyboardButton(
                "Set Chain" if not chain_id else f"Network: {chain_name}",
                callback_data=Command.SET_CHAIN.value,
            ),
            InlineKeyboardButton(
                f"Slippage: {slippage}%", callback_data=Command.SET_SLIPPAGE.value
            ),
        ]
    )

    # Only if a chain has been chosen, the user can set the token addresses
    token0_name = user.get("token0_name")
    token1_name = user.get("token1_name")
    if chain_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    "Token0" if not token0_name else f"Token0: {token0_name}",
                    callback_data=Command.SET_TOKEN0.value,
                ),
                InlineKeyboardButton(
                    "Token1" if not token1_name else f"Token1: {token1_name}",
                    callback_data=Command.SET_TOKEN1.value,
                ),
            ]
        )

    # Assume token name to be set along with address (if there is a name, there will be an address.)
    if token0_name and token1_name:
        # Buy/Sell buttons
        buttons.append(
            [
                InlineKeyboardButton(
                    f"Buy {token0_name}", callback_data=Command.BUY.value
                ),
                InlineKeyboardButton(
                    f"Sell {token0_name}", callback_data=Command.SELL.value
                ),
            ]
        )

    buttons.append(
        [InlineKeyboardButton("Refresh", callback_data=Command.REFRESH.value)]
    )

    return InlineKeyboardMarkup(buttons)


async def show_main_menu(user: dict, context):
    """Default prompt which shows token0/token1 graph, wallet address and balance"""
    user_id = user["id"]

    # Loading message because stuff takes pretty long to load here.
    await context.bot.send_message(chat_id=user_id, text="Loading, please wait...")

    chain_id = user.get("chain_id")
    wallet = get_wallet_details(user["derivation_path"])
    wallet_address = wallet["address"]

    text = ""
    text += f"Wallet Address: `{wallet_address}` (tap to copy)\n"
    text += "Send tokens to this address to deposit.\n"
    text += "REMINDER: You need to deposit the gas token for your selected chain to perform transactions.\n"

    # If chain has been set, we can retrieve token balance for the user
    if chain_id:
        oneinch = OneInchAPI()
        # Mapping of address to value
        balances: dict[str, str] = oneinch.get_token_balance(chain_id, wallet_address)

        text += "\nBalance:\n"
        # Mapping of address to a dict containing balance and token name
        nonzero_balances: dict[str, dict] = {}
        for token_address, token_value_str in balances.items():
            # For non-zero balances, look up more info on the token
            if token_value_str != "0":
                # Look up info using API
                # TODO: Actually test this
                token_info = oneinch.get_token_info(chain_id, token_address)
                token_name = token_info.get("symbol", token_address)
                decimals = token_info.get("decimals")
                nonzero_balances[token_address] = {
                    "amount": parse_decimal(int(token_value_str), decimals),
                    "name": token_name,
                    "decimals": decimals,
                }

        # Append text and calculate USD equivalent
        usd_equiv = 0
        token0_address = user["token0_address"]
        token1_address = user["token1_address"]
        network_info = networks[chain_id]
        usdc_address = network_info["usdc_address"]

        for token_address, info in nonzero_balances.items():
            amount: float = info["amount"]
            name: str = info["name"]
            decimals = info["decimals"]
            if token_address.lower() == usdc_address:
                usd_equiv += amount
            else:
                # Get a quote from oneinch
                dst_amount = oneinch.quoted_swap(
                    chain_id,
                    token_address,
                    usdc_address,
                    format_decimal(amount, decimals),
                )
                # 6 decimals as stablecoins only up to 6 decimals
                human_form = parse_decimal(dst_amount, 6)
                usd_equiv += human_form

            # Append text for current iterating token
            text += f"{name}: {amount}\n"

        # Show USD equivalent of all coins
        text += f"Total Balance (USD): {usd_equiv}"

    chart = None
    token0_address = user.get("token0_address")
    token1_address = user.get("token1_address")
    if chain_id and token0_address and token1_address:
        token0_name = user["token0_name"]
        token1_name = user["token1_name"]
        chart = generate_chart(
            chain_id, token0_address, token0_name, token1_address, token1_name
        )
        if chart is not None:
            await context.bot.send_photo(
                photo=chart,
                chat_id=user_id,
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard(user),
            )
            return

    # In case there is no graph, we send a message without the photo
    await context.bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user),
    )


### Command Handlers ###


#### WALLET ####
async def handle_withdraw(query, context):
    """
    Withdraw command
    """
    user_id = query.from_user.id
    user = get_user(user_id)
    assert user is not None
    chain_id = user.get("chain_id")
    derivation_path = user["derivation_path"]
    wallet = get_wallet_details(derivation_path)
    wallet_address = wallet["address"]

    oneinch = OneInchAPI()

    buttons: list[list[InlineKeyboardButton]] = []

    # For each token that the user holds, create a new button to select it
    balances: dict[str, str] = oneinch.get_token_balance(chain_id, wallet_address)
    for token_address, amount_str in balances.items():
        if amount_str != "0":
            token_info = oneinch.get_token_info(chain_id, token_address)
            token_name = token_info.get("symbol", token_address)
            buttons.append(
                [InlineKeyboardButton(token_name, callback_data=token_address)]
            )

    # Ask user to select token
    set_user_current_stage(user_id, Command.WITHDRAW, 1)
    markup = InlineKeyboardMarkup(buttons)
    text = "Select token to withdraw"
    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=markup)


async def handle_withdraw_selected_token(data: str, user: dict, context):
    token_address = data
    user_id = user["id"]
    withdrawal[user_id] = {"withdraw_token_address": token_address}

    # Prompt user to enter withdrawal address
    text = "Enter wallet address to withdraw to:"
    await context.bot.send_message(chat_id=user_id, text=text)

    # Update next stage: Get withdrawal address
    set_user_current_stage(user_id, Command.WITHDRAW, 2)


async def handle_withdraw_wallet_address(data: str, user: dict, context):
    wallet_address = data
    user_id = user["id"]
    current_withdraw_info = withdrawal[user_id]
    withdrawal[user_id] = {
        **current_withdraw_info,
        "withdraw_wallet_address": wallet_address,
    }

    # Prompt user to input withdrawal amount
    text = "Enter amount to withdraw:"
    await context.bot.send_message(chat_id=user_id, text=text)

    # Update next stage: Get withdrawal amount
    set_user_current_stage(user_id, Command.WITHDRAW, 3)


async def handle_withdraw_amount(data: str, user: dict, context):
    amount_str = data
    amount = float(amount_str)
    user_id = user["id"]

    current_withdraw_info = withdrawal[user_id]
    withdrawal[user_id] = {**current_withdraw_info, "withdraw_amount": amount}
    current_withdraw_info = withdrawal[user_id]
    amount = current_withdraw_info["withdraw_amount"]
    withdraw_wallet_address = current_withdraw_info["withdraw_wallet_address"]
    token_address = current_withdraw_info["withdraw_token_address"]

    oneinch = OneInchAPI()
    token_info = oneinch.get_token_info(user["chain_id"], token_address)
    token_name = token_info["symbol"]
    text = f"Performing withdrawal of {amount}{token_name} to {withdraw_wallet_address}"
    await context.bot.send_message(chat_id=user_id, text=text)

    chain_id = user["chain_id"]
    rpc = networks.get(chain_id).get("rpc")
    derivation_path = user["derivation_path"]
    wallet_details = get_wallet_details(derivation_path)
    success = withdraw_tokens(
        rpc,
        chain_id,
        token_address,
        withdraw_wallet_address,
        wallet_details["private_key"],
    )

    if not success:
        text = "Failed to withdraw funds"
    else:
        text = "Success!"
    await context.bot.send_message(chat_id=user_id, text=text)

    # Finished withdrawal
    del withdrawal[user_id]
    unset_user_current_stage(user_id)

    await show_main_menu(user, context)


#### SET CHAIN ####
async def handle_set_chain(query, context):
    """
    Set Chain command: Get Chain ID
    """
    # Get chain ID from user input
    user = query.from_user
    user_id = user.id
    text = "Enter chain ID:"
    await context.bot.send_message(chat_id=user_id, text=text)
    set_user_current_stage(user_id, Command.SET_CHAIN, 1)


async def set_chain(update: Update, user_id: int, text: str, context):
    chain_id = text
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET chain_id=%s, token0_address=NULL, token1_address=NULL, token0_name=NULL, token1_name=NULL WHERE id=%s",
        (chain_id, user_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Get chain name if known
    chain_info = networks.get(int(chain_id))
    chain_name = chain_info["name"] if chain_info else chain_id

    user = get_user(user_id)
    assert user is not None
    text = f"Your chain has been updated to {chain_name}!\nYour token addresses have been reset.\n\nWhat else would you like to do?"
    await context.bot.send_message(chat_id=user_id, text=text)

    unset_user_current_stage(user_id)
    await show_main_menu(user, context)


#### Set slippage ####
async def handle_set_slippage(query, context):
    """
    Set Chain command: Get slippage percentage
    """
    # Get current slippage
    user = query.from_user
    user_id = user.id
    user = get_user(user_id)
    assert user is not None
    current_slippage = user.get("slippage")
    text = f"Your current slippage is {current_slippage}%. Enter your new value(%):"
    await context.bot.send_message(chat_id=user_id, text=text)
    set_user_current_stage(user_id, Command.SET_SLIPPAGE, 1)


async def set_slippage(update: Update, user_id: int, text: str, context):
    slippage = float(text)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET slippage=%s WHERE id=%s", (slippage, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    user = get_user(user_id)
    assert user is not None
    text = f"Your slippage has been updated to {slippage}%!"
    await context.bot.send_message(chat_id=user_id, text=text)

    unset_user_current_stage(user_id)
    await show_main_menu(user, context)


async def handle_set_token0(query, context):
    """Handle set token 0 command"""
    user_id = query.from_user.id
    text = "Paste token0 address (click here to /cancel):"
    await context.bot.send_message(chat_id=user_id, text=text)
    set_user_current_stage(user_id, Command.SET_TOKEN0, 1)


async def set_token0(update: Update, user_id: int, text: str, context):
    # Get user
    user = get_user(user_id)
    assert user is not None

    # Disallow setting same as token 1
    token_address = text
    token1_address: str | None = user.get("token1_address")
    if token1_address and token_address.lower() == token1_address.lower():
        text = f"Cannot be the same address as your sell token. Please enter another address."
        await context.bot.send_message(chat_id=user_id, text=text)
        return

    chain_id = user["chain_id"]
    oneinch = OneInchAPI()
    token_info = oneinch.get_token_info(chain_id, token_address)
    token_name = token_info.get("symbol")
    if not token_name:
        text = f"Invalid token address. Please enter another address."
        await context.bot.send_message(chat_id=user_id, text=text)
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET token0_address=%s, token0_name=%s WHERE id=%s",
        (token_address.lower(), token_name, user_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    user = get_user(user_id)
    assert user is not None
    text = "Updated!"
    await context.bot.send_message(chat_id=user_id, text=text)

    await show_main_menu(user, context=context)

    unset_user_current_stage(user_id)


async def handle_set_token1(query, context):
    """Handle set sell token command"""
    # TODO: Hide the button by default if chain not set
    user_id = query.from_user.id
    text = "Paste token1 address (click here to /cancel):"
    await context.bot.send_message(chat_id=user_id, text=text)
    set_user_current_stage(user_id, Command.SET_TOKEN1, 1)


async def set_token1(update: Update, user_id: int, text: str, context):
    # Get user
    user = get_user(user_id)
    assert user is not None

    # Disallow setting same as token 0
    token_address = text
    token0_address: str | None = user.get("token0_address")
    if token0_address and token_address.lower() == token0_address.lower():
        text = (
            f"Cannot be the same address as your token 0. Please enter another address."
        )
        await context.bot.send_message(chat_id=user_id, text=text)
        return

    chain_id = user["chain_id"]
    oneinch = OneInchAPI()
    token_info = oneinch.get_token_info(chain_id, token_address)
    token_name = token_info.get("symbol")
    if not token_name:
        text = f"Invalid token address. Please enter another address."
        await context.bot.send_message(chat_id=user_id, text=text)
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET token1_address=%s, token1_name=%s WHERE id=%s",
        (token_address.lower(), token_name, user_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    user = get_user(user_id)
    assert user is not None
    text = "Updated!"
    await context.bot.send_message(chat_id=user_id, text=text)

    await show_main_menu(user, context=context)

    unset_user_current_stage(user_id)


async def handle_refresh(query, context):
    user_id = query.from_user.id
    user = get_user(user_id)
    assert user is not None
    await show_main_menu(user, context)


async def handle_buy(query, context):
    user_id = query.from_user.id
    user = get_user(user_id)
    assert user is not None

    token0_name = user["token0_name"]
    token1_name = user["token1_name"]

    # Present 4 options - 25%, 50%, 75%, 100%
    buttons: list[list[InlineKeyboardButton]] = []

    buttons.append(
        [
            InlineKeyboardButton("25%", callback_data="25"),
            InlineKeyboardButton("50%", callback_data="50"),
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton("75%", callback_data="75"),
            InlineKeyboardButton("100%", callback_data="100"),
        ]
    )

    markup = InlineKeyboardMarkup(buttons)

    text = (
        f"How much {token1_name} to convert to {token0_name}? (click here to /cancel)"
    )
    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=markup)

    # Set to stage 1: Get amount
    set_user_current_stage(user_id, Command.BUY, 1)


async def handle_buy_amount(data: str, user: dict, context):
    user_id = user["id"]
    text = "Processing..."
    await context.bot.send_message(chat_id=user_id, text=text)

    token1_percentage = int(data)
    chain_id = user["chain_id"]
    token0_address = user["token0_address"]
    token0_name = user["token0_name"]
    token1_address = user["token1_address"]
    token1_name = user["token1_name"]

    # Get a quote for how much token1 is required to buy token0
    oneinch = OneInchAPI()
    token1_info = oneinch.get_token_info(chain_id, token1_address)
    token1_decimals = token1_info["decimals"]
    token0_info = oneinch.get_token_info(chain_id, token0_address)
    token0_decimals = token0_info["decimals"]

    derivation_path = user["derivation_path"]
    wallet_details = get_wallet_details(derivation_path)
    wallet_address = wallet_details["address"]
    slippage = 1  # 1 because we don't understand the min 1 max 50 in Swagger docs

    # Check balance
    balances = oneinch.get_token_balance(chain_id, wallet_address, [token1_address])
    assert isinstance(balances, dict)
    token_address, balance = list(balances.items())[0]
    token1_balance = parse_decimal(balance, token1_decimals)
    if token1_balance == 0:
        amount_to_convert = 0
    else:
        amount_to_convert = token1_balance / 100 * token1_percentage

    if amount_to_convert == 0:
        text = "Not enough funds."
        await context.bot.send_message(chat_id=user_id, text=text)
    else:
        # Proceed with the transaction
        rpc = networks[chain_id]["rpc"]
        private_key = wallet_details["private_key"].hex()

        amount_to_convert_str = format_decimal(amount_to_convert, token1_decimals)
        transaction = oneinch.approve_swap_calldata(
            chain_id, token1_address, amount_to_convert_str
        )
        success = execute_transaction(rpc, transaction, private_key)
        if success:
            transaction = oneinch.perform_swap_calldata(
                chain_id,
                token1_address,
                token0_address,
                amount_to_convert_str,
                wallet_address,
                slippage,
            )
            success = execute_transaction(rpc, transaction["tx"], private_key)
            if success:
                text = "Success!"
                await context.bot.send_message(chat_id=user_id, text=text)
                unset_user_current_stage(user_id)
                await show_main_menu(user, context)
                return

    fail_text = "Transaction Failed."
    await context.bot.send_message(chat_id=user_id, text=fail_text)
    unset_user_current_stage(user_id)
    await show_main_menu(user, context)


async def handle_sell(query, context):
    user_id = query.from_user.id
    user = get_user(user_id)
    assert user is not None

    token0_name = user["token0_name"]
    token1_name = user["token1_name"]

    # Present 4 options - 25%, 50%, 75%, 100%
    buttons: list[list[InlineKeyboardButton]] = []

    buttons.append(
        [
            InlineKeyboardButton("25%", callback_data="25"),
            InlineKeyboardButton("50%", callback_data="50"),
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton("75%", callback_data="75"),
            InlineKeyboardButton("100%", callback_data="100"),
        ]
    )

    markup = InlineKeyboardMarkup(buttons)

    text = (
        f"How much {token0_name} to convert to {token1_name}? (click here to /cancel)"
    )
    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=markup)

    # Set to stage 1: Get amount
    set_user_current_stage(user_id, Command.SELL, 1)


async def handle_sell_amount(data: str, user: dict, context):
    user_id = user["id"]
    text = "Processing..."
    await context.bot.send_message(chat_id=user_id, text=text)

    token0_percentage = int(data)
    chain_id = user["chain_id"]
    token0_address = user["token0_address"]
    token0_name = user["token0_name"]
    token1_address = user["token1_address"]
    token1_name = user["token1_name"]

    # Get a quote for how much token1 is required to buy token0
    oneinch = OneInchAPI()
    token1_info = oneinch.get_token_info(chain_id, token1_address)
    token1_decimals = token1_info["decimals"]
    token0_info = oneinch.get_token_info(chain_id, token0_address)
    token0_decimals = token0_info["decimals"]

    derivation_path = user["derivation_path"]
    wallet_details = get_wallet_details(derivation_path)
    wallet_address = wallet_details["address"]
    slippage = 1  # 1 because we don't understand the min 1 max 50 in Swagger docs

    # Check balance
    balances = oneinch.get_token_balance(chain_id, wallet_address, [token0_address])
    assert isinstance(balances, dict)
    token_address, balance = list(balances.items())[0]
    token0_balance = parse_decimal(balance, token0_decimals)
    if token0_balance == 0:
        amount_to_convert = 0
    else:
        amount_to_convert = token0_balance / 100 * token0_percentage

    if amount_to_convert == 0:
        text = "Not enough funds."
        await context.bot.send_message(chat_id=user_id, text=text)
    else:
        # Proceed with the transaction
        rpc = networks[chain_id]["rpc"]
        private_key = wallet_details["private_key"].hex()

        amount_to_convert_str = format_decimal(amount_to_convert, token0_decimals)
        transaction = oneinch.approve_swap_calldata(
            chain_id, token0_address, amount_to_convert_str
        )
        success = execute_transaction(rpc, transaction, private_key)
        if success:
            transaction = oneinch.perform_swap_calldata(
                chain_id,
                token0_address,
                token1_address,
                amount_to_convert_str,
                wallet_address,
                slippage,
            )
            success = execute_transaction(rpc, transaction["tx"], private_key)
            if success:
                text = "Success!"
                await context.bot.send_message(chat_id=user_id, text=text)
                unset_user_current_stage(user_id)
                await show_main_menu(user, context)
                return

    fail_text = "Transaction Failed."
    await context.bot.send_message(chat_id=user_id, text=fail_text)
    unset_user_current_stage(user_id)
    await show_main_menu(user, context)


### Command Handlers END ###

# Map command to stage 0 functions
handlers: dict[str, Callable] = {
    Command.WITHDRAW.value: handle_withdraw,
    Command.SET_CHAIN.value: handle_set_chain,
    Command.SET_SLIPPAGE.value: handle_set_slippage,
    Command.SET_TOKEN0.value: handle_set_token0,
    Command.SET_TOKEN1.value: handle_set_token1,
    Command.REFRESH.value: handle_refresh,
    Command.BUY.value: handle_buy,
    Command.SELL.value: handle_sell,
}


# Handle /start command
async def start(update: Update, context) -> None:
    user_id = update.effective_user.id

    # Create user in database
    if not get_user(user_id):
        add_user(user_id)

    user = get_user(user_id)
    assert user is not None

    # Reset current prompt if it exists, as the user may use this command to cancel
    unset_user_current_stage(user_id)

    await show_main_menu(user, context=context)


# Callback handlers for each button
async def button_callback(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()

    # If user is in nested stage
    user_id = query.from_user.id
    data = query.data
    command_stage = get_user_current_stage(user_id) or {}
    command = command_stage.get("command")
    stage = command_stage.get("stage")

    if not (command and stage):
        # If user on main menu
        command = query.data
        callback = handlers.get(command)

        if callback:
            await callback(query, context=context)
    elif command == Command.WITHDRAW and stage == 1:
        # Withdraw stage 1: data is token selected
        user = get_user(user_id)
        assert user is not None
        await handle_withdraw_selected_token(data, user, context)
    elif command == Command.BUY and stage == 1:
        # Buy stage 1: user selects percentage of token1 to convert
        user = get_user(user_id)
        assert user is not None
        await handle_buy_amount(data, user, context)
    elif command == Command.SELL and stage == 1:
        # Buy stage 1: user selects percentage of token1 to convert
        user = get_user(user_id)
        assert user is not None
        await handle_sell_amount(data, user, context)


async def message_handler(update: Update, context) -> None:
    user = update.effective_user
    user_id = user.id

    # Check that the user has initialized with /start
    user = get_user(user_id)
    if not user:
        text = "Hi there, let's get started by typing /start!"
        await context.bot.send_message(chat_id=user_id, text=text)
        return

    current_prompt = get_user_current_stage(user_id)

    # Nothing to handle
    if not current_prompt:
        await show_main_menu(user, context=context)
        return

    text = update.message.text

    if current_prompt["command"] == Command.WITHDRAW and current_prompt["stage"] == 2:
        await handle_withdraw_wallet_address(text, user, context=context)
    elif current_prompt["command"] == Command.WITHDRAW and current_prompt["stage"] == 3:
        await handle_withdraw_amount(text, user, context=context)
    elif (
        current_prompt["command"] == Command.SET_CHAIN and current_prompt["stage"] == 1
    ):
        await set_chain(update, user_id, text, context=context)
    elif current_prompt["command"] == Command.SET_SLIPPAGE:
        await set_slippage(update, user_id, text, context=context)
    elif current_prompt["command"] == Command.SET_TOKEN0:
        await set_token0(update, user_id, text, context=context)
    elif current_prompt["command"] == Command.SET_TOKEN1:
        await set_token1(update, user_id, text, context=context)


def main() -> None:
    # Replace 'TOKEN' with your bot token
    bot_token = getenv("BOT_TOKEN")
    application = Application.builder().token(bot_token).build()

    # Start command to display the main menu
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", start))

    # CallbackQueryHandler to handle button presses
    application.add_handler(CallbackQueryHandler(button_callback))

    # MessageHandler to handle arbitrary messages, based on user's main menu selection
    application.add_handler(MessageHandler(filters.ALL, message_handler))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
