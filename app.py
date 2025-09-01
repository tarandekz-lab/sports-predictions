import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd

st.set_page_config(page_title="Sports Predictions", layout="wide")

st.title("📊 Sports Predictions App v8.3")

API_KEY = st.sidebar.text_input("Unesi The Odds API ključ", type="password")
hours_ahead = st.sidebar.slider("Koliko sati unaprijed gledati", 6, 48, 24)

if not API_KEY:
    st.warning("🔑 Unesi svoj The Odds API ključ u sidebaru.")
    st.stop()

sports_url = f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}"
sports = requests.get(sports_url).json()

if not isinstance(sports, list):
    st.error("❌ Neuspješan dohvat sportova. Provjeri API ključ.")
    st.stop()

selected_sports = [s["key"] for s in sports if isinstance(s, dict) and s.get("active")]

all_matches = []
for sport in selected_sports:
    odds_url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?regions=eu&markets=h2h,totals&oddsFormat=decimal&apiKey={API_KEY}"
    data = requests.get(odds_url).json()

    # Ako API vrati grešku (string ili dict), preskoči
    if not isinstance(data, list):
        continue

    for match in data:
        teams = f"{match.get('home_team','')} - {match.get('away_team','')}"
        commence = match.get("commence_time")
        try:
            match_time = datetime.fromisoformat(commence.replace("Z","+00:00"))
        except:
            continue

        # filtriraj na vrijeme
        if match_time > datetime.now(timezone.utc) + timedelta(hours=hours_ahead):
            continue

        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                for outcome in market.get("outcomes", []):
                    row = {
                        "Sport": sport,
                        "Utakmica": teams,
                        "Vrijeme": match_time,
                        "Tip": outcome.get("name"),
                        "Tržište": market_key,
                        "Granica": outcome.get("point"),
                        "Kvota": outcome.get("price")
                    }
                    all_matches.append(row)

if not all_matches:
    st.warning("⚠️ Nema dostupnih utakmica u odabranom vremenu.")
    st.stop()

df = pd.DataFrame(all_matches)

# Ukloni duplikate (isti sport, utakmica, tip, tržište, granica, kvota)
df = df.drop_duplicates(subset=["Sport","Utakmica","Tip","Tržište","Granica","Kvota"])

# SAFE: kvota >= 1.40 (20 parova, prioritet totals 3:2)
safe = df[df["Kvota"] >= 1.40].sort_values("Kvota").head(20)

# LONGSHOT: kvota 2.00-5.50
longshot = df[(df["Kvota"] >= 2.00) & (df["Kvota"] <= 5.50)].sort_values("Kvota").head(20)

st.subheader("✅ SAFE izbori (20 parova, min 1.40)")
st.dataframe(safe)

st.subheader("🎯 LONGSHOT izbori (2.00 - 5.50)")
st.dataframe(longshot)
