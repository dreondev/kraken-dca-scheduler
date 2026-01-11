import krakenex
import yaml
import logging
import sys
import asyncio
import locale
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Bot
from telegram.error import TelegramError

### Hilfsfunktionen ###

async def send_telegram_message(bot_token: str, chat_id: str, message: str, logger):
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info("Telegram-Nachricht gesendet.")
    except TelegramError as e:
        logger.error(f"Telegram-Sendefehler: {e}")

def setup_logging(log_file="script.log"):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def create_kraken_client(api_key: str, api_secret: str):
    return krakenex.API(key=api_key, secret=api_secret)

def get_ticker_info(kraken_client, pair="XXBTZEUR"):
    resp = kraken_client.query_public("Ticker", {"pair": pair})
    if resp.get("error"):
        raise Exception(f"Kraken API Error: {resp['error']}")
    return resp["result"][pair]

def get_balance(kraken_client):
    resp = kraken_client.query_private("Balance")
    if resp.get("error"):
        raise Exception(f"Kraken API Error (Balance): {resp['error']}")
    return resp["result"]

def get_free_eur(kraken_client, logger, fee_puffer=1.005):
    balance = get_balance(kraken_client)
    eur_balance = float(balance.get("ZEUR", 0.0))

    open_orders_resp = kraken_client.query_private("OpenOrders")
    if open_orders_resp.get("error"):
        raise Exception(f"Kraken API Error (OpenOrders): {open_orders_resp['error']}")

    open_orders = open_orders_resp["result"]["open"]
    reserved_eur = 0.0

    for order_id, order_info in open_orders.items():
        order_descr = order_info["descr"]["order"]
        parts = order_descr.split()
        volume = float(parts[1])
        limit_price = None
        for i, p in enumerate(parts):
            if p == 'limit':
                limit_price = float(parts[i+1])
                break
        if limit_price is None:
            continue

        order_eur_needed = volume * limit_price * fee_puffer
        reserved_eur += order_eur_needed

    free_eur = eur_balance - reserved_eur
    logger.info(f"Frei verfügbares EUR-Guthaben (bereinigt um offene Orders): {free_eur}")
    return free_eur

def place_limit_order(kraken_client, pair, volume, price, validate=True):
    order_data = {
        "pair": pair,
        "type": "buy",
        "ordertype": "limit",
        "price": str(price),
        "volume": str(volume),
        "validate": "true" if validate else "false",
    }
    resp = kraken_client.query_private("AddOrder", order_data)
    if resp.get("error"):
        raise Exception(f"Orderfehler: {resp['error']}")
    return resp["result"]

def get_timestamp(tz):
    now_local = datetime.now(tz) if tz else datetime.now()
    return now_local.strftime("%d.%m.%Y %H:%M:%S %Z")

def format_values(amount_eur, discount, free_eur, eur_balance, ask_price, bid_price, limit_price=None, btc_volume=None):
    """Formatiert alle benötigten Werte für die Ausgabe."""
    discount_percent = discount * 100
    discount_percent_str = locale.format_string('%.2f', discount_percent, grouping=True)
    formatted_amount_eur = locale.format_string('%.2f', amount_eur, grouping=True)
    formatted_eur_balance = locale.format_string('%.2f', eur_balance, grouping=True)
    formatted_free_eur = locale.format_string('%.2f', free_eur, grouping=True)
    formatted_ask = locale.format_string('%.2f', ask_price, grouping=True)
    formatted_bid = locale.format_string('%.2f', bid_price, grouping=True)

    formatted_limit_price = None
    if limit_price is not None:
        formatted_limit_price = locale.format_string('%.2f', limit_price, grouping=True)

    btc_volume_str = None
    if btc_volume is not None:
        btc_volume_str = f"{btc_volume:.8f}"

    return {
        "discount_percent_str": discount_percent_str,
        "formatted_amount_eur": formatted_amount_eur,
        "formatted_eur_balance": formatted_eur_balance,
        "formatted_free_eur": formatted_free_eur,
        "formatted_ask": formatted_ask,
        "formatted_bid": formatted_bid,
        "formatted_limit_price": formatted_limit_price,
        "btc_volume_str": btc_volume_str
    }

def build_message(validate_order, timestamp_str, values, order_result=None, error=None, insufficient=False):
    """
    Baut je nach Situation (Erfolg, Fehler, Insufficient funds) die Telegram-Nachricht zusammen.
    """
    base_info = (
        f"Order (validate={validate_order}) am {timestamp_str}:\n"
        f"Betrag: {values['formatted_amount_eur']} EUR\n"
    )

    if insufficient:
        # Planung statt tatsächlicher Ausführung
        msg = (
            f"Nicht genug frei verfügbares EUR-Guthaben am {timestamp_str}:\n"
            f"Order (validate={validate_order}) geplant:\n"
            f"Betrag: {values['formatted_amount_eur']} EUR\n"
            f"Limit-Preis: {values['formatted_limit_price']} EUR\n"
            f"BTC Menge: {values['btc_volume_str']}\n"
            f"Abschlag: {values['discount_percent_str']}% unter Ask\n"
            f"Gesamt-EUR: {values['formatted_eur_balance']} EUR\n"
            f"Frei verfügbar: {values['formatted_free_eur']} EUR\n"
            f"Aktueller Ask: {values['formatted_ask']} EUR, Bid: {values['formatted_bid']} EUR"
        )
        return msg

    # Für Erfolg und Fehler brauchen wir Limit-Preis und BTC Menge
    msg = base_info
    if values['formatted_limit_price'] and values['btc_volume_str']:
        msg += (
            f"Limit-Preis: {values['formatted_limit_price']} EUR\n"
            f"BTC Menge: {values['btc_volume_str']}\n"
        )
    msg += (
        f"Abschlag: {values['discount_percent_str']}% unter Ask\n"
        f"Gesamt-EUR: {values['formatted_eur_balance']} EUR\n"
        f"Frei verfügbar: {values['formatted_free_eur']} EUR\n"
        f"Aktueller Ask: {values['formatted_ask']} EUR, Bid: {values['formatted_bid']} EUR\n"
    )

    if order_result:
        msg += f"Order-Result: {order_result}"

    if error:
        msg += f"\nFehler: {error}"

    return msg


### Hauptprogramm ###

if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Starte Skript...")

    config = load_config()
    kraken_client = create_kraken_client(
        config["kraken"]["api_key"],
        config["kraken"]["api_secret"]
    )

    ticker = get_ticker_info(kraken_client)
    ask_price = float(ticker["a"][0])
    bid_price = float(ticker["b"][0])

    locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

    formatted_ask = locale.format_string("%.2f", ask_price, grouping=True)
    formatted_bid = locale.format_string("%.2f", bid_price, grouping=True)
    logger.info(f"Aktuelle BTC/EUR Preise: Ask={formatted_ask}, Bid={formatted_bid}")
    print(f"BTC/EUR Ask: {formatted_ask}, Bid: {formatted_bid}")

    amount_eur_str = str(config["trade"]["amount_eur"])
    amount_eur = float(amount_eur_str.replace(',', '.'))

    discount_str = config["trade"]["discount_percent"]
    discount = float(discount_str.replace(',', '.'))

    validate_order = config["trade"].get("validate_order", True)
    pair = "XXBTZEUR"

    free_eur = get_free_eur(kraken_client, logger)

    # TZ laden
    tz = ZoneInfo(config["general"]["timezone"]) if "general" in config and "timezone" in config["general"] else None
    timestamp_str = get_timestamp(tz)

    # Prüfen ob genug frei verfügbar
    if free_eur >= amount_eur:
        limit_price = ask_price * (1 - discount)
        limit_price = round(limit_price, 1)
        btc_volume = amount_eur / limit_price

        logger.info(f"Berechneter BTC Menge: {btc_volume:.6f} BTC bei Limit-Preis {limit_price:.1f} EUR")

        try:
            order_result = place_limit_order(kraken_client, pair, btc_volume, limit_price, validate=validate_order)
            logger.info(f"Order Ergebnis: {order_result}")

            balance = get_balance(kraken_client)
            eur_balance = float(balance.get("ZEUR", 0.0))

            values = format_values(amount_eur, discount, free_eur, eur_balance, ask_price, bid_price, limit_price, btc_volume)
            msg = build_message(validate_order, timestamp_str, values, order_result=order_result)

            if "telegram" in config and "bot_token" in config["telegram"] and "chat_id" in config["telegram"]:
                asyncio.run(send_telegram_message(
                    config["telegram"]["bot_token"],
                    config["telegram"]["chat_id"],
                    msg,
                    logger
                ))

        except Exception as e:
            logger.error(f"Fehler beim Orderprozess: {e}")
            balance = get_balance(kraken_client)
            eur_balance = float(balance.get("ZEUR", 0.0))

            values = format_values(amount_eur, discount, free_eur, eur_balance, ask_price, bid_price, limit_price, btc_volume)
            error_msg = build_message(validate_order, timestamp_str, values, error=e)

            if "telegram" in config and "bot_token" in config["telegram"] and "chat_id" in config["telegram"]:
                asyncio.run(send_telegram_message(
                    config["telegram"]["bot_token"],
                    config["telegram"]["chat_id"],
                    error_msg,
                    logger
                ))
    else:
        # Nicht genug frei verfügbar
        planned_limit_price = ask_price * (1 - discount)
        planned_limit_price = round(planned_limit_price, 1)
        planned_btc_volume = amount_eur / planned_limit_price

        balance = get_balance(kraken_client)
        eur_balance = float(balance.get("ZEUR", 0.0))

        values = format_values(amount_eur, discount, free_eur, eur_balance, ask_price, bid_price, planned_limit_price, planned_btc_volume)
        insufficient_msg = build_message(validate_order, timestamp_str, values, insufficient=True)

        logger.warning("Nicht genug frei verfügbares EUR-Guthaben für den Kauf vorhanden.")

        if "telegram" in config and "bot_token" in config["telegram"] and "chat_id" in config["telegram"]:
            asyncio.run(send_telegram_message(
                config["telegram"]["bot_token"],
                config["telegram"]["chat_id"],
                insufficient_msg,
                logger
            ))
