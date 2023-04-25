import aiohttp
import logging
import sqlite3
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters

BOT_TOKEN = '5874093840:AAHRFXHGso9n7PkhgA6ZxFPmJh2NdU7zX2Y'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

reply_keyboard = [['/address', '/phone'],
                  ['/site', '/help']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)


# Основная задача кода - нахождение места на карте
async def geocoder(update, context):
    geocoder_uri = "http://geocode-maps.yandex.ru/1.x/"
    response = await get_response(geocoder_uri, params={
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "format": "json",
        "geocode": update.message.text
    })

    toponym = response["response"]["GeoObjectCollection"][
        "featureMember"][0]["GeoObject"]
    ll, spn = get_ll_spn(toponym)

    static_api_request = f"http://static-maps.yandex.ru/1.x/?ll={ll}&spn={spn}&l=map"
    await context.bot.send_photo(
        update.message.chat_id,  # Идентификатор чата. Куда посылать картинку.
        # Ссылка на static API, по сути, ссылка на картинку.
        static_api_request,
        caption="Нашёл:"
    )


async def get_response(url, params):
    logger.info(f"getting {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


# Начало и запись id в базу данных
async def start(update, context):
    await update.message.reply_text("Я мультибот. Чтобы узнать все мои возможности нажмите /help .", reply_markup=markup)
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS login_id(
        id INTEGER
    )""")
    connect.commit()

    people_id = update.message.chat.id
    cursor.execute(f"SELECT id FROM login_id WHERE id = {people_id}")
    data = cursor.fetchone()
    if data is None:
        user_id = [update.message.chat.id]
        cursor.execute("INSERT INTO login_id VALUES(?);", user_id)
        connect.commit()


# Удаление id из базы данных
async def delete_id(update, context):
    await update.message.reply_text("Вы были удалены из списка пользователей.")
    connect = sqlite3.connect('users.db')
    cursor = connect.cursor()
    people_id = update.message.chat.id
    cursor.execute(f"DELETE FROM login_id WHERE id = {people_id}")
    connect.commit()


# Закрытие клавиатуры бота
async def close_keyboard(update, context):
    await update.message.reply_text("Ok", reply_markup=ReplyKeyboardRemove())


# Функция помощи пользователю
async def help(update, context):
    await update.message.reply_text("Я мультибот."
                                    "После нажатия старт вы можете ввести название любой точки мира,"
                                    "и я отправлю фотографию с этим местом на карте."
                                    "Вот список доступных команд:"
                                    " /address, /phone, /site, /work_time, /start,"
                                    " /help, /stickers, /delete_id, /sales, /books, /films")


# Функции с полезной для пользователя информацией
async def address(update, context):
    await update.message.reply_text("Адрес cоздателя: 'Закрыт для всеобщего доступа'")


async def stickers(update, context):
    await update.message.reply_text("Найти стикеры для телеграма вы можете здесь: https://chpic.su/ru/stickers")


async def phone(update, context):
    await update.message.reply_text("Телефон создателя: +7-952-594-84-78."
                                    " Связаться можно через Телеграмм,"
                                    " на звонки не отвечает!")


async def site(update, context):
    await update.message.reply_text(
        "Сайт: http://www.yandex.ru/company,"
        " оказали помощь в создании")


async def sales(update, context):
    await update.message.reply_text(
        "Канал: https://t.me/rzdticket,"
        " в нём вы сможете найди скидки на билеты на поезда, автобусы, самолёты")


async def books(update, context):
    await update.message.reply_text(
        "Канал: https://t.me/flibusta,"
        "  для любителей чтения")


async def films(update, context):
    await update.message.reply_text(
        "Канал: https://t.me/Filmy_Kinomania,"
        "  для любителей кино")


async def work_time(update, context):
    await update.message.reply_text(
        "Время работы бота: круглосуточно, если запущена программа.")


# Запуск Функций
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, geocoder))
    application.add_handler(CommandHandler("address", address))
    application.add_handler(CommandHandler("phone", phone))
    application.add_handler(CommandHandler("site", site))
    application.add_handler(CommandHandler("work_time", work_time))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("close", close_keyboard))
    application.add_handler(CommandHandler("stickers", stickers))
    application.add_handler(CommandHandler("delete_id", delete_id))
    application.add_handler(CommandHandler("sales", sales))
    application.add_handler(CommandHandler("books", books))
    application.add_handler(CommandHandler("films", films))
    application.run_polling()


# Нахождение координат для получения картинки
def get_ll_spn(toponym):
    # Координаты центра топонима:
    toponym_coodrinates = toponym["Point"]["pos"]
    # Долгота и Широта :
    toponym_longitude, toponym_lattitude = toponym_coodrinates.split(" ")

    # Собираем координаты в параметр ll
    ll = ",".join([toponym_longitude, toponym_lattitude])

    # Рамка вокруг объекта:
    envelope = toponym["boundedBy"]["Envelope"]

    # левая, нижняя, правая и верхняя границы из координат углов:
    l, b = envelope["lowerCorner"].split(" ")
    r, t = envelope["upperCorner"].split(" ")

    # Вычисляем полуразмеры по вертикали и горизонтали
    dx = abs(float(l) - float(r)) / 2.0
    dy = abs(float(t) - float(b)) / 2.0

    # Собираем размеры в параметр span
    span = f"{dx},{dy}"

    return ll, span


if __name__ == '__main__':
    main()
