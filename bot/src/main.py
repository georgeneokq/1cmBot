from os import getenv
from typing import Callable
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from features.database import get_connection
from features.database.user import get_user, add_user
from features.commands.types import Command
from cache.user import get_user_current_stage, set_user_current_stage, unset_user_current_stage
from util import tuple_to_dict

# Map button text to command enum value
# NOTE: Can't map to Command enum literal, must use its int representation as it must be JSON serializable
commands: dict[str, str] = {
    "Wallet": Command.WALLET.value,
    "Set Chain": Command.SET_CHAIN.value,
    "Set Slippage": Command.SET_SLIPPAGE.value,
    "Set Buy Token": Command.SET_BUY_TOKEN.value,
    "Set Sell Token": Command.SET_SELL_TOKEN.value,
    "Show Buy Chart": Command.SHOW_BUY_CHART.value,
    "Show Sell Chart": Command.SHOW_SELL_CHART.value,
    "Buy": Command.BUY.value,
    "Sell": Command.SELL.value,
}

# Define the main menu keyboard layout
main_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton(display_text, callback_data=command)]
    for (display_text, command) in commands.items()
])

async def show_main_menu(update: Update):
    await update.message.reply_text(
        "What would you like to do today?", reply_markup=main_menu_keyboard
    )

### Command Handlers ###

async def handle_wallet(query):
    """
    Wallet command: Display wallet address and balances
    """
    # TODO: Get actual token balances and show USD equivalent
    text = """
Wallet Address: 0x0192383492592...
USDC: 200.00
XSGD: 100.00
    """.strip()
    try:
        # Will raise an exception if the edit content is the same as current content. Ignore it
        await query.edit_message_text(text=text, reply_markup=main_menu_keyboard)
    except Exception:
        pass

async def handle_set_chain(query):
    """
    Set Chain command: Get Chain ID
    """
    # Get chain ID from user input
    await query.edit_message_text("Enter chain ID:")
    user = query.from_user
    user_id = user.id
    set_user_current_stage(user_id, Command.SET_CHAIN, 1)


def set_chain(user_id: int, chain_id: str):
    # TODO: Save to database
    pass


### Command Handlers END ###

# Map command to handler functions
handlers: dict[str, Callable] = {
    Command.WALLET.value: handle_wallet,
    Command.SET_CHAIN.value: handle_set_chain,
}

# Handle /start command
async def start(update: Update, context) -> None:
    user_id = update.effective_user.id
    
    # Create user in database
    if not get_user(user_id):
        add_user(user_id)

    # Reset current prompt if it exists, as the user may use this command to cancel
    unset_user_current_stage(user_id)

    await show_main_menu(update)


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
    current_prompt = get_user_current_stage(user_id)

    # Nothing to handle
    if not current_prompt:
        await show_main_menu(update)
        return

    text = update.message.text

    if current_prompt["command"] == Command.SET_CHAIN and current_prompt["stage"] == 1:
        set_chain(user_id, text)
        print(f"Received message: {text}")
        await update.message.reply_text(
            f"Chain has been set to {text} Polygon (TODO: Change this)",
            reply_markup=main_menu_keyboard,
        )

        # End of stage, reset user prompt
        unset_user_current_stage(user_id)


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
