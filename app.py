import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from data_layer import get_prices, extract_prices
from data_layer import build_portfolio_from_transactions

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

st.subheader("📂 Transaktionen hochladen")

uploaded_file = st.file_uploader("CSV-Datei auswählen", type=["csv"])

if uploaded_file:

    # =========================
    # 📥 CSV einlesen
    # =========================
    transactions = pd.read_csv(uploaded_file, sep=";")

    # =========================
    # 🔍 Debug (optional)
    # =========================
    debug = st.checkbox("🔍 Debug anzeigen")

    if debug:
        st.write("Original Spalten:", transactions.columns)
        st.write(transactions.head())

    # =========================
    # 🧼 Spalten bereinigen
    # =========================
    transactions.columns = transactions.columns.str.lower().str.strip()

    # =========================
    # 🔄 Spaltennamen mappen (falls nötig)
    # =========================
    transactions = transactions.rename(columns={
        "transaction type": "type",
        "typ": "type",
        "stück": "shares",
        "menge": "shares",
        "preis": "price"
    })

    # =========================
    # 🛡️ Validierung
    # =========================
    required_cols = ["date", "asset", "type", "shares", "price"]

    missing = [col for col in required_cols if col not in transactions.columns]

    if missing:
        st.error(f"❌ Fehlende Spalten: {missing}")
        st.write("Gefundene Spalten:", transactions.columns)
        st.stop()

    # =========================
    # 🔧 Werte normalisieren
    # =========================
    transactions["type"] = transactions["type"].str.lower().str.strip()

    transactions["type"] = transactions["type"].replace({
        "kauf": "buy",
        "verkauf": "sell"
    })

    # =========================
    # 🧠 Debug nach Bereinigung
    # =========================
    if debug:
        st.subheader("Nach Bereinigung")
        st.write(transactions.head())
        st.write("Unique types:", transactions["type"].unique())

    # =========================
    # ⚙️ Portfolio bauen
    # =========================
    df = build_portfolio_from_transactions(transactions)

    # =========================
    # 📡 Preise laden
    # =========================
    from data_layer import get_prices, extract_prices

    data = get_prices(df["asset"].tolist())
    prices = extract_prices(data, df["asset"].tolist())

    df["current_price"] = prices

    # 🔧 Absicherung
    if "current_price" not in df.columns:
        st.error("❌ current_price fehlt")
        st.stop()

    df["current_price"] = pd.to_numeric(df["current_price"], errors="coerce")

    if df["current_price"].isna().all():
        st.error("❌ Keine Preise geladen (API Problem)")
        st.stop()

    # =========================
    # 📊 Ergebnis anzeigen
    # =========================
    st.subheader("📊 Portfolio (berechnet aus Transaktionen)")
    st.write(df)

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

    insights = []

    max_weight = df["weight"].max()

    if max_weight > 50:
        insights.append("⚠️ Eine Position macht über 50% aus → hohes Klumpenrisiko")

    elif max_weight > 30:
        insights.append("⚠️ Eine Position ist sehr dominant (>30%)")
    else:
        insights.append("✅ Gute Verteilung ohne dominante Position")

    if volatility > 0.3:
        insights.append("⚠️ Sehr hohe Volatilität → stark schwankendes Portfolio")

    elif volatility > 0.15:
        insights.append("⚠️ Mittlere Volatilität")

    else:
        insights.append("✅ Niedrige Volatilität → stabiles Portfolio")

    if max_drawdown < -0.4:
        insights.append("⚠️ Großer historischer Verlust (>40%)")

    elif max_drawdown < -0.2:
        insights.append("⚠️ Moderater Drawdown")

    else:
        insights.append("✅ Geringe Rückschläge bisher")

    if sharpe > 2:
        insights.append("🔥 Sehr gute risikoadjustierte Rendite")

    elif sharpe > 1:
        insights.append("👍 Solide Rendite im Verhältnis zum Risiko")

    else:
        insights.append("⚠️ Rendite im Verhältnis zum Risiko eher schwach")

    #Score-System
    recommendations = []

    for _, row in df.iterrows():

        score = 0
        reasons = []

        # 🎯 Abweichung vom Ziel
        if row["diff"] < -5:
            score += 2
            reasons.append("übergewichtet")

        elif row["diff"] > 5:
            score += 2
            reasons.append("untergewichtet")

        # 🧠 Konzentration
        if row["weight"] > 40:
            score += 2
            reasons.append("sehr große Position")

        elif row["weight"] > 25:
            score += 1
            reasons.append("dominante Position")

        # ⚠️ globales Risiko berücksichtigen
        if volatility > 0.25:
            score += 1
            reasons.append("hohe Gesamtvolatilität")

        # 👉 Entscheidung ableiten
        if score >= 3:

            if row["diff"] < 0:
                action = "🔻 Reduzieren"
            else:
                action = "🟢 Aufstocken"

            recommendations.append({
                "asset": row["asset"],
                "action": action,
                "value": abs(row["rebalance_value"]),
                "reasons": reasons,
                "score": score
            })

    recommendations = sorted(recommendations, key=lambda x: x["score"], reverse=True)


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

    #🧠 Insights
    st.subheader("🧠 Insights")

    for insight in insights:
        st.write(insight)

    st.subheader("🤖 Smarte Empfehlungen")

    if not recommendations:
        st.success("✅ Dein Portfolio ist gut ausbalanciert")

    for rec in recommendations:

        st.markdown(f"### {rec['action']} {rec['asset']}")

        st.write(f"💰 Betrag: {rec['value']:.0f} €")

        st.write("📌 Gründe:")
        for r in rec["reasons"]:
            st.write(f"- {r}")

        st.divider()