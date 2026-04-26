import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

def get_portfolio_history(df, period="6mo"):
    import yfinance as yf
    import pandas as pd

    all_data = {}

    for asset in df["asset"]:
        ticker = yf.Ticker(asset)
        hist = ticker.history(period=period)["Close"]

        if not hist.empty:
            all_data[asset] = hist

    prices_df = pd.DataFrame(all_data)

    # Fehlende Werte auffüllen
    prices_df = prices_df.ffill()

    return prices_df

st.set_page_config(page_title="Portfolio Tool", layout="wide")

st.title("📊 Portfolio Analyse Tool")

uploaded_file = st.file_uploader("Lade dein Portfolio (CSV)", type=["csv"])

fx = yf.Ticker("EURUSD=X")
fx_data = fx.history(period="1d")

eur_usd = fx_data["Close"].iloc[-1]
usd_to_eur = 1 / eur_usd

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    prices = []

    for asset in df["asset"]:
        ticker = yf.Ticker(asset)
        data = ticker.history(period="1d")

        if not data.empty:
            price = data["Close"].iloc[-1]
            price = price * usd_to_eur
        else:
            price = None

        prices.append(price)

    df["current_price"] = prices

    # Berechnung
    df["value"] = df["shares"] * df["current_price"]
    df["cost"] = df["shares"] * df["buy_price"]

    total_value = df["value"].sum()
    total_cost = df["cost"].sum()

    return_pct = (total_value - total_cost) / total_cost * 100

    df["weight"] = df["value"] / total_value * 100
    
    st.subheader("📈 Performance über Zeit")

    prices_df = get_portfolio_history(df)

    #Portfolio-Wert pro Tag berechnen
    portfolio_history = pd.DataFrame()

    for asset in df["asset"]:
        shares = df.loc[df["asset"] == asset, "shares"].values[0]
        portfolio_history[asset] = prices_df[asset] * shares

    portfolio_history["total"] = portfolio_history.sum(axis=1)

    st.line_chart(portfolio_history["total"])

    returns = portfolio_history["total"].pct_change().dropna()

    #Volitilität
    volatility = returns.std() * (252 ** 0.5)

    #MaxDradown
    cum_max = portfolio_history["total"].cummax()
    drawdown = (portfolio_history["total"] - cum_max) / cum_max

    max_drawdown = drawdown.min()

    #SharpeRatio
    risk_free_rate = 0.02  # 2% angenommen

    sharpe = (returns.mean() * 252 - risk_free_rate) / volatility

    #Charts
    df = df.sort_values(by="value", ascending=False)
    st.subheader("🥧 Gewichtung im Portfolio")

    fig, ax = plt.subplots()
    ax.pie(df["weight"], labels=df["asset"], autopct="%1.1f%%")
    ax.axis("equal")

    st.pyplot(fig)

    st.subheader("📊 Wert pro Asset")

    fig2, ax2 = plt.subplots()
    ax2.bar(df["asset"], df["value"])
    ax2.set_ylabel("Wert in €")

    st.pyplot(fig2)

    st.subheader("📋 Portfolio (inkl. Gewichtung)")

    df_display = df.copy()
    df_display["weight"] = df_display["weight"].round(2)

    st.write(df_display)

    #Top-Position
    top_asset = df.loc[df["weight"].idxmax()]

    st.subheader("🏆 Größte Position")
    st.write(f"{top_asset['asset']} mit {top_asset['weight']:.2f}%")

    st.subheader("⚠️ Risiko Kennzahlen")

    st.metric("📊 Volatilität (jährlich)", f"{volatility:.2%}")
    st.metric("📉 Max Drawdown", f"{max_drawdown:.2%}")
    st.metric("🧠 Sharpe Ratio", f"{sharpe:.2f}")

    st.subheader("📉 Drawdown Verlauf")
    st.line_chart(drawdown)

    st.subheader("📊 Kennzahlen")
    st.metric("💰 Gesamtwert", f"{total_value:,.2f} €")
    st.metric("📉 Rendite", f"{return_pct:.2f} %")

    #Rebalancing
    st.subheader("⚖️ Ziel-Gewichtung")

    targets = {}

    for asset in df["asset"]:
        targets[asset] = st.number_input(
            f"{asset} Ziel (%)",
            min_value=0.0,
            max_value=100.0,
            value=round(100 / len(df), 2)
        )

        df["target_weight"] = df["asset"].map(targets)
        df["diff"] = df["target_weight"] - df["weight"]

        df["rebalance_value"] = df["diff"] / 100 * total_value

    st.subheader("🔄 Rebalancing Vorschläge")

    for _, row in df.iterrows():
        action = "Kaufen" if row["rebalance_value"] > 0 else "Verkaufen"

        st.write(
            f"{action} {row['asset']} im Wert von {abs(row['rebalance_value']):.2f} €"
        )

    st.subheader("📊 Abweichung vom Ziel")
    st.bar_chart(df.set_index("asset")["diff"])