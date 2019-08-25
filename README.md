# Shopify Webhook Forwarding

For dev, run `SHOPIFY_SIGNING_SECRET=XXXX UPWARD_API_KEY=XXXX FLASK_APP=app.py FLASK_DEBUG=1 python -m flask run`

Requirements in `requirements.txt`; you know the drill. If that doesn't work, this needs:

* `flask`
* `dateutil`
* `requests`

## Env Vars

`UPWARD_API_KEY`: mandatory; Upward API key

`SHOPIFY_SIGNING_SECRET`: mandatory; webhook signing secret (visible in the Webhooks section of the Notifications options in Shopify).

`UPWARD_API_URL`: optional but mandataory for production; the Upward API URL to use for requests. Defaults to sandbox (`https://sandbox.upwardlogistics.net/`) if not set otherwise (e.g. to production (`https://api.upwardlogistics.net/v1/`))

The `/` route will show you the status of these three vars.
