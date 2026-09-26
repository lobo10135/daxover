import datetime
import os
import pandas as pd
import streamlit as st
import yfinance as yf

# Streamlit Layout konfigurieren
st.set_page_config(page_title="Dax Overnight", page_icon="🦉", layout="wide")


@st.cache_data(ttl=60)
def get_dax_live_data():
    """Lädt historische Tagesdaten für den EMA 20 und den aktuellen Live-Kurs des DAX."""
    ticker_symbol = "^GDAXI"
    ticker = yf.Ticker(ticker_symbol)
    
    # 1. Historische Tagesdaten (1 Jahr) für die saubere EMA-20-Berechnung laden
    df_history = ticker.history(period="1y", interval="1d")
    
    # 2. Aktuellen Live-Kurs (Intraday) abfragen
    live_price = None
    try:
        live_price = ticker.fast_info.last_price
    except Exception:
        pass
        
    # Fallback, falls fast_info nicht erreichbar ist
    if not live_price or pd.isna(live_price):
        try:
            live_price = ticker.info.get("regularMarketPrice")
        except Exception:
            pass
            
    # Letzter Fallback auf den letzten historischen Schlusskurs
    if not live_price or pd.isna(live_price) and not df_history.empty:
        live_price = float(df_history["Close"].iloc[-1])
        
    return df_history, live_price


def evaluate_dax_overnight(df_history, live_price):
    """Prüft, ob der aktuelle DAX-Live-Kurs über dem EMA 20 liegt."""
    try:
        if df_history is None or len(df_history) < 25:
            return None

        # MultiIndex-Spalten von yfinance bereinigen falls nötig
        if isinstance(df_history.columns, pd.MultiIndex):
            df_history.columns = df_history.columns.get_level_values(0)

        # Zeitzone entfernen
        if df_history.index.tz is not None:
            df_history.index = df_history.index.tz_localize(None)

        # EMA 20 auf Basis der historischen Schlusskurse berechnen
        df_history["EMA20"] = df_history["Close"].ewm(span=20, adjust=False).mean()

        # Den aktuellsten berechneten EMA 20 Wert nehmen
        ema20_value = float(df_history["EMA20"].iloc[-1])
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        is_above = live_price > ema20_value
        diff_points = round(live_price - ema20_value, 2)
        diff_percent = round((live_price / ema20_value - 1) * 100, 2)

        return {
            "Timestamp": date_str,
            "LivePrice": round(float(live_price), 2),
            "EMA20": round(ema20_value, 2),
            "IsAbove": is_above,
            "DiffPoints": diff_points,
            "DiffPercent": diff_percent,
        }
    except Exception as e:
        return None


# --- Benutzeroberfläche mit zentriertem Layout ---
_, col_center, _ = st.columns([1, 2, 1])

with col_center:
    if os.path.exists("bulle.jpg"):
        st.image("bulle.jpg", use_container_width=True)

    st.markdown("### 🦉 Dax Overnight Scanner")
    st.markdown("""
    Es wird überprüft, ob der DAX über dem **20-Tage gleitenden Durchschnitt (EMA 20)** liegt. 
    Wenn ja: Long-Position um **17:30 Uhr** eröffnen und am nächsten Tag um **09:00 Uhr** schließen.
    
    * **🟢 GO:** Der DAX liegt über dem EMA 20.
    * **🔴 NO GO:** Der DAX liegt unter dem EMA 20.
    """)
    st.write("---")

    # Button zum manuellen Aktualisieren
    if st.button("🔄 Live-Daten jetzt aktualisieren", type="primary", use_container_width=True):
        st.cache_data.clear()

    # Daten laden und auswerten
    df_history, live_price = get_dax_live_data()
    result = evaluate_dax_overnight(df_history, live_price)

    if result:
        st.caption(f"Letzte Abfrage: {result['Timestamp']}")
        
        # Visuelle Signal-Ausgabe
        if result["IsAbove"]:
            st.success("### 🟢 GO – Long-Position um 17:30 Uhr eröffnen!")
        else:
            st.error("### 🔴 NO GO – Keine Long-Position (unter EMA 20)!")

        # Kennzahlen-Übersicht in Spalten
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(label="DAX Live-Kurs", value=f"{result['LivePrice']:,.2f}")
        with m2:
            st.metric(label="EMA 20 (Basis Tagesbasis)", value=f"{result['EMA20']:,.2f}")
        with m3:
            st.metric(
                label="Abstand", 
                value=f"{result['DiffPoints']} Pkt.", 
                delta=f"{result['DiffPercent']}%"
            )

        with st.expander("📊 Historische Chart-Daten anzeigen (letzte 30 Tage)"):
            display_df = df_history[["Close", "EMA20"]].tail(30).copy()
            display_df.columns = ["Historischer Schlusskurs", "EMA 20"]
            st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Es konnten keine aktuellen DAX-Daten geladen werden.")
