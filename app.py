import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd
from dateutil import parser

st.set_page_config(page_title="Sports Predictions", layout="wide")
st.title("📊 Sports Predictions (24h, All Sports)")

api_key = st.text_input("Unesi svoj Odds API key:", type="password")

if api_key:
    # Povuci sve dostupne sportove
    sports_url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
    resp_sports = requests.get(sports_url)
    if resp_sports.status_code != 200:
        st.error("Ne mogu povući listu sportova. Provjeri API key ili limit.")
    else:
        sports_data = resp_sports.json()
        sports = [s['key'] for s in sports_data]

        matches = []

        # Koristimo timezone-aware datetimes (UTC)
        now = datetime.now(timezone.utc)
        limit = now + timedelta(hours=24)

        for sport in sports:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
            params = {
                "apiKey": api_key,
                "regions": "eu",
                "markets": "h2h,totals",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            }

            resp = requests.get(url, params=params)
            if resp.status_code != 200:
                continue

            data = resp.json()

            for game in data:
                try:
                    commence = parser.isoparse(game["commence_time"])
                except Exception:
                    continue

                if not (now <= commence <= limit):
                    continue

                home = game["home_team"]
                away = game["away_team"]

                for book in game.get("bookmakers", []):
                    for market in book.get("markets", []):
                        for outcome in market.get("outcomes", []):
                            matches.append({
                                "Sport": sport,
                                "Utakmica": f"{home} vs {away}",
                                "Vrijeme": commence.strftime("%Y-%m-%d %H:%M %Z"),
                                "Tip": outcome["name"],
                                "Kvota": outcome["price"]
                            })

        if matches:
            df = pd.DataFrame(matches)

            # Safe pick: min kvota 1.4, 20 parova s najmanjim kvotama
            safe_picks = df[df["Kvota"] >= 1.4].sort_values("Kvota").head(20)
            st.subheader("✅ Top 20 sigurnih (min kvota 1.40)")
            st.dataframe(safe_picks)

            # Longshot: kvota >= 2.0, 10 najvećih kvota
            longshots = df[df["Kvota"] >= 2.0].sort_values("Kvota", ascending=False).head(10)
            st.subheader("🎯 Top 10 longshot (>2.0)")
            st.dataframe(longshots)
        else:
            st.warning("Nema događaja u sljedećih 24h.")
else:
    st.info("Unesi svoj API key za prikaz podataka.")
