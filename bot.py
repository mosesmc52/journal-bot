import logging
import os
import random
from datetime import datetime, time, timedelta

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

# ----------------------- Setup & Config -----------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

load_dotenv(".env")

conversation = Conversation(
    service_account_file=os.getenv("SERVICE_ACCOUNT_FILE"),
    drive_folder_parent_id=os.getenv("GOOGLE_DRIVE_PARENT_FOLDER_ID"),
)

CHOOSING, TYPING_REPLY, TYPING_CHOICE, PHOTO = range(4)

reply_keyboard = [
    ["Share an Experience", "Share a Thought", "Share a Photo"],
    ["Answer a Reflection Question", "Talk Tomorrow"],
    ["Bye"],
]
markup = ReplyKeyboardMarkup(
    reply_keyboard, one_time_keyboard=True, resize_keyboard=True
)


# ----------------------- Helpers -----------------------


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    jobs = context.job_queue.get_jobs_by_name(name)
    if not jobs:
        return False
    for job in jobs:
        job.schedule_removal()
    return True


# Short, friendly prompts (time-aware + anytime)
MORNING_PROMPTS = [
    "What’s up today?",
    "One small win you want?",
    "How did you sleep?",
    "What would make today feel good?",
    "What’s your vibe this morning?",
]
AFTERNOON_PROMPTS = [
    "How’s your day going?",
    "Anything interesting happen?",
    "What took energy? What gave it?",
    "What’s one thing you’re proud of?",
    "What surprised you?",
]
EVENING_PROMPTS = [
    "How’d the day go?",
    "Highlight of today?",
    "Tough moment? How’d you handle it?",
    "What are you grateful for?",
    "What will you tweak tomorrow?",
]
ANYTIME_CHECKINS = [
    "Right now I feel… (one word + why)",
    "Energy 1–5? What would raise it by 1?",
    "Need more of ___ / less of ___?",
    "One sentence you’d send future‑you?",
    "What’s one 5‑minute task you can finish?",
]

SUGGESTED_TAGS = ["#win", "#mood", "#gratitude", "#note", "#focus"]


def pick_timebox_prompts():
    p = period_of_day(os.getenv("TIMEZONE"))
    if p == "morning":
        base = MORNING_PROMPTS
    elif p in ("noon", "afternoon"):
        base = AFTERNOON_PROMPTS
    else:
        base = EVENING_PROMPTS
    prompts = random.sample(base, k=2) + [random.choice(ANYTIME_CHECKINS)]
    random.shuffle(prompts)
    return prompts


def format_daily_prompt(first_name: str) -> str:
    today = datetime.now().strftime("%b %d")
    prompts = pick_timebox_prompts()
    tags = " ".join(random.sample(SUGGESTED_TAGS, k=3))
    return (
        f"📝 *Daily Journal* — {today}\n"
        f"Hi {first_name}, quick check‑in:\n\n"
        f"1) {prompts[0]}\n"
        f"2) {prompts[1]}\n"
        f"3) {prompts[2]}\n\n"
        f"_Tags:_ {tags}"
    )


def greeting():
    p = period_of_day(os.getenv("TIMEZONE"))
    if p == "morning":
        return random.choice(
            ["Morning! How’s it going?", "Hey—did you sleep okay?", "What’s up today?"]
        )
    elif p in ["noon", "afternoon"]:
        return random.choice(
            [
                "Hey, how’s your day?",
                "What’s been going on?",
                "Got a minute to check in?",
            ]
        )
    else:
        return random.choice(
            [
                "Evening! How’d the day go?",
                "How are you feeling tonight?",
                "Quick check‑in?",
            ]
        )


# ----------------------- Handlers -----------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_message.chat_id
    remove_job_if_exists(str(chat_id), context)

    reply_text = (
        f"Hey there {update.effective_user.first_name}, I’m {os.getenv('BOT_NAME')} 🙂 "
        "Want to share anything from today?"
    )
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text, reply_markup=markup)

    # also send today’s prompt (short & friendly)
    prompt_text = format_daily_prompt(update.effective_user.first_name)
    conversation.add_content(
        os.getenv("BOT_NAME"), prompt_text, is_bot=True, category="prompt"
    )
    await update.message.reply_text(prompt_text, parse_mode="Markdown")

    return CHOOSING


async def send_today_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt_text = format_daily_prompt(update.effective_user.first_name)
    conversation.add_content(
        os.getenv("BOT_NAME"), prompt_text, is_bot=True, category="prompt"
    )
    await update.message.reply_text(
        prompt_text, parse_mode="Markdown", reply_markup=markup
    )
    return CHOOSING


async def received_information(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    answer = update.message.text
    conversation.add_content("me", answer)

    reply_text = "Got it 😊 Add anything else?"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text, reply_markup=markup)

    return CHOOSING


async def share_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "How’s your day been?"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text)
    return TYPING_REPLY


async def share_thought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "What’s on your mind?"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text)
    return TYPING_REPLY


async def share_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_text = "Nice! Send it over 📷"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text)
    return PHOTO


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    conversation.add_media(photo_file.file_path, "image/jpeg")

    reply_text = "Love it! Want to add a few words?"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text, reply_markup=markup)
    return CHOOSING


async def reflection_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    curated = MORNING_PROMPTS + AFTERNOON_PROMPTS + EVENING_PROMPTS + ANYTIME_CHECKINS
    question = random.choice(curated)
    text = f"Here’s one:\n\n{question}"
    conversation.add_content(
        os.getenv("BOT_NAME"), text, category="reflection", is_bot=True
    )
    await update.message.reply_text(text)
    return TYPING_REPLY


async def initiate_conversation(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    hello = greeting()
    await context.bot.send_message(job.chat_id, text=hello, reply_markup=markup)

    prompt_text = format_daily_prompt(first_name="there")
    conversation.add_content(
        os.getenv("BOT_NAME"), prompt_text, is_bot=True, category="prompt"
    )
    await context.bot.send_message(job.chat_id, text=prompt_text, parse_mode="Markdown")


async def talk_later(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # schedule tomorrow at 6:00 PM local
    chat_id = update.effective_message.chat_id
    now = datetime.now()
    target = (now + timedelta(days=1)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    seconds_difference = int((target - now).total_seconds())

    context.job_queue.run_once(
        initiate_conversation,
        seconds_difference,
        chat_id=chat_id,
        name=str(chat_id),
        data=seconds_difference,
    )
    reply_text = "Cool—I’ll check in tomorrow at 6pm 😊"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.effective_message.reply_text(reply_text)


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    reply_text = "Thanks for sharing. Talk soon 👋"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


# ----------------------- App Bootstrap -----------------------


def main() -> None:
    persistence = PicklePersistence(filepath="eva-journal-bot")

    application = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_BOT_TOKEN"))
        .persistence(persistence)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(os.getenv("BOT_NAME"), start),
            CommandHandler("hi", start),
            CommandHandler("start", start),
            CommandHandler("today", send_today_prompt),  # manual daily prompts
        ],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex(r"^(Share an Experience)$"), share_experience
                ),
                MessageHandler(filters.Regex(r"^(Share a Thought)$"), share_thought),
                MessageHandler(filters.Regex(r"^(Share a Photo)$"), share_photo),
                MessageHandler(
                    filters.Regex(r"^(Answer a Reflection Question)$"),
                    reflection_question,
                ),
                MessageHandler(filters.Regex(r"^(Talk Tomorrow)$"), talk_later),
            ],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            TYPING_REPLY: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex(r"^Bye$")),
                    received_information,
                )
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(r"^Bye$"), done)],
        name="journal-bot",
    )
    application.add_handler(conv_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
