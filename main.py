from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from excel_manager import ExcelManager
import logging
from pydub import AudioSegment
import whisper
import re
import os
from thefuzz import fuzz


# Путь на рабочий стол (пример для пользователя PC)
desktop_cache = r"C:\Users\PC\Desktop\.cache"
os.makedirs(desktop_cache, exist_ok=True)
os.environ["XDG_CACHE_HOME"] = desktop_cache

# Загружаем модель Whisper
model = whisper.load_model("base")

# Инициализация логгера
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Менеджер Excel
excel_manager = ExcelManager()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")

    eng, rus = excel_manager.get_random_pair()
    context.user_data["current_phrase"] = eng

    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n"
        f"Давайте потренируем ваше произношение:\n\n"
        f"🇬🇧 Произнесите: <b>{eng}</b>\n"
        f"🇷🇺 Перевод: <i>{rus}</i>\n\n"
        "Отправьте голосовое сообщение с вашим произношением!",
        parse_mode="HTML"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Вот, что я умею:\n\n"
        "/start — начать тренировку с новой фразой\n"
        "/next — следующая фраза\n"
        "/words — случайные слова для тренировки\n"
        "🎤 Отправь голосовое сообщение, чтобы я проверил произношение!"
    )


def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "current_phrase" not in context.user_data:
        await update.message.reply_text("Сначала используйте /start")
        return
    correct_phrase = "Well, I've been playing it since I was at school - since I was quite young, 'cos my dad was always very keen on it and he used to give me lessons, and then at university I joined a team and we used to play quite a lot.It's quite fashionable at the moment, actually, all over Europe it's becoming more fashionable and it's often difficult to book courts, you've got to get in there a week before. Urn I like it because it requires a lot of stamina, you've got to be fit, it's constant running right the way through and it doesn't take a long time."
    #correct_phrase = context.user_data["current_phrase"]

    voice_file = await update.message.voice.get_file()
    input_ogg = "input.ogg"
    input_wav = "input.wav"

    try:
        await voice_file.download_to_drive(input_ogg)
        sound = AudioSegment.from_file(input_ogg)
        sound.export(input_wav, format="wav")

        result = model.transcribe(input_wav, language="en")
        transcription = result["text"].strip()
        logger.info(f"Transcription: {transcription}")

        transcription_filtered = normalize_text(transcription)
        correct_filtered = normalize_text(correct_phrase)
        similarity = fuzz.token_sort_ratio(transcription_filtered, correct_filtered) / 100

        threshold = 0.8

        if similarity >= threshold:
            reply_text = (
                f"✅ Отлично! Вы правильно произнесли фразу:\n\n<b>{correct_phrase}</b>"
            )
        else:
            reply_text = (
                f"❌ Попробуйте ещё раз.\n\n"
                f"Вы сказали: <i>{transcription}</i>\n"
                f"Правильная фраза: <b>{correct_phrase}</b>\n"
                f"Похожесть (гибкое сравнение): {similarity:.2f}"
            )

        await update.message.reply_text(reply_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        await update.message.reply_text("Произошла ошибка при распознавании речи. Попробуйте ещё раз.")
    finally:
        if os.path.exists(input_ogg):
            os.remove(input_ogg)
        if os.path.exists(input_wav):
            os.remove(input_wav)


async def next_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eng, rus = excel_manager.get_random_pair()
    context.user_data["current_phrase"] = eng

    await update.message.reply_text(
        f"🇬🇧 Следующая фраза: <b>{eng}</b>\n"
        f"🇷🇺 Перевод: <i>{rus}</i>",
        parse_mode="HTML"
    )


async def words_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    random_words = excel_manager.get_random_words()
    word_list = '\n'.join(random_words)
    await update.message.reply_text(
        f"Список случайных слов для тренировки:\n\n<b>{word_list}</b>",
        parse_mode="HTML"
    )


def main():
    application = Application.builder().token("7571103626:AAFh5msmOyGXhlfMOUom2RtRb03xBOJnc6I").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("next", next_phrase))
    application.add_handler(CommandHandler("words", words_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    application.run_polling()


if __name__ == "__main__":
    main()
