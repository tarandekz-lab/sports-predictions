import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sports Predictions", layout="wide")

st.title("⚽ Sports Betting Predictions")
st.write("Predikcije za idućih 24h na temelju kvota sa **The Odds API**.")

# Unos API ključa
api_key = st.text_input("Unesi svoj The Odds API ključ:", type="password")

if api_key:
    url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/"
    params = {
        "apiKey": api_key,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    resp = requests.get(url, params=params)

    if resp.status_code != 200:
        st.error("Greška kod dohvaćanja podataka. Provjeri API key.")
    else:
        data = resp.json()
        matches = []

        for game in data:
            home = game["home_team"]
            away = game["away_team"]
            commence = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))

            for book in game["bookmakers"]:
                for market in book["markets"]:
                    for outcome in market["outcomes"]:
                        matches.append({
                            "Utakmica": f"{home} vs {away}",
                            "Vrijeme": commence.strftime("%Y-%m-%d %H:%M"),
                            "Tip": outcome["name"],
                            "Kvota": outcome["price"]
                        })

        df = pd.DataFrame(matches)

        if not df.empty:
            # sortiraj po kvoti (sigurni parovi = niža kvota)
            safe_picks = df.sort_values("Kvota").head(10)
            longshots = df[df["Kvota"] >= 2.0].sort_values("Kvota", ascending=False).head(10)

            st.subheader("✅ Top 10 sigurnijih parova")
            st.dataframe(safe_picks, use_container_width=True)

            st.subheader("🎯 Top 10 s kvotom >= 2.0")
            st.dataframe(longshots, use_container_width=True)
        else:
            st.warning("Nema podataka za prikaz.")
