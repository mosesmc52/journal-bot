import logging
import os
import random

from conversation import Conversation
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)
from utils import period_of_day

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# load environmental variables
load_dotenv(".env")

conversation = Conversation(
    service_account_file=os.getenv("SERVICE_ACCOUNT_FILE"),
    drive_folder_parent_id=os.getenv("GOOGLE_DRIVE_PARENT_FOLDER_ID"),
)

CHOOSING, TYPING_REPLY, TYPING_CHOICE, PHOTO = range(4)

reply_keyboard = [
    ["Share an Experience", "Share a Thought", "Share a Photo"],
    ["Answer a Reflection Question", "Talk Later"],
    ["Done"],
]

markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def greeting():
    period = period_of_day(os.getenv("TIMEZONE"))

    # conversation.add_content("me", user_input)

    if period == "morning":
        messages = ["Morning, *smile* How are you doing luv?"]
    elif period in ["noon", "afternoon"]:
        messages = ["Good to hear from you, *smile* How are you doing luv?"]
    elif period == "evening":
        messages = ["Good evening, How are doing?"]

    random_index = random.randint(0, len(messages) - 1)

    return messages[random_index]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data:
        reply_text = greeting()
    else:
        reply_text = f"Hi {update.effective_user.first_name}, I'm { os.getenv('BOT_NAME') }. I'm here to help you keep track of your memories in life. Tell me what do yo want to share"

    conversation.add_content(os.getenv("BOT_NAME"), reply_text)
    await update.message.reply_text(reply_text, reply_markup=markup)

    return CHOOSING


async def received_information(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    answer = update.message.text

    conversation.add_content("me", answer)

    reply_text = (
        "Neat! ** blink ** I want to hear more. :)",
        "Is there anything else you would like to tell me?",
    )
    conversation.add_content(os.getenv("BOT_NAME"), reply_text)
    await update.message.reply_text(
        reply_text,
        reply_markup=markup,
    )

    return CHOOSING


async def share_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = f"How is your day going? ** smile ** :)"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text)
    await update.message.reply_text(reply_text)

    return TYPING_REPLY


async def share_thought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = f"Hit me! What are you thinking?"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text)
    await update.message.reply_text(reply_text)

    return TYPING_REPLY


async def share_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = f"Oh, photos. I want to see."
    conversation.add_content(os.getenv("BOT_NAME"), reply_text)
    await update.message.reply_text(reply_text)
    return PHOTO


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive("user_photo.jpg")
    reply_text = ("Wow, Gorgeous!", "Is there anything else you would like to tell me?")

    conversation.add_content(os.getenv("BOT_NAME"), reply_text)
    await update.message.reply_text(
        reply_text,
        reply_markup=markup,
    )

    return CHOOSING


async def reflection_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = conversation.get_reflection_question()
    conversation.add_content(
        os.getenv("BOT_NAME"), question, category="reflection", is_bot=True
    )

    await update.message.reply_text(question)
    return TYPING_REPLY


async def initiate_conversation(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    await context.bot.send_message(
        job.chat_id, text=f"Beep! {job.data} seconds are over!"
    )


async def talk_later(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    future_day = 24 * 60 * 60  # 1 day in seconds

    context.job_queue.run_once(
        initiate_conversation, future_day, chat_id=chat_id, name=str(chat_id), data=due
    )
    reply_text = "Great! Let's talk tomorrow."
    conversation.add_content(os.getenv("BOT_NAME"), reply_text)

    await update.effective_message.reply_text(reply_text)


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the gathered info and end the conversation."""
    user_data = context.user_data
    messages = ["Thanks for sharing. I really enjoy learning more about you."]
    random_index = random.randint(0, len(messages) - 1)
    reply_text = messages[random_index]

    await update.message.reply_text(
        reply_text,
        reply_markup=ReplyKeyboardRemove(),
    )

    user_data.clear()

    return ConversationHandler.END


def main() -> None:
    persistence = PicklePersistence(filepath="eva-journal-bot")

    application = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_BOT_TOKEN"))
        .persistence(persistence)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("hi", start)],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex("^(Share an Experience)$"), share_experience
                ),
                MessageHandler(filters.Regex("^(Share a Thought)$"), share_thought),
                MessageHandler(filters.Regex("^(Share a Photo)$"), share_photo),
                MessageHandler(
                    filters.Regex("^(Answer a Reflection Question)$"),
                    reflection_question,
                ),
            ],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            TYPING_REPLY: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^bye$")),
                    received_information,
                )
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^bye$"), done)],
        name="journal-bot",
        persistent=True,
    )
    application.add_handler(conv_handler)
    # application.add_handler(CommandHandler("hi", start))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
