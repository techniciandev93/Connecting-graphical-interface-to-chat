import asyncio
import logging
import os
import socket
import sys
from datetime import datetime

import aiofiles
import exceptiongroup

from anyio import create_task_group, run
from async_timeout import timeout
from environs import Env

import gui
from send_message_to_chat import submit_message, authorise, check_user_info

logger = logging.getLogger('watchdog_logger')


async def read_msgs(host, port, queue, file_queue, status_queue, watchdog_queue, wait_timeout=10.0):
    writer = None
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            while not reader.at_eof():
                try:
                    async with timeout(wait_timeout):
                        message = await reader.readline()
                        timestamp = datetime.now().strftime("[%d.%m.%y %H:%M]")
                        formatted_message = f"{timestamp} {message.decode()}"
                        queue.put_nowait(formatted_message)
                        file_queue.put_nowait(formatted_message)
                        status_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
                        await watchdog_queue.put('New message in chat')

                except asyncio.IncompleteReadError:
                    logger.error('Соединение неожиданно прервалось.', exc_info=True)
                    status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
                    break

                except asyncio.CancelledError:
                    logger.error('Соединение отменено.')
                    status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
                    break

                except asyncio.TimeoutError:
                    logger.error(f'Соединение потеряно.')
                    status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
                    await asyncio.sleep(5)
                    continue

        except Exception as error:
            logger.error(f'Произошло Exception {error}.',  exc_info=True)
            status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
            await asyncio.sleep(5)
            continue

        finally:
            if writer is not None:
                logger.info('Соединение закрыто.')
                status_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
                writer.close()
                await writer.wait_closed()
                break


async def save_messages(file_path, queue):
    async with aiofiles.open(file_path, mode='a') as history_file:
        while True:
            message = await queue.get()
            await history_file.write(message)
            await history_file.flush()
            queue.task_done()


async def send_msgs(host, port, token, queue, watchdog_queue, status_updates_queue):
    while True:
        message = await queue.get()
        await submit_message(host, port, message, token, watchdog_queue, status_updates_queue)


async def watch_for_connection(watchdog_queue, wait_timeout=10.0 * 60):
    while True:
        try:
            async with timeout(wait_timeout):
                message = await watchdog_queue.get()
                timestamp = datetime.now().strftime('[%s]')
                logger.debug(f'{timestamp} Connection is alive. Source: {message}')
                watchdog_queue.task_done()
        except asyncio.TimeoutError:
            timestamp = datetime.now().strftime('[%s]')
            logger.debug(f'{timestamp} {wait_timeout}s timeout is elapsed.')
            raise ConnectionError('Connection timeout')


async def keep_connection_alive(host, port, token, watchdog_queue, status_updates_queue, ping_pong_timeout=15,
                                ping_pong_interval=10):
    while True:
        try:
            async with timeout(ping_pong_timeout):
                await submit_message(host, port, "", token, watchdog_queue, status_updates_queue)
            watchdog_queue.put_nowait('Ping message was successful')
        except socket.gaierror:
            watchdog_queue.put_nowait('Connection lost!')
        await asyncio.sleep(ping_pong_interval)


async def main(host, read_message_chat_port, send_message_port, token, history_file_path):
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    file_for_message_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    check_authorise = await authorise(host, send_message_port, token, status_updates_queue, watchdog_queue)
    if not check_authorise:
        raise

    if os.path.exists(history_file_path):
        async with aiofiles.open(history_file_path, mode='r') as history_file:
            async for line in history_file:
                await messages_queue.put(line)

    async with create_task_group() as tg:
        tg.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
        tg.start_soon(read_msgs, host, read_message_chat_port, messages_queue, file_for_message_queue,
                      status_updates_queue, watchdog_queue)
        tg.start_soon(save_messages, history_file_path, file_for_message_queue)
        tg.start_soon(send_msgs, host, send_message_port, token, sending_queue, watchdog_queue, status_updates_queue)
        tg.start_soon(watch_for_connection, watchdog_queue),
        tg.start_soon(keep_connection_alive, host, send_message_port, token, watchdog_queue, status_updates_queue)

if __name__ == '__main__':
    env = Env()
    env.read_env()

    chat_host = env.str('HOST', 'minechat.dvmn.org')
    read_chat_port = env.str('READ_CHAT_PORT', '5000')
    send_message_chat_port = env.str('SEND_MESSAGE_PORT', '5050')
    chat_token = env.str('TOKEN', None)
    chat_history_file_path = env.str('HISTORY_FILE_PATH', 'chat_history.txt')
    user_file_path = env.str('USER_FILE_PATH', 'user.json')

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger.setLevel(logging.INFO)

    if not chat_token:
        chat_token = check_user_info(user_file_path)

    try:
        run(main, chat_host, read_chat_port, send_message_chat_port, chat_token, chat_history_file_path)
    except exceptiongroup.ExceptionGroup as exc:
        for sub_exception in exc.exceptions:
            if isinstance(sub_exception, exceptiongroup.ExceptionGroup):
                for sub_sub_exception in sub_exception.exceptions:
                    if isinstance(sub_sub_exception, gui.TkAppClosed):
                        sys.exit()
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.exit()
