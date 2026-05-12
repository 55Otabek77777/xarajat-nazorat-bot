import requests

def get_usd_rate():
    try:
        response = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/", timeout=5)
        data = response.json()
        for currency in data:
            if currency["Ccy"] == "USD":
                return float(currency["Rate"])
    except:
        pass
    return 12650

def format_currency(amount, show_usd=False):
    formatted = f"{amount:,}".replace(",", " ")
    if show_usd:
        usd = amount / get_usd_rate()
        return f"{formatted} som (${usd:.2f})"
    return f"{formatted} som"