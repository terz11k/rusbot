# ✅ RUSGO — Telegram-бот с GPT на Python (aiogram)
# Описание: RUSGO — это ваш надёжный помощник в повседневных вопросах, связанных с жизнью в России.
# Он подскажет, где оформить документы, как найти жильё, что делать со справками, симками и картами.
# Всё просто, по-человечески и с уважением. Работает на русском, узбекском и таджикском языках.
# Можно выбрать язык, задать вопрос, получить секретные советы, узнать как устроиться и не потеряться в новой обстановке.
# Бот отвечает доброжелательно, без занудства, и всегда старается объяснить так, чтобы было понятно каждому.

from aiogram import Bot, Dispatcher, executor, types
import asyncio
import logging
from openai import OpenAI
import random
import langdetect
from deep_translator import GoogleTranslator
import aiohttp

# === ТВОИ ДАННЫЕ ===


client = OpenAI(api_key=OPENAI_API_KEY)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

user_languages = {}
user_sessions = {}  # user_id: {"messages": [...], "last_active": datetime}

# === ПРИВЕТСТВИЕ И ВЫБОР ЯЗЫКА ===
@dp.message_handler(commands=["start"])
async def send_language_choice(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🇷🇺 Русский", "🇺🇿 O'zbekcha", "🇹🇯 Тоҷикӣ")
    await message.answer("👋 Привет! Я — RUSGO. Помогаю разобраться в повседневных вопросах по жизни в России.\n\nВыбери язык, на котором тебе удобно общаться:", reply_markup=keyboard)

# === ОБРАБОТКА ВЫБОРА ЯЗЫКА ===
@dp.message_handler(lambda message: message.text in ["🇷🇺 Русский", "🇺🇿 O'zbekcha", "🇹🇯 Тоҷикӣ"])
async def set_language(message: types.Message):
    lang_map = {
        "🇷🇺 Русский": "ru",
        "🇺🇿 O'zbekcha": "uz",
        "🇹🇯 Тоҷикӣ": "tg"
    }
    user_languages[message.from_user.id] = lang_map[message.text]

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📄 Хочу сделать регистрацию — как?", "📑 Как оформить патент на работу?")
    keyboard.row("🏠 Где найти жильё или прописку?", "🚑 Где пройти медосмотр быстро?")
    keyboard.row("📱 Где купить симку без проблем?", "💳 Как открыть карту в банке?")
    keyboard.row("🔍 Найти рядом")
    keyboard.row("✍️ Задать свой вопрос")

    await message.answer("✅ Язык сохранён. Теперь можешь выбрать нужную тему или задать свой вопрос:", reply_markup=keyboard)

# === GPT-ответ ===
@dp.message_handler()
async def gpt_reply(message: types.Message):
    try:
        from datetime import datetime, timedelta

        user_text = message.text
        from_user = message.from_user.id
        now = datetime.now()

        session = user_sessions.get(from_user)
        if not session or now - session.get("last_active", now) > timedelta(minutes=30):
            session = {
                "messages": [{
                    "role": "system",
                    "content": "Ты Telegram-бот RUSGO. Помогаешь людям, оказавшимся в России, решать повседневные и юридические вопросы — как устроиться, где оформить документы, как продлить регистрацию, оформить патент, сделать медсправку, найти жильё и т.д. Если пользователь пишет ‘патент’, по умолчанию считай, что речь идёт о разрешении на работу. Отвечай просто, по-человечески, как опытный человек, который знает реальные схемы. Не морализируй."
                }]
            }

        session["messages"].append({"role": "user", "content": user_text})
        session["last_active"] = now
        user_sessions[from_user] = session

        if any(word in user_text.lower() for word in ["хочу кафе", "где поесть", "где кафе", "кафе рядом"]):
            query = "кафе Пушкино"
            url = f"https://search-maps.yandex.ru/v1/?text={query}&type=biz&lang=ru_RU&apikey={YANDEX_API_KEY}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()

            features = data.get("features", [])[:3]
            if not features:
                await message.answer("😔 Не нашёл кафе поблизости. Попробуй уточнить запрос.")
                return

            response_text = "☕ Вот несколько кафе рядом:\n\n"
            for place in features:
                name = place["properties"]["CompanyMetaData"]["name"]
                address = place["properties"]["CompanyMetaData"].get("address", "Адрес неизвестен")
                phone = place["properties"]["CompanyMetaData"].get("Phones", [{}])[0].get("formatted", "")
                response_text += f"📍 {name}\n📬 {address}\n📞 {phone}\n\n"

            await message.answer(response_text)
            return

        lang_code = user_languages.get(message.from_user.id, "ru")

        if lang_code != "ru":
            user_text = GoogleTranslator(source='auto', target='ru').translate(user_text)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=session["messages"]
        )
        reply = response.choices[0].message.content
        session["messages"].append({"role": "assistant", "content": reply})

        suffixes = [
            "",
            "\n\nЕсли что — напиши, брат, я подскажу ещё.",
            "\n\nЕсли не понял — скажи проще, я объясню по-человечески.",
            "\n\nНадо будет — разберёмся как надо, брат."
        ]
        reply += random.choice(suffixes)

        if lang_code != "ru":
            reply = GoogleTranslator(source='ru', target=lang_code).translate(reply)

        await message.answer(reply)
    except Exception as e:
        await message.answer("⚠️ Произошла ошибка при ответе. Попробуй позже.")
        print(e)

# === ЯНДЕКС ПОИСК ===
@dp.message_handler(commands=["найти"])
async def find_places(message: types.Message):
    try:
        query = message.get_args()
        if not query:
            await message.answer("❗ Укажи, что искать. Пример: /найти медосмотр Москва")
            return

        url = f"https://search-maps.yandex.ru/v1/?text={query}&type=biz&lang=ru_RU&apikey={YANDEX_API_KEY}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        features = data.get("features", [])[:3]
        if not features:
            await message.answer("😔 Ничего не нашёл. Попробуй уточнить запрос.")
            return

        response_text = "🔍 Нашёл вот что:\n\n"
        for place in features:
            name = place["properties"]["CompanyMetaData"]["name"]
            address = place["properties"]["CompanyMetaData"].get("address", "Адрес неизвестен")
            phone = place["properties"]["CompanyMetaData"].get("Phones", [{}])[0].get("formatted", "")
            response_text += f"📍 {name}\n📬 {address}\n📞 {phone}\n\n"

        await message.answer(response_text)

    except Exception as e:
        await message.answer("⚠️ Ошибка при поиске. Попробуй позже.")
        print(e)

@dp.message_handler(lambda message: message.text == "🔍 Найти рядом")
async def handle_find_button(message: types.Message):
    await message.answer("✍️ Напиши, что именно хочешь найти и в каком городе.\n\nНапример:\n/найти медосмотр Москва")

# === ЗАПУСК ===
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

