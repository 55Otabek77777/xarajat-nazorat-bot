import requests
from datetime import datetime

def get_usd_rate():
    try:
        response = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/")
        data = response.json()
        for currency in data:
            if currency["Ccy"] == "USD":
                return {
                    "rate": float(currency["Rate"]),
                    "date": currency["Date"],
                    "diff": currency.get("Diff", "0")
                }
        return {"rate": 12650, "date": datetime.now().strftime("%Y-%m-%d"), "diff": "0"}
    except:
        return {"rate": 12650, "date": datetime.now().strftime("%Y-%m-%d"), "diff": "0"}

def som_to_usd(som_amount):
    rate = get_usd_rate()["rate"]
    return round(som_amount / rate, 2)

def format_currency(amount, show_usd=True):
    formatted_som = f"{amount:,.0f} so'm"
    if show_usd:
        usd = som_to_usd(amount)
        formatted_som += f" (${usd:,.2f})"
    return formatted_som
