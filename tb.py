import asyncio
import logging
import os
import time

from aiogram import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import BotCommand

from botusers import *
from rmq_sender import *

config = workconfig.read_config('config')
logger = logging.getLogger(__name__)


class UserState(StatesGroup):
    waiting_for_org = State()
    waiting_for_tel_number = State()
    user_registered = State()


# Регистрация команд, отображаемых в интерфейсе Telegram
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/user_register", description="Зарегистрироваться"),
        BotCommand(command="/start", description="Передать данные"),
        BotCommand(command="/cancel", description="Отменить текущее действие")
    ]
    await bot.set_my_commands(commands)


async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    curr_user = User()
    curr_code = str(message.from_user.id)
    if get_list_org_for_user_id(curr_user, curr_code):
        keyboard = types.InlineKeyboardMarkup()
        await message.answer(f"Привет, {curr_user.username}!")
        if len(curr_user.list_org) > 1:
            for org in curr_user.list_org:
                keyboard.add(types.InlineKeyboardButton(text=org.name, callback_data=org.inn))
            await message.answer("Выберите организацию", reply_markup=keyboard)
        else:
            for org in curr_user.list_org:
                await state.update_data(chosen_org=org.inn)
                await message.answer(f"Отправьте изображение или документ ({org.inn})")
        await UserState.waiting_for_org.set()
    else:
        await message.answer(f'Вы не зарегистрированы в системе. ({curr_code}).')


async def send_inn_value(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(chosen_org=call.data)
    await call.message.answer(f"Отправьте изображение или документ ({call.data})")


async def cmd_chose_org(message: types.Message, state: FSMContext):
    await state.finish()
    await state.update_data(chosen_org=message.text.lower())
    await message.answer("Организация выбрана!")


async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Действие отменено", reply_markup=types.ReplyKeyboardRemove())


async def cmd_user_register(message: types.Message):

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(text="Отправить номер телефона.", request_contact=True))
    await message.answer("Для отправки данных, нажмите кнопку внизу.", reply_markup=keyboard)


def watch_db_update(message: types.Message, user: types.User):
    full_filename = config.get('PathToDocs', 'path')+'\\domain.usr.json'
    if not os.path.exists(full_filename):
        print("Ошибка: файл domain.usr.json не найден")
        return
    timestamp = os.stat(full_filename).st_mtime
    i = 1
    while i < 5:
        time.sleep(1)
        i += 1
        if timestamp != os.stat(full_filename).st_mtime:
            if get_list_org_for_user_id(user, str(message.contact.user_id)):
                # await message.answer("Вы зарегистрированы.")
                # await cmd_start(message)
                return True
    # await message.answer("Ошибка регистрации. Свяжитесь с администратором")
    return False


async def cmd_start_user_register(message: types.Message, state: FSMContext):
    telegram_id: str
    if message.contact is not None:
        keyboard2 = types.ReplyKeyboardRemove()
        await message.answer('Номер принят...', reply_markup=keyboard2)
        user = User()
        # if not get_list_org_for_user_id(user, str(message.contact.user_id)):
        if get_list_org_for_user_phone(user, str(message.contact.phone_number)):
            user.telegram_id = str(message.contact.user_id)
            user.phone = str(message.contact.phone_number)
            # user.username = message.contact.first_name + " " + message.contact.last_name
            data = json.dumps({'tgid': user.telegram_id, 'phone': user.phone}, indent=4, ensure_ascii=False)
            send_data_to_rmq(data=data, routing_key='1cc.from.tg_user_register')
            await message.answer('Запрос на регистрацию принят. Ожидайте подтверждения.')
            if watch_db_update(message, user):
                await message.answer("Вы зарегистрированы.")
                await cmd_start(message, state)
            else:
                await message.answer("Ошибка регистрации. Свяжитесь с администратором")
        else:
            await message.answer('Ошибка. Отказ в обслуживании')


async def check_path(pathname: str):
    conf_path = config.get('PathToDocs', 'path')
    curr_path = os.path.join(conf_path, pathname)
    if not os.path.exists(curr_path):
        os.makedirs(curr_path)
    return curr_path


async def download_photo(message: types.Message, state: FSMContext):
    curr_path = config.get('PathToDocs', 'path_temp')
    if message.photo is not None:
        file_id = message.photo[-1].file_id
        await message.photo[-1].download(destination_file=curr_path + '\\' + file_id+'.jpg')
        with open(curr_path + '\\' + file_id+'.jpg', 'rb') as myfile:
            file_bytes = myfile.read()
        userdata = await state.get_data()
        send_data_to_rmq(data=file_bytes,  routing_key=f'1cc.from.tg_data_accept_'
                                                       f'{message.from_user.id}_{userdata["chosen_org"]}')
        await message.answer("OK. Фото получено.")
        print('Получено изображение от ' + message.chat.first_name + ' ' + message.chat.last_name + ' с кодом: ' + str(
            message.message_id))


async def download_doc(message: types.Message,  state: FSMContext):
    curr_path = config.get('PathToDocs', 'path_temp')
    if message.document is not None:
        await message.document.download(destination=curr_path + message.document.file_name)
        with open(curr_path + '\\' + message.document.file_name, 'rb') as myfile:
            file_bytes = myfile.read()
        userdata = await state.get_data()
        send_data_to_rmq(data=file_bytes,
                         routing_key=f'1cc.from.tg_data_accept_{message.from_user.id}_{userdata["chosen_org"]}')
        await message.answer("OK. Документ получен.")
        print('Получен документ от ' + message.chat.first_name + ' ' + message.chat.last_name + '_' +
              message.document.file_name)


def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands="start", state="*")
    dp.register_message_handler(cmd_user_register, commands="user_register", state="*")
    dp.register_message_handler(cmd_start_user_register, content_types=['contact'], state="*")
    dp.register_message_handler(cmd_chose_org, commands="chose_org", state="*")
    dp.register_message_handler(cmd_cancel, commands="cancel", state="*")
    dp.register_callback_query_handler(send_inn_value, state="*")
    dp.register_message_handler(download_photo, content_types=['photo'], state=UserState.waiting_for_org)
    dp.register_message_handler(download_doc, content_types=[types.ContentType.DOCUMENT],
                                state=UserState.waiting_for_org)


async def main():
    # Настройка логирования в stdout
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger.info("Starting bot")

    # Парсинг файла конфигурации
    config = workconfig.read_config('config')
    # Объявление и инициализация объектов бота и диспетчера
    bot = Bot(token=config.get('TokenForTelegramBot', 'token'))
    dp = Dispatcher(bot, storage=MemoryStorage())

    # Регистрация хэндлеров
    # register_handlers_registry(dp)
    # register_handlers_send_data(dp)

    # Установка команд бота
    await set_commands(bot)
    register_handlers_common(dp)
    # Запуск поллинга
    await dp.skip_updates()  # пропуск накопившихся апдейтов (необязательно)
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
