import telegram

my_token = ''

def send(msg, chat_id, token=my_token):

	bot = telegram.Bot(token=token)
	bot.sendMessage(chat_id=chat_id, text=msg)

if __name__ == "__main__":
    send("hello\n22", "chat_id", "token")
