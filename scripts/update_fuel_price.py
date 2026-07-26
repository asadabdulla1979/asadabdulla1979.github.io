#!/usr/bin/env python3
"""Update fuel.json from PSO's official fuel price page (psopk.com).

Runs on a schedule in GitHub Actions. Petrol on PSO's site is the product
named "PREMIER EURO 5". Fails safe: if the page cannot be fetched, the
pattern is not found, or the number looks implausible, fuel.json is left
untouched and the site keeps showing the previous price with its date.
"""
import json
import re
import datetime
import urllib.request

URL = "https://psopk.com/en/fuels/fuel-prices"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MacroNotesFuelBot/1.0; +https://asadabdulla1979.github.io)"}
SANITY_MIN, SANITY_MAX = 200.0, 600.0  # plausible Rs/litre band; widen if prices ever leave it

MONTHS = {"jan": "January", "feb": "February", "mar": "March", "apr": "April",
          "may": "May", "jun": "June", "jul": "July", "aug": "August",
          "sep": "September", "oct": "October", "nov": "November", "dec": "December"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def main():
    html = fetch(URL)

    # Petrol price: the number that follows the product name "PREMIER EURO 5"
    m = re.search(r"PREMIER\s*EURO\s*5.{0,600}?Rs\.?\s*(\d{3}(?:\.\d{1,2})?)\s*/?\s*Ltr",
                  html, re.I | re.S)
    if not m:  # fallback: number appearing shortly before the product name
        m = re.search(r"Rs\.?\s*(\d{3}(?:\.\d{1,2})?)\s*/?\s*Ltr.{0,600}?PREMIER\s*EURO\s*5",
                      html, re.I | re.S)
    if not m:
        print("Premier Euro 5 price not found on page; fuel.json left unchanged.")
        return
    price = float(m.group(1))
    if not (SANITY_MIN <= price <= SANITY_MAX):
        print(f"Price {price} outside sanity bounds; fuel.json left unchanged.")
        return

    # Effective date, e.g. "Effective From: July 25, 2026"
    d = re.search(r"Effective\s*From:\s*([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})", html, re.I)
    if d:
        month = MONTHS.get(d.group(1)[:3].lower(), d.group(1))
        date = f"{int(d.group(2))} {month} {d.group(3)}"
    else:
        date = datetime.datetime.utcnow().strftime("%d %B %Y").lstrip("0")

    with open("fuel.json") as f:
        data = json.load(f)
    if abs(float(data.get("petrol", 0)) - price) < 0.005:
        print(f"Price unchanged at Rs {price}; nothing to commit.")
        return

    data["petrol"] = price
    data["date"] = date
    with open("fuel.json", "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"Updated fuel.json: petrol Rs {price}, notified {date}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Fuel update failed safe:", e)
