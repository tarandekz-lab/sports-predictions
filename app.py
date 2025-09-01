
import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime, timezone

# Pokušaj učitavanja API key-a iz config.json
API_KEY = None
try:
    with open("config.json", "r") as f:
        config = json.load(f)
        API_KEY = config.get("API_KEY")
except FileNotFoundError:
    pass

st.title("Sports Predictions App v8.5")

# Ako nema key-a u configu, omogućiti unos
if not API_KEY:
    API_KEY = st.text_input("Unesi API key:", type="password")

if not API_KEY:
    st.warning("Molimo unesite API key ili ga stavite u config.json.")
    st.stop()

# Podešavanja
safe_limit = st.slider("Broj SAFE parova", 5, 50, 20)
longshot_limit = st.slider("Broj LONGSHOT parova", 5, 50, 10)

# Dohvat podataka
url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
params = {
    "apiKey": API_KEY,
    "regions": "eu",
    "markets": "h2h,totals",
    "oddsFormat": "decimal"
}

try:
    response = requests.get(url, params=params)
    data = response.json()
except Exception as e:
    st.error(f"Greška pri dohvaćanju podataka: {e}")
    st.stop()

matches = []
seen = set()

for match in data:
    try:
        teams = f"{match['home_team']} - {match['away_team']}"
        if teams in seen:
            continue
        seen.add(teams)

        commence = datetime.fromisoformat(match['commence_time'].replace("Z","+00:00")).astimezone(timezone.utc)
        if commence < datetime.now(timezone.utc):
            continue

        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        matches.append({
                            "teams": teams,
                            "commence_time": commence.strftime("%Y-%m-%d %H:%M"),
                            "market": "Konačni ishod",
                            "pick": outcome["name"],
                            "odds": outcome["price"]
                        })
                elif market["key"] == "totals":
                    for outcome in market["outcomes"]:
                        line = market.get("outcomes", [])[0].get("point", "")
                        matches.append({
                            "teams": teams,
                            "commence_time": commence.strftime("%Y-%m-%d %H:%M"),
                            "market": f"Over/Under {line}",
                            "pick": outcome["name"],
                            "odds": outcome["price"]
                        })
    except Exception:
        continue

df = pd.DataFrame(matches).drop_duplicates()

if df.empty:
    st.warning("Nema dostupnih podataka.")
    st.stop()

# SAFE izbori
safe_df = df[df["odds"] >= 1.40].sort_values("odds").head(safe_limit)
st.subheader("SAFE izbori")
st.dataframe(safe_df)

# LONGSHOT izbori
longshot_df = df[(df["odds"] >= 2.00) & (df["odds"] <= 5.50)].sort_values("odds").head(longshot_limit)
st.subheader("LONGSHOT izbori")
st.dataframe(longshot_df)

# Download gumb
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("📥 Preuzmi ponudu u CSV formatu", csv, "ponuda.csv", "text/csv")
