import telebot
import time
import traceback
import requests
import datetime
from telebot import util
from threading import Thread
import json
import config

# Однопользовательская версия без сохранения состояний

token = config.TOKEN
access_key = config.VK_access_key

mybot = telebot.TeleBot(token)
chat_ids_file = open('chat_ids.txt', 'a')
chat_ids_file.close()


@mybot.message_handler(commands = ['start', 'help'])
def send_welcome(message):
    text = 'Я напоминаю тебе поздравлять друзей с Днем рождения. Для этого ' \
           'потребуется лишь id твоей страницы Вконтакте, авторизация не нужна. ' \
           'Чтобы добавить или сменить страницу Вконтакте, воспользуйся командой /set_id'
    mybot.send_message(message.chat.id, text)


@mybot.message_handler(commands = ['set_id'])
def send_id_welcome(message):
    text = 'Пришли id на страницу Вконтакте. ' \
           'Его можно быстро узнать здесь: http://regvk.com/id/'
    msg = mybot.send_message(message.chat.id, text)
    mybot.register_next_step_handler(msg, id_saver)


# Защита от белеберды
def check_vk_id_for_validity(id):
    global access_key
    url = 'https://api.vk.com/method/users.get?user_id=' + str(
        id) + '&access_token=' + access_key + '&v=5.52'
    resp = requests.get(url).json()
    return resp


def id_saver(message):
    vk_id = message.text
    if "error" in check_vk_id_for_validity(vk_id):
        text = 'Неправильный id, попробуй еще раз'
        msg = mybot.send_message(message.chat.id, text)
        mybot.register_next_step_handler(msg, send_id_welcome)
    else:
        user_info = {'chat_id': message.chat.id, 'f_name': message.chat.first_name,
             'l_name': message.chat.last_name, 'vk_id': message.text}
        json.dump(user_info, open('text' + str(message.chat.id) + '.txt', 'w'))
        global chat_ids_file
        chat_ids_file = open('chat_ids.txt', 'a')
        chat_ids_file.write(str(message.chat.id) + '\n')
        chat_ids_file.close()
        repl = 'Страница сохранена. Теперь я буду уведомлять тебя о Днях рождения твоих друзей'
        mybot.send_message(message.chat.id, repl)


# Запрос к вк с возвращением списка друзей и дат рождения, отсортированный по алфавиту
def get_birthdays(myid):
    global access_key
    url = 'https://api.vk.com/method/friends.get?user_id=' + str(myid) + \
          '&order=name&fields=bdate&access_token=' + access_key + '&v=5.52'
    resp = requests.get(url).json()
    list = []
    for i in range(resp['response']['count']):
        if 'bdate' in resp['response']['items'][i]:
            list.append(resp['response']['items'][i]['first_name'] + ' '
                 + resp['response']['items'][i]['last_name'] + ' '
                 + resp['response']['items'][i]['bdate'])
    return list


# Достаем массив чат id из файла и причесываем
def paper_work():
    global chat_ids_file
    chat_ids_file = open('chat_ids.txt')
    Chat_ids = []
    line = chat_ids_file.readline()
    while line:
        Chat_ids.append(line),
        line = chat_ids_file.readline()
    chat_ids_file.close()
    for j in range(len(Chat_ids)):
        Chat_ids[j] = Chat_ids[j][:-1]
    return Chat_ids


@mybot.message_handler(commands = ['b_list'])
def birthday_list(message):
    chat_ids = paper_work()
    if str(message.chat.id) in chat_ids:
        f = open('text' + str(message.chat.id) + '.txt').read()
        user_properties = json.loads(f)
        vk_id = user_properties['vk_id']
        LIST = get_birthdays(vk_id)
        reply = ''
        for i in range(len(LIST)):
            reply = reply + LIST[i] + ' \n'
        splitted_text = util.split_string(reply, 3000)
        for text in splitted_text:
            mybot.send_message(message.chat.id, text)
    else:
        mybot.send_message(message.chat.id, 'Страница не задана. Для начала воспользуйся /set_id')


def get_current_birthdays(myid):
    global access_key
    url = 'https://api.vk.com/method/friends.get?user_id=' + str(myid) + '&fields=bdate&access_token=' + access_key + '&v=5.52'
    resp = requests.get(url).json()
    bdays = []
    ids = []
    names = []
    for i in range(resp['response']['count']):
        if 'bdate' in resp['response']['items'][i]:
            bdays.append(resp['response']['items'][i]['bdate'])
            ids.append(resp['response']['items'][i]['id'])
            names.append(resp['response']['items'][i]['first_name'] + ' '
                         + resp['response']['items'][i]['last_name'])
    nums = []
    respond = []
    for j in range(len(bdays)):
        nums.append(bdays[j].split('.'))
        if (str(datetime.datetime.now().day) == nums[j][0]) & (str(datetime.datetime.now().month) == nums[j][1]):
            respond.append(names[j] + " сегодня празднует День рождения")
    return respond


def send_bdays():
    while True:
        chat_ids = paper_work()
        for i in range(len(chat_ids)):
            f = open('text' + chat_ids[i] + '.txt').read()
            user_properties = json.loads(f)
            if (datetime.datetime.now().hour == 23) & (datetime.datetime.now().minute == 33):
                    send = get_current_birthdays(user_properties['vk_id'])
                    for j in range(len(send)):
                        mybot.send_message(user_properties['chat_id'], send[j])
                    time.sleep(60)


def polling():
    while True:
        try:
            mybot.polling(none_stop=True)
        except Exception as e:
            traceback.print_exc()
            time.sleep(15)


th_1, th_2 = Thread(target = send_bdays), Thread(target = polling)
if __name__ == '__main__':
    th_1.start(), th_2.start()
    th_1.join(), th_2.join()