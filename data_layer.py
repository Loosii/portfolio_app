import yfinance as yf
import streamlit as st
import pandas as pd

# =========================
# 📡 Preise laden (gebündelt + cached)
# =========================
@st.cache_data(ttl=300)
def get_prices(assets):
    data = yf.download(
        tickers=" ".join(assets),
        period="1d",
        group_by="ticker",
        threads=False
    )
    return data


# =========================
# 💶 Preis extrahieren
# =========================
def extract_prices(data, assets):
    prices = []

    for asset in assets:
        try:
            # MultiIndex prüfen
            if isinstance(data.columns, pd.MultiIndex):
                price = data[(asset, "Close")].dropna().iloc[-1]
            else:
                # Single Asset Fall
                price = data["Close"].dropna().iloc[-1]

        except Exception as e:
            print(f"Fehler bei {asset}: {e}")
            price = None

        prices.append(price)

    return prices
# =========================
# 🧮 Holdings berechnen
# =========================
def build_holdings(transactions):
    df = transactions.copy()

    # Buy = +, Sell = -
    df["signed_shares"] = df.apply(
        lambda x: x["shares"] if x["type"] == "buy" else -x["shares"],
        axis=1
    )

    holdings = df.groupby("asset")["signed_shares"].sum().reset_index()
    holdings.rename(columns={"signed_shares": "shares"}, inplace=True)

    # Nur positive Positionen behalten
    holdings = holdings[holdings["shares"] > 0]

    return holdings


# =========================
# 💰 Durchschnittlicher Kaufpreis
# =========================
def calculate_avg_price(transactions):
    df = transactions.copy()

    # Nur Käufe berücksichtigen
    buys = df[df["type"] == "buy"]

    avg_price = buys.groupby("asset").apply(
        lambda x: (x["shares"] * x["price"]).sum() / x["shares"].sum()
    )

    return avg_price.to_dict()


# =========================
# 🧩 Kombinieren
# =========================
def build_portfolio_from_transactions(transactions):
    holdings = build_holdings(transactions)
    avg_prices = calculate_avg_price(transactions)

    holdings["buy_price"] = holdings["asset"].map(avg_prices)

    return holdings