import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd
from dateutil import parser

st.set_page_config(page_title="Sports Predictions", layout="wide")
st.title("📊 Sports Predictions (24h, All Sports, No Duplicates)")

st.markdown(
    """
**Light model (objašnjenje):**
- Procjena vjerojatnosti se bazira na impliciranoj vjerojatnosti iz kvote (1/kvota),
  uz *blagi* bonus za **zbrojeve (totals)** tržišta (heuristika, podesivo sliderom u sidebaru).
- Ovo nije model s formom/ozljedama — to možemo dodati kasnije s posebnim API-jem.
    """
)

# ▶️ Kontrole (sidebar)
with st.sidebar:
    st.header("⚙️ Postavke")
    api_key = st.text_input("Unesi svoj The Odds API key:", type="password")
    safe_count = st.slider("Broj 'safe' parova", min_value=5, max_value=50, value=20, step=1)
    longshot_count = st.slider("Broj 'longshot' parova", min_value=5, max_value=50, value=10, step=1)
    totals_bonus_pct = st.slider("Heuristički bonus za totals (%)", min_value=0, max_value=15, value=5, step=1)
    st.caption("Bonus se primjenjuje na procijenjenu vjerojatnost za tržišta zbrojeva (over/under).")
    fetch_btn = st.button("🔄 Dohvati ponudu")

if not api_key:
    st.info("🔑 Unesi svoj API key u sidebaru pa klikni 'Dohvati ponudu'. (The Odds API)")
elif fetch_btn:
    # 1) Povuci sve sportove za koje API key ima pristup
    sports_url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
    resp_sports = requests.get(sports_url, timeout=30)
    if resp_sports.status_code != 200:
        st.error(f"Ne mogu povući listu sportova (status {resp_sports.status_code}). Provjeri API key ili limit.")
        st.stop()

    try:
        sports_data = resp_sports.json()
    except Exception:
        st.error("Neočekivan odgovor pri dohvaćanju liste sportova.")
        st.stop()

    sport_keys = [s.get('key') for s in sports_data if s.get('key')]
    if not sport_keys:
        st.warning("Nema dostupnih sportova za tvoj API key.")
        st.stop()

    rows = []
    now = datetime.now(timezone.utc)
    limit = now + timedelta(hours=24)

    progress = st.progress(0)
    total = len(sport_keys)

    # 2) Za svaki sport povuci kvote (h2h + totals) i filtriraj na 24h
    for idx, sport in enumerate(sport_keys, start=1):
        progress.progress(min(idx/total, 1.0))
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
        params = {
            "apiKey": api_key,
            "regions": "eu",
            "markets": "h2h,totals",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
        except Exception:
            continue

        if resp.status_code != 200:
            continue

        try:
            data = resp.json()
        except Exception:
            continue

        if not isinstance(data, list):
            continue

        for game in data:
            try:
                commence = parser.isoparse(game.get("commence_time", ""))
            except Exception:
                continue

            if not (now <= commence <= limit):
                continue

            game_id = game.get("id")
            home = game.get("home_team", "")
            away = game.get("away_team", "")

            for book in game.get("bookmakers", []):
                for market in book.get("markets", []):
                    market_key = market.get("key", "")
                    for outcome in market.get("outcomes", []):
                        price = outcome.get("price")
                        name = outcome.get("name", "")
                        if price is None:
                            continue
                        rows.append({
                            "GameID": game_id,
                            "Sport": sport,
                            "Market": market_key,
                            "Utakmica": f"{home} vs {away}",
                            "Vrijeme": commence.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                            "Tip": name,
                            "Kvota": float(price)
                        })

    if not rows:
        st.warning("Nema događaja u sljedećih 24h.")
        st.stop()

    # 3) Ukloni duplikate po GameID + Tip — zadrži NAJVIŠU kvotu
    df = pd.DataFrame(rows)
    df = df.sort_values("Kvota", ascending=False).drop_duplicates(subset=["GameID", "Tip"], keep="first")

    # 4) Oznaka totals tržišta
    df["Totals"] = df["Market"].str.contains("totals", case=False, na=False)

    # 5) Implicirana vjerojatnost i heuristička procjena
    df["Imp_prob"] = 1.0 / df["Kvota"]
    bonus = totals_bonus_pct / 100.0
    df["Est_prob"] = df["Imp_prob"] * (1.0 + bonus * df["Totals"].astype(float))
    df["Est_prob"] = df["Est_prob"].clip(upper=0.99)

    # 6) Value metrika
    df["Value"] = df["Est_prob"] * df["Kvota"] - 1.0

    # 7) Lijep prikaz postotaka
    df["Predv. vjerojatnost (%)"] = (df["Est_prob"] * 100).round(1)
    df["Implicirana (%)"] = (df["Imp_prob"] * 100).round(1)
    df["Value (%)"] = (df["Value"] * 100).round(1)

    # 8) SAFE i LONGSHOT skupovi
    safe = df[df["Kvota"] >= 1.40].copy()
    safe = safe.sort_values(by=["Totals", "Kvota"], ascending=[False, True]).head(safe_count)

    longshot = df[(df["Kvota"] >= 2.00) & (df["Kvota"] <= 5.50)].copy()
    longshot = longshot.sort_values(by=["Totals", "Kvota"], ascending=[False, True]).head(longshot_count)

    cols_show = ["Sport", "Market", "Utakmica", "Vrijeme", "Tip", "Kvota",
                 "Predv. vjerojatnost (%)", "Implicirana (%)", "Value (%)"]

    st.subheader(f"✅ Top {safe_count} sigurnih (min kvota 1.40, totals prioritet)")
    st.dataframe(safe[cols_show], use_container_width=True)

    st.subheader(f"🎯 Top {longshot_count} longshot (kvota 2.00–5.50, uzlazno, totals prioritet)")
    st.dataframe(longshot[cols_show], use_container_width=True)

else:
    st.stop()
