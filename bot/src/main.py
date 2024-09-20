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
from mytypes import Command, CommandStage
from features.chain import set_chain

# Map user id to current selection + stage (the handler itself will be index 0, subsequent handling will increment)
user_current_prompt: dict[int, CommandStage] = {}


def get_user_current_prompt(user_id: int):
    return user_current_prompt.get(user_id)


def set_user_current_prompt(user_id: int, command: Command, stage: int):
    user_current_prompt[user_id] = {"command": command, "stage": stage}


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


### Command handlers ###
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
        await query.edit_message_text(text=text, reply_markup=main_menu_keyboard())
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
    set_user_current_prompt(user_id, Command.SET_CHAIN, 1)
    print(user_current_prompt)


# Map command to handler functions
handlers: dict[str, Callable] = {
    Command.WALLET.value: handle_wallet,
    Command.SET_CHAIN.value: handle_set_chain,
}


# Define the main menu keyboard layout
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(display_text, callback_data=command)]
        for (display_text, command) in commands.items()
    ]
    return InlineKeyboardMarkup(keyboard)


# Command handler to display the main menu
async def start(update: Update, context) -> None:
    # TODO: Ensure user is created in database

    # Reset current prompt if it exists, as the user may use this command to cancel
    user_id = update.effective_user.id
    user_current_prompt.pop(user_id, "")

    await show_main_menu(update)


async def show_main_menu(update: Update):
    await update.message.reply_text(
        "What would you like to do today?", reply_markup=main_menu_keyboard()
    )


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
    current_prompt = get_user_current_prompt(user_id)
    print("debug2")
    print(user_id)
    print(current_prompt)

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
            reply_markup=main_menu_keyboard(),
        )


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
