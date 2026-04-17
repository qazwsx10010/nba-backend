from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
import httpx
import os
import json as _json
from datetime import datetime, date, timedelta
import pytz

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])

TW = pytz.timezone("Asia/Taipei")
DB_URL    = os.environ.get("DATABASE_URL", "")
ODDS_KEY  = os.environ.get("ODDS_API_KEY", "")   # MLB Odds API key
JBOT_TOKEN= os.environ.get("JBOT_TOKEN", "DEV_ONLY_FOR_FREE_TOKEN")
SPORT     = os.environ.get("SPORT", "mlb").lower()  # 固定 mlb

# ── MLB 球隊資料（ELO 初始值，每小時由 ESPN standings 更新）
TEAM_DATA = {
    "Arizona Diamondbacks": {"elo":1495,"rs":4.7,"ra":4.6,"abbr":"ARI"},
    "Atlanta Braves":        {"elo":1590,"rs":5.0,"ra":3.9,"abbr":"ATL"},
    "Baltimore Orioles":     {"elo":1560,"rs":4.9,"ra":4.2,"abbr":"BAL"},
    "Boston Red Sox":        {"elo":1525,"rs":4.8,"ra":4.5,"abbr":"BOS"},
    "Chicago Cubs":          {"elo":1500,"rs":4.6,"ra":4.5,"abbr":"CHC"},
    "Chicago White Sox":     {"elo":1430,"rs":4.0,"ra":4.9,"abbr":"CWS"},
    "Cincinnati Reds":       {"elo":1480,"rs":4.6,"ra":4.7,"abbr":"CIN"},
    "Cleveland Guardians":   {"elo":1520,"rs":4.4,"ra":4.1,"abbr":"CLE"},
    "Colorado Rockies":      {"elo":1400,"rs":4.4,"ra":5.4,"abbr":"COL"},
    "Detroit Tigers":        {"elo":1460,"rs":4.3,"ra":4.5,"abbr":"DET"},
    "Houston Astros":        {"elo":1575,"rs":4.8,"ra":4.0,"abbr":"HOU"},
    "Kansas City Royals":    {"elo":1470,"rs":4.3,"ra":4.5,"abbr":"KC"},
    "Los Angeles Angels":    {"elo":1425,"rs":4.1,"ra":4.8,"abbr":"LAA"},
    "Los Angeles Dodgers":   {"elo":1610,"rs":5.2,"ra":3.8,"abbr":"LAD"},
    "Miami Marlins":         {"elo":1395,"rs":3.9,"ra":4.8,"abbr":"MIA"},
    "Milwaukee Brewers":     {"elo":1540,"rs":4.6,"ra":4.1,"abbr":"MIL"},
    "Minnesota Twins":       {"elo":1490,"rs":4.4,"ra":4.4,"abbr":"MIN"},
    "New York Mets":         {"elo":1510,"rs":4.6,"ra":4.4,"abbr":"NYM"},
    "New York Yankees":      {"elo":1585,"rs":5.1,"ra":4.1,"abbr":"NYY"},
    "Athletics":             {"elo":1415,"rs":4.0,"ra":4.9,"abbr":"ATH"},
    "Philadelphia Phillies": {"elo":1565,"rs":4.9,"ra":4.2,"abbr":"PHI"},
    "Pittsburgh Pirates":    {"elo":1445,"rs":4.2,"ra":4.7,"abbr":"PIT"},
    "San Diego Padres":      {"elo":1530,"rs":4.7,"ra":4.3,"abbr":"SD"},
    "San Francisco Giants":  {"elo":1465,"rs":4.2,"ra":4.4,"abbr":"SF"},
    "Seattle Mariners":      {"elo":1545,"rs":4.5,"ra":4.0,"abbr":"SEA"},
    "St. Louis Cardinals":   {"elo":1505,"rs":4.5,"ra":4.4,"abbr":"STL"},
    "Tampa Bay Rays":        {"elo":1515,"rs":4.5,"ra":4.3,"abbr":"TB"},
    "Texas Rangers":         {"elo":1535,"rs":4.8,"ra":4.4,"abbr":"TEX"},
    "Toronto Blue Jays":     {"elo":1485,"rs":4.5,"ra":4.5,"abbr":"TOR"},
    "Washington Nationals":  {"elo":1450,"rs":4.3,"ra":4.7,"abbr":"WSH"},
}

# 球場得分係數 (100=中性, >100=打者球場)
PARK_FACTORS = {
    "COL":121,"CIN":107,"BOS":106,"PHI":105,"TEX":104,"HOU":104,"NYY":103,"LAD":102,
    "DET":102,"ATL":101,"KC":101,"MIL":100,"CLE":100,"ARI":100,"MIA":100,"BAL":99,
    "TOR":99,"MIN":98,"WSH":98,"SD":97,"NYM":97,"STL":97,"SEA":96,"SF":96,
    "CHC":96,"CWS":95,"PIT":94,"TB":93,"LAA":93,"ATH":92,
}

TEAM_NAME_NORMALIZE = {
    "LA Angels":           "Los Angeles Angels",
    "LA Dodgers":          "Los Angeles Dodgers",
    "NY Mets":             "New York Mets",
    "NY Yankees":          "New York Yankees",
    "SF Giants":           "San Francisco Giants",
    "St Louis Cardinals":  "St. Louis Cardinals",
    "Saint Louis Cardinals":"St. Louis Cardinals",
    "Oakland Athletics":   "Athletics",
}

def normalize_team(name):
    return TEAM_NAME_NORMALIZE.get(name, name)

# 台灣運彩中文 → 英文
TW_TEAM_MAP = {
    "亞利桑那響尾蛇":"Arizona Diamondbacks","亞特蘭大勇士":"Atlanta Braves",
    "巴爾的摩金鶯":"Baltimore Orioles","波士頓紅襪":"Boston Red Sox",
    "芝加哥小熊":"Chicago Cubs","芝加哥白襪":"Chicago White Sox",
    "辛辛那提紅人":"Cincinnati Reds","克里夫蘭守護者":"Cleveland Guardians",
    "科羅拉多落磯":"Colorado Rockies","底特律老虎":"Detroit Tigers",
    "休士頓太空人":"Houston Astros","堪薩斯皇家":"Kansas City Royals",
    "洛杉磯天使":"Los Angeles Angels","洛杉磯道奇":"Los Angeles Dodgers",
    "邁阿密馬林魚":"Miami Marlins","密爾瓦基釀酒人":"Milwaukee Brewers",
    "明尼蘇達雙城":"Minnesota Twins","紐約大都會":"New York Mets",
    "紐約洋基":"New York Yankees","運動家":"Athletics",
    "費城費城人":"Philadelphia Phillies","匹茲堡海盜":"Pittsburgh Pirates",
    "聖地牙哥教士":"San Diego Padres","舊金山巨人":"San Francisco Giants",
    "西雅圖水手":"Seattle Mariners","聖路易紅雀":"St. Louis Cardinals",
    "坦帕灣光芒":"Tampa Bay Rays","德州遊騎兵":"Texas Rangers",
    "多倫多藍鳥":"Toronto Blue Jays","華盛頓國民":"Washington Nationals",
}

# MLB Polymarket 短名集合
MLB_PM_TEAMS = {
    "Diamondbacks","Braves","Orioles","Red Sox","Cubs","White Sox","Reds",
    "Guardians","Rockies","Tigers","Astros","Royals","Angels","Dodgers",
    "Marlins","Brewers","Twins","Mets","Yankees","Athletics","Phillies",
    "Pirates","Padres","Giants","Mariners","Cardinals","Rays","Rangers",
    "Blue Jays","Nationals",
}

# ESPN MLB team IDs
ESPN_MLB_IDS = {
    "Arizona Diamondbacks":"29","Atlanta Braves":"15","Baltimore Orioles":"1",
    "Boston Red Sox":"2","Chicago Cubs":"16","Chicago White Sox":"4",
    "Cincinnati Reds":"17","Cleveland Guardians":"5","Colorado Rockies":"27",
    "Detroit Tigers":"6","Houston Astros":"18","Kansas City Royals":"7",
    "Los Angeles Angels":"3","Los Angeles Dodgers":"19","Miami Marlins":"28",
    "Milwaukee Brewers":"8","Minnesota Twins":"9","New York Mets":"21",
    "New York Yankees":"10","Athletics":"11","Philadelphia Phillies":"22",
    "Pittsburgh Pirates":"23","San Diego Padres":"25","San Francisco Giants":"26",
    "Seattle Mariners":"12","St. Louis Cardinals":"24","Tampa Bay Rays":"30",
    "Texas Rangers":"13","Toronto Blue Jays":"14","Washington Nationals":"20",
}

# ── DB（optional，沒設 DATABASE_URL 就全部跳過）
async def get_db():
    if not DB_URL: return None
    url = DB_URL.replace("postgres://","postgresql://",1) if DB_URL.startswith("postgres://") else DB_URL
    return await asyncpg.connect(url)

async def init_db():
    if not DB_URL: return
    conn = await get_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            sport TEXT DEFAULT 'mlb',
            game_date DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            predicted_winner TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            bet_type TEXT,
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
    # 安全加欄位（舊 DB 可能沒有 sport 欄）
    try: await conn.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS sport TEXT DEFAULT 'mlb'")
    except: pass
    await conn.close()
    print("✅ DB 初始化完成")

# ── MLB 模型
def calc_model_mlb(home_en, away_en, bp, home_inj=None, away_inj=None):
    h = TEAM_DATA.get(home_en, {"elo":1500,"rs":4.3,"ra":4.3})
    a = TEAM_DATA.get(away_en, {"elo":1500,"rs":4.3,"ra":4.3})
    ha = h.get("abbr",""); aa = a.get("abbr","")
    # 主場優勢 Elo +24（MLB 主場勝率約 53%，NBA 是 57%）
    elo_p = 1 / (1 + 10 ** (-(h["elo"] - a["elo"] + 24) / 400))
    # 場均得失分差
    off_p = 0.5 + ((h["rs"] - a["ra"]) - (a["rs"] - h["ra"])) * 0.06
    # 傷兵（MLB 影響較小）
    hi = sum(3 if i.get("status_type")=="Out" else 1 for i in (home_inj or []))
    ai = sum(3 if i.get("status_type")=="Out" else 1 for i in (away_inj or []))
    inj_adj = (ai - hi) * 0.015
    # 球場係數
    pf = (PARK_FACTORS.get(ha, 100) - 100) * 0.001
    park_adj = -pf  # 打者球場對主隊略不利
    model = elo_p*0.35 + off_p*0.20 + bp*0.40 + 0.5*0.05 + inj_adj + park_adj
    return max(0.05, min(0.95, model))

# ── ESPN MLB 傷兵
async def fetch_espn_injuries():
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries"
            )
            data = res.json()
        injuries = {}
        for team_data in data.get("injuries", []):
            team_name = team_data.get("team", {}).get("displayName", "")
            team_name = normalize_team(team_name)
            if not team_name: continue
            players = []
            for item in team_data.get("injuries", []):
                athlete = item.get("athlete", {})
                status_type = item.get("type", {}).get("description", "")
                pos = athlete.get("position", {}).get("abbreviation", "")
                players.append({
                    "player": athlete.get("displayName", ""),
                    "position": pos,
                    "status_type": status_type,
                    "detail": item.get("shortComment", ""),
                    # 先發投手特別標記
                    "is_starter": pos in ("SP","P") and status_type in ("Out","Doubtful"),
                })
            injuries[team_name] = players
        return {"status":"ok","injuries":injuries,"updated":datetime.now(TW).strftime("%Y-%m-%d %H:%M")}
    except Exception as e:
        return {"status":"error","message":str(e),"injuries":{}}

# ── MLB Stats（ESPN standings → 更新 TEAM_DATA）
async def fetch_mlb_stats():
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://site.api.espn.com/apis/v2/sports/baseball/mlb/standings",
                params={"season": datetime.now(TW).year}
            )
            data = res.json()
        stats = {}
        updated = 0
        for conf in data.get("children", []):
            for entry in conf.get("standings", {}).get("entries", []):
                team_name = normalize_team(entry.get("team", {}).get("displayName", ""))
                if team_name not in TEAM_DATA: continue
                wins = losses = 0
                rs = ra = None
                home_w = home_l = away_w = away_l = 0
                for stat in entry.get("stats", []):
                    n = stat.get("name","")
                    v = stat.get("value", 0)
                    dv = stat.get("displayValue","")
                    if n == "wins":
                        try: wins = int(v)
                        except: pass
                    if n == "losses":
                        try: losses = int(v)
                        except: pass
                    # MLB 場均得分/失分
                    if n in ("avgRunsScored","runsScored","avgPointsFor"):
                        try:
                            val = round(float(v), 2)
                            if 1 < val < 15: rs = val
                        except: pass
                    if n in ("avgRunsAllowed","runsAllowed","avgPointsAgainst"):
                        try:
                            val = round(float(v), 2)
                            if 1 < val < 15: ra = val
                        except: pass
                    # 主客場紀錄
                    if n == "Home":
                        try:
                            p = dv.split("-"); home_w,home_l = int(p[0]),int(p[1])
                        except: pass
                    if n in ("Road","Away"):
                        try:
                            p = dv.split("-"); away_w,away_l = int(p[0]),int(p[1])
                        except: pass

                if wins + losses > 0:
                    wp = wins / (wins + losses)
                    new_elo = round(1500 + (wp - 0.5) * 600)
                    TEAM_DATA[team_name]["elo"] = new_elo
                    if rs and rs > 1: TEAM_DATA[team_name]["rs"] = rs
                    if ra and ra > 1: TEAM_DATA[team_name]["ra"] = ra
                    hw = round(home_w/(home_w+home_l)*100,1) if home_w+home_l>0 else None
                    aw = round(away_w/(away_w+away_l)*100,1) if away_w+away_l>0 else None
                    stats[team_name] = {
                        "wins":wins,"losses":losses,"win_pct":round(wp*100,1),
                        "elo":new_elo,"rs":TEAM_DATA[team_name]["rs"],"ra":TEAM_DATA[team_name]["ra"],
                        "home_win_pct":hw,"away_win_pct":aw,
                    }
                    updated += 1
        print(f"✅ MLB Stats 更新 {updated} 支球隊")
        return {"status":"ok","updated":updated,"stats":stats}
    except Exception as e:
        return {"status":"error","message":str(e)}

# ── Polymarket MLB 勝率
async def fetch_polymarket_odds():
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://gamma-api.polymarket.com/events",
                params={
                    "active":"true","closed":"false","limit":"50",
                    "tag_slug":"baseball",
                    "order":"volume24hr","ascending":"false",
                },
                headers={"User-Agent":"Mozilla/5.0"}
            )
            data = res.json()

        events = data if isinstance(data, list) else data.get("events", [])
        result = {}

        non_mlb = ["Premier League","Champions","Arsenal","Chelsea","Barcelona",
                   "IPL","NHL","NBA","NFL","Oilers","Flames","Leafs"]

        for event in events:
            event_vol = float(event.get("volume24hr",0) or event.get("volume",0) or 0)
            title = event.get("title","")

            if any(kw in title for kw in non_mlb): continue
            found = [t for t in MLB_PM_TEAMS if t in title]
            if len(found) < 2: continue

            for m in event.get("markets", []):
                question = m.get("question","")
                # 只要 moneyline（"X vs. Y"，不要 Spread/Total）
                if "vs." not in question: continue
                if any(x in question.lower() for x in ["spread","total","points","inning","draw"]): continue

                outcomes_raw = m.get("outcomes","[]")
                prices_raw   = m.get("outcomePrices","[]")
                try: outcomes = _json.loads(outcomes_raw) if isinstance(outcomes_raw,str) else outcomes_raw
                except: continue
                try: prices = _json.loads(prices_raw) if isinstance(prices_raw,str) else prices_raw
                except: continue

                if len(outcomes) != 2 or len(prices) != 2: continue
                t1,t2 = str(outcomes[0]).strip(), str(outcomes[1]).strip()
                if t1 not in MLB_PM_TEAMS or t2 not in MLB_PM_TEAMS: continue

                try: p1,p2 = float(prices[0]),float(prices[1])
                except: continue
                if not (0 < p1 < 1 and 0 < p2 < 1): continue

                vol = float(m.get("volume24hr",0) or m.get("volumeNum",0) or event_vol or 0)
                result[t1] = {"prob":round(p1*100,1),"volume":round(vol),"reliable":vol>=5000}
                result[t2] = {"prob":round(p2*100,1),"volume":round(vol),"reliable":vol>=5000}
                break

        return {"status":"ok","odds":result,"markets":len(result)//2}
    except Exception as e:
        return {"status":"error","message":str(e),"odds":{}}

# ── 台灣運彩 MLB
async def fetch_tw_odds(target_date=None):
    if not target_date: target_date = date.today().strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                "https://api.sportsbot.tech/v2/odds",
                params={"sport":"MLB","date":target_date,"mode":"close"},
                headers={"X-JBot-Token":JBOT_TOKEN}
            )
            data = res.json()
        if data.get("status") != "OK":
            return {"status":"error","message":str(data)}
        games = []
        for item in data.get("data",[]):
            away_en = TW_TEAM_MAP.get(item.get("away",""), item.get("away",""))
            home_en = TW_TEAM_MAP.get(item.get("home",""), item.get("home",""))
            odds_list = item.get("odds",[])
            if not odds_list: continue
            latest = odds_list[-1]
            normal = latest.get("normal",{})
            handi  = latest.get("handi",{})
            total_data = latest.get("total",{})
            main_spread=main_h=main_a=None
            for sv,sd in handi.items():
                if sd.get("m"): main_spread=float(sv);main_h=sd.get("h");main_a=sd.get("a");break
            main_total=main_over=main_under=None
            for tv,ti in total_data.items():
                if ti.get("m"): main_total=float(tv);main_over=ti.get("o");main_under=ti.get("u");break
            games.append({
                "home_tw":item.get("home",""),"away_tw":item.get("away",""),
                "home_en":home_en,"away_en":away_en,"time":item.get("time",""),
                "normal_home":normal.get("h"),"normal_away":normal.get("a"),
                "spread":main_spread,"spread_home_odds":main_h,"spread_away_odds":main_a,
                "total":main_total,"over_odds":main_over,"under_odds":main_under,
            })
        return {"status":"ok","date":target_date,"games":games,"quota":data.get("user",{})}
    except Exception as e:
        return {"status":"error","message":str(e)}

# ── Odds API 抓盤 + 儲存預測
async def fetch_and_predict():
    if not ODDS_KEY: return {"status":"error","message":"缺少 ODDS_API_KEY"}
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] MLB 抓取今日賽程...")
    try:
        inj_data  = await fetch_espn_injuries()
        injuries  = inj_data.get("injuries",{})

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(
                "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/",
                params={
                    "apiKey":ODDS_KEY,"regions":"us","markets":"h2h,spreads",
                    "oddsFormat":"decimal","dateFormat":"iso"
                }
            )
            data = res.json()

        conn = await get_db()
        today = date.today(); saved = 0

        for game in data:
            hEn = normalize_team(game["home_team"])
            aEn = normalize_team(game["away_team"])
            h2hH=h2hA=spLine=spHO=spAO=None
            for bk in game.get("bookmakers",[]):
                for mk in bk.get("markets",[]):
                    if mk["key"]=="h2h":
                        ho=next((o for o in mk["outcomes"] if normalize_team(o["name"])==hEn),None)
                        ao=next((o for o in mk["outcomes"] if normalize_team(o["name"])==aEn),None)
                        if ho and ao: h2hH=ho["price"]; h2hA=ao["price"]
                    if mk["key"]=="spreads":
                        ho=next((o for o in mk["outcomes"] if normalize_team(o["name"])==hEn),None)
                        ao=next((o for o in mk["outcomes"] if normalize_team(o["name"])==aEn),None)
                        if ho and ao: spLine=ho["point"]; spHO=ho["price"]; spAO=ao["price"]
                break
            if not h2hH: continue

            bp = (1/h2hH)/((1/h2hH)+(1/h2hA))
            home_inj = injuries.get(hEn,[])
            away_inj = injuries.get(aEn,[])
            mp = calc_model_mlb(hEn, aEn, bp, home_inj, away_inj)
            # MLB 跑分差（最大約 ±2.5）
            ms = (mp - 0.5) * 5
            conf = max(round(mp*100), round((1-mp)*100))

            # 下注建議（MLB 讓分幾乎固定 ±1.5）
            if spLine is not None:
                diff = ms - spLine
                if abs(diff) < 0.15:
                    bet=hEn if mp>=0.5 else aEn
                    odds=h2hH if mp>=0.5 else h2hA; btype="不讓分"
                elif diff > 0:
                    bet=hEn; odds=spHO or 1.85
                    btype=f"讓分 {spLine}" if spLine<0 else f"吃分 +{spLine}"
                else:
                    bet=aEn; odds=spAO or 1.85
                    away_sp = -spLine
                    btype=f"讓分 {away_sp}" if away_sp<0 else f"吃分 +{away_sp}"
            else:
                bet=hEn if mp>=0.5 else aEn
                odds=h2hH if mp>=0.5 else h2hA; btype="不讓分"
            ev = (conf/100*odds-1)*100

            # DB optional
            if conn:
                exists = await conn.fetchrow(
                    "SELECT id,result FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3 AND sport='mlb'",
                    today, hEn, aEn)
                if not exists:
                    await conn.execute("""
                        INSERT INTO predictions(sport,game_date,home_team,away_team,predicted_winner,
                            confidence,bet_type,bet_odds,ev_pct,spread_line,model_spread)
                        VALUES('mlb',$1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    """, today,hEn,aEn,bet,conf,btype,odds,ev,spLine,ms)
                    saved+=1
                elif exists["result"] is None:
                    await conn.execute("""
                        UPDATE predictions SET predicted_winner=$1,confidence=$2,bet_type=$3,
                            bet_odds=$4,ev_pct=$5,spread_line=$6,model_spread=$7
                        WHERE id=$8
                    """, bet,conf,btype,odds,ev,spLine,ms,exists["id"])
                    saved+=1

        if conn: await conn.close()
        print(f"✅ MLB 儲存 {saved} 場")
        return {"status":"ok","saved":saved}
    except Exception as e:
        return {"status":"error","message":str(e)}

# ── 更新比賽結果
async def update_results():
    if not DB_URL: return
    try:
        tw_yesterday = (datetime.now(TW) - timedelta(days=1)).date()
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
                params={"dates": tw_yesterday.strftime("%Y%m%d")}
            )
            data = res.json()
        conn = await get_db()
        if not conn: return
        updated = 0
        for ev in data.get("events",[]):
            comp = ev["competitions"][0]
            if ev["status"]["type"]["state"] != "post": continue
            home = next((c for c in comp["competitors"] if c["homeAway"]=="home"),None)
            away = next((c for c in comp["competitors"] if c["homeAway"]=="away"),None)
            if not home or not away: continue
            hName = normalize_team(home["team"]["displayName"])
            aName = normalize_team(away["team"]["displayName"])
            hScore = int(home.get("score",0))
            aScore = int(away.get("score",0))
            winner = hName if hScore > aScore else aName
            row = await conn.fetchrow(
                "SELECT id,predicted_winner,bet_type,spread_line FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3 AND sport='mlb'",
                tw_yesterday, hName, aName)
            if not row: continue
            bet_type   = row["bet_type"] or ""
            spread_line= row["spread_line"]
            predicted  = row["predicted_winner"]
            if ("讓分" in bet_type or "吃分" in bet_type) and spread_line is not None:
                if "讓分" in bet_type:
                    result = (hScore + spread_line) > aScore
                else:
                    result = (aScore - spread_line) > hScore
            else:
                result = predicted == winner
            await conn.execute(
                "UPDATE predictions SET actual_winner=$1,actual_home_score=$2,actual_away_score=$3,result=$4 WHERE id=$5",
                winner, hScore, aScore, result, row["id"])
            updated += 1
        await conn.close()
        print(f"✅ MLB 更新 {updated} 場結果")
    except Exception as e:
        print(f"❌ update_results: {e}")

# ── API 路由
@app.get("/")
async def root():
    return {"status":"ok","message":"MLB 預測系統後端運作中","version":"v1.0-mlb"}

@app.get("/api/injuries")
async def get_injuries(): return await fetch_espn_injuries()

@app.get("/api/b2b")
async def get_b2b():
    # MLB 不適用，回傳空物件保持前端相容
    return {"status":"ok","b2b":{}}

@app.get("/api/mlb-stats")
async def get_mlb_stats(): return await fetch_mlb_stats()

@app.get("/api/team-data")
async def get_team_data():
    result = {}
    for name, d in TEAM_DATA.items():
        abbr = d.get("abbr","")
        if not abbr: continue
        result[abbr] = {
            "elo": d.get("elo",1500),
            "rs":  d.get("rs",4.3),
            "ra":  d.get("ra",4.3),
            "recent_adj": d.get("recent_adj",0),
        }
    return {"status":"ok","data":result}

@app.get("/api/polymarket")
async def get_polymarket(): return await fetch_polymarket_odds()

@app.get("/api/tw-odds")
async def get_tw_odds(date_str:str=None): return await fetch_tw_odds(date_str)

@app.get("/api/predictions/history")
async def get_history(days:int=90):
    if not DB_URL: return []
    conn = await get_db()
    try:
        rows = await conn.fetch("""
            SELECT * FROM predictions
            WHERE sport='mlb' AND result IS NOT NULL
            AND game_date >= CURRENT_DATE - ($1 * INTERVAL '1 day')
            ORDER BY game_date DESC, confidence DESC
        """, days)
        await conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        await conn.close(); return []

@app.get("/api/stats")
async def get_stats():
    empty = {"today":{"rate":0,"wins":0,"total":0},"week":{"rate":0,"wins":0,"total":0},
             "month":{"rate":0,"wins":0,"total":0},"high_conf":{"rate":0,"wins":0,"total":0}}
    if not DB_URL: return empty
    conn = await get_db()
    def wr(r):
        if not r or not r["total"]: return {"rate":0,"wins":0,"total":0}
        return {"rate":round((r["wins"] or 0)/r["total"]*100),"wins":int(r["wins"] or 0),"total":r["total"]}
    try:
        td=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE sport='mlb' AND game_date=CURRENT_DATE AND result IS NOT NULL")
        wk=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE sport='mlb' AND game_date>=CURRENT_DATE-interval '7 days' AND result IS NOT NULL")
        mn=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE sport='mlb' AND game_date>=CURRENT_DATE-interval '30 days' AND result IS NOT NULL")
        hc=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE sport='mlb' AND confidence>=70 AND result IS NOT NULL")
        await conn.close()
        return {"today":wr(td),"week":wr(wk),"month":wr(mn),"high_conf":wr(hc)}
    except:
        await conn.close(); return empty

@app.post("/api/trigger/predict")
async def trigger_predict(): return await fetch_and_predict() or {"status":"ok"}

@app.post("/api/trigger/results")
async def trigger_results(): await update_results(); return {"status":"ok"}

@app.post("/api/trigger/mlb-stats")
async def trigger_mlb_stats(): return await fetch_mlb_stats()

# ── 排程
scheduler = AsyncIOScheduler(timezone=TW)

@app.on_event("startup")
async def startup():
    await init_db()
    # MLB 排程
    scheduler.add_job(fetch_and_predict,  "cron", hour=5,  minute=0)   # 05:00 開賽前抓盤
    scheduler.add_job(fetch_and_predict,  "cron", hour=14, minute=0)   # 14:00 補抓稍晚場次
    scheduler.add_job(update_results,     "cron", hour=4,  minute=0)   # 04:00 更新前日結果
    scheduler.add_job(fetch_mlb_stats,    "cron", minute=0)            # 每小時整點
    scheduler.add_job(fetch_espn_injuries,"cron", minute=15)           # 每小時15分
    scheduler.start()
    # 啟動立即執行
    await fetch_mlb_stats()
    print("✅ MLB 後端啟動完成")
