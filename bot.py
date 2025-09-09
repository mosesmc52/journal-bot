import logging
import os
import random
from datetime import datetime, time, timedelta
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


def get_tz() -> ZoneInfo:
    tz = os.getenv("TIMEZONE") or "UTC"
    try:
        return ZoneInfo(tz)
    except Exception:
        return ZoneInfo("UTC")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    jobs = context.job_queue.get_jobs_by_name(name)
    if not jobs:
        return False
    for job in jobs:
        job.schedule_removal()
    return True


def job_name_for_chat(chat_id: int) -> str:
    return f"daily-{chat_id}"


def parse_hhmm(s: str) -> tuple[int, int] | None:
    try:
        hh, mm = s.strip().split(":")
        h, m = int(hh), int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except Exception:
        pass
    return None


def schedule_daily_checkin(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, hh: int, mm: int
) -> None:
    """
    Schedules a daily recurring check-in for this chat. Replaces existing job if present.
    Time is interpreted in the user's TIMEZONE (from .env).
    """
    tz = get_tz()
    name = job_name_for_chat(chat_id)
    remove_job_if_exists(name, context)
    context.job_queue.run_daily(
        initiate_conversation,
        time=time(hour=hh, minute=mm, tzinfo=tz),
        chat_id=chat_id,
        name=name,
        data={"hh": hh, "mm": mm, "tz": str(tz)},
    )


def ensure_daily_scheduled(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """
    Ensure a daily job exists using either user preference (chat_data['daily_time'])
    or a sensible default (18:00).
    """
    cd = context.chat_data
    dt = cd.get("daily_time")  # {'hh': int, 'mm': int}
    if dt is None:
        dt = {"hh": 18, "mm": 0}
        cd["daily_time"] = dt
    schedule_daily_checkin(context, chat_id, dt["hh"], dt["mm"])


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
    today = datetime.now(get_tz()).strftime("%b %d")
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

    # Always (re)ensure a daily schedule on /start
    ensure_daily_scheduled(context, chat_id)

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


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /daily HH:MM — set (or change) the local reminder time.
    /daily off   — disables the daily reminder.
    /daily       — shows current time.
    """
    chat_id = update.effective_message.chat_id
    args = context.args or []

    if not args:
        dt = context.chat_data.get("daily_time")
        if dt:
            await update.message.reply_text(
                f"Your daily reminder is set to {dt['hh']:02d}:{dt['mm']:02d} ({os.getenv('TIMEZONE')})."
            )
        else:
            await update.message.reply_text("No daily reminder set.")
        return

    arg = " ".join(args).lower().strip()
    if arg in {"off", "disable", "stop"}:
        name = job_name_for_chat(chat_id)
        removed = remove_job_if_exists(name, context)
        context.chat_data.pop("daily_time", None)
        if removed:
            await update.message.reply_text("Daily reminder turned off.")
        else:
            await update.message.reply_text("No daily reminder was set.")
        return

    hhmm = parse_hhmm(arg)
    if not hhmm:
        await update.message.reply_text(
            "Please use `/daily HH:MM` (24h), e.g. `/daily 18:00`.",
            parse_mode="Markdown",
        )
        return

    hh, mm = hhmm
    context.chat_data["daily_time"] = {"hh": hh, "mm": mm}
    schedule_daily_checkin(context, chat_id, hh, mm)
    await update.message.reply_text(
        f"Got it! I’ll nudge you daily at {hh:02d}:{mm:02d} ({os.getenv('TIMEZONE')})."
    )


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
    chat_id = job.chat_id
    hello = greeting()
    await context.bot.send_message(chat_id, text=hello, reply_markup=markup)

    prompt_text = format_daily_prompt(first_name="there")
    conversation.add_content(
        os.getenv("BOT_NAME"), prompt_text, is_bot=True, category="prompt"
    )
    await context.bot.send_message(chat_id, text=prompt_text, parse_mode="Markdown")


async def talk_later(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Schedule a one-shot for tomorrow 18:00 local AND convert it to the daily recurring time,
    so you keep getting nudged every day at that time.
    """
    chat_id = update.effective_message.chat_id
    tz = get_tz()
    now = datetime.now(tz)
    target = (now + timedelta(days=1)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )

    seconds_difference = max(0, int((target - now).total_seconds()))
    # one-shot tomorrow
    context.job_queue.run_once(
        initiate_conversation,
        when=seconds_difference,
        chat_id=chat_id,
        name=f"oneshot-{chat_id}",
        data={},
    )
    # persist as daily going forward
    context.chat_data["daily_time"] = {"hh": 18, "mm": 0}
    schedule_daily_checkin(context, chat_id, 18, 0)

    reply_text = "Cool—I’ll check in tomorrow at 18:00 and every day after that 😊"
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


def restore_schedules_on_startup(application):
    """
    When the bot restarts, re-create any daily jobs for chats that
    have a saved preference in persistence. PTB will load chat_data
    before we call this (because of PicklePersistence).
    """
    # application.chat_data is a dict: {chat_id: dict}
    for chat_id, cd in application.chat_data.items():
        try:
            if (
                isinstance(chat_id, int)
                and isinstance(cd, dict)
                and cd.get("daily_time")
            ):
                dt = cd["daily_time"]
                schedule_daily_checkin(
                    application.job_queue, chat_id, dt["hh"], dt["mm"]
                )
        except Exception as e:
            logging.warning(f"Failed to restore schedule for chat {chat_id}: {e}")


def main() -> None:
    persistence = PicklePersistence(filepath="eva-journal-bot")

    application = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_BOT_TOKEN"))
        .persistence(persistence)
        .build()
    )

    # Restore scheduled jobs for all known chats on startup
    restore_schedules_on_startup(application)

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
    application.add_handler(
        CommandHandler("daily", daily)
    )  # set/see/disable daily reminders

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
