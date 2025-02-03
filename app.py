from flask import Flask, request, abort
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent
from linebot.v3.webhook import WebhookHandler
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

# 設定 LINE Channel 資訊
CHANNEL_ACCESS_TOKEN = 'DWRA+HWkxIdL6/2+W+omDW7lIVnYaEO/ORyCo+rm3TtkGDzwo9dnJvSGIxke8/om+Pbj3FLr8iApjCGeeSmYkWxD67CewJfnk/nuVStpggxP+JlZCKCyDAM8plcJOdocNSt1g+/u9N+Qxne5586Y/AdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '1d3649a096dd20c6b4e0917b3270841f'

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    try:
        user_message = event.message.text
        response_message = f"你說的是：{user_message}"
        app.logger.info(f"接收到訊息：{user_message}")
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response_message)]
                )
            )
        app.logger.info(f"成功回覆訊息：{response_message}")
    except Exception as e:
        app.logger.error(f"回覆訊息失敗：{e}")

@app.route("/callback", methods=['POST'])
def callback():
    # 確保有接收到訊息並處理
    try:
        # 從 LINE 伺服器取得訊息
        body = request.get_data(as_text=True)
        app.logger.info(f"Request body: {body}")

        # 使用 LINE Bot SDK 處理訊息
        signature = request.headers['X-Line-Signature']
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            app.logger.error("Invalid signature")
            abort(400)

        # 確保返回 200 OK
        return 'OK', 200
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return 'Internal Server Error', 500

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    try:
        reply_text = "收到圖片，感謝您！"
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
    except Exception as e:
        app.logger.error(f"處理圖片訊息失敗：{e}")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
