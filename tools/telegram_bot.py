"""
tools/telegram_bot.py — Jan Sahayak Telegram interface

Wraps the existing core/agent_engine.py with zero changes to its logic.
This file ONLY handles: receiving Telegram messages (text or voice),
converting voice to text when needed, calling the agent, and sending
the response back (as text, and as voice when VOICE_ENABLED is True).

DEPLOYMENT MODE:
Runs in WEBHOOK mode (not polling) when deployed, because Render's free
tier only supports Web Services, not Background Workers — and webhook
mode is itself the correct production pattern for Telegram bots anyway
(Telegram pushes updates to us instead of us repeatedly asking).

Locally, for quick testing without a public URL, polling mode still
works — set RENDER_DEPLOYMENT=False (or leave unset) to use polling.
On Render, RENDER_DEPLOYMENT is automatically set via render.yaml.

Requires TELEGRAM_BOT_TOKEN in .env (get one from @BotFather on Telegram).
"""

import logging
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from core import agent_engine

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

RENDER_DEPLOYMENT = os.environ.get("RENDER_DEPLOYMENT", "False").strip().lower() == "true"
PORT = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")


WELCOME_MESSAGE = (
    "Namaste! Main Jan Sahayak hoon. Aap mujhse kisan yojanaon ke baare "
    "mein Hindi ya English mein sawal pooch sakte hain — text ya voice "
    "message dono se.\n\n"
    "Hello! I'm Jan Sahayak. Ask me about farmer schemes in Hindi or "
    "English — text or voice message both work."
)

SLOW_START_NOTICE = (
    "\n\n_(Pehli baar shuru ho raha hai, isliye thoda samay lag sakta hai. "
    "First response may take up to a minute as the service wakes up.)_"
)


class TypingIndicator:
    """
    Keeps Telegram's "typing..." indicator alive for as long as the
    agent is processing, since Telegram's native indicator only lasts
    ~5 seconds on its own. Also detects unusually long waits (likely a
    cold start after Render's free-tier spin-down) and sends a one-time
    friendly heads-up so the silence doesn't read as broken.
    """

    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id
        self._task = None
        self._notice_sent = False

    async def _keep_typing(self):
        elapsed = 0
        while True:
            await self.bot.send_chat_action(chat_id=self.chat_id, action="typing")
            await asyncio.sleep(4)
            elapsed += 4
            if elapsed >= 10 and not self._notice_sent:
                self._notice_sent = True
                try:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text="Soch raha hoon... thoda samay lagega. Still thinking, this may take a bit longer than usual.",
                    )
                except Exception:
                    pass

    async def __aenter__(self):
        self._task = asyncio.create_task(self._keep_typing())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._task:
            self._task.cancel()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG] /start command received from {update.effective_user.id}")
    await update.message.reply_text(WELCOME_MESSAGE)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG] handle_text_message FIRED. Raw text: {update.message.text!r}")
    user_query = update.message.text
    user_id = update.effective_user.id

    from core.language_detect import detect_language
    detected_language = detect_language(user_query)
    logger.info(f"[text] from {user_id} (lang={detected_language}): {user_query}")

    async with TypingIndicator(context.bot, update.effective_chat.id):
        result = await asyncio.to_thread(
            agent_engine.handle_query, user_query, language=detected_language, user_id=user_id
        )

    backend_tag = f"\n\n_Answered by: {result['backend_used'] or 'verified local data'}_"
    await update.message.reply_text(result["answer"] + backend_tag, parse_mode="Markdown")


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"[voice] from {user_id}")

    if not config.VOICE_ENABLED:
        await update.message.reply_text(
            "Voice message receive hua, lekin voice processing abhi off hai. "
            "Kripya text mein apna sawal poochein.\n\n"
            "Voice received, but voice processing is currently disabled. "
            "Please type your question instead."
        )
        return

    async with TypingIndicator(context.bot, update.effective_chat.id):
        from tools.voice import stt, tts

        voice_file = await update.message.voice.get_file()
        audio_path = f"/tmp/voice_in_{user_id}.ogg"
        await voice_file.download_to_drive(audio_path)

        transcribed_text = stt.transcribe(audio_path)
        logger.info(f"[voice transcribed]: {transcribed_text}")

        result = await asyncio.to_thread(
            agent_engine.handle_query, transcribed_text, language=config.LANGUAGE_DEFAULT, user_id=user_id
        )

    backend_tag = f"\n\n_Answered by: {result['backend_used'] or 'verified local data'}_"
    await update.message.reply_text(
        f"Aapne poocha: \"{transcribed_text}\"\n\n{result['answer']}{backend_tag}",
        parse_mode="Markdown",
    )

    audio_out_path = tts.synthesize(result["answer"], language=config.LANGUAGE_DEFAULT)
    if audio_out_path:
        with open(audio_out_path, "rb") as audio_file:
            await update.message.reply_voice(voice=audio_file)


def main():
    print(f"[DEBUG] Raw RENDER_DEPLOYMENT env value: {os.environ.get('RENDER_DEPLOYMENT', '<not set>')!r}")
    print(f"[DEBUG] Parsed RENDER_DEPLOYMENT = {RENDER_DEPLOYMENT}")

    if not config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env. Get one from @BotFather.")
        sys.exit(1)

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .build()
    )

    async def error_handler(update, context):
        print(f"[DEBUG] ERROR HANDLER FIRED: {context.error}")
        import traceback
        traceback.print_exception(type(context.error), context.error, context.error.__traceback__)

    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    if RENDER_DEPLOYMENT:
        if not RENDER_EXTERNAL_URL:
            print("ERROR: RENDER_EXTERNAL_URL not set. Render provides this automatically.")
            sys.exit(1)
        webhook_url = f"{RENDER_EXTERNAL_URL}/{config.TELEGRAM_BOT_TOKEN}"
        print(f"Jan Sahayak starting in WEBHOOK mode on port {PORT}...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=config.TELEGRAM_BOT_TOKEN,
            webhook_url=webhook_url,
        )
    else:
        print("Jan Sahayak starting in POLLING mode (local dev)... (Ctrl+C to stop)")
        app.run_polling()


if __name__ == "__main__":
    main()
