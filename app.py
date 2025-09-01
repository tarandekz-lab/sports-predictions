import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Sports Predictions v8.1", layout="wide")

st.title("⚽🏀 Sports Predictions v8.1")
st.sidebar.header("⚙️ Postavke")

api_key = st.sidebar.text_input("Unesi The Odds API ključ", type="password")

safe_count = st.sidebar.slider("Broj SAFE parova", 10, 30, 20)
longshot_count = st.sidebar.slider("Broj LONGSHOT parova", 5, 20, 10)
totals_bonus = st.sidebar.slider("Bonus za totals (%)", 0, 30, 10)

if st.sidebar.button("🔄 Dohvati ponudu"):
    if not api_key:
        st.error("⚠️ Unesi API ključ!")
    else:
        sports_url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
        sports = requests.get(sports_url).json()
        selected_sports = [s['key'] for s in sports if s.get('active')]

        rows = []
        for sport in selected_sports:
            odds_url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={api_key}&regions=eu&markets=h2h,totals&oddsFormat=decimal"
            data = requests.get(odds_url).json()
            for match in data:
                teams = match.get("home_team","") + " - " + match.get("away_team","")
                commence = match.get("commence_time")
                try:
                    match_time = datetime.fromisoformat(commence.replace("Z","+00:00"))
                except:
                    continue
                if match_time > datetime.now(timezone.utc) + timedelta(hours=24):
                    continue
                for bookmaker in match.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        mkey = market.get("key")
                        for outcome in market.get("outcomes", []):
                            price = outcome.get("price")
                            name = outcome.get("name")
                            point = outcome.get("point","-")
                            imp_prob = 1/price*100 if price else None
                            est_prob = imp_prob + totals_bonus if mkey=="totals" else imp_prob
                            value = (est_prob/100 * price - 1)*100 if price else None
                            rows.append({
                                "Liga": sport,
                                "Utakmica": teams,
                                "Tip": mkey,
                                "Granica": point,
                                "Ishod": name,
                                "Kvota": price,
                                "Imp_%": round(imp_prob,1) if imp_prob else None,
                                "Predv_%": round(est_prob,1) if est_prob else None,
                                "Value_%": round(value,1) if value else None,
                                "Vrijeme": match_time
                            })
        df = pd.DataFrame(rows).drop_duplicates()

        # Odvajanje na totals i moneyline
        df_totals = df[df["Tip"]=="totals"].copy()
        df_money = df[df["Tip"]=="h2h"].copy()

        # Rangiranje po value
        df_totals = df_totals.sort_values("Value_%", ascending=False)
        df_money = df_money.sort_values("Value_%", ascending=False)

        # SAFE izbor: omjer ~3:2 u korist totals
        safe_totals_n = int(safe_count*0.6)
        safe_money_n = safe_count - safe_totals_n
        safe_picks = pd.concat([df_totals.head(safe_totals_n), df_money.head(safe_money_n)])

        # LONGSHOT izbor: kvote 2.00-5.5
        df_long = df[(df["Kvota"]>=2.0) & (df["Kvota"]<=5.5)]
        long_totals_n = int(longshot_count*0.6)
        long_money_n = longshot_count - long_totals_n
        long_picks = pd.concat([
            df_long[df_long["Tip"]=="totals"].head(long_totals_n),
            df_long[df_long["Tip"]=="h2h"].head(long_money_n)
        ]).sort_values("Kvota")

        st.subheader("✅ SAFE parovi")
        st.dataframe(safe_picks.reset_index(drop=True))

        st.subheader("🎯 LONGSHOT parovi")
        st.dataframe(long_picks.reset_index(drop=True))
