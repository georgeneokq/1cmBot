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
from charts import generate_chart
from constants import networks

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

    # Get the chain name if we support it
    chain_id = user.get("chain_id", -1)
    chain_info = networks.get(chain_id)
    chain_name = chain_info["name"] if chain_info else chain_id
    buttons.append([InlineKeyboardButton("Set Chain" if not chain_id else f"Network: {chain_name}", callback_data=Command.SET_CHAIN.value)])

    slippage = user["slippage"]
    buttons.append([InlineKeyboardButton(f"Slippage: {slippage}%", callback_data=Command.SET_SLIPPAGE.value)])

    # Only if a chain has been chosen, the user can set the token addresses    
    token0_name = user.get("token0_name")
    token1_name = user.get("token1_name")
    if chain_id:
        buttons.append([
            InlineKeyboardButton("Token0" if not token0_name else f"Token0: {token0_name}", callback_data=Command.SET_TOKEN0.value),
            InlineKeyboardButton("Token1" if not token1_name else f"Token1: {token1_name}", callback_data=Command.SET_TOKEN1.value)
        ])

    # Assume token name to be set along with address (if there is a name, there will be an address.)
    if token0_name and token1_name:
        # Chart buttons
        buttons.append([
            InlineKeyboardButton(f"{token0_name}/{token1_name} 📈", callback_data=Command.SHOW_TOKEN0_CHART.value),
            InlineKeyboardButton(f"{token1_name}/{token0_name} 📈", callback_data=Command.SHOW_TOKEN1_CHART.value)
        ])
    
        # Buy/Sell buttons
        buttons.append([
            InlineKeyboardButton(f"Buy {token0_name}", callback_data=Command.SET_TOKEN0.value),
            InlineKeyboardButton(f"Sell {token0_name}", callback_data=Command.SET_TOKEN1.value)
        ])

    return InlineKeyboardMarkup(buttons)


async def show_main_menu(user: dict, context):
    """ Default prompt which shows token0/token1 graph, wallet address and balance """
    user_id = user['id']
    chain_id = user.get("chain_id")

    wallet = get_wallet_details(user["derivation_path"])
    wallet_address = wallet["address"]

    text = ""
    text += f"Wallet Address: `{wallet_address}` (tap to copy)\n"

    # If chain has been set, we can retrieve token balance for the user
    if chain_id:
        oneinch = OneInchAPI()
        balances = oneinch.get_token_balance(chain_id, wallet_address)
        print(balances)

    await context.bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard(user))

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
    chain_id = text
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET chain_id=%s, token0_address=NULL, token1_address=NULL, token0_name=NULL, token1_name=NULL WHERE id=%s", (chain_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    # Get chain name if known
    chain_info = networks.get(int(chain_id))
    chain_name = chain_info["name"] if chain_info else chain_id

    user = get_user(user_id)
    assert user is not None
    await update.message.reply_text(
        f"Your chain has been updated to {chain_name}!\nYour token addresses have been reset.\n\nWhat else would you like to do?",
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
        f"Your slippage has been updated to {slippage}%!\n\nWhat else would you like to do?",
        reply_markup=main_menu_keyboard(user),
    )

    unset_user_current_stage(user_id)


async def handle_set_token0(query):
    """Handle set token 0 command"""
    user_id = query.from_user.id
    await query.edit_message_text(f"Paste token address:")
    set_user_current_stage(user_id, Command.SET_TOKEN0, 1)


async def set_token0(update: Update, user_id: int, text: str):
    # Get user
    user = get_user(user_id)
    assert user is not None

    # Disallow setting same as token 1
    token_address = text
    token1_address: str | None = user.get("token1_address")
    if token1_address and token_address.lower() == token1_address.lower():
        await update.message.reply_text(
            f"Cannot be the same address as your sell token. Please enter another address."
        )
        return

    chain_id = user["chain_id"]
    oneinch = OneInchAPI()
    token_info = oneinch.get_token_info(chain_id, token_address)
    token_name = token_info.get("symbol")
    if not token_name:
        await update.message.reply_text(
            f"Invalid token address. Please enter another address."
        )
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
    await update.message.reply_text(
        f"Updated.\n\nWhat else would you like to do?",
        reply_markup=main_menu_keyboard(user),
    )

    unset_user_current_stage(user_id)


async def handle_set_token1(query):
    """Handle set sell token command"""
    # TODO: Hide the button by default if chain not set
    user_id = query.from_user.id
    await query.edit_message_text(f"Paste token address:")
    set_user_current_stage(user_id, Command.SET_TOKEN1, 1)


async def set_token1(update: Update, user_id: int, text: str):
    # Get user
    user = get_user(user_id)
    assert user is not None

    # Disallow setting same as token 0
    token_address = text
    token0_address: str | None = user.get("token0_address")
    if token0_address and token_address.lower() == token0_address.lower():
        await update.message.reply_text(
            f"Cannot be the same address as your token 0. Please enter another address."
        )
        return

    chain_id = user["chain_id"]
    oneinch = OneInchAPI()
    token_info = oneinch.get_token_info(chain_id, token_address)
    token_name = token_info.get("symbol")
    if not token_name:
        await update.message.reply_text(
            f"Invalid token address. Please enter another address."
        )
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
    await update.message.reply_text(
        f"Updated.\n\nWhat else would you like to do?",
        reply_markup=main_menu_keyboard(user),
    )

    unset_user_current_stage(user_id)


async def handle_show_token0_chart(query, context):
    user_id = query.from_user.id
    user = get_user(user_id)
    assert user is not None

    # Get token addresses
    chain_id = user["chain_id"]
    token0_address = user["token0_address"]
    token0_name = user["token0_name"]
    token1_address = user["token1_address"]
    token1_name = user["token1_name"]

    chart = generate_chart(chain_id, token0_address, token0_name, token1_address, token1_name)

    await context.bot.send_message(chat_id=user_id, text="Generating chart...")

    await context.bot.send_photo(chat_id=user_id, photo=chart)

    await context.bot.send_message(chat_id=user_id, text="Here you go!")


async def handle_show_token1_chart(query, context):
    user_id = query.from_user.id
    user = get_user(user_id)
    assert user is not None

    # Get token addresses
    chain_id = user["chain_id"]
    token0_address = user["token0_address"]
    token1_address = user["token1_address"]

    chart = generate_chart(chain_id, token1_address, token0_address)

    await context.bot.send_photo(chat_id=user_id, photo=chart)

    await context.bot.send_message(chat_id=user_id, text="Here you go!")

### Command Handlers END ###

# Map command to handler functions
handlers: dict[str, Callable] = {
    Command.WALLET.value: handle_wallet,
    Command.SET_CHAIN.value: handle_set_chain,
    Command.SET_SLIPPAGE.value: handle_set_slippage,
    Command.SET_TOKEN0.value: handle_set_token0,
    Command.SET_TOKEN1.value: handle_set_token1,
    Command.SHOW_TOKEN0_CHART.value: handle_show_token0_chart,
    Command.SHOW_TOKEN1_CHART.value: handle_show_token1_chart,
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

    command = query.data
    callback = handlers.get(command)

    if callback:
        await callback(query, context=context)


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
        await show_main_menu(user, context=context)
        return

    text = update.message.text

    if current_prompt["command"] == Command.SET_CHAIN and current_prompt["stage"] == 1:
        await set_chain(update, user_id, text)
    elif current_prompt["command"] == Command.SET_SLIPPAGE:
        await set_slippage(update, user_id, text)
    elif current_prompt["command"] == Command.SET_TOKEN0:
        await set_token0(update, user_id, text)
    elif current_prompt["command"] == Command.SET_TOKEN1:
        await set_token1(update, user_id, text)


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
