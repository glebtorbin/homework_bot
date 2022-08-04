
import logging
import os
import sys
import time
import telegram
from http import HTTPStatus

import requests
from dotenv import load_dotenv

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TELEGRAM_RETRY_TIME: int = 600
ENDPOINT = os.getenv('ENDPOINT')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO,
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Функция отправки сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except exceptions.MessageSendError as error:
        logger.error(f'Не получается отправить сообщние: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except exceptions.APIUnexpectedHTTPStatus:
        logger.error('Сбой при запросе к эндпоинту')
    if response.status_code != HTTPStatus.OK:
        message = 'Не получается подключиться к ENDPOINT'
        logger.error(message)
        raise exceptions.APIUnexpectedHTTPStatus(message)
    try:
        return response.json()
    except exceptions.JSONError:
        logger.error('Формат не Json')


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info('Проверка корректности API...')
    try:
        list_of_homeworks = response['homeworks']
    except KeyError as error:
        message = f'Нет доступа по ключу: {error}'
        logger.error(message)
        raise exceptions.KeyNotFoundError(message)
    if not isinstance(list_of_homeworks, list):
        message = 'homeworks не является списком'
        logger.error(message)
        raise exceptions.APIFormatError(message)
    return list_of_homeworks


def parse_status(homework: dict):
    """Извлекает из информации о конкретной домашней работе статус."""
    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        message = f'Ошибка доступа по ключу homework_name: {error}'
        logger.error(message)
    try:
        homework_status = homework['status']
    except KeyError as error:
        message = f'Ошибка доступа по ключу status: {error}'
        logger.error(message)
    verdict = HOMEWORK_VERDICTS[homework_status]
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Ключ из homewor_status не обнаружен в  HOMEWORK_VERDICTS'
        logger.error(message)
        raise exceptions.KeyNotFoundError(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют переменные окружения'
        logger.critical(message)
        raise exceptions.UnavailableToken(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    last_hw_status = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
        except exceptions.APIUnexpectedHTTPStatus as error:
            logger.error(error)
        try:
            homeworks = check_response(response)
            hw_status = homeworks[0].get('status')
            if hw_status != last_hw_status:
                last_hw_status = hw_status
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Статус не обновлен')

        except exceptions.NotWorkingError as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(TELEGRAM_RETRY_TIME)


if __name__ == '__main__':
    main()
