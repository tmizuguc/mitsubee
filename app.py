import os
import openai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
)
from langchain.prompts.chat import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import BaseCallbackManager

app = Flask(__name__)

# LINE Messaging APIの準備
line_bot_api = LineBotApi(os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])
# OpenAIの準備
openai.api_key = os.getenv("OPENAI_API_KEY")

# 設定プロンプト
character_setting = "YOUR_FAVORITE_PROMPT"

# チャットプロンプトテンプレート
prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(character_setting),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}"),
    ]
)

# チャットモデル
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    max_tokens=512,
    temperature=0.2,
    streaming=True,
    callback_manager=BaseCallbackManager([StreamingStdOutCallbackHandler()]),
)
# メモリ
memory = ConversationBufferWindowMemory(k=3, return_messages=True)
# 会話チェーン
conversation = ConversationChain(memory=memory, prompt=prompt, llm=llm, verbose=True)

@app.route("/")
def test_get():
    print("**GET**")
    print(f"request.headers: {request.headers}")
    print(f"request.body: {request.get_data(as_text=True)}")
    return "It Works as Get!"

@app.route("/", methods=["POST"])
def test_post():
    print("**POST**")
    print(f"request.headers: {request.headers}")
    print(f"request.body: {request.get_data(as_text=True)}")
    return "It Works as Post!"

@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    response = conversation.predict(input=event.message.text)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))


if __name__ == "__main__":
    app.run()
