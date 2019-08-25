from flask import Flask, request, abort
import hmac
import hashlib
import base64

app = Flask(__name__)

SECRET = 'hush'


def verify_webhook(data, hmac_header):
    digest = hmac.new(SECRET, data.encode('utf-8'), hashlib.sha256).digest()
    computed_hmac = base64.b64encode(digest)

    return hmac.compare_digest(computed_hmac, hmac_header.encode('utf-8'))


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_data()
    verified = verify_webhook(
        data, request.headers.get('X-Shopify-Hmac-SHA256'))

    if not verified:
        abort(401)

    # process webhook payload
    # ...

    return ('Webhook verified', 200)
