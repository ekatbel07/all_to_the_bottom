
Парсер логов для интернет магазина "Все на дно!"
Для запуска парсера логов и заполнения бд нужно ввести команду:

python parsers_logs.py "имя_файла_с_логами"(без кавычек)

Необходимо установить библиотеки:
pip install bokeh
pip install bottle
pip install pandas
pip install requests


Чтобы запустить веб-приложение введите команду: 

bokeh serve --show main.py


