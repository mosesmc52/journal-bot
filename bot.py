import logging
import os
import random
from datetime import datetime, time
from zoneinfo import ZoneInfo

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

CHOOSING, TYPING_REPLY, TYPING_CHOICE, MEDIA = range(4)

reply_keyboard = [
    ["Share an Experience", "Share a Thought"],
    ["Share a Photo", "Upload Audio"],
    ["Answer a Reflection Question", "Enable Daily Prompt"],
    ["Disable Daily Prompt"],
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


def configured_timezone() -> ZoneInfo | None:
    timezone_name = os.getenv("TIMEZONE")
    if not timezone_name:
        return None

    try:
        return ZoneInfo(timezone_name)
    except Exception:
        logging.warning("Invalid TIMEZONE %r. Falling back to server local time.", timezone_name)
        return None


def configured_daily_prompt_time() -> time:
    raw_value = os.getenv("DAILY_PROMPT_TIME", "18:00")

    try:
        hour_text, minute_text = raw_value.split(":", 1)
        return time(
            hour=int(hour_text),
            minute=int(minute_text),
            tzinfo=configured_timezone(),
        )
    except (TypeError, ValueError):
        logging.warning(
            "Invalid DAILY_PROMPT_TIME %r. Falling back to 18:00.", raw_value
        )
        return time(hour=18, minute=0, tzinfo=configured_timezone())


def daily_prompt_job_name(chat_id: int) -> str:
    return f"daily-prompt:{chat_id}"


def schedule_daily_prompt(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    remove_job_if_exists(daily_prompt_job_name(chat_id), context)
    context.job_queue.run_daily(
        initiate_conversation,
        time=configured_daily_prompt_time(),
        chat_id=chat_id,
        name=daily_prompt_job_name(chat_id),
    )


def daily_prompt_status_text() -> str:
    timezone_name = os.getenv("TIMEZONE") or "server local time"
    return (
        f"I’ll send a journal prompt every day at "
        f"{configured_daily_prompt_time().strftime('%H:%M')} ({timezone_name})."
    )


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
    context.chat_data["daily_prompt_enabled"] = True
    schedule_daily_prompt(chat_id, context)

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
    await update.message.reply_text(daily_prompt_status_text(), reply_markup=markup)

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
    context.user_data["expected_media_type"] = "photo"
    reply_text = "Send a photo."
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text)
    return MEDIA


async def share_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["expected_media_type"] = "audio"
    reply_text = "Send an audio file or voice note."
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text)
    return MEDIA


def media_filter():
    return filters.PHOTO | filters.AUDIO | filters.VOICE


async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    media_file = None
    mimetype = None
    extension = None
    media_label = "media"
    received_media_type = None
    expected_media_type = context.user_data.get("expected_media_type")

    if message.photo:
        media_file = await message.photo[-1].get_file()
        mimetype = "image/jpeg"
        media_label = "photo"
        received_media_type = "photo"
        if media_file.file_path and "." in media_file.file_path:
            extension = media_file.file_path.rsplit(".", 1)[-1]
    elif message.audio:
        media_file = await message.audio.get_file()
        mimetype = message.audio.mime_type or "audio/mpeg"
        media_label = "audio"
        received_media_type = "audio"
        if message.audio.file_name and "." in message.audio.file_name:
            extension = message.audio.file_name.rsplit(".", 1)[-1]
    elif message.voice:
        media_file = await message.voice.get_file()
        mimetype = message.voice.mime_type or "audio/ogg"
        media_label = "voice note"
        received_media_type = "audio"
        extension = "ogg"

    if not media_file or not mimetype:
        reply_text = "I can save photos, audio files, and voice notes."
        await message.reply_text(reply_text, reply_markup=markup)
        return CHOOSING

    if expected_media_type and received_media_type != expected_media_type:
        if expected_media_type == "photo":
            reply_text = "That looks like audio. Tap Share a Photo and send an image."
        else:
            reply_text = (
                "That looks like a photo. Tap Upload Audio and send an audio file or voice note."
            )
        await message.reply_text(reply_text, reply_markup=markup)
        return CHOOSING

    file_bytes = bytes(await media_file.download_as_bytearray())
    conversation.add_media(file_bytes, mimetype, extension=extension)
    context.user_data.pop("expected_media_type", None)

    if message.caption:
        conversation.add_content("me", message.caption, category="media_caption")

    reply_text = f"Saved your {media_label}. Want to add a few words?"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await message.reply_text(reply_text, reply_markup=markup)
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
    hello = greeting()
    await context.bot.send_message(job.chat_id, text=hello, reply_markup=markup)

    prompt_text = format_daily_prompt(first_name="there")
    conversation.add_content(
        os.getenv("BOT_NAME"), prompt_text, is_bot=True, category="prompt"
    )
    await context.bot.send_message(job.chat_id, text=prompt_text, parse_mode="Markdown")


async def enable_daily_prompt(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    chat_id = update.effective_message.chat_id
    context.chat_data["daily_prompt_enabled"] = True
    schedule_daily_prompt(chat_id, context)
    reply_text = daily_prompt_status_text()
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.effective_message.reply_text(reply_text, reply_markup=markup)
    return CHOOSING


async def disable_daily_prompt(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    chat_id = update.effective_message.chat_id
    remove_job_if_exists(daily_prompt_job_name(chat_id), context)
    context.chat_data["daily_prompt_enabled"] = False

    reply_text = "Daily journal prompts are off. Send /start or tap Enable Daily Prompt to turn them back on."
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.effective_message.reply_text(reply_text, reply_markup=markup)
    return CHOOSING


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    reply_text = "Thanks for sharing. Talk soon 👋"
    conversation.add_content(os.getenv("BOT_NAME"), reply_text, is_bot=True)
    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())
    user_data.clear()
    return ConversationHandler.END


async def restore_daily_prompt_jobs(application) -> None:
    for chat_id, chat_data in application.chat_data.items():
        if not chat_data.get("daily_prompt_enabled"):
            continue

        application.job_queue.run_daily(
            initiate_conversation,
            time=configured_daily_prompt_time(),
            chat_id=chat_id,
            name=daily_prompt_job_name(chat_id),
        )


# ----------------------- App Bootstrap -----------------------


def main() -> None:
    persistence = PicklePersistence(filepath="eva-journal-bot")

    application = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_BOT_TOKEN"))
        .persistence(persistence)
        .post_init(restore_daily_prompt_jobs)
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
                MessageHandler(
                    filters.Regex(r"^(Share a Photo)$"),
                    share_photo,
                ),
                MessageHandler(filters.Regex(r"^(Upload Audio)$"), share_audio),
                MessageHandler(
                    filters.Regex(r"^(Answer a Reflection Question)$"),
                    reflection_question,
                ),
                MessageHandler(
                    filters.Regex(r"^(Enable Daily Prompt)$"), enable_daily_prompt
                ),
                MessageHandler(
                    filters.Regex(r"^(Disable Daily Prompt)$"), disable_daily_prompt
                ),
                MessageHandler(media_filter(), receive_media),
            ],
            MEDIA: [MessageHandler(media_filter(), receive_media)],
            TYPING_REPLY: [
                MessageHandler(media_filter(), receive_media),
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
    application.add_handler(CommandHandler("daily_on", enable_daily_prompt))
    application.add_handler(CommandHandler("daily_off", disable_daily_prompt))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
