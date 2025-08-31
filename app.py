import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd
from dateutil import parser

st.set_page_config(page_title="Sports Predictions", layout="wide")
st.title("📊 Sports Predictions (24h, Multi-Sport)")

api_key = st.text_input("Unesi svoj Odds API key:", type="password")

if api_key:
    sports = [
        "soccer",
        "basketball_nba",
        "basketball_euroleague",
        "icehockey_nhl",
        "baseball_mlb",
        "americanfootball_nfl",
        "tennis"
    ]

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

        # Najsigurniji (kvote najniže, 10 najboljih)
        safe_picks = df.sort_values("Kvota").head(10)
        st.subheader("✅ Top 10 sigurnih")
        st.dataframe(safe_picks)

        # Longshot (kvota >= 2.0)
        longshots = df[df["Kvota"] >= 2.0].sort_values("Kvota", ascending=False).head(10)
        st.subheader("🎯 Top 10 longshot (>2.0)")
        st.dataframe(longshots)
    else:
        st.warning("Nema događaja u sljedećih 24h za odabrane sportove.")
else:
    st.info("Unesi svoj API key za prikaz podataka.")
