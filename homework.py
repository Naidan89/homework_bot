from json import JSONDecodeError
import logging
import os
import time

import requests
import telegram

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения в телеграм чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено в чат.')
    except telegram.TelegramError as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Запрос к API и возврат ответа в JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_statuses.status_code != requests.codes.ok:
            logger.error('Ошибка. status_code != 200')
            raise RuntimeError('Ошибка. status_code != 200')
        try:
            logger.info('Получен ответ от API')
            return homework_statuses.json()
        except JSONDecodeError as error:
            logger.error(f'Ошибка при формировании JSON: {error}')
    except requests.RequestException as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')


def check_response(response):
    """Проверка корректности ответа от API."""
    if type(response) is not dict:
        logger.error('Ошибка типа данных ответа.')
        raise TypeError('Ошибка типа данных ответа.')
    if 'homeworks' not in response:
        logger.error('Ошибка. В ответе нет элемента homeworks.')
        raise TypeError('Ошибка типа данных ответа.')
    if type(response.get('homeworks')) is not list:
        logger.error('Ошибка типа данных ответа.')
        raise TypeError('Ошибка типа данных ответа.')
    logger.info('Проверен ответ от API, ошибок нет.')
    try:
        response.get('homeworks')[0]
        return response.get('homeworks')
    except IndexError:
        logger.error('Ошибка. Ответ пустой.')
        raise TypeError('Ошибка типа данных ответа.')


def parse_status(homework):
    """Проверка статуса домашнего задания."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError:
        logger.error('Ошибка. "homework_name" отсутствует.')
        raise TypeError('Ошибка. "homework_name" отсутствует.')
    try:
        homework_status = homework.get('status')
    except KeyError:
        logger.error('Ошибка. "status" отсутствует.')
        raise TypeError('Ошибка. "status" отсутствует.')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        logger.error('Ошибка. "verdict" не соответствует значению.')
        raise KeyError('Ошибка. "verdict" не соответствует значению.')
    logger.info('Проверен статус домашней работы.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all((TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if check_tokens():
        logger.info('Переменные окружения проверены.')
    else:
        raise KeyError('Ошибка в обязательных переменных окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    hw_status_old = ''
    message_old = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)[0]
            if hw_status_old != homework.get('status'):
                message = parse_status(homework)
                send_message(bot, message)
                hw_status_old = homework.get('status')
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message_old != message:
                send_message(bot, message)
                message_old = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
