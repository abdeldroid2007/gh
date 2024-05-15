from hug.hugchat import hugchat
from hug.hugchat.login import Login
from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

EMAIL = "984margo@finacenter.com"
PASSWD = "Simou@2007"
sign = Login(EMAIL, PASSWD)
cookies = sign.login(save_cookies=True)
chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

@app.route('/chat', methods=['POST'])
def process_post_request():
    data = request.get_json()
    prompt = data.get('prompt')

    def generate_response():
        for resp in chatbot.query(prompt, stream=True):
            yield resp  

    return Response(stream_with_context(generate_response()), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=True)