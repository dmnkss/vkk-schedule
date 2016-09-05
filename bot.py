from peewee import *
from config import *
from telegram import (ReplyKeyboardMarkup)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
import json
import datetime
import logging
import botan

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Хэш запросов для работы в БД во время диалога
querys = {}  

WEEK, GROUP, COURSE, DAY = range(4)

def splitArr(arr, size):
     arrs = []
     while len(arr) > size:
         pice = arr[:size]
         arrs.append(pice)
         arr   = arr[size:]
     arrs.append(arr)
     return arrs

def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)

# Ветка получения расписания
def get(bot, update):
    id = update.message.chat_id
    querys[id] = {}
    reply_keyboard = [['Текущая неделя'],['Следующая неделя']]
    bot.sendMessage(update.message.chat_id,
                    text='Выберите неделю 🗓',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    
    botan.track(token=botan_token, uid=update.message.from_user.id, message=update.message.text, name='Get Schedule')

    return WEEK


def week(bot, update):
    id = update.message.chat_id
    text = update.message.text

    # Проверяем правильность ввода недели
    # При неправильном вводе отменяем разговор
    continueConv = False
    if text == 'Текущая неделя':
        dateStart = datetime.date.today()
        dateStart = dateStart - datetime.timedelta(days=dateStart.weekday())
        dateEnd = dateStart + datetime.timedelta(days=6)
        querys[id]['week'] = [dateStart,dateEnd]
        isExists = Schedule.select().where(Schedule.middleDate.between(dateStart,dateEnd)).exists()
        if isExists:
            continueConv = True
        else:
            bot.sendMessage(update.message.chat_id,
                        text='Расписание на текущую неделю недоступно')
            
    elif text == 'Следующая неделя':
        dateNow = datetime.date.today()
        dateStart = next_weekday(dateNow,0)
        dateEnd = next_weekday(dateStart,6)
        querys[id]['week'] = [dateStart,dateEnd]
        isExists = Schedule.select().where(Schedule.middleDate.between(dateStart,dateEnd)).exists()
        if isExists:
            continueConv = True
        else: 
            bot.sendMessage(update.message.chat_id,
                        text='Расписание на следующую неделю недоступно',
                        reply_markup=ReplyKeyboardMarkup(schelude_keyboard, one_time_keyboard=True))
    if continueConv:
        reply_keyboard = [["ИС","К"],["Г","Р"],["Б","Ю"],["ТОП"]]
        bot.sendMessage(update.message.chat_id,
                        text='Выберите специальность 🕵',
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return GROUP
    else:
        return ConversationHandler.END

    

def group(bot, update):
    id = update.message.chat_id
    text = update.message.text
    
    # Достаем доступные группы на эту неделю и
    # оставляем только по выбранной специальности
    querys[id]['group'] = update.message.text
    courses = Schedule.select().where(Schedule.middleDate.between(querys[id]['week'][0],querys[id]['week'][1])).get().data
    courses = json.loads(courses)
    coursesArr = []
    for course in courses:
        if querys[id]['group'] in course:
            coursesArr.append(course)
    reply_keyboard = splitArr(coursesArr,2)
    bot.sendMessage(update.message.chat_id,
                    text='Выберите группу 🎓',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return COURSE

def course(bot, update):
    id = update.message.chat_id
    text = update.message.text
    querys[id]['course'] = update.message.text
    reply_keyboard = [['ПН',"ВТ"],["СР","ЧТ"],["ПТ","Вся неделя"]]
    bot.sendMessage(update.message.chat_id,
                    text='Выберите учебный день 📅',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return DAY

def day(bot, update):
    id = update.message.chat_id
    text = update.message.text
    querys[id]['day'] = update.message.text
    courses = Schedule.select().where(Schedule.middleDate.between(querys[id]['week'][0],querys[id]['week'][1])).get().data
    courses = json.loads(courses)
    # Сама отрисовка расписания
    outTxt = ''
    try:
        if querys[id]['day'] == 'Вся неделя':
            daysArrs = ['ПН','ВТ','СР','ЧТ','ПТ']
            for day in daysArrs:
                outTxt += '\n📅{}📅'.format(day)
                subCount = 1
                for subject in courses[str(querys[id]['course'])][day]:
                    if len(subject) > 1:
                        outTxt += '\n{0}: {1}\n    👤{2}'.format(subCount, subject[0],subject[1])
                    else:
                        outTxt += '\n {0}'.format(subject[0])
                    subCount += 1
        else:
            outTxt += '\n📅{}📅'.format(querys[id]['day'])
            subCount = 1
            for subject in courses[str(querys[id]['course'])][str(querys[id]['day'])]:
                if len(subject) > 1:
                    outTxt += '\n{0}: {1}\n    👤{2}'.format(subCount, subject[0],subject[1])
                else:
                    outTxt += '\n {0}'.format(subject[0])
                subCount += 1
    except Exception as e:
        logging.exception("message")

    # Очищаем хэш текущего диалога и заканчиваем диалог
    querys[id] = None
    
    bot.sendMessage(update.message.chat_id,
                    text=outTxt,
                    reply_markup=ReplyKeyboardMarkup(schelude_keyboard, one_time_keyboard=True))

    return ConversationHandler.END

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

# Диалог отменяет по команде /cancel
def cancel(bot, update):
    bot.sendMessage(update.message.chat_id,
                    text='Операция отменена')

    return ConversationHandler.END

# Подписка
def subscribe(bot, update):
    # Проверяем наличие id пользователя в БД
    # если присутствует, то просто обновляем статус
    # чтобы избежать дублирования
    exists = Follower.select().where(
        Follower.chatId == update.message.chat_id).exists()
    if exists:
        isAcitve = Follower.select().where(                     #Если подписка уже активна,
        Follower.chatId == update.message.chat_id).get().active #то оповещяем
        if isAcitve:
            bot.sendMessage(update.message.chat_id,
                            text='Вы уже подписаны.\nМожно отписаться от обновлений при помощи команды /unsubscribe',
                    reply_markup=ReplyKeyboardMarkup(schelude_keyboard, one_time_keyboard=True))
        else:
            subQuery = Follower.update(active=True).where(Follower.chatId == update.message.chat_id)
            subQuery.execute()
            bot.sendMessage(update.message.chat_id,
                        text='Теперь вы подписаны на обновления расписания.'+
                             '\nМожно отписаться от обновлений при помощи команды /unsubscribe',
                    reply_markup=ReplyKeyboardMarkup(schelude_keyboard, one_time_keyboard=True))
    else:
        Follower.create(name= update.message.chat.username,chatId=update.message.chat_id, active=True)
        bot.sendMessage(update.message.chat_id,
                        text='Теперь вы подписаны на обновления расписания.'+
                             '\nМожно отписаться от обновлений при помощи команды /unsubscribe',
                    reply_markup=ReplyKeyboardMarkup(schelude_keyboard, one_time_keyboard=True))
    botan.track(token=botan_token, uid=update.message.from_user.id, message=update.message.text, name='Subscribe')

# Отписка
def unsubscribe(bot, update):
    exists = Follower.select().where(
        Follower.chatId == update.message.chat_id).exists()
    if exists:
        isAcitve = Follower.select().where(
        Follower.chatId == update.message.chat_id).get().active
        if isAcitve:
            ubsubQuery = Follower.update(active=False).where(Follower.chatId == update.message.chat_id)
            ubsubQuery.execute()
            bot.sendMessage(update.message.chat_id,
                        text='Теперь вы отписаны от рассылки.\nМожно подписаться при помощи команды /subscribe')
        else:
           bot.sendMessage(update.message.chat_id,
                        text='Вы не подписаны на обновления.\nМожно подписаться при помощи команды /subscribe')

    else: 
        bot.sendMessage(update.message.chat_id,
                        text='Вы не подписаны на обновления.\nМожно подписаться при помощи команды /subscribe')
    botan.track(token=botan_token, uid=update.message.from_user.id, message=update.message.text, name='Unsubscribe')

# Команды приветствия и помощи
def start(bot, update):
    bot.sendMessage(update.message.chat_id,
                    text='Привет! Я бот Вологодского Кооперативного Колледжа 🤖'+
                         '\nОт меня ты можешь узнать расписание на текущую или следующую неделю при помощи команды /get'+
                         '\nЕще ты можешь подписаться на обвноления расписания при помощи команды /subscribe')
    botan.track(token=botan_token, uid=update.message.from_user.id, message=update.message.text, name='Start')

def help(bot, update):
    bot.sendMessage(update.message.chat_id,
                    text='Доступные команды:'+
                         '\n/subscribe - подписаться на обновления расписания'+
                         '\n/unsubscribe - отписаться от обновления'+
                         '\n/get - получить расписание'+
                         '\n/cancel - отменить операцию')
    botan.track(token=botan_token, uid=update.message.from_user.id, message=update.message.text, name='Help')


class BotThread:
    def __call__(self):
        updater = Updater(token)

        dp = updater.dispatcher

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('get', get)
            ,RegexHandler('^(Расписание|Получить расписание|расписание|📋 Получить расписание 📋)$', get)],

            states={
                WEEK: [MessageHandler([Filters.text], week)],
                GROUP: [MessageHandler([Filters.text], group)],
                COURSE: [MessageHandler([Filters.text], course)],
                DAY: [RegexHandler('^(ПН|ВТ|СР|ЧТ|ПТ|Вся неделя)$', day)]
            },

            fallbacks=[CommandHandler('cancel', cancel)]
        )
        
        dp.add_handler(conv_handler)
        dp.addHandler(CommandHandler('help', help))
        dp.addHandler(CommandHandler('start', start))
        dp.addHandler(CommandHandler('subscribe', subscribe))
        dp.addHandler(CommandHandler('unsubscribe', unsubscribe))

        dp.add_error_handler(error)

        updater.start_polling()

        updater.idle()
