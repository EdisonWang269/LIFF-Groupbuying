import configparser
import requests

# config_path = '/home/wangpython/Gogroupbuy/backend/config.ini'
config_path = 'backend/config.ini'
config = configparser.ConfigParser()
config.read(config_path)
channel_access_token = config['line-bot']['CHANNEL_ACCESS_TOKEN']

def send_message(userid, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}"
    }

    data = {
        "to": userid,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json(), response.status_code
