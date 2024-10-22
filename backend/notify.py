from flask import Flask, abort, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import configparser

config_path = 'backend\config.ini'

config = configparser.ConfigParser()
config.read(config_path)

line_bot_api = LineBotApi(config['line-bot']['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(config['line-bot']['CHANNEL_SECRET'])

app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        print(body, signature)
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def pretty_echo(event):

    if event.source.user_id != "Udeadbeefdeadbeefdeadbeefdeadbeef":

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage("nmsl")
        )

def send_message_to_user(user_id, message):
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text=message)
    )

@app.route("/send_message", methods=['POST'])
def send_message():
    data = request.get_json()
    user_id = data['user_id']
    message = "到貨通知：您的訂單已送達，請盡快取貨。"
    try:
        send_message_to_user(user_id, message)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    app.run()