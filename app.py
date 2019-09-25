#!/usr/bin/env python3

# using Shopify API 2019-07, Upward API v1.3

import base64
import dateutil.parser
import hmac
import hashlib
import json
import logging
import os
import requests
import sys

from flask import Flask, request, abort

app = Flask(__name__)

DEFAULT_SECRET = '123changeme'
SHOPIFY_SIGNING_SECRET = os.getenv('SHOPIFY_SIGNING_SECRET', DEFAULT_SECRET)
DELETION_SECRET = os.getenv('DELETION_SECRET', None)
UPWARD_API_KEY = os.getenv('UPWARD_API_KEY', DEFAULT_SECRET)
UPWARD_API_URL = os.getenv(
    'UPWARD_API_URL', 'https://sandbox.upwardlogistics.net/v1/')

# guniorn logging
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

# stdout logging
root = logging.getLogger()
root.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

def verify_webhook(data, hmac_header):
    digest = hmac.new(SHOPIFY_SIGNING_SECRET.encode(
        'utf-8'), data, hashlib.sha256).digest()
    computed_hmac = base64.b64encode(digest)

    return hmac.compare_digest(computed_hmac, hmac_header.encode('utf-8'))


def extract_shipment_info(order_data):
    shipment_data = order_data['shipping_address']
    return {
        'shipMethod': 'PSFC',  # TODO
        'shipToName': shipment_data['first_name'] + ' ' + shipment_data['last_name'],
        'shipToAddressLine1': shipment_data['address1'],
        'shipToAddressLine2': shipment_data.get('address2') or '',
        'shipToAddressLine3': '',  # not provided by shopify
        'shipToCity': shipment_data['city'],
        'shipToState': shipment_data['province'],
        'shipToPostalCode': shipment_data['zip'],
        'shipToCountryCode': shipment_data['country_code'],
        'shipToContactPhone': shipment_data['phone'],
    }


def extract_item_info(order_data):
    return list(map(lambda item: {'productCode': item['sku'], 'quantityToShip': item['quantity']}, order_data['line_items']))


def make_upward_api_call(endpoint, data=None, method="post"):
    url = UPWARD_API_URL + endpoint
    headers = {'api_key': UPWARD_API_KEY}
    if method == 'post':
        response = requests.post(url, json=data, headers=headers)
    elif method == 'delete':
        response = requests.delete(url, json=data, headers=headers)
    elif method == 'get':
        response = requests.get(url, json=data, headers=headers)
    else:
        raise NotImplementedError
    return response


@app.route('/', methods=['GET'])
def status():
    shopify_secret_status = "signing secret set, " if SHOPIFY_SIGNING_SECRET != DEFAULT_SECRET else '**SIGNING SECRET NOT SET**, '
    upward_api_key_status = "api key set, " if UPWARD_API_KEY != DEFAULT_SECRET else '**API KEY NOT SET**, '
    deletion_secret_status = "deletion secret set, " if DELETION_SECRET else '**DELETION KEY NOT SET**, '
    upward_api_url = 'using ' + UPWARD_API_URL
    return ('Alive, ' + shopify_secret_status + upward_api_key_status + deletion_secret_status + upward_api_url, 200)


@app.route('/create', methods=['POST'])
def handle_webhook():
    data = request.get_data()
    app.logger.info('Webhook recieved')

    # verify webhook signature
    verified = verify_webhook(
        data,
        request.headers.get('X-Shopify-Hmac-SHA256')
    )
    if not verified:
        app.logger.error('Webhook verification failed!')
        abort(401)
    app.logger.info('Webhook verified')

    # extract data
    order_data = json.loads(data.decode('utf-8)'))
    order = {}

    order['orderNumber'] = {"_orderNumber": 306}  # TODO
    order['orderDate'] = dateutil.parser.parse(
        order_data['created_at']).strftime('%m-%d-%Y')
    order['shipmentInfo'] = extract_shipment_info(order_data)
    order['items'] = extract_item_info(order_data)
    order['customerID'] = order_data['email']
    app.logger.info('Webhook parsing complete')

    response = make_upward_api_call('Orders', [order])
    try:
        app.logger.info([order])
        response.raise_for_status()
        app.logger.info("Server says '%s'" % (response.text))
    except requests.exceptions.HTTPError as e:
        app.logger.error('Upward API failure!')
        app.logger.error(e)
        app.logger.error(response.content)

    app.logger.info("Processing complete; order %s forwarded" %
                    (order_data['number']))

    return ('', 200)

@app.route('/delete', methods=['GET'])
def delete_order():
    if not DELETION_SECRET:
        return ('Deletion secret is not set; deletion not permitted. See the README for instructions on setting this environment variable.', 403)

    password = request.args.get('password')
    try:
        order_number = int(request.args.get('order'))
    except ValueError as e:
        return ('Order number not specified or unparsable.', 400)

    if not password or password != DELETION_SECRET:
        return ('Password not specified or incorrect.', 403)

    response = make_upward_api_call('Orders/%i' % (order_number), method = 'delete')

    if response.status_code == 200:
        return ('Order %i deleted successfully!' % (order_number))
    elif response.status_code == 403:
        return ('Order %i already in progress and cannot be deleted!' % (order_number), 403)
    else:
        return ('An unknown error occurred (HTTP%i). This may mean the order is already deleted, or that something went wrong.' % (response.status_code), 400)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
