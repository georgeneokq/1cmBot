from os import getenv
from typing import Callable
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
from features.wallet import get_wallet_details
from features.commands.types import Command
from cache.user import (
    get_user_current_stage,
    set_user_current_stage,
    unset_user_current_stage,
)
from oneinch_api import OneInchAPI

Account.enable_unaudited_hdwallet_features()

# Define the main menu keyboard layout
def main_menu_keyboard(user: dict):
    """
    Args:
        user (dict): Result from get_user
    """
    buttons: list[list[InlineKeyboardButton]] = []

    # Populate current configuration into button text
    buttons.append([InlineKeyboardButton("Wallet", callback_data=Command.WALLET.value)])

    chain = user.get("chain_id")
    buttons.append([InlineKeyboardButton("Set Chain" if not chain else f"Network: {chain}", callback_data=Command.SET_CHAIN.value)])

    slippage = user["slippage"]
    buttons.append([InlineKeyboardButton(f"Slippage: {slippage}%", callback_data=Command.SET_SLIPPAGE.value)])

    # Only if a chain has been chosen, the user can set the token addresses    
    if chain:
        buttons.append([InlineKeyboardButton("Set Buy Token", callback_data=Command.SET_BUY_TOKEN.value)])
        buttons.append([InlineKeyboardButton("Set Sell Token", callback_data=Command.SET_SELL_TOKEN.value)])


    # Assume token name to be set along with address (if there is a name, there will be an address.)
    buy_token_name = user.get("buy_token_name")
    sell_token_name = user.get("sell_token_name")
    if buy_token_name and sell_token_name:
        # Chart buttons
        buttons.append([InlineKeyboardButton(f"{buy_token_name}/{sell_token_name} chart", callback_data=Command.SHOW_BUY_CHART.value)])
        buttons.append([InlineKeyboardButton(f"{sell_token_name}/{buy_token_name} chart", callback_data=Command.SHOW_SELL_CHART.value)])
    
        # Buy/Sell buttons
        buttons.append([InlineKeyboardButton(f"Buy {buy_token_name}", callback_data=Command.SET_BUY_TOKEN.value)])
        buttons.append([InlineKeyboardButton(f"Sell {buy_token_name}", callback_data=Command.SET_SELL_TOKEN.value)])

    return InlineKeyboardMarkup(buttons)


async def show_main_menu(update: Update, user):
    await update.message.reply_text(
        "What would you like to do today?", reply_markup=main_menu_keyboard(user)
    )


### Command Handlers ###


#### WALLET ####
async def handle_wallet(query):
    """
    Wallet command: Display wallet address and balances
    """
    # TODO: Get actual token balances and show USD equivalent
    # Get wallet details
    user_id = query.from_user.id
    user = get_user(user_id)
    assert user is not None
    wallet = get_wallet_details(user["derivation_path"])

    # Craft the reply message. TODO: Fix the copy paste
    text = f"Wallet Address: `{wallet.get('address')}`"

    try:
        # Will raise an exception if the edit content is the same as current content. Ignore it
        await query.edit_message_text(
            text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard(user)
        )
    except Exception:
        pass


#### SET CHAIN ####
async def handle_set_chain(query):
    """
    Set Chain command: Get Chain ID
    """
    # Get chain ID from user input
    await query.edit_message_text("Enter chain ID:")
    user = query.from_user
    user_id = user.id
    set_user_current_stage(user_id, Command.SET_CHAIN, 1)


async def set_chain(update: Update, user_id: int, text: str):
    chain = text
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET chain_id=%s WHERE id=%s", (chain, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    user = get_user(user_id)
    assert user is not None
    await update.message.reply_text(
        f"Your chain has been updated to {chain}!\n\nWhat else would you like to do today?",
        reply_markup=main_menu_keyboard(user),
    )

    unset_user_current_stage(user_id)


#### Set slippage ####
async def handle_set_slippage(query):
    """
    Set Chain command: Get slippage percentage
    """
    # Get current slippage
    user = query.from_user
    user_id = user.id
    user = get_user(user_id)
    assert user is not None
    current_slippage = user.get("slippage")
    await query.edit_message_text(
        f"Your current slippage is {current_slippage}%. Enter your new value(%):"
    )
    set_user_current_stage(user_id, Command.SET_SLIPPAGE, 1)


async def set_slippage(update: Update, user_id: int, text: str):
    slippage = float(text)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET slippage=%s WHERE id=%s", (slippage, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    user = get_user(user_id)
    assert user is not None
    await update.message.reply_text(
        f"Your slippage has been updated to {slippage}%!\n\nWhat else would you like to do today?",
        reply_markup=main_menu_keyboard(user),
    )

    unset_user_current_stage(user_id)


async def handle_set_buy_token(query):
    """Handle set buy token command"""
    # TODO: Hide the button by default if chain not set
    user_id = query.from_user.id
    await query.edit_message_text(f"Paste the address of buy token:")
    set_user_current_stage(user_id, Command.SET_BUY_TOKEN, 1)


async def set_buy_token(update: Update, user_id: int, text: str):
    # Get user
    user = get_user(user_id)
    assert user is not None

    # Disallow setting same as sell token
    token_address = text
    sell_token_address: str | None = user.get("sell_token_address")
    if sell_token_address and token_address.lower() == sell_token_address.lower():
        await update.message.reply_text(
            f"Cannot be the same address as your sell token. Please enter another address."
        )
        return

    chain_id = user["chain_id"]
    oneinch = OneInchAPI()
    token_info = oneinch.get_token_info(chain_id, token_address)
    token_name = token_info.get("name")
    if not token_name:
        await update.message.reply_text(
            f"Invalid token address. Please enter another address."
        )
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET buy_token_address=%s, buy_token_name=%s WHERE id=%s",
        (token_address.lower(), token_name, user_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text(
        f"Updated.\n\nWhat else would you like to do today?",
        reply_markup=main_menu_keyboard(get_user(user_id)),
    )

    unset_user_current_stage(user_id)


async def handle_set_sell_token(query):
    """Handle set sell token command"""
    # TODO: Hide the button by default if chain not set
    user = query.from_user
    user_id = user.id
    assert user is not None
    await query.edit_message_text(f"Paste the address of sell token:")
    set_user_current_stage(user_id, Command.SET_SELL_TOKEN, 1)


async def set_sell_token(update: Update, user_id: int, text: str):
    # Get user
    user = get_user(user_id)
    assert user is not None

    # Disallow setting same as buy token
    token_address = text
    buy_token_address: str | None = user.get("buy_token_address")
    if buy_token_address and token_address.lower() == buy_token_address.lower():
        await update.message.reply_text(
            f"Cannot be the same address as your buy token. Please enter another address."
        )
        return

    chain_id = user["chain_id"]
    oneinch = OneInchAPI()
    token_info = oneinch.get_token_info(chain_id, token_address)
    token_name = token_info.get("name", "")
    if not token_name:
        await update.message.reply_text(
            f"Invalid token address. Please enter another address."
        )
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET sell_token_address=%s, sell_token_name=%s WHERE id=%s",
        (token_address.lower(), token_name, user_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text(
        f"Updated.\n\nWhat else would you like to do today?",
        reply_markup=main_menu_keyboard(get_user(user_id)),
    )

    unset_user_current_stage(user_id)


### Command Handlers END ###

# Map command to handler functions
handlers: dict[str, Callable] = {
    Command.WALLET.value: handle_wallet,
    Command.SET_CHAIN.value: handle_set_chain,
    Command.SET_SLIPPAGE.value: handle_set_slippage,
    Command.SET_BUY_TOKEN.value: handle_set_buy_token,
    Command.SET_SELL_TOKEN.value: handle_set_sell_token,
}


# Handle /start command
async def start(update: Update, context) -> None:
    user_id = update.effective_user.id

    # Create user in database
    if not get_user(user_id):
        add_user(user_id)

    user = get_user(user_id)

    # Reset current prompt if it exists, as the user may use this command to cancel
    unset_user_current_stage(user_id)

    await show_main_menu(update, user)


# Callback handlers for each button
async def button_callback(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()

    command = query.data
    callback = handlers.get(command)

    if callback:
        await callback(query)


async def message_handler(update: Update, context) -> None:
    user = update.effective_user
    user_id = user.id

    # Check that the user has initialized with /start
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Hi there, let's get started by typing /start!")
        return

    current_prompt = get_user_current_stage(user_id)

    # Nothing to handle
    if not current_prompt:
        await show_main_menu(update, user)
        return

    text = update.message.text

    if current_prompt["command"] == Command.SET_CHAIN and current_prompt["stage"] == 1:
        await set_chain(update, user_id, text)
    elif current_prompt["command"] == Command.SET_SLIPPAGE:
        await set_slippage(update, user_id, text)
    elif current_prompt["command"] == Command.SET_BUY_TOKEN:
        await set_buy_token(update, user_id, text)
    elif current_prompt["command"] == Command.SET_SELL_TOKEN:
        await set_sell_token(update, user_id, text)


def main() -> None:
    # Replace 'TOKEN' with your bot token
    bot_token = getenv("BOT_TOKEN")
    application = Application.builder().token(bot_token).build()

    # Start command to display the main menu
    application.add_handler(CommandHandler("start", start))

    # CallbackQueryHandler to handle button presses
    application.add_handler(CallbackQueryHandler(button_callback))

    # MessageHandler to handle arbitrary messages, based on user's main menu selection
    application.add_handler(MessageHandler(filters.ALL, message_handler))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
