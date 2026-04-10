from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
import httpx
import os
import json
from datetime import datetime, date, timedelta
import pytz

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TW = pytz.timezone("Asia/Taipei")
DB_URL = os.environ.get("DATABASE_URL", "")
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")

# ── ELO 資料
TEAM_DATA = {
    "Atlanta Hawks":{"elo":1697,"pts":116.3,"opp":112.1,"pace":101.5,"abbr":"ATL"},
    "Boston Celtics":{"elo":1759,"pts":117.8,"opp":108.9,"pace":97.5,"abbr":"BOS"},
    "Brooklyn Nets":{"elo":1180,"pts":106.4,"opp":118.2,"pace":99.5,"abbr":"BKN"},
    "Charlotte Hornets":{"elo":1635,"pts":111.8,"opp":113.5,"pace":100.2,"abbr":"CHA"},
    "Chicago Bulls":{"elo":1280,"pts":104.6,"opp":117.8,"pace":97.2,"abbr":"CHI"},
    "Cleveland Cavaliers":{"elo":1677,"pts":113.9,"opp":108.4,"pace":96.2,"abbr":"CLE"},
    "Dallas Mavericks":{"elo":1250,"pts":104.2,"opp":117.8,"pace":97.8,"abbr":"DAL"},
    "Denver Nuggets":{"elo":1651,"pts":114.5,"opp":111.2,"pace":97.9,"abbr":"DEN"},
    "Detroit Pistons":{"elo":1723,"pts":115.4,"opp":109.2,"pace":99.3,"abbr":"DET"},
    "Golden State Warriors":{"elo":1488,"pts":107.9,"opp":113.1,"pace":100.8,"abbr":"GSW"},
    "Houston Rockets":{"elo":1596,"pts":113.2,"opp":110.8,"pace":99.6,"abbr":"HOU"},
    "Indiana Pacers":{"elo":1430,"pts":118.5,"opp":121.2,"pace":103.2,"abbr":"IND"},
    "Los Angeles Clippers":{"elo":1558,"pts":110.2,"opp":111.9,"pace":98.1,"abbr":"LAC"},
    "Los Angeles Lakers":{"elo":1666,"pts":112.7,"opp":110.5,"pace":98.8,"abbr":"LAL"},
    "Memphis Grizzlies":{"elo":1300,"pts":111.4,"opp":119.2,"pace":100.5,"abbr":"MEM"},
    "Miami Heat":{"elo":1470,"pts":107.2,"opp":115.3,"pace":96.5,"abbr":"MIA"},
    "Milwaukee Bucks":{"elo":1450,"pts":108.8,"opp":114.1,"pace":99.1,"abbr":"MIL"},
    "Minnesota Timberwolves":{"elo":1320,"pts":109.8,"opp":116.2,"pace":97.6,"abbr":"MIN"},
    "New Orleans Pelicans":{"elo":1380,"pts":108.2,"opp":116.5,"pace":98.7,"abbr":"NOP"},
    "New York Knicks":{"elo":1720,"pts":114.1,"opp":109.8,"pace":96.8,"abbr":"NYK"},
    "Oklahoma City Thunder":{"elo":1869,"pts":120.5,"opp":107.3,"pace":100.1,"abbr":"OKC"},
    "Orlando Magic":{"elo":1578,"pts":109.4,"opp":107.6,"pace":95.8,"abbr":"ORL"},
    "Philadelphia 76ers":{"elo":1220,"pts":103.8,"opp":118.5,"pace":96.9,"abbr":"PHI"},
    "Phoenix Suns":{"elo":1360,"pts":106.5,"opp":115.8,"pace":98.3,"abbr":"PHX"},
    "Portland Trail Blazers":{"elo":1200,"pts":106.2,"opp":120.4,"pace":100.3,"abbr":"POR"},
    "Sacramento Kings":{"elo":1340,"pts":115.2,"opp":118.4,"pace":102.1,"abbr":"SAC"},
    "San Antonio Spurs":{"elo":1903,"pts":118.2,"opp":105.1,"pace":98.2,"abbr":"SAS"},
    "Toronto Raptors":{"elo":1500,"pts":108.6,"opp":114.2,"pace":99.4,"abbr":"TOR"},
    "Utah Jazz":{"elo":1120,"pts":107.6,"opp":122.3,"pace":100.9,"abbr":"UTA"},
    "Washington Wizards":{"elo":1150,"pts":105.8,"opp":121.5,"pace":101.4,"abbr":"WAS"},
}

INJURIES = {
    "MIA": [{"player":"吉米·巴特勒","status":"缺陣","part":"膝"}],
    "DAL": [{"player":"盧卡·唐西奇","status":"缺陣","part":"膝"}],
    "BOS": [{"player":"波爾辛吉斯","status":"存疑","part":"腿"}],
    "LAL": [{"player":"勒布朗·詹姆斯","status":"存疑","part":"腳"}],
    "MEM": [{"player":"賈·莫蘭特","status":"存疑","part":"手"}],
    "PHI": [{"player":"喬爾·恩比德","status":"缺陣","part":"膝"}],
    "OKC": [{"player":"切特·霍姆格倫","status":"存疑","part":"背"}],
}

def inj_penalty(abbr):
    inj = INJURIES.get(abbr, [])
    return sum(4 if i["status"] == "缺陣" else 1.5 for i in inj)

def calc_model(home_en, away_en, bookie_prob):
    h = TEAM_DATA.get(home_en, {"elo":1400,"pts":110,"opp":110})
    a = TEAM_DATA.get(away_en, {"elo":1400,"pts":110,"opp":110})
    ha = h.get("abbr","")
    aa = a.get("abbr","")
    elo_diff = h["elo"] - a["elo"] + 70
    elo_prob = 1 / (1 + 10 ** (-elo_diff / 400))
    off_edge = (h["pts"] - a["opp"]) - (a["pts"] - h["opp"])
    off_prob = 0.5 + off_edge * 0.012
    inj_adj = (inj_penalty(aa) - inj_penalty(ha)) * 0.02
    model_prob = elo_prob*0.35 + off_prob*0.25 + bookie_prob*0.3 + 0.5*0.1 + inj_adj
    return max(0.05, min(0.95, model_prob))

def calc_ev(prob, odds):
    return (prob * odds - 1) * 100

async def get_db():
    return await asyncpg.connect(DB_URL)

async def init_db():
    if not DB_URL:
        return
    conn = await get_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            game_date DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            predicted_winner TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            bet_type TEXT NOT NULL,
            bet_odds FLOAT,
            ev_pct FLOAT,
            spread_line FLOAT,
            model_spread FLOAT,
            actual_winner TEXT,
            actual_home_score INTEGER,
            actual_away_score INTEGER,
            result BOOLEAN,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.close()

async def fetch_and_predict():
    """每天早上8點自動抓賽程並儲存預測"""
    if not ODDS_KEY or not DB_URL:
        print("缺少 ODDS_KEY 或 DB_URL")
        return
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] 開始抓取今日賽程...")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
                params={"apiKey": ODDS_KEY, "regions": "us", "markets": "h2h,spreads", "oddsFormat": "decimal", "dateFormat": "iso"},
                timeout=30
            )
            data = res.json()
        conn = await get_db()
        today = date.today()
        saved = 0
        for game in data:
            home_en = game["home_team"]
            away_en = game["away_team"]
            h2h_home = h2h_away = sp_line = sp_home_odds = sp_away_odds = None
            for bk in game.get("bookmakers", []):
                for mk in bk.get("markets", []):
                    if mk["key"] == "h2h":
                        ho = next((o for o in mk["outcomes"] if o["name"] == home_en), None)
                        ao = next((o for o in mk["outcomes"] if o["name"] == away_en), None)
                        if ho and ao:
                            h2h_home = ho["price"]
                            h2h_away = ao["price"]
                    if mk["key"] == "spreads":
                        ho = next((o for o in mk["outcomes"] if o["name"] == home_en), None)
                        ao = next((o for o in mk["outcomes"] if o["name"] == away_en), None)
                        if ho and ao:
                            sp_line = ho["point"]
                            sp_home_odds = ho["price"]
                            sp_away_odds = ao["price"]
                break
            if not h2h_home:
                continue
            raw_h = 1/h2h_home
            raw_a = 1/h2h_away
            bp = raw_h / (raw_h + raw_a)
            mp = calc_model(home_en, away_en, bp)
            ms = (mp - 0.5) * 28
            conf = max(round(mp*100), round((1-mp)*100))
            # 決定下注方向
            if sp_line is not None:
                diff = ms - sp_line
                if abs(diff) < 0.5:
                    bet_team = home_en if mp >= 0.5 else away_en
                    bet_odds = h2h_home if mp >= 0.5 else h2h_away
                    bet_type = "不讓分"
                elif diff > 0:
                    bet_team = home_en
                    bet_odds = sp_home_odds or 1.72
                    bet_type = f"讓分 {sp_line}"
                else:
                    bet_team = away_en
                    bet_odds = sp_away_odds or 1.72
                    bet_type = f"吃分 +{abs(sp_line)}"
            else:
                bet_team = home_en if mp >= 0.5 else away_en
                bet_odds = h2h_home if mp >= 0.5 else h2h_away
                bet_type = "不讓分"
            ev = calc_ev(conf/100, bet_odds)
            # 避免重複插入
            exists = await conn.fetchval(
                "SELECT id FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",
                today, home_en, away_en
            )
            if not exists:
                await conn.execute("""
                    INSERT INTO predictions (game_date, home_team, away_team, predicted_winner, confidence, bet_type, bet_odds, ev_pct, spread_line, model_spread)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """, today, home_en, away_en, bet_team, conf, bet_type, bet_odds, ev, sp_line, ms)
                saved += 1
        await conn.close()
        print(f"✅ 儲存 {saved} 場預測")
    except Exception as e:
        print(f"❌ 錯誤: {e}")

async def update_results():
    """每天凌晨2點抓昨天比賽結果並更新"""
    if not DB_URL:
        return
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] 更新昨日比賽結果...")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
                timeout=15
            )
            data = res.json()
        conn = await get_db()
        yesterday = date.today() - timedelta(days=1)
        updated = 0
        for event in data.get("events", []):
            comp = event["competitions"][0]
            status = event["status"]["type"]["state"]
            if status != "post":
                continue
            home = next((c for c in comp["competitors"] if c["homeAway"] == "home"), None)
            away = next((c for c in comp["competitors"] if c["homeAway"] == "away"), None)
            if not home or not away:
                continue
            home_name = home["team"]["displayName"]
            away_name = away["team"]["displayName"]
            home_score = int(home.get("score", 0))
            away_score = int(away.get("score", 0))
            actual_winner = home_name if home_score > away_score else away_name
            row = await conn.fetchrow(
                "SELECT id, predicted_winner FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",
                yesterday, home_name, away_name
            )
            if row:
                result = row["predicted_winner"] == actual_winner
                await conn.execute("""
                    UPDATE predictions SET actual_winner=$1, actual_home_score=$2, actual_away_score=$3, result=$4
                    WHERE id=$5
                """, actual_winner, home_score, away_score, result, row["id"])
                updated += 1
        await conn.close()
        print(f"✅ 更新 {updated} 場結果")
    except Exception as e:
        print(f"❌ 錯誤: {e}")

# ── API 路由
@app.get("/")
async def root():
    return {"status": "ok", "message": "NBA 預測系統後端運作中"}

@app.get("/api/predictions/today")
async def get_today():
    """今日預測"""
    if not DB_URL:
        return {"error": "DB not configured"}
    conn = await get_db()
    rows = await conn.fetch(
        "SELECT * FROM predictions WHERE game_date=$1 ORDER BY confidence DESC",
        date.today()
    )
    await conn.close()
    return [dict(r) for r in rows]

@app.get("/api/predictions/history")
async def get_history(days: int = 30):
    """歷史回測（只含有結果的）"""
    if not DB_URL:
        return {"error": "DB not configured"}
    conn = await get_db()
    rows = await conn.fetch("""
        SELECT * FROM predictions
        WHERE result IS NOT NULL
        AND game_date >= CURRENT_DATE - $1::interval
        ORDER BY game_date DESC, confidence DESC
    """, f"{days} days")
    await conn.close()
    return [dict(r) for r in rows]

@app.get("/api/stats")
async def get_stats():
    """勝率統計"""
    if not DB_URL:
        return {"error": "DB not configured"}
    conn = await get_db()
    today_stats = await conn.fetchrow("""
        SELECT COUNT(*) as total, SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins
        FROM predictions WHERE game_date=CURRENT_DATE AND result IS NOT NULL
    """)
    week_stats = await conn.fetchrow("""
        SELECT COUNT(*) as total, SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins
        FROM predictions WHERE game_date >= CURRENT_DATE - interval '7 days' AND result IS NOT NULL
    """)
    month_stats = await conn.fetchrow("""
        SELECT COUNT(*) as total, SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins
        FROM predictions WHERE game_date >= CURRENT_DATE - interval '30 days' AND result IS NOT NULL
    """)
    high_conf = await conn.fetchrow("""
        SELECT COUNT(*) as total, SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins
        FROM predictions WHERE confidence >= 70 AND result IS NOT NULL
    """)
    await conn.close()
    def wr(row):
        if not row or not row["total"]:
            return {"rate": 0, "wins": 0, "total": 0}
        return {"rate": round(row["wins"]/row["total"]*100), "wins": row["wins"], "total": row["total"]}
    return {
        "today": wr(today_stats),
        "week": wr(week_stats),
        "month": wr(month_stats),
        "high_conf": wr(high_conf)
    }

@app.post("/api/trigger/predict")
async def trigger_predict():
    """手動觸發預測（測試用）"""
    await fetch_and_predict()
    return {"status": "ok"}

@app.post("/api/trigger/results")
async def trigger_results():
    """手動觸發更新結果（測試用）"""
    await update_results()
    return {"status": "ok"}

# ── 啟動定時任務
scheduler = AsyncIOScheduler(timezone=TW)

@app.on_event("startup")
async def startup():
    await init_db()
    # 每天早上8點抓預測
    scheduler.add_job(fetch_and_predict, "cron", hour=8, minute=0)
    # 每天凌晨2點更新結果
    scheduler.add_job(update_results, "cron", hour=2, minute=0)
    scheduler.start()
    print("✅ NBA 預測後端啟動完成")
