Сервер и клиент группового чата были разработаны на языке Python 3.5.2

Исходный код сервера находится в файле server.py

Исходный код клиента находится в файле client.py

# База данных
В качестве базы данных используется mysqlite3. Если файла базы данных нет в папке с сервером, то программа автоматически создает этот файл вместе со всей схемой
# Конфигурационные файлы
Для сервера и клиента используются конфигурационные файлы, которые называются serverSetup.json и clientSetup.json соответствено. Эти файл конфигурации нужно расположить в одной папке с приложением, чтобы программа смогла его прочитать. Если конфигурационных файлов не будет или он окажется не корректен, то будут использованы стандартные значения.
## Конфигурационный файл для Клиента
```
{
    "buffer": <Количество байт, которые принимает сервер за одно сообщение>,
    "ip": "<ip адрес сервера>",
    "port": <Номер порта на котором работает сервер>,
    "servername": "<Имя сервера, которое будет отображатся в чате>",
    "dbName": "<Имя файла базы данных>"
}
```
## Конфигурационный файл для Сервера
```
{
    "buffer": <Количество байт, которые принимает клиент за одно сообщение>,
    "ip": "<К какому ip адресу подключается клиент>",
    "port": <К какому порту подключается клиент>
}
```