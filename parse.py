from grab import Grab
import xlrd, os, re, json, logging
from urllib.request import urlretrieve
from time import sleep
from peewee import *
import datetime
from config import *
from telegram.ext import Updater,Job
from telegram import (ReplyKeyboardMarkup)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


u = Updater(token)
j = u.job_queue

# Оповещение пользователей
def alarmAll(bot, job):
    for follower_item in Follower.select():
        bot.sendMessage(follower_item.chatId,
                    text=job.context,
                    reply_markup=ReplyKeyboardMarkup(schelude_keyboard, one_time_keyboard=True))

# Получаем даты расписания из файла excel
def getDates(file):
    sh = file.sheet_by_index(0)
    cell = sh.cell_value(rowx=3, colx=0)
    dates = re.findall(r'\d{2}.\d{2}.\d{4}', cell)
    dateArr = []
    for date in dates:
        dateArr.append(date.split('.'))
    dateStart = datetime.datetime(int(dateArr[0][2]), int(dateArr[0][1]), int(dateArr[0][0]), 00, 00)
    dateStart = dateStart - datetime.timedelta(days=dateStart.weekday())
    dateEnd = dateStart + datetime.timedelta(days=6)
    dateMid = dateStart + datetime.timedelta(days=3)
    datesOut = [dateStart,dateEnd,dateMid]
    return datesOut

# Сбор расписания из файла excel
def getSchelude(file):
    sh = file.sheet_by_index(0)
    schelude = {}
    cellsArr = ['']
    for i in range(0,35):
        cell = sh.cell_value(rowx=4, colx=i) 
        if cell != '':
            if cell in cellsArr:
                cell += ' (2)'
                
            cell = re.sub('[ \f\t\v]{1,}$', "", str(cell))
            cellsArr.append(cell)
            schelude[str(cell)] = {}
            for day in day_cell_ranges:
                schelude[str(cell)][str(day[0])] = []
                for d in range(day[1],day[2]+1):
                    obj = re.split('\s{3,}', sh.cell_value(rowx=d, colx=i))
                    schelude[str(cell)][str(day[0])].append(obj)
    return schelude

class MainParser:
    def __call__(self):
        while True:
            try:
                # Конектимся к сайту
                g = Grab()
                g.go('http://vkk.edu.ru/student/schedule/')
                
                # Начинаем перебирать елементы
                for elem in g.doc.select('//span[@class="file xls"]/a/@href'):
                    link = "http://vkk.edu.ru{}".format(elem.text())
                    fileName = elem.text().split('/')[-1]
                    # Если такой файл не присутствует в базе, то добавляем
                    fileExists = Schedule.select().where(Schedule.name == fileName).exists()
                    if fileExists != True:
                        # Скачиваем файл расписания и временно сохраняем
                        urlretrieve(link, fileName)
                        # Открываем первую книгу и получаем даты и само расписание
                        rb = xlrd.open_workbook(fileName,formatting_info=False)
                        dates = getDates(rb)
                        fileData = getSchelude(rb)
                        # Удаляем расписания, присутствующие в БД на этой неделе
                        exists = Schedule.select().where(
                                Schedule.middleDate.between(dates[0],dates[1])).exists()
                        if exists:
                            Schedule.delete().where(Schedule.middleDate.between(dates[0],dates[1]))
                        # Создаем расписание в БД
                        Schedule.create(
                                        name=fileName, 
                                        startDate=dates[0], 
                                        endDate=dates[1], 
                                        middleDate=dates[2], 
                                        data=json.dumps(fileData)
                                    )
                        # Оповещяем пользователей о новом расписании или об обвнолении, если расписание
                        # этой недели уже присутствовало в БД
                        if exists:
                            j.put(Job(alarmAll, 0, repeat=False, context='Обновлено расписание\nС {0} по {1}'
                             .format(dates[0].strftime("%d.%m.%Y"),dates[1].strftime("%d.%m.%Y"))))
                        else:
                            j.put(Job(alarmAll, 0, repeat=False, context='Опубликовано новое расписание\nС {0} по {1}'
                             .format(dates[0].strftime("%d.%m.%Y"),dates[1].strftime("%d.%m.%Y"))))
                        # Удаляем расписание
                        os.remove(fileName)

            except BaseException as e:
                print("Error: {}".format(e))

            sleep(parse_pause)