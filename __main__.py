import argparse
import os
import threading
import json
import yaml
import jwt
import telegram
import telegram.ext
from flask import Flask, request

parser = argparse.ArgumentParser(description='Send telegram bot message through HTTP.')
parser.add_argument('-p', '--port', default=8000, help='HTTP listen port')
parser.add_argument('-l', '--host', default='::', help='HTTP listen host')
args = parser.parse_args()

config = None
with open('config.yaml', 'r') as f:
    config = yaml.load(f)
bot_token = config['bot_token']
endpoint = config['endpoint'].rstrip('/')

def cmd_start(bot, update):
    try:
        chat_id = update.message.chat.id
        token = {'chat_id': chat_id}
        token = jwt.encode(token, bot_token).decode('utf8')
        update.message.reply_text(f'The endpoint for this chat is `{endpoint}/{token}`', parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        print(e)

bot = telegram.Bot(config['bot_token'])
updater = telegram.ext.Updater(bot=bot)
updater.dispatcher.add_handler(telegram.ext.CommandHandler('start', cmd_start))
updater.start_polling(timeout=120)

app = Flask(__name__)

@app.route('/<string:token>', methods=['POST'])
@app.route('/<string:token>/<string:fmt>', methods=['POST'])
def http_handler(token, fmt=None):
    try:
        token = jwt.decode(token, bot_token)
    except Exception:
        return 'Invalid token', 401
    if 'chat_id' not in token:
        return 'Unknown token', 400
    if request.content_length > 4096:
        return 'Message too long', 400
    content = request.form or request.json or request.data
    if isinstance(content, dict):
        if fmt == 'yaml':
            content = yaml.dump(content, default_flow_style=True)
        else:
            content = json.dumps(content, indent=2)
    elif isinstance(content, bytes):
        content = content.decode('utf-8')
    if len(content.encode('utf8')) >= 4096:
        return 'Message too long', 400
    if fmt == 'markdown' or fmt == 'md':
        bot.send_message(token['chat_id'], text=content, parse_mode=telegram.ParseMode.MARKDOWN)
    elif fmt == 'html':
        bot.send_message(token['chat_id'], text=content, parse_mode=telegram.ParseMode.HTML)
    else:
        bot.send_message(token['chat_id'], text=content)
    return '', 200

if __name__ == '__main__':
    app.run(host=args.host, port=args.port)

