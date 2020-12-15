import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext, Filters, ConversationHandler
import re
import csv
from ftplib import FTP
from pathlib import Path
import subprocess

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

NOTIFICATION_MESSAGE = range(1)
ADMIN_TOKEN, REQUEST = range(2)
ADD_ADMIN_TOKEN = range(1)
COMPANY_NAME, QUANTITY, STORE_REQUEST = range(3)

def start_bot(update: Update, context: CallbackContext) -> None:
    print(update.message.from_user.username)
    print(update.message.from_user.first_name)
    print(update.message.from_user.last_name)
    print(update.message['chat']['id'])
    chat_id = update.message['chat']['id']
    
    conn = psycopg2.connect(user="", password="", host="", database="")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    #INSERT INTO bot_users(chat_id, username, first_name, last_name) VALUES
    fetch_statement = "SELECT chat_id FROM shegna_bot_admins WHERE chat_id = {0};".format(chat_id)
        
    cur.execute(fetch_statement)
    res = cur.fetchall()
    
    cur.close()
    conn.close()
    
    print(len(res))
    if len(res) >= 1:
        context.user_data['is_admin'] = True
        update.message.reply_text('enjoy bot')
    else:
        context.user_data['is_admin'] = False
        update.message.reply_text('cant use bot')
    
def insert_admin_token(admin_token):
    
    statement = "INSERT INTO shegna_bot_admin_tokens(token_string) VALUES('{0}');".format(admin_token);
    
    conn = psycopg2.connect(user="", password="", host="", database="")
    conn.autocommit = True
    
    cursor = conn.cursor()
    
    cursor.execute(statement)
    
    conn.commit()
    cursor.close()
    conn.close()

    
def get_admin_token():
    conn = psycopg2.connect(user="", password="", host="", database="")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    #INSERT INTO bot_users(chat_id, username, first_name, last_name) VALUES
    fetch_token_statement = "SELECT token_string FROM shegna_bot_admin_tokens;"
    
    cur.execute(fetch_token_statement)
    
    return cur.fetchall()[-1]

def db_res_processor(res, n):
    result_length = len(res)
    print('length: ', result_length)
    pages = int(result_length / 10)
    if result_length % 10 != 0:
        pages += 1
    content_range = (n-1) * 10
    content_range2 = n*10 - 1
    if n*10 > result_length:
        content_range2 = result_length - 1
    
    print('r1: ', content_range)
    print('r2', content_range2)
    
    return [res[content_range:content_range2], pages]

def get_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data='1'),
            InlineKeyboardButton("2", callback_data='2'),
            InlineKeyboardButton("3", callback_data='3'),
        ],
        [
            InlineKeyboardButton("4", callback_data='4'),
            InlineKeyboardButton("5", callback_data='5'),
            InlineKeyboardButton("6", callback_data='6'),
        ],
        [
            InlineKeyboardButton("7", callback_data='7'),
            InlineKeyboardButton("8", callback_data='8'),
            InlineKeyboardButton("9", callback_data='9'),
        ],
        [
            InlineKeyboardButton("<<", callback_data='previous'),
            InlineKeyboardButton(">>", callback_data='next'),
        ],
    ]
    
    return keyboard

def format_message(database_results, pages, current_page, result_indicator='All'):
    formatted_message = ''
    for i, product in enumerate(database_results):
        formatted_message += str(i+1) + '. ' + product['product_name'] + '\n\n'
    
    formatted_message += 'Page ' + str(current_page) + ' of ' + str(pages) + '\nResults: ' + result_indicator
    
    return formatted_message

def button(update: Update, context: CallbackContext) -> None:
    
    keyboard = get_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query
    
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    
    #get page number from message text
    message_r = query.message.text.split()
    current_page = int(message_r[-5])
    total_pages = int(message_r[-3])
    key_word = message_r[-1]
    print(current_page, total_pages)
    
    #print(query.message)
    chat_id = query.message['chat']['id']
    message_id = query.message['message_id']
    print(chat_id)
    
    if query.data == 'previous':
        current_page -= 1
        if current_page < 1:
            current_page = total_pages
    elif query.data == 'next':
        current_page += 1
        if current_page > total_pages:
            current_page = 1
        
    print('page', current_page)
    #result_and_pages = fetch_db(current_page, key_word)
    updated_page_results = db_res_processor(context.user_data['db_results'], current_page)
    context.user_data['ranged_results'] = updated_page_results[0]
    context.user_data['pages'] = updated_page_results[1]
    
    #self.send_product_detail(database_results, query)
    
    message_formatted = format_message(context.user_data['ranged_results'], context.user_data['pages'], current_page, key_word)
    
    #query.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Selected\n option: {query.data} " + str(self.counter),reply_markup=reply_markup)
    if query.data == 'previous' or query.data == 'next':
        query.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message_formatted, reply_markup=reply_markup)
    else:
        send_product_detail(context.user_data['ranged_results'], query)

def send_product_detail(database_results, query):
    product_id = int(query.data)
    print(database_results)
    formatted_message = 'Product Name: ' + database_results[product_id-1]['product_name'] + '\n\nQuantity: ' + str(database_results[product_id-1]['quantity']) + '\n\nRequested by: ' + str(database_results[product_id-1]['first_name'] + ' ' + database_results[product_id-1]['last_name'] + '\n\nCompany: ' + database_results[product_id-1]['company_name'])
    
    print(formatted_message)
    query.message.reply_text(formatted_message)

def add_admin_token_entry_point(update: Update, context: CallbackContext) -> None:
    if context.user_data['is_admin'] == True:
        update.message.reply_text('Enter new token: ')
    else:
        update.message.reply_text('This bot is for admins only. Please use @atran_test_bot or talk to bot admin @slurms')
    return ADD_ADMIN_TOKEN

def add_admin_token(update: Update, context: CallbackContext) -> None:
    insert_admin_token(update.message.text)
    update.message.reply_text('Registration token has been updated')
    return ConversationHandler.END

def register_admin_entry_point(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Enter your admin token: ')
    print(context.user_data['is_admin'])
    return ADMIN_TOKEN

def register_admin(update: Update, context: CallbackContext) -> None:
    chat_id = update.message['chat']['id']
    token = get_admin_token()
    print('token = ', token['token_string'])
    print(update.message.text)
    
    if update.message.text == token['token_string']:
        conn = psycopg2.connect(user="", password="", host="", database="")
        conn.autocommit = True
        
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO shegna_bot_admins(chat_id, username, first_name, last_name) VALUES ('{0}', '{1}', '{2}', '{3}')".format(chat_id, update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name))
        
        conn.commit()
        cursor.close()
        conn.close()
        update.message.reply_text('You have been registered as an admin. Please use /start to activate.')
    else:
        update.message.reply_text('Registration failed. Make sure you have the right token.')
        
    return ConversationHandler.END

def display_admin_token(update: Update, context: CallbackContext) -> None:
    if context.user_data['is_admin'] == True:
        update.message.reply_text('Admin registration token: ' + get_admin_token()['token_string'])
    else:
        update.message.reply_text('This bot is for admins only. Please use @atran_test_bot or talk to bot admin @slurms')

def fetch_db(n=0):
    #0/default=request 1=bot_users
    conn = psycopg2.connect(user="", password="", host="", database="")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    fetch_statement = "SELECT product_name, quantity, chat_id, username, first_name, last_name, company_name FROM client_product_requests ORDER BY product_name ASC NULLS LAST;"
    if n == 1:
        fetch_statement = "SELECT chat_id, first_name, last_name, username FROM bot_users ORDER BY first_name ASC NULLS LAST;"
        
    cur.execute(fetch_statement)
    res = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return res

def show_all_requests(update: Update, context: CallbackContext) -> None:
    if context.user_data['is_admin'] == True:
        context.user_data['db_results'] = fetch_db()
        processed_res = db_res_processor(res=context.user_data['db_results'], n=1)
        context.user_data['ranged_results'] = processed_res[0]
        context.user_data['pages'] = processed_res[1]
        
        message_formatted = format_message(context.user_data['ranged_results'], context.user_data['pages'], 1)
        
        keyboard = get_keyboard()

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(message_formatted, reply_markup=reply_markup)
    else:
        update.message.reply_text('This bot is for admins only. Please use @atran_test_bot or talk to bot admin @slurms')

def send_notification_to_all_entry_point(update: Update, context: CallbackContext) -> None:
    if context.user_data['is_admin'] == True:
        update.message.reply_text('Enter the notification you would like to send to your bot users: ')
        return NOTIFICATION_MESSAGE
    else:
        update.message.reply_text('This bot is for admins only. Please use @atran_test_bot or talk to bot admin @slurms')
        return ConversationHandler.END

def send_notification(update: Update, context: CallbackContext) -> None:
    users = fetch_db(1)
    bot = Bot(token='1477373220:AAE7ROMGkdI75Sd5uRhsjmOroLU0NDFfmao')
    for user in users:
        bot.sendMessage(chat_id=user['chat_id'], text=update.message.text)
    update.message.reply_text('Your notification has been sent')
    return ConversationHandler.END
        

def main():
    # token_id | token_string shegna_bot_admin_tokens
    # chat_id | username | first_name | last_name shegna_bot_admins
    updater = Updater("1463611925:AAH8rUhFJEMow58AkTkoiZoLR2bB-IA9jNU", use_context=True)
    
    admin_reg_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register_admin_entry_point)],
        states={
            ADMIN_TOKEN: [MessageHandler(Filters.text & ~Filters.command, register_admin, pass_user_data=True)],
        },
        fallbacks=[CommandHandler('cancel', display_admin_token)],
    )
        
    add_admin_token_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('update_token', add_admin_token_entry_point)],
        states={
            ADD_ADMIN_TOKEN: [MessageHandler(Filters.text & ~Filters.command, add_admin_token, pass_user_data=True)],
        },
        fallbacks=[CommandHandler('cancel', display_admin_token)],
    )
        
    send_notification_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('send_notification', send_notification_to_all_entry_point)],
        states={
            NOTIFICATION_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, send_notification, pass_user_data=True)],
        },
        fallbacks=[CommandHandler('cancel', display_admin_token)],
    )
    
    updater.dispatcher.add_handler(add_admin_token_conv_handler)
    updater.dispatcher.add_handler(admin_reg_conv_handler)
    updater.dispatcher.add_handler(send_notification_conv_handler)
    updater.dispatcher.add_handler(CommandHandler('start', start_bot, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler('get_token', display_admin_token, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler('show_all', show_all_requests, pass_user_data=True))
    updater.dispatcher.add_handler(CallbackQueryHandler(button, pass_user_data=True))
     # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()
    
if __name__ == "__main__":
    main()
    #send_notification_to_all_entry_point()
    #print(fetch_db(1))
    
