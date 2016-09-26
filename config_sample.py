from peewee import *

# Доступные группы
avib_groups = ["ИС","К","Г","Р","Б","Ю","ТОП"]
# Интервалы строк относительно дня недели (пн,вт,ср,чт,пт)
day_cell_ranges = [["ПН",8,11],["ВТ",12,15],["СР",16,19],["ЧТ",20,23],["ПТ",24,27]]

# Количество столбцов в расписании
col_range = 33

# Вау, токен
token = 'token'

# Вау, еще один токен
botan_token = 'Botan token'

# Стандартная кнопка после сообщения
schelude_keyboard = [['📋 Получить расписание 📋']]

# Частота обновления сайта (секунды)
parse_pause = 600

# База данных
db = SqliteDatabase('vkk.db')

# Таблица расписаний
class Schedule(Model):
    name = CharField()
    startDate = DateField()
    endDate = DateField()
    middleDate = DateField()
    data = CharField()

    class Meta:
        database = db

# Таблица подписчиков
class Follower(Model):
    name = CharField()
    chatId = CharField()
    active = BooleanField()
    
    class Meta:
        database = db