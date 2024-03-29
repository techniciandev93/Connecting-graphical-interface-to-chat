# Подключаемся к чату через Интерфейс

Этот скрипт предназначен для подключения и отправки сообщений в чат через интерфейс, а также для сохранения переписки в файл.

## Как установить

Python 3.10 должен быть уже установлен.
Затем используйте `pip` (или `pip3`, есть конфликт с Python2) для установки зависимостей:
```
pip install -r requirements.txt
```

Создайте файл .env в корневой директории проекта и добавьте переменные окружения:
```
HOST=Укажи хост чата. По умолчанию minechat.dvmn.org
READ_CHAT_PORT=Укажите порт чата для получения сообщений. По умолчанию 5000
SEND_MESSAGE_PORT=Укажите порт чата для отправки сообщений. По умолчанию 5050

TOKEN=Укажите токен для чата. Если нет токена то сначало нужно зарегистрироваться, 
 и данные для авторизации будут взяты из файла.

HISTORY_FILE_PATH=Укажите путь к файлу куда будет сохраняться переписка чата. 
По умолчанию будет сохраняться переписка в файл chat_histry.txt в корне проекта.

USER_FILE_PATH=Укажите путь к файлу куда будут сохраняться данные для авторизации.
По уолчанию будет сохраняться в файл user.json в корне проекта.
```

## Как запустить
### register.py
Для регистрации в чате запустите register.py, укажите в поле свой nickname и нажмите кнопку Зарегистрироваться.
```
python register.py
```

### main.py
Для подключения к чату и отправки сообщений через интерфейс, запустите main.py
```
python main.py
```