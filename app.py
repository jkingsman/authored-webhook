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

from flask import Flask, request, abort

app = Flask(__name__)

DEFAULT_SECRET = '123changeme'
SHOPIFY_SIGNING_SECRET = os.getenv('SHOPIFY_SIGNING_SECRET', DEFAULT_SECRET)
UPWARD_API_KEY = os.getenv('UPWARD_API_KEY', DEFAULT_SECRET)
UPWARD_API_URL = os.getenv(
    'UPWARD_API_URL', 'https://sandbox.upwardlogistics.net/v1/')

gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

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
        # TODO maybe? shopify doesn't meed E.164
        'shipToContactPhone': shipment_data['phone'],
    }


def extract_item_info(order_data):
    return list(map(lambda item: {'productCode': item['sku'], 'quantityToShip': item['quantity']}, order_data['line_items']))


def make_upward_api_call(endpoint, data):
    url = UPWARD_API_URL + endpoint
    headers = headers = {'api_key': UPWARD_API_KEY}
    response = requests.post(url, json=data)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        app.logger.error('Upward API failure!')
        app.logger.error(e)


@app.route('/', methods=['GET'])
def status():
    shopify_secret_status = "signing secret set, " if SHOPIFY_SIGNING_SECRET != DEFAULT_SECRET else '**SIGNING SECRET NOT SET**, '
    upward_api_key_status = "api key set, " if UPWARD_API_KEY != DEFAULT_SECRET else '**API KEY NOT SET**, '
    upward_api_url = 'using ' + UPWARD_API_URL

    return ('Alive, ' + shopify_secret_status + upward_api_key_status + upward_api_url, 200)


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

    order['_orderNumber'] = order_data['number']
    order['orderDate'] = dateutil.parser.parse(
        order_data['created_at']).strftime('%m-%d-%Y')
    order['shipment_info'] = extract_shipment_info(order_data)
    order['items'] = extract_item_info(order_data)
    order['customerID'] = order_data['email']
    app.logger.info('Webhook parsing complete')
    app.logger.info(order)

    # make_upward_api_call('Orders', order)
    app.logger.info("Processing complete; order %s forwarded" %
                    (order['_orderNumber']))

    return ('Webhook verified & forwarded', 200)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
