import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Analyzer", layout="wide")

st.title("📊 Portfolio Analyzer")

st.sidebar.title("🔐 Login")

username = st.sidebar.text_input("Username")

if not username:
    st.warning("Bitte Username eingeben")
    st.stop()

# =========================
# 📂 CSV Upload
# =========================
uploaded_file = st.file_uploader("CSV hochladen", type=["csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file)

    # =========================
    # 📡 Preise holen
    # =========================
    prices = []

    for asset in df["asset"]:
        ticker = yf.Ticker(asset)
        data = ticker.history(period="1d")

        if not data.empty:
            price = data["Close"].iloc[-1]
        else:
            price = None

        prices.append(price)

    df["current_price"] = prices

    # =========================
    # 💶 Portfolio Berechnung
    # =========================
    df["value"] = df["shares"] * df["current_price"]
    df["cost"] = df["shares"] * df["buy_price"]

    total_value = df["value"].sum()
    total_cost = df["cost"].sum()

    return_pct = (total_value - total_cost) / total_cost * 100

    df["weight"] = df["value"] / total_value * 100

    # =========================
    # 📈 Performance (Zeitreihe)
    # =========================
    def get_history(df, period="6mo"):
        all_data = {}

        for asset in df["asset"]:
            hist = yf.Ticker(asset).history(period=period)["Close"]
            if not hist.empty:
                all_data[asset] = hist

        prices_df = pd.DataFrame(all_data).ffill()
        return prices_df

    prices_df = get_history(df)

    portfolio_history = pd.DataFrame()

    for asset in df["asset"]:
        if asset in prices_df.columns:
            shares = df.loc[df["asset"] == asset, "shares"].values[0]
            portfolio_history[asset] = prices_df[asset] * shares

    if not portfolio_history.empty:
        portfolio_history["total"] = portfolio_history.sum(axis=1)
        normalized = portfolio_history["total"] / portfolio_history["total"].iloc[0] * 100
    else:
        normalized = None

    # =========================
    # ⚠️ Risiko
    # =========================
    if not portfolio_history.empty:

        returns = portfolio_history["total"].pct_change().dropna()

        volatility = returns.std() * (252 ** 0.5)

        cum_max = portfolio_history["total"].cummax()
        drawdown = (portfolio_history["total"] - cum_max) / cum_max
        max_drawdown = drawdown.min()

        sharpe = (returns.mean() * 252 - 0.02) / volatility

    else:
        volatility, max_drawdown, sharpe = 0, 0, 0
        drawdown = None

    # =========================
    # ⚖️ Rebalancing
    # =========================
    targets = {}
    for asset in df["asset"]:
        targets[asset] = 100 / len(df)

    df["target_weight"] = df["asset"].map(targets)
    df["diff"] = df["target_weight"] - df["weight"]
    df["rebalance_value"] = df["diff"] / 100 * total_value

    import os

    save_path = f"data/{username}.csv"

    #Ordner erstellen falls nicht existiert
    os.makedirs("data", exist_ok=True)


    #Speichern Session-State
    if "portfolio" not in st.session_state:
        st.session_state["portfolio"] = None

    if st.button("💾 speichern"):
        st.session_state["portfolio"] = df

    if st.button("📂 laden"):
        if st.session_state["portfolio"] is not None:
            df = st.session_state["portfolio"]

    # =========================
    # 🖥️ UI (nur Anzeige!)
    # =========================

    st.subheader("📊 Übersicht")

    col1, col2, col3 = st.columns(3)

    col1.metric("💰 Gesamtwert", f"{total_value:,.2f} €")
    col2.metric("📈 Rendite", f"{return_pct:.2f} %")
    col3.metric("⚠️ Volatilität", f"{volatility:.2%}")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Portfolio",
        "📈 Performance",
        "⚠️ Risiko",
        "🔄 Rebalancing"
    ])

    # 📋 Portfolio
    with tab1:
        st.write(df)

    # 📈 Performance
    with tab2:
        if normalized is not None:
            st.line_chart(normalized)
        else:
            st.write("Keine Daten verfügbar")

    # ⚠️ Risiko
    with tab3:
        st.metric("Volatilität", f"{volatility:.2%}")
        st.metric("Max Drawdown", f"{max_drawdown:.2%}")
        st.metric("Sharpe Ratio", f"{sharpe:.2f}")

        if drawdown is not None:
            st.line_chart(drawdown)

    # 🔄 Rebalancing
    with tab4:
        st.bar_chart(df.set_index("asset")["diff"])

        for _, row in df.iterrows():
            action = "Kaufen" if row["rebalance_value"] > 0 else "Verkaufen"
            st.write(f"{action} {row['asset']} → {abs(row['rebalance_value']):.2f} €")