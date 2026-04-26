import yfinance as yf
import streamlit as st

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
            if len(assets) == 1:
                price = data["Close"].iloc[-1]
            else:
                price = data[asset]["Close"].iloc[-1]
        except:
            price = None

        prices.append(price)

    return prices