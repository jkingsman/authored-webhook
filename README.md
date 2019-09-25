# Shopify Webhook Forwarding

This is a little cobbled together; apologies. Fundamentally, the `/create` endpoint is built to receive order creation webhooks (POST) from Shopify and pass them to Upward logistics. The `/delete` endpoint is a manual and hopefully rarely used endpoint to delete orders (in the format of `GET /delete?password=<DELETION_SECRET>&order=<order number>`).

For dev, run `SHOPIFY_SIGNING_SECRET=XXXX UPWARD_API_KEY=XXXX DELETION_SECRET=XXXX FLASK_APP=app.py FLASK_DEBUG=1 python -m flask run`.

See below for environment variables; note that you'll need to explicitly specify the production Upward API when running in production.

Requirements in `requirements.txt`; you know the drill. If that doesn't work, this needs:

* `flask`
* `dateutil`
* `requests`

## Env Vars

`UPWARD_API_KEY`: mandatory; Upward API key

`SHOPIFY_SIGNING_SECRET`: mandatory; webhook signing secret (visible in the Webhooks section of the Notifications options in Shopify).

`UPWARD_API_URL`: optional but mandatory for production; the Upward API URL to use for requests. Defaults to sandbox (`https://sandbox.upwardlogistics.net/`) if not set otherwise (e.g. to production (`https://api.upwardlogistics.net/v1/`))

`DELETION_SECRET`: optional but mandatory for order deletion; to be placed in the URL in the form of `/delete?password=<DELETION_SECRET>&order=<order number>` to delete orders.

The `/` route will show you the status of these vars.
