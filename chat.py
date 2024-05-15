from hug.hugchat import hugchat
from hug.hugchat.login import Login
from flask import Flask, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

EMAIL = "984margo@finacenter.com"
PASSWD = "Simou@2007"
sign = Login(EMAIL, PASSWD)
cookies = sign.login(save_cookies=True)
chatbot = hugchat.ChatBot(cookies=cookies.get_dict())
def answer(query):
    query_result = chatbot.chat(query)
    return query_result


@app.route('/chat', methods=['POST'])
def process_post_request():
    d = request.json
    prompt = d.get['prompt']
    return answer(prompt)