import asyncio
import json
import logging
import os
from tkinter import messagebox

from async_timeout import timeout

import gui

logger = logging.getLogger('Logger send message to chat')


class InvalidToken(Exception):
    pass


def check_user_info(file_path):
    if not os.path.exists(file_path):
        return False
    with open(file_path, 'r', encoding='utf-8') as file:
        user_info = json.load(file)

    if 'nickname' not in user_info and 'account_hash' not in user_info:
        return False
    if not user_info['nickname'] and not user_info['account_hash']:
        return False
    return user_info['account_hash']


async def register(host, port, nickname, user_file_path, wait_timeout=10):
    writer = None
    account_hash = check_user_info(user_file_path)
    if account_hash:
        logger.info(f'Данные пользователя есть в файле - {user_file_path}')
        return account_hash
    try:
        async with timeout(wait_timeout):
            reader, writer = await asyncio.open_connection(host, port)
            logger.debug(await reader.readline())

            writer.write('\n'.encode())
            await writer.drain()

            logger.debug(await reader.readline())
            writer.write(f'{nickname.strip()}\n'.encode())
            await writer.drain()

            chat_info = await reader.readline()
            user_info = json.loads(chat_info.decode())

            with open(user_file_path, mode='w', encoding='utf-8') as json_file:
                json.dump(user_info, json_file)

            logger.info(f'Пользователь создан, данные записаны в файл - {user_file_path}')

    except asyncio.exceptions.TimeoutError as error:
        logger.error(f'Тайм-аут при подключении к серверу: {error}', exc_info=True)
        return error
    except asyncio.exceptions.CancelledError as error:
        logger.error('Подключение было отменено', exc_info=True)
        return error
    except Exception as error:
        logger.error(f'Ошибка при регистрации: {error}', exc_info=True)
        return error

    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
    return account_hash


async def authorise(host, port, token, queue, watchdog_queue):
    writer = None
    try:
        await watchdog_queue.put('Prompt before auth')
        reader, writer = await asyncio.open_connection(host, port)
        logger.debug(await reader.readline())

        writer.write(f'{token}\n'.encode())
        await writer.drain()

        response = await reader.readline()
        chat_response = json.loads(response)
        if chat_response is None:
            raise InvalidToken('Проверьте токен, сервер его не узнал')

        event = gui.NicknameReceived(chat_response["nickname"])
        queue.put_nowait(event)
        await watchdog_queue.put('Authorization done')
        logger.info(f'Выполнена авторизация. Пользователь {chat_response["nickname"]}.')
        return True

    except asyncio.exceptions.TimeoutError as error:
        logger.error(f'Тайм-аут при подключении к серверу: {error}', exc_info=True)
        messagebox.showerror('Тайм-аут при подключении к серверу:', f'{error}')

    except asyncio.exceptions.CancelledError:
        logger.error('Подключение было отменено', exc_info=True)
        messagebox.showerror('Ошибка при авторизации', 'Подключение было отменено')

    except InvalidToken as error:
        logger.error('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
        messagebox.showerror('Ошибка при авторизации', f'{error}')

    except Exception as error:
        logger.error(f'Ошибка при авторизации: {error}', exc_info=True)
        messagebox.showerror('Ошибка при авторизации', f'{error}')
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
    return False


async def submit_message(host, port, message, token, watchdog_queue, status_updates_queue):
    writer = None
    if not token:
        logger.info('Необходимо выполнить авторизацию перед отправкой сообщения.')
        return
    try:
        reader, writer = await asyncio.open_connection(host, port)
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
        logger.debug(await reader.readline())
        writer.write(f'{token}\n'.encode())
        await writer.drain()

        check_token = await reader.readline()
        if json.loads(check_token) is None:
            logger.info('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
            logger.debug(await reader.readline())
        else:
            logger.debug(await reader.readline())
            writer.write(f'\n'.encode())
            await writer.drain()

            logger.debug(await reader.readline())

            writer.write(f'{message.strip()}\n\n'.encode())
            await writer.drain()
            await watchdog_queue.put('Message sent')
            logger.debug('Сообщение отправлено.')
    except asyncio.exceptions.TimeoutError as error:
        logger.error(f'Тайм-аут при подключении к серверу: {error}', exc_info=True)
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
        raise error
    except asyncio.exceptions.CancelledError as error:
        logger.error('Подключение было отменено', exc_info=True)
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
        raise error
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
        raise error
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
