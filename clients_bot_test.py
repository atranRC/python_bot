#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=W0613, C0116
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that uses inline keyboards.
"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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

KEYWORD, REQUEST = range(2)
COMPANY_NAME, QUANTITY, STORE_REQUEST = range(3)

def fetch_db(key_word='All'):
    conn = psycopg2.connect(user="", password="", host="", database="")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    fetch_statement = "SELECT product_name, selling_price, expiration_date, quantity FROM products ORDER BY product_name ASC NULLS LAST;"
    if key_word != 'All':
        fetch_statement = "SELECT product_name, selling_price, expiration_date, quantity FROM products WHERE LOWER(product_name) LIKE LOWER('%" + key_word + "%') ORDER BY product_name ASC NULLS LAST;"
        
    cur.execute(fetch_statement)
    res = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return res
    
def db_res_processor(res, n, key_word='All'):
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

def get_csv(chat_id):
    conn = psycopg2.connect(user="", password="", host="", database="")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    fetch_statement = "SELECT product_name, selling_price, expiration_date, quantity FROM products ORDER BY product_name ASC NULLS LAST;"
        
    cur.execute(fetch_statement)
    res = cur.fetchall()
    
    file_name = 'product_list_' + str(chat_id) + '.csv'
    write_to_csv(res, file_name)
    
    return file_name


def format_message(database_results, pages, current_page, result_indicator='All'):
    formatted_message = ''
    for i, product in enumerate(database_results):
        formatted_message += str(i+1) + '. ' + product['product_name'] + '\n\n'
    
    formatted_message += 'Page ' + str(current_page) + ' of ' + str(pages) + '\nResults: ' + result_indicator
    
    return formatted_message

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

def send_product_detail(database_results, query):
    product_id = int(query.data)
    
    formatted_message = 'Product Name: ' + database_results[product_id-1]['product_name'] + '\n\nPrice: ' + str(database_results[product_id-1]['selling_price']) + '\n\nExpiration date: ' + str(database_results[product_id-1]['expiration_date']) + '\n\nAvailable in stock: ' + str(database_results[product_id-1]['quantity'])
    
    print(formatted_message)
    query.message.reply_text(formatted_message)
    

def write_to_csv(dict_db, file_name):
    with open(file_name, mode='w') as csv_file:
        fieldnames = ['product_name', 'price', 'exp_date', 'Available']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writeheader()
        for product in dict_db:
            writer.writerow({'product_name': product['product_name'], 'price': product['selling_price'], 'exp_date': product['expiration_date'], 'Available': product['quantity']})
            
            
def catalogue_spreadsheet(update: Update, context: CallbackContext) -> None:
    
    #request_id | product_name | quantity | chat_id | username | first_name | last_name | company_name 
    #client_product_requests
    #bot_db
    
    #"curl -F document=@"product_list_1234.csv" https://api.telegram.org/bot1477373220:AAE7ROMGkdI75Sd5uRhsjmOroLU0NDFfmao/sendDocument?chat_id=850638880"
    chat_id = update.message['chat']['id']
    file_name = get_csv(chat_id)
    child_process = subprocess.Popen("curl -F document=@'{0}' https://api.telegram.org/bot1477373220:AAE7ROMGkdI75Sd5uRhsjmOroLU0NDFfmao/sendDocument?chat_id={1}".format(file_name, str(chat_id)), shell=True)

    child_process.wait()

def take_client_request(update: Update, context: CallbackContext) -> None:
    conn = psycopg2.connect(user="", password="", host="", database="")
    conn.autocomit = True
    
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO client_product_requests(product_name, quantity, chat_id, username, first_name, last_name, company_name) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format())
    return 1
    
    
def show_all(update: Update, context: CallbackContext) -> None:
    
    context.user_data['db_results'] = fetch_db()
    processed_res = db_res_processor(res=context.user_data['db_results'], n=1)
    context.user_data['ranged_results'] = processed_res[0]
    context.user_data['pages'] = processed_res[1]
    
    message_formatted =format_message(context.user_data['ranged_results'], context.user_data['pages'], 1)
    
    keyboard = get_keyboard()

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(message_formatted, reply_markup=reply_markup)
    
def search_entry_point(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Enter keyword: ')
    
    return KEYWORD


def search(update: Update, context: CallbackContext) -> None:
    #prompt user to enter key word
    client_keyword = update.message.text
    
    context.user_data['db_results'] = fetch_db(key_word=client_keyword)
    processed_res = db_res_processor(res=context.user_data['db_results'], n=1)
    context.user_data['ranged_results'] = processed_res[0]
    context.user_data['pages'] = processed_res[1]
    
    message_formatted = format_message(context.user_data['ranged_results'], context.user_data['pages'], 1, client_keyword)
    
    keyboard = get_keyboard()

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(message_formatted, reply_markup=reply_markup)
    
    return ConversationHandler.END
    
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

def save_bot_user(update: Update, context: CallbackContext) -> None:
    print(update.message.from_user.username)
    print(update.message.from_user.first_name)
    print(update.message.from_user.last_name)
    print(update.message['chat']['id'])
    
    conn = psycopg2.connect(user="", password="", host="", database="")
    conn.autocommit = True
    
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO bot_users(chat_id, username, first_name, last_name) VALUES ('{0}', '{1}', '{2}', '{3}')".format(update.message['chat']['id'], update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name))
    
    conn.commit()
    cursor.close()
    conn.close()
    update.message.reply_text('Use this bot to browse from a catalogue of medical supplies')

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Use /start to test this bot.")
    

def product_request_entry_point(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Enter product name: ')
    return QUANTITY

def get_quantity(update: Update, context: CallbackContext) -> None:
    context.user_data["client_message"] = update.message.text
    update.message.reply_text('Enter quantity: ')
    return COMPANY_NAME

def get_company_name(update: Update, context: CallbackContext) -> None:
    context.user_data["client_message"] += '/*' + update.message.text
    update.message.reply_text('Enter company name: ')
    return STORE_REQUEST

def store_client_request(update: Update, context: CallbackContext) -> None:
    context.user_data['client_message'] += '/*' + update.message.text
    client_request_details = context.user_data['client_message'].split('/*')
    print(client_request_details)
    print(update.message.from_user.username)
    print(update.message.from_user.first_name)
    print(update.message.from_user.last_name)
    
    conn = psycopg2.connect(user="", password="", host="", database="")
    conn.autocommit = True
    
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO client_product_requests(product_name, quantity, chat_id, username, first_name, last_name, company_name) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(client_request_details[0], client_request_details[1], update.message['chat']['id'], update.message.from_user.username, update.message.from_user.first_name, update.message.from_user.last_name, client_request_details[2]))
    
    conn.commit()
    cursor.close()
    conn.close()
    update.message.reply_text('Thank you for your request. We will notify you as soon as the product is available in stock')
    return ConversationHandler.END


#equest_id | product_name | quantity | chat_id | username | first_name | last_name | company_name 


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    
    updater = Updater("1477373220:AAE7ROMGkdI75Sd5uRhsjmOroLU0NDFfmao", use_context=True)
    
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('search', search_entry_point)],
        states={
            KEYWORD: [MessageHandler(Filters.text & ~Filters.command, search)],
        },
        fallbacks=[CommandHandler('cancel', show_all)],
    )
    
    req_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('request', product_request_entry_point)],
        states={
            QUANTITY: [MessageHandler(filters=Filters.text, callback=get_quantity, pass_user_data=True)],
            COMPANY_NAME: [MessageHandler(filters=Filters.text, callback=get_company_name, pass_user_data=True)],
            STORE_REQUEST: [MessageHandler(filters=Filters.text, callback=store_client_request, pass_user_data=True)],
        },
        fallbacks=[CommandHandler('cancel', show_all)],
    )

    updater.dispatcher.add_handler(conv_handler)
    updater.dispatcher.add_handler(req_conv_handler)

    updater.dispatcher.add_handler(CommandHandler('show_all', show_all, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler('start', save_bot_user))
    #updater.dispatcher.add_handler(MessageHandler(Filters.text, search))
    updater.dispatcher.add_handler(CommandHandler('catalogue', catalogue_spreadsheet))
    updater.dispatcher.add_handler(CallbackQueryHandler(button, pass_user_data=True))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()
    #write_to_csv()
    #write_to_csv(fetch_db(1)[0])
    #print(fetch_db(25))
    #print(get_csv_url(get_csv('1234')))
