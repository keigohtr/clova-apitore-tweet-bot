import os
import urllib3
import json
import re
from cek import Clova
from flask import Flask, request, jsonify, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError, LineBotApiError, BaseError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
from models import db, Notifications, AccessTokens


flask_debug = bool(os.getenv("FLASK_DEBUG", "True"))

application_id = os.getenv('CLOVA_EXTENSION_ID', 'YOUR EXTENSION ID')
clova = Clova(application_id=application_id, default_language="ja", debug_mode=True)

apitore_access_token_debug = os.getenv('APITORE_ACCESS_TOKEN_DEBUG', 'YOUR APITORE TOKEN')
apitore_tweet_summarize_api = os.getenv('APITORE_ENDPOINT', 'https://api.apitore.com/api/27/twitter-summarize/get')

line_access_token = os.getenv('LINE_ACCESS_TOKEN', 'YOUR LINE TOKEN')
line_secret = os.getenv('LINE_SECRET', 'YOUR LINE SECRET')
line_bot_api = LineBotApi(line_access_token)
handler = WebhookHandler(line_secret)

usage = "はじめまして。\n" \
        "ご利用には初期設定が必要です。下記リンクの手順に従って初期設定を完了してください。\n\n" \
        "https://github.com/keigohtr/clova-apitore-tweet-bot/blob/master/README.md"

app = Flask(__name__)


def initialize_app(flask_app: Flask) -> None:
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///clova-apitore-tweet-bot.sqlite3"
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    flask_app.config['DEBUG'] = flask_debug
    flask_app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
    flask_app.config['RESTPLUS_VALIDATE'] = True
    db.init_app(flask_app)
    db.create_all(app=flask_app)

@clova.handle.launch
def launch_request_handler(clova_request):
    print("Launch request")
    user_id = clova_request.user_id
    print(f'CEK userId: {user_id}')
    obj = AccessTokens.query.filter_by(user_id=user_id).one_or_none()
    if obj is None:
        try:
            line_bot_api.push_message(user_id, TextSendMessage(text=usage))
            message = "はじめまして。まずLINEで友達追加をして初期設定を行ってください。"
            return clova.response(message, end_session=True)
        except:
            message = "はじめまして。まずLINEで友達追加をして初期設定を行ってください。"
            return clova.response(message, end_session=True)
    else:
        return clova.response("はい、なにをしらべますか")

@clova.handle.default
def default_handler(clova_request):
    print("Default request")
    return clova.response("聞き取れませんでした、もう一度お願いします")

@clova.handle.intent("targetWordIntent")
def intent_targetword_handler(clova_request):
    cek_response=None
    notify_message=None
    user_id=None
    try:
        print("targetWordIntent request")
        user_id = clova_request.user_id
        print(f'CEK userId: {user_id}')
        aobj = AccessTokens.query.filter_by(user_id=user_id).one_or_none()
        target = clova_request.slots_dict["target"]
        notify_message, cek_response = make_response_tweet_summarize(target=target, num=1, token=aobj)
        #raise LineBotApiError(status_code=400, error=BaseError("debug")) # DEBUG
        line_bot_api.push_message(user_id, TextSendMessage(text=notify_message))
        return cek_response
    except LineBotApiError as e:
        nobj = Notifications(user_id=user_id, message=notify_message)
        db.session.add(nobj)
        db.session.commit()
        print(str(e))
        return cek_response
    except Exception as e:
        print(str(e))
        return clova.response("ごめんなさい。知らない単語です。")

@clova.handle.intent("nextIntent")
def intent_next_handler(clova_request):
    cek_response=None
    notify_message=None
    user_id=None
    try:
        print("nextIntent request")
        user_id = clova_request.user_id
        print(f'CEK userId: {user_id}')
        aobj = AccessTokens.query.filter_by(user_id=user_id).one_or_none()
        target = clova_request.session_attributes["target"]
        num = int(clova_request.session_attributes["num"])+1
        notify_message, cek_response = make_response_tweet_summarize(target=target, num=num, token=aobj)
        line_bot_api.push_message(user_id, TextSendMessage(text=notify_message))
        return cek_response
    except LineBotApiError as e:
        nobj = Notifications(user_id=user_id, message=notify_message)
        db.session.add(nobj)
        db.session.commit()
        print(str(e))
        return cek_response
    except Exception as e:
        print(str(e))
        return clova.response("私に話しかけるときは、なになにについて教えて、と話しかけてください。")

def make_response_tweet_summarize(target:str, num:int=1, token:AccessTokens=None):
    print("make_response_tweet_summarize")
    numofTweet, tweet = get_apitore_tweet_summarize(target, num, token)
    text = re.sub('https?://[^\s]+', 'リンク', tweet)
    text = re.sub('#[^\s]+', '', text)
    text = re.sub('@[^\s]+', '', text)
    if len(text) > 50:
        text = text[0:50]
    if num == 1:
        notify_message = f'{target}について直近のツイートの要約です。↓↓↓\n\n{tweet}'
        cek_message = f'{target}について直近のツイートの要約です。。。{text}。。。以上です。'
    else:
        notify_message = f'{num}番目の要約です。↓↓↓\n\n{tweet}'
        cek_message = f'{num}番目の要約です。。。{text}。。。以上です。'
    cek_response = clova.response(cek_message)
    cek_response.session_attributes = {"target": target, "num": str(num)}
    return (notify_message, cek_response)

def get_apitore_tweet_summarize(target:str, num:int, token:AccessTokens):
    print("get_apitore_tweet_summarize")
    if token is None:
        '''FIXME: Debug用
        '''
        apitore_access_token = apitore_access_token_debug
    else:
        apitore_access_token = token.token
    http = urllib3.PoolManager()
    r = http.request(
        'GET',
        apitore_tweet_summarize_api,
        fields={'access_token': apitore_access_token,
                'q': f'{target} -RT',
                'num' : num})
    res = json.loads(r.data.decode('utf-8'))
    numofTweets = res["numofTweets"]
    return (numofTweets, res["tweets"][num-1]["text"])

@clova.handle.end
def end_handler(clova_request):
    return clova.response("要約はボットから確認できるよ。またね。", end_session=True)

@app.route('/hackathon/', methods=['POST'])
def my_service():
    resp = clova.route(request.data, request.headers)
    resp = jsonify(resp)
    # make sure we have correct Content-Type that CEK expects
    resp.headers['Content-Type'] = 'application/json;charset-UTF-8'
    return resp

@app.route("/hackathon/bot/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event:MessageEvent):
    user_id = event.source.sender_id
    text = event.message.text
    print(f'LINE userId: {user_id}')
    message = None
    if text == "使い方を教えて":
        message = usage
    elif text == "アクセストークンはxxxxx-xxxxx-xxxxx":
        message = "はい、その形式で投稿してください。"
    elif text.startswith("アクセストークンは"):
        m = re.search(r'アクセストークンは([a-zA-Z0-9\-]+)', text)
        if m and m.group(1):
            token = m.group(1)
            aobj = AccessTokens(user_id=user_id, token=token)
            db.session.add(aobj)
            db.session.commit()
            message = "アクセストークンを登録しました。"
        else:
            message = "アクセストークンが不正です。"
    elif text == "未読はある":
        nobj = Notifications.query.filter_by(user_id=user_id).one_or_none()
        if nobj is None:
            message = "未読はありません。"
        else:
            message = nobj.message
            db.session.query(Notifications).filter(
                Notifications.id == nobj.id).delete()
            db.session.commit()
    else:
        pass
    if message is not None:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=message))


if __name__ == '__main__':
    initialize_app(app)
    app.run(host='0.0.0.0', port=40000)
