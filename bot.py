import requests
import json
import os
from datetime import datetime, timedelta

WB_TOKEN = os.environ["WB_TOKEN"]
TG_BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]
STATE_FILE = "orders_state.json"


def get_fbo_orders():
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/orders"
    date_from = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00")
    params = {"dateFrom": date_from, "flag": 0}
    headers = {"Authorization": WB_TOKEN}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def send_tg_message(text):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload, timeout=30)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def main():
    state = load_state()
    first_run = len(state) == 0
    orders = get_fbo_orders()

    for order in orders:
        oid = str(order.get("srid", ""))
        if not oid:
            continue

        is_cancel = order.get("isCancel", False)
        status = "Отменён ❌" if is_cancel else "Новый заказ 🆕"

        subject = order.get("subject", "—")
        article = order.get("supplierArticle", "—")
        brand = order.get("brand", "—")
        price = order.get("priceWithDisc", order.get("totalPrice", 0))
        region = order.get("regionName", "—")
        oblast = order.get("oblastOkrugName", "—")
        warehouse = order.get("warehouseName", "—")

        if oid not in state:
            if not first_run:
                send_tg_message(
                    f"🆕 <b>Новый заказ FBO!</b>\n\n"
                    f"📦 <b>Товар:</b> {subject}\n"
                    f"🏷 <b>Бренд:</b> {brand}\n"
                    f"🔢 <b>Артикул:</b> {article}\n"
                    f"💰 <b>Цена:</b> {price} ₽\n"
                    f"📍 <b>Куда:</b> {region}, {oblast}\n"
                    f"🏬 <b>Склад отгрузки:</b> {warehouse}"
                )
            state[oid] = status
        elif state[oid] != status:
            send_tg_message(
                f"🔄 <b>Изменение статуса</b>\n\n"
                f"📦 <b>Товар:</b> {subject}\n"
                f"🔢 <b>Артикул:</b> {article}\n"
                f"📌 <b>Статус:</b> {status}"
            )
            state[oid] = status

    save_state(state)
    print(f"[{datetime.now():%H:%M:%S}] Проверка выполнена. Заказов: {len(orders)}")


if __name__ == "__main__":
    main()
