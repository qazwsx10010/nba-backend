from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
import httpx
import os
from datetime import datetime, date, timedelta
import pytz

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])

TW = pytz.timezone("Asia/Taipei")
DB_URL = os.environ.get("DATABASE_URL","")
ODDS_KEY = os.environ.get("ODDS_API_KEY","")
JBOT_TOKEN = os.environ.get("JBOT_TOKEN","DEV_ONLY_FOR_FREE_TOKEN")

# ══════════════════════════════════════════════════════
# NBA 球隊資料
# ══════════════════════════════════════════════════════
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

TEAM_NAME_NORMALIZE = {
    "LA Clippers": "Los Angeles Clippers",
    "LA Lakers": "Los Angeles Lakers",
    "GS Warriors": "Golden State Warriors",
    "SA Spurs": "San Antonio Spurs",
    "OKC Thunder": "Oklahoma City Thunder",
    "NO Pelicans": "New Orleans Pelicans",
    "NY Knicks": "New York Knicks",
    "NJ Nets": "Brooklyn Nets",
}

def normalize_team(name):
    return TEAM_NAME_NORMALIZE.get(name, name)

TW_TEAM_MAP = {
    "亞特蘭大老鷹":"Atlanta Hawks","波士頓塞爾提克":"Boston Celtics",
    "布魯克林籃網":"Brooklyn Nets","夏洛特黃蜂":"Charlotte Hornets",
    "芝加哥公牛":"Chicago Bulls","克里夫蘭騎士":"Cleveland Cavaliers",
    "達拉斯獨行俠":"Dallas Mavericks","丹佛金塊":"Denver Nuggets",
    "底特律活塞":"Detroit Pistons","金州勇士":"Golden State Warriors",
    "休士頓火箭":"Houston Rockets","印第安納溜馬":"Indiana Pacers",
    "洛杉磯快艇":"Los Angeles Clippers","洛杉磯湖人":"Los Angeles Lakers",
    "曼菲斯灰熊":"Memphis Grizzlies","邁阿密熱火":"Miami Heat",
    "密爾瓦基公鹿":"Milwaukee Bucks","明尼蘇達灰狼":"Minnesota Timberwolves",
    "紐奧良鵜鶘":"New Orleans Pelicans","紐約尼克":"New York Knicks",
    "奧克拉荷馬雷霆":"Oklahoma City Thunder","奧蘭多魔術":"Orlando Magic",
    "費城76人":"Philadelphia 76ers","鳳凰城太陽":"Phoenix Suns",
    "波特蘭拓荒者":"Portland Trail Blazers","沙加緬度國王":"Sacramento Kings",
    "聖安東尼奧馬刺":"San Antonio Spurs","多倫多暴龍":"Toronto Raptors",
    "猶他爵士":"Utah Jazz","華盛頓巫師":"Washington Wizards",
}

ESPN_TEAM_IDS = {
    "Atlanta Hawks":"1","Boston Celtics":"2","Brooklyn Nets":"17",
    "Charlotte Hornets":"30","Chicago Bulls":"4","Cleveland Cavaliers":"5",
    "Dallas Mavericks":"6","Denver Nuggets":"7","Detroit Pistons":"8",
    "Golden State Warriors":"9","Houston Rockets":"10","Indiana Pacers":"11",
    "Los Angeles Clippers":"12","Los Angeles Lakers":"13","Memphis Grizzlies":"29",
    "Miami Heat":"14","Milwaukee Bucks":"15","Minnesota Timberwolves":"16",
    "New Orleans Pelicans":"3","New York Knicks":"18","Oklahoma City Thunder":"25",
    "Orlando Magic":"19","Philadelphia 76ers":"20","Phoenix Suns":"21",
    "Portland Trail Blazers":"22","Sacramento Kings":"23","San Antonio Spurs":"24",
    "Toronto Raptors":"28","Utah Jazz":"26","Washington Wizards":"27",
}

def inj_penalty(injuries_list):
    return sum(4 if i.get("status_type")=="Out" else 2 if i.get("status_type")=="Doubtful" else 1 for i in injuries_list)

def calc_model(home_en, away_en, bp, home_inj=None, away_inj=None, home_b2b=False, away_b2b=False):
    h=TEAM_DATA.get(home_en,{"elo":1400,"pts":110,"opp":110})
    a=TEAM_DATA.get(away_en,{"elo":1400,"pts":110,"opp":110})
    elo_p=1/(1+10**(-(h["elo"]-a["elo"]+70)/400))
    off_p=0.5+((h["pts"]-a["opp"])-(a["pts"]-h["opp"]))*0.012
    hi=inj_penalty(home_inj or [])
    ai=inj_penalty(away_inj or [])
    inj_adj=(ai-hi)*0.02
    b2b_adj=(-0.05 if home_b2b else 0)+(0.05 if away_b2b else 0)
    model=elo_p*0.35+off_p*0.25+bp*0.3+0.5*0.1+inj_adj+b2b_adj
    return max(0.05,min(0.95,model))

# ══════════════════════════════════════════════════════
# MLB 球隊資料
# ══════════════════════════════════════════════════════
MLB_TEAM_DATA = {
    "Los Angeles Dodgers":  {"elo":1820,"era":3.20,"fip":3.35,"woba":0.340,"home_adj":0.06,"abbr":"LAD"},
    "New York Yankees":     {"elo":1780,"era":3.55,"fip":3.68,"woba":0.330,"home_adj":0.05,"abbr":"NYY"},
    "Houston Astros":       {"elo":1740,"era":3.42,"fip":3.55,"woba":0.325,"home_adj":0.05,"abbr":"HOU"},
    "Atlanta Braves":       {"elo":1720,"era":3.60,"fip":3.72,"woba":0.322,"home_adj":0.05,"abbr":"ATL"},
    "Philadelphia Phillies":{"elo":1700,"era":3.68,"fip":3.80,"woba":0.318,"home_adj":0.05,"abbr":"PHI"},
    "Baltimore Orioles":    {"elo":1690,"era":3.75,"fip":3.88,"woba":0.316,"home_adj":0.04,"abbr":"BAL"},
    "New York Mets":        {"elo":1680,"era":3.80,"fip":3.92,"woba":0.315,"home_adj":0.04,"abbr":"NYM"},
    "Milwaukee Brewers":    {"elo":1660,"era":3.72,"fip":3.85,"woba":0.312,"home_adj":0.04,"abbr":"MIL"},
    "Minnesota Twins":      {"elo":1640,"era":3.90,"fip":4.02,"woba":0.310,"home_adj":0.04,"abbr":"MIN"},
    "Seattle Mariners":     {"elo":1630,"era":3.85,"fip":3.98,"woba":0.308,"home_adj":0.04,"abbr":"SEA"},
    "San Diego Padres":     {"elo":1620,"era":3.88,"fip":4.00,"woba":0.306,"home_adj":0.04,"abbr":"SD"},
    "Boston Red Sox":       {"elo":1610,"era":4.05,"fip":4.18,"woba":0.305,"home_adj":0.04,"abbr":"BOS"},
    "Toronto Blue Jays":    {"elo":1600,"era":4.10,"fip":4.22,"woba":0.304,"home_adj":0.04,"abbr":"TOR"},
    "San Francisco Giants": {"elo":1590,"era":4.02,"fip":4.15,"woba":0.302,"home_adj":0.03,"abbr":"SF"},
    "St. Louis Cardinals":  {"elo":1580,"era":4.08,"fip":4.20,"woba":0.300,"home_adj":0.03,"abbr":"STL"},
    "Texas Rangers":        {"elo":1570,"era":4.15,"fip":4.28,"woba":0.298,"home_adj":0.03,"abbr":"TEX"},
    "Cleveland Guardians":  {"elo":1560,"era":4.12,"fip":4.25,"woba":0.296,"home_adj":0.03,"abbr":"CLE"},
    "Tampa Bay Rays":       {"elo":1550,"era":4.05,"fip":4.18,"woba":0.295,"home_adj":0.03,"abbr":"TB"},
    "Arizona Diamondbacks": {"elo":1540,"era":4.20,"fip":4.32,"woba":0.293,"home_adj":0.03,"abbr":"ARI"},
    "Detroit Tigers":       {"elo":1520,"era":4.25,"fip":4.38,"woba":0.290,"home_adj":0.03,"abbr":"DET"},
    "Chicago Cubs":         {"elo":1510,"era":4.30,"fip":4.42,"woba":0.288,"home_adj":0.03,"abbr":"CHC"},
    "Kansas City Royals":   {"elo":1490,"era":4.35,"fip":4.48,"woba":0.286,"home_adj":0.03,"abbr":"KC"},
    "Los Angeles Angels":   {"elo":1470,"era":4.40,"fip":4.52,"woba":0.284,"home_adj":0.03,"abbr":"LAA"},
    "Cincinnati Reds":      {"elo":1460,"era":4.45,"fip":4.58,"woba":0.282,"home_adj":0.03,"abbr":"CIN"},
    "Pittsburgh Pirates":   {"elo":1440,"era":4.50,"fip":4.62,"woba":0.280,"home_adj":0.02,"abbr":"PIT"},
    "Miami Marlins":        {"elo":1420,"era":4.55,"fip":4.68,"woba":0.278,"home_adj":0.02,"abbr":"MIA"},
    "Athletics":            {"elo":1400,"era":4.60,"fip":4.72,"woba":0.276,"home_adj":0.02,"abbr":"OAK"},
    "Colorado Rockies":     {"elo":1380,"era":4.90,"fip":5.02,"woba":0.274,"home_adj":0.08,"abbr":"COL"},
    "Chicago White Sox":    {"elo":1320,"era":5.10,"fip":5.22,"woba":0.268,"home_adj":0.02,"abbr":"CWS"},
    "Washington Nationals": {"elo":1350,"era":4.80,"fip":4.92,"woba":0.272,"home_adj":0.02,"abbr":"WSH"},
}

MLB_TEAM_NORMALIZE = {
    "NY Yankees":"New York Yankees","NY Mets":"New York Mets",
    "LA Dodgers":"Los Angeles Dodgers","LA Angels":"Los Angeles Angels",
    "Chi Cubs":"Chicago Cubs","Chi White Sox":"Chicago White Sox",
    "KC Royals":"Kansas City Royals","SD Padres":"San Diego Padres",
    "SF Giants":"San Francisco Giants","TB Rays":"Tampa Bay Rays",
    "Oakland Athletics":"Athletics",
}

def normalize_mlb_team(name):
    return MLB_TEAM_NORMALIZE.get(name, name)

def calc_mlb_model(home_en, away_en, bp, home_starter=None, away_starter=None):
    h = MLB_TEAM_DATA.get(home_en, {"elo":1500,"era":4.5,"fip":4.6,"woba":0.300,"home_adj":0.04})
    a = MLB_TEAM_DATA.get(away_en, {"elo":1500,"era":4.5,"fip":4.6,"woba":0.300,"home_adj":0.04})
    elo_p = 1 / (1 + 10 ** (-(h["elo"] - a["elo"]) / 400))
    h_fip = home_starter.get("fip", h["fip"]) if home_starter else h["fip"]
    a_fip = away_starter.get("fip", a["fip"]) if away_starter else a["fip"]
    pitch_adj = (a_fip - h_fip) * 0.04
    off_adj = (h["woba"] - a["woba"]) * 1.2
    home_adj = h.get("home_adj", 0.04)
    if bp:
        model = elo_p * 0.25 + bp * 0.45 + pitch_adj + off_adj + home_adj
    else:
        model = elo_p * 0.40 + pitch_adj + off_adj + home_adj
    return max(0.05, min(0.95, model))

# ══════════════════════════════════════════════════════
# 資料庫
# ══════════════════════════════════════════════════════
async def get_db():
    url=DB_URL
    if url.startswith("postgres://"): url=url.replace("postgres://","postgresql://",1)
    return await asyncpg.connect(url)

async def init_db():
    if not DB_URL: return
    conn=await get_db()
    # NBA table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
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
            home_b2b BOOLEAN DEFAULT FALSE,
            away_b2b BOOLEAN DEFAULT FALSE,
            actual_winner TEXT,
            actual_home_score INTEGER,
            actual_away_score INTEGER,
            result BOOLEAN,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    for col in ["home_b2b BOOLEAN DEFAULT FALSE","away_b2b BOOLEAN DEFAULT FALSE"]:
        try: await conn.execute(f"ALTER TABLE predictions ADD COLUMN IF NOT EXISTS {col}")
        except: pass
    # MLB table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS mlb_predictions (
            id SERIAL PRIMARY KEY,
            game_date DATE NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            predicted_winner TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            bet_type TEXT,
            bet_odds FLOAT,
            ev_pct FLOAT,
            run_line FLOAT,
            home_starter TEXT,
            away_starter TEXT,
            home_starter_fip FLOAT,
            away_starter_fip FLOAT,
            actual_winner TEXT,
            actual_home_score INTEGER,
            actual_away_score INTEGER,
            result BOOLEAN,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.close()
    print("✅ NBA + MLB DB 初始化完成")

# ══════════════════════════════════════════════════════
# NBA 功能（原版完整保留）
# ══════════════════════════════════════════════════════
async def fetch_espn_injuries():
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res=await client.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries")
            data=res.json()
        injuries={}
        for team_data in data.get("injuries",[]):
            team_name=team_data.get("team",{}).get("displayName","")
            if not team_name: continue
            players=[]
            for item in team_data.get("injuries",[]):
                athlete=item.get("athlete",{})
                status_type=item.get("type",{}).get("description","")
                players.append({
                    "player": athlete.get("displayName",""),
                    "position": athlete.get("position",{}).get("abbreviation",""),
                    "status": item.get("status",""),
                    "status_type": status_type,
                    "detail": item.get("shortComment",""),
                })
            injuries[team_name]=players
        return {"status":"ok","injuries":injuries,"updated":datetime.now(TW).strftime("%Y-%m-%d %H:%M")}
    except Exception as e:
        return {"status":"error","message":str(e),"injuries":{}}

async def fetch_b2b_status():
    try:
        yesterday=(date.today()-timedelta(days=1)).strftime("%Y%m%d")
        today=date.today().strftime("%Y%m%d")
        async with httpx.AsyncClient(timeout=15) as client:
            res_y=await client.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}")
            res_t=await client.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={today}")
        yd=res_y.json(); td=res_t.json()
        played_yesterday=set()
        for ev in yd.get("events",[]):
            for comp in ev.get("competitions",[]):
                for team in comp.get("competitors",[]):
                    played_yesterday.add(team["team"]["displayName"])
        playing_today={}
        for ev in td.get("events",[]):
            for comp in ev.get("competitions",[]):
                for team in comp.get("competitors",[]):
                    tn=team["team"]["displayName"]
                    playing_today[tn]=tn in played_yesterday
        return {"status":"ok","b2b":playing_today}
    except Exception as e:
        return {"status":"error","message":str(e),"b2b":{}}

async def fetch_nba_stats():
    try:
        updated = 0
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings",
                params={"season": "2026"}
            )
            data = res.json()
        stats = {}
        children = data.get("children", [])
        for conf in children:
            for entry in conf.get("standings", {}).get("entries", []):
                team_name = entry.get("team", {}).get("displayName", "")
                if team_name == "LA Clippers": team_name = "Los Angeles Clippers"
                wins = losses = 0
                pts = opp = None
                recent_adj_raw = 0
                recent_str = ""
                for stat in entry.get("stats", []):
                    n = stat.get("name",""); v = stat.get("value", 0); sdv = stat.get("displayValue","")
                    if n == "wins":
                        try: wins = int(v)
                        except: pass
                    if n == "losses":
                        try: losses = int(v)
                        except: pass
                    if n == "avgPointsFor":
                        try:
                            val = round(float(v), 1)
                            if val > 80: pts = val
                        except: pass
                    if n == "avgPointsAgainst":
                        try:
                            val = round(float(v), 1)
                            if val > 80: opp = val
                        except: pass
                    if n == "Last Ten Games":
                        recent_str = sdv
                        try:
                            if "-" in str(sdv):
                                p = sdv.split("-"); rw, rl = int(p[0]), int(p[1])
                            else:
                                rw = int(float(v)); rl = 10 - rw
                            if rw + rl > 0: recent_adj_raw = round((rw/(rw+rl) - 0.5) * 100)
                        except: recent_adj_raw = 0
                if team_name in TEAM_DATA and wins + losses > 0:
                    games = wins + losses
                    win_pct = wins / games
                    new_elo = round(1500 + (win_pct - 0.5) * 800) + recent_adj_raw
                    TEAM_DATA[team_name]["recent_adj"] = recent_adj_raw
                    TEAM_DATA[team_name]["elo"] = new_elo
                    if pts and pts > 80: TEAM_DATA[team_name]["pts"] = pts
                    if opp and opp > 80: TEAM_DATA[team_name]["opp"] = opp
                    home_w=home_l=away_w=away_l=0
                    for stat in entry.get("stats", []):
                        n=stat.get("name","")
                        if n == "Home":
                            try:
                                parts = str(stat.get("displayValue","")).split("-")
                                if len(parts)==2: home_w,home_l=int(parts[0]),int(parts[1])
                            except: pass
                        if n == "Road":
                            try:
                                parts = str(stat.get("displayValue","")).split("-")
                                if len(parts)==2: away_w,away_l=int(parts[0]),int(parts[1])
                            except: pass
                    home_win_pct=round(home_w/(home_w+home_l)*100,1) if home_w+home_l>0 else None
                    away_win_pct=round(away_w/(away_w+away_l)*100,1) if away_w+away_l>0 else None
                    stats[team_name] = {
                        "wins": wins, "losses": losses, "win_pct": round(win_pct*100, 1), "elo": new_elo,
                        "pts": TEAM_DATA[team_name]["pts"], "opp": TEAM_DATA[team_name]["opp"],
                        "home_win_pct": home_win_pct, "away_win_pct": away_win_pct,
                        "recent_adj": recent_adj_raw, "recent": recent_str
                    }
                    updated += 1
                    recent_adj_raw = 0
        print(f"✅ ESPN Stats 更新 {updated} 支球隊")
        return {"status": "ok", "updated": updated, "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def fetch_polymarket_odds():
    try:
        import json as _json
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://gamma-api.polymarket.com/events",
                params={"active":"true","closed":"false","limit":"50","tag_slug":"basketball","order":"volume24hr","ascending":"false"},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = res.json()
        events = data if isinstance(data, list) else data.get("events", [])
        result = {}
        nba_teams = {
            "Hawks","Celtics","Nets","Hornets","Bulls","Cavaliers","Mavericks","Nuggets",
            "Pistons","Warriors","Rockets","Pacers","Clippers","Lakers","Grizzlies","Heat",
            "Bucks","Timberwolves","Pelicans","Knicks","Thunder","Magic","76ers","Suns",
            "Trail Blazers","Kings","Spurs","Raptors","Jazz","Wizards"
        }
        non_nba_keywords = ["Oilers","Flames","Leafs","Canucks","Jets","Senators","IPL","Premier League","Champions League","Arsenal","Chelsea"]
        for event in events:
            event_volume = float(event.get("volume24hr", 0) or event.get("volume", 0) or 0)
            event_title = event.get("title", "")
            if any(kw in event_title for kw in non_nba_keywords): continue
            found_teams = [t for t in nba_teams if t in event_title]
            if len(found_teams) < 2: continue
            home_team, away_team = found_teams[0], found_teams[1]
            for m in event.get("markets", []):
                question = m.get("question", "")
                if "vs." not in question or any(x in question.lower() for x in ["spread","total","points","quarter","half","draw"]): continue
                outcomes_raw = m.get("outcomes", "[]"); prices_raw = m.get("outcomePrices", "[]")
                if isinstance(outcomes_raw, str):
                    try: outcomes = _json.loads(outcomes_raw)
                    except: continue
                else: outcomes = outcomes_raw
                if isinstance(prices_raw, str):
                    try: prices = _json.loads(prices_raw)
                    except: continue
                else: prices = prices_raw
                if len(outcomes) != 2 or len(prices) != 2: continue
                t1, t2 = str(outcomes[0]).strip(), str(outcomes[1]).strip()
                if t1 not in nba_teams or t2 not in nba_teams: continue
                try: p1, p2 = float(prices[0]), float(prices[1])
                except: continue
                if not (0 < p1 < 1 and 0 < p2 < 1): continue
                vol = event_volume
                result[t1] = {"prob": round(p1*100,1), "volume": round(vol), "reliable": vol>=5000}
                result[t2] = {"prob": round(p2*100,1), "volume": round(vol), "reliable": vol>=5000}
                break
        return {"status":"ok","odds":result,"markets":len(result)//2}
    except Exception as e:
        return {"status":"error","message":str(e),"odds":{}}

async def fetch_tw_odds(target_date=None):
    if not target_date: target_date=date.today().strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res=await client.get("https://api.sportsbot.tech/v2/odds",
                params={"sport":"NBA","date":target_date,"mode":"close"},
                headers={"X-JBot-Token":JBOT_TOKEN})
            data=res.json()
        if data.get("status")!="OK": return {"status":"error","message":str(data)}
        games=[]
        for item in data.get("data",[]):
            away_en=TW_TEAM_MAP.get(item.get("away",""),item.get("away",""))
            home_en=TW_TEAM_MAP.get(item.get("home",""),item.get("home",""))
            odds_list=item.get("odds",[])
            if not odds_list: continue
            latest=odds_list[-1]
            normal=latest.get("normal",{}); handi=latest.get("handi",{}); total_data=latest.get("total",{})
            main_spread=main_h=main_a=None
            for sv,sd in handi.items():
                if sd.get("m"): main_spread=float(sv);main_h=sd.get("h");main_a=sd.get("a");break
            main_total=main_over=main_under=None
            for tv,ti in total_data.items():
                if ti.get("m"): main_total=float(tv);main_over=ti.get("o");main_under=ti.get("u");break
            games.append({"home_tw":item.get("home",""),"away_tw":item.get("away",""),"home_en":home_en,"away_en":away_en,
                "time":item.get("time",""),"normal_home":normal.get("h"),"normal_away":normal.get("a"),
                "spread":main_spread,"spread_home_odds":main_h,"spread_away_odds":main_a,
                "total":main_total,"over_odds":main_over,"under_odds":main_under})
        return {"status":"ok","date":target_date,"games":games,"quota":data.get("user",{})}
    except Exception as e:
        return {"status":"error","message":str(e)}

async def fetch_and_predict():
    if not ODDS_KEY or not DB_URL: return {"status":"error","message":"缺少設定"}
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] 抓取今日 NBA 賽程...")
    try:
        inj_data=await fetch_espn_injuries(); b2b_data=await fetch_b2b_status()
        injuries=inj_data.get("injuries",{}); b2b=b2b_data.get("b2b",{})
        async with httpx.AsyncClient(timeout=30) as client:
            res=await client.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
                params={"apiKey":ODDS_KEY,"regions":"us","markets":"h2h,spreads","oddsFormat":"decimal","dateFormat":"iso"})
            data=res.json()
        conn=await get_db(); today=date.today(); saved=0
        for game in data:
            hEn=normalize_team(game["home_team"]); aEn=normalize_team(game["away_team"])
            h2hH=h2hA=spLine=spHO=spAO=None
            for bk in game.get("bookmakers",[]):
                for mk in bk.get("markets",[]):
                    if mk["key"]=="h2h":
                        ho=next((o for o in mk["outcomes"] if o["name"]==hEn),None)
                        ao=next((o for o in mk["outcomes"] if o["name"]==aEn),None)
                        if ho and ao: h2hH=ho["price"]; h2hA=ao["price"]
                    if mk["key"]=="spreads":
                        ho=next((o for o in mk["outcomes"] if o["name"]==hEn),None)
                        ao=next((o for o in mk["outcomes"] if o["name"]==aEn),None)
                        if ho and ao: spLine=ho["point"]; spHO=ho["price"]; spAO=ao["price"]
                break
            if not h2hH: continue
            bp=(1/h2hH)/((1/h2hH)+(1/h2hA))
            mp=calc_model(hEn,aEn,bp,injuries.get(hEn,[]),injuries.get(aEn,[]),b2b.get(hEn,False),b2b.get(aEn,False))
            ms=(mp-0.5)*28; conf=max(round(mp*100),round((1-mp)*100))
            if spLine is not None:
                diff=ms-spLine
                if abs(diff)<0.5: bet=hEn if mp>=0.5 else aEn; odds=h2hH if mp>=0.5 else h2hA; btype="不讓分"
                elif diff>0: bet=hEn; odds=spHO or 1.72; btype=f"讓分 {spLine}" if spLine<0 else f"吃分 +{spLine}"
                else: bet=aEn; odds=spAO or 1.72; away_spread=-spLine; btype=f"讓分 {away_spread}" if away_spread<0 else f"吃分 +{away_spread}"
            else: bet=hEn if mp>=0.5 else aEn; odds=h2hH if mp>=0.5 else h2hA; btype="不讓分"
            ev=(conf/100*odds-1)*100
            exists=await conn.fetchrow("SELECT id,result FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",today,hEn,aEn)
            if not exists:
                await conn.execute("INSERT INTO predictions(game_date,home_team,away_team,predicted_winner,confidence,bet_type,bet_odds,ev_pct,spread_line,model_spread,home_b2b,away_b2b) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)",
                    today,hEn,aEn,bet,conf,btype,odds,ev,spLine,ms,b2b.get(hEn,False),b2b.get(aEn,False)); saved+=1
            elif exists["result"] is None:
                await conn.execute("UPDATE predictions SET predicted_winner=$1,confidence=$2,bet_type=$3,bet_odds=$4,ev_pct=$5,spread_line=$6,model_spread=$7,home_b2b=$8,away_b2b=$9 WHERE id=$10",
                    bet,conf,btype,odds,ev,spLine,ms,b2b.get(hEn,False),b2b.get(aEn,False),exists["id"]); saved+=1
        await conn.close(); print(f"✅ NBA 儲存 {saved} 場")
        return {"status":"ok","saved":saved}
    except Exception as e:
        return {"status":"error","message":str(e)}

async def update_results():
    if not DB_URL: return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res=await client.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")
            data=res.json()
        conn=await get_db(); yesterday=date.today()-timedelta(days=1); updated=0
        for ev in data.get("events",[]):
            comp=ev["competitions"][0]
            if ev["status"]["type"]["state"]!="post": continue
            home=next((c for c in comp["competitors"] if c["homeAway"]=="home"),None)
            away=next((c for c in comp["competitors"] if c["homeAway"]=="away"),None)
            if not home or not away: continue
            hName=home["team"]["displayName"]; aName=away["team"]["displayName"]
            hScore=int(home.get("score",0)); aScore=int(away.get("score",0))
            winner=hName if hScore>aScore else aName
            row=await conn.fetchrow("SELECT id,predicted_winner,bet_type,spread_line FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",yesterday,hName,aName)
            if row:
                bet_type=row["bet_type"] or ""; spread_line=row["spread_line"]; predicted=row["predicted_winner"]
                if "讓分" in bet_type and spread_line is not None: result=(hScore+spread_line)>aScore
                elif "吃分" in bet_type and spread_line is not None: result=(aScore-spread_line)>hScore
                else: result=predicted==winner
                await conn.execute("UPDATE predictions SET actual_winner=$1,actual_home_score=$2,actual_away_score=$3,result=$4 WHERE id=$5",winner,hScore,aScore,result,row["id"]); updated+=1
        await conn.close(); print(f"✅ NBA 更新 {updated} 場結果")
        return {"status":"ok","updated":updated}
    except Exception as e:
        return {"status":"error","message":str(e)}

# ══════════════════════════════════════════════════════
# MLB 功能（新增）
# ══════════════════════════════════════════════════════
async def fetch_mlb_starters():
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard")
            data = res.json()
        starters = {}
        for ev in data.get("events", []):
            comp = ev["competitions"][0]
            for c in comp.get("competitors", []):
                team_name = normalize_mlb_team(c["team"]["displayName"])
                probable = c.get("probable", {})
                if probable:
                    athlete = probable.get("athlete", {})
                    starters[team_name] = {
                        "name": athlete.get("displayName", "TBD"),
                        "era": float(probable.get("era", 4.50) or 4.50),
                        "fip": float(probable.get("fip", 4.60) or 4.60),
                    }
        print(f"✅ MLB 先發投手 {len(starters)} 隊")
        return {"status": "ok", "starters": starters}
    except Exception as e:
        return {"status": "error", "starters": {}}

async def fetch_mlb_stats():
    try:
        updated = 0
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://site.api.espn.com/apis/v2/sports/baseball/mlb/standings",
                params={"season": str(date.today().year)}
            )
            data = res.json()
        children = data.get("children", [])
        for league in children:
            for division in league.get("children", []) or [league]:
                for entry in division.get("standings", {}).get("entries", []):
                    team_name = normalize_mlb_team(entry.get("team", {}).get("displayName", ""))
                    wins = losses = 0
                    recent_str = ""
                    for stat in entry.get("stats", []):
                        n = stat.get("name", ""); v = stat.get("value", 0); dv = stat.get("displayValue", "")
                        if n == "wins":
                            try: wins = int(v)
                            except: pass
                        if n == "losses":
                            try: losses = int(v)
                            except: pass
                        if n in ("Last Ten Games", "L10"): recent_str = dv
                    if team_name in MLB_TEAM_DATA and wins + losses > 0:
                        win_pct = wins / (wins + losses)
                        new_elo = round(1500 + (win_pct - 0.5) * 600)
                        recent_adj = 0
                        if recent_str and "-" in recent_str:
                            try:
                                rw, rl = int(recent_str.split("-")[0]), int(recent_str.split("-")[1])
                                recent_adj = round((rw / (rw + rl) - 0.5) * 60)
                            except: pass
                        new_elo += recent_adj
                        MLB_TEAM_DATA[team_name]["elo"] = new_elo
                        MLB_TEAM_DATA[team_name]["recent_adj"] = recent_adj
                        updated += 1
        print(f"✅ MLB Stats 更新 {updated} 隊")
        return {"status": "ok", "updated": updated}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def fetch_and_predict_mlb():
    if not ODDS_KEY or not DB_URL: return {"status":"error","message":"缺少設定"}
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] 抓取今日 MLB 賽程...")
    try:
        starter_data = await fetch_mlb_starters()
        starters = starter_data.get("starters", {})
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get("https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/",
                params={"apiKey":ODDS_KEY,"regions":"us","markets":"h2h,spreads","oddsFormat":"decimal","dateFormat":"iso"})
            data = res.json()
        conn = await get_db(); today = date.today(); saved = 0
        for game in data:
            h_en = normalize_mlb_team(game["home_team"])
            a_en = normalize_mlb_team(game["away_team"])
            h2h_h=h2h_a=run_line=rl_h_odds=rl_a_odds=None
            for bk in game.get("bookmakers", []):
                for mk in bk.get("markets", []):
                    if mk["key"] == "h2h":
                        ho=next((o for o in mk["outcomes"] if normalize_mlb_team(o["name"])==h_en),None)
                        ao=next((o for o in mk["outcomes"] if normalize_mlb_team(o["name"])==a_en),None)
                        if ho and ao: h2h_h=ho["price"]; h2h_a=ao["price"]
                    if mk["key"] == "spreads":
                        ho=next((o for o in mk["outcomes"] if normalize_mlb_team(o["name"])==h_en),None)
                        ao=next((o for o in mk["outcomes"] if normalize_mlb_team(o["name"])==a_en),None)
                        if ho and ao: run_line=ho["point"]; rl_h_odds=ho["price"]; rl_a_odds=ao["price"]
                break
            if not h2h_h: continue
            bp=(1/h2h_h)/((1/h2h_h)+(1/h2h_a))
            mp=calc_mlb_model(h_en,a_en,bp,starters.get(h_en),starters.get(a_en))
            conf=max(round(mp*100),round((1-mp)*100))
            if mp>=0.5: bet=h_en; ml_odds=h2h_h; ml_ev=(mp*ml_odds-1)*100
            else: bet=a_en; ml_odds=h2h_a; ml_ev=((1-mp)*ml_odds-1)*100
            bet_type="不讓分(ML)"; bet_odds=ml_odds; ev=ml_ev
            if run_line is not None:
                rl_prob=mp-0.08 if mp>=0.5 else (1-mp)-0.08
                rl_odds_pick=rl_h_odds if mp>=0.5 else rl_a_odds
                rl_ev=(rl_prob*(rl_odds_pick or 1.9)-1)*100
                if rl_ev>ml_ev+5 and conf>=65:
                    bet_type=f"讓分(RL {run_line})"; bet_odds=rl_odds_pick or 1.9; ev=rl_ev
            h_starter=starters.get(h_en,{}); a_starter=starters.get(a_en,{})
            exists=await conn.fetchrow("SELECT id,result FROM mlb_predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",today,h_en,a_en)
            if not exists:
                await conn.execute("INSERT INTO mlb_predictions(game_date,home_team,away_team,predicted_winner,confidence,bet_type,bet_odds,ev_pct,run_line,home_starter,away_starter,home_starter_fip,away_starter_fip) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)",
                    today,h_en,a_en,bet,conf,bet_type,bet_odds,ev,run_line,
                    h_starter.get("name",""),a_starter.get("name",""),h_starter.get("fip"),a_starter.get("fip")); saved+=1
            elif exists["result"] is None:
                await conn.execute("UPDATE mlb_predictions SET predicted_winner=$1,confidence=$2,bet_type=$3,bet_odds=$4,ev_pct=$5,run_line=$6,home_starter=$7,away_starter=$8 WHERE id=$9",
                    bet,conf,bet_type,bet_odds,ev,run_line,h_starter.get("name",""),a_starter.get("name",""),exists["id"]); saved+=1
        await conn.close(); print(f"✅ MLB 儲存 {saved} 場")
        return {"status":"ok","saved":saved}
    except Exception as e:
        return {"status":"error","message":str(e)}

async def update_mlb_results():
    if not DB_URL: return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res=await client.get("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard")
            data=res.json()
        conn=await get_db(); yesterday=date.today()-timedelta(days=1); updated=0
        for ev in data.get("events",[]):
            comp=ev["competitions"][0]
            if ev["status"]["type"]["state"]!="post": continue
            home=next((c for c in comp["competitors"] if c["homeAway"]=="home"),None)
            away=next((c for c in comp["competitors"] if c["homeAway"]=="away"),None)
            if not home or not away: continue
            h_name=normalize_mlb_team(home["team"]["displayName"])
            a_name=normalize_mlb_team(away["team"]["displayName"])
            h_score=int(home.get("score",0)); a_score=int(away.get("score",0))
            winner=h_name if h_score>a_score else a_name
            row=await conn.fetchrow("SELECT id,predicted_winner,bet_type,run_line FROM mlb_predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",yesterday,h_name,a_name)
            if row:
                bet_type=row["bet_type"] or ""; run_line=row["run_line"]; predicted=row["predicted_winner"]
                if "讓分(RL" in bet_type and run_line is not None:
                    result=(h_score+run_line)>a_score if predicted==h_name else (a_score-run_line)>h_score
                else:
                    result=(predicted==winner)
                await conn.execute("UPDATE mlb_predictions SET actual_winner=$1,actual_home_score=$2,actual_away_score=$3,result=$4 WHERE id=$5",winner,h_score,a_score,result,row["id"]); updated+=1
        await conn.close(); print(f"✅ MLB 更新 {updated} 場結果")
        return {"status":"ok","updated":updated}
    except Exception as e:
        return {"status":"error","message":str(e)}

# ══════════════════════════════════════════════════════
# API 路由 - NBA（原版）
# ══════════════════════════════════════════════════════
@app.get("/")
async def root(): return {"status":"ok","message":"NBA + MLB 預測系統後端","version":"v4.0"}

@app.get("/api/injuries")
async def get_injuries(): return await fetch_espn_injuries()

@app.get("/api/b2b")
async def get_b2b(): return await fetch_b2b_status()

@app.get("/api/team-data")
async def get_team_data():
    result = {}
    for name, d in TEAM_DATA.items():
        abbr = d.get("abbr","")
        if not abbr: continue
        result[abbr] = {"elo":d.get("elo",1400),"pts":d.get("pts",110),"opp":d.get("opp",110),"pace":d.get("pace",99),"recent_adj":d.get("recent_adj",0)}
    return {"status":"ok","data":result}

@app.get("/api/nba-stats")
async def get_nba_stats(): return await fetch_nba_stats()

@app.get("/api/polymarket")
async def get_polymarket(): return await fetch_polymarket_odds()

@app.get("/api/tw-odds")
async def get_tw_odds(date_str:str=None): return await fetch_tw_odds(date_str)

@app.get("/api/predictions/today")
async def get_today():
    if not DB_URL: return []
    conn=await get_db()
    rows=await conn.fetch("SELECT * FROM predictions WHERE game_date=$1 ORDER BY confidence DESC",date.today())
    await conn.close(); return [dict(r) for r in rows]

@app.get("/api/predictions/history")
async def get_history(days:int=90):
    if not DB_URL: return []
    conn=await get_db()
    try:
        rows=await conn.fetch("SELECT * FROM predictions WHERE result IS NOT NULL AND game_date>=CURRENT_DATE-($1*INTERVAL '1 day') ORDER BY game_date DESC,confidence DESC",days)
        await conn.close(); return [dict(r) for r in rows]
    except Exception as e:
        await conn.close(); return []

@app.get("/api/stats")
async def get_stats():
    if not DB_URL: return {"today":{"rate":0,"wins":0,"total":0},"week":{"rate":0,"wins":0,"total":0},"month":{"rate":0,"wins":0,"total":0},"high_conf":{"rate":0,"wins":0,"total":0}}
    conn=await get_db()
    def wr(r):
        if not r or not r["total"]: return {"rate":0,"wins":0,"total":0}
        return {"rate":round((r["wins"] or 0)/r["total"]*100),"wins":int(r["wins"] or 0),"total":r["total"]}
    td=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE game_date=CURRENT_DATE AND result IS NOT NULL")
    wk=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE game_date>=CURRENT_DATE-interval '7 days' AND result IS NOT NULL")
    mn=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE game_date>=CURRENT_DATE-interval '30 days' AND result IS NOT NULL")
    hc=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE confidence>=70 AND result IS NOT NULL")
    await conn.close()
    return {"today":wr(td),"week":wr(wk),"month":wr(mn),"high_conf":wr(hc)}

@app.post("/api/trigger/predict")
async def trigger_predict(): return await fetch_and_predict() or {"status":"ok"}

@app.post("/api/trigger/results")
async def trigger_results(): return await update_results() or {"status":"ok"}

@app.post("/api/trigger/nba-stats")
async def trigger_nba_stats_post(): return await fetch_nba_stats()

# ══════════════════════════════════════════════════════
# API 路由 - MLB（新增，全部以 /api/mlb/ 開頭）
# ══════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════
# Polymarket MLB 勝率（解決 CORS，從後端抓）
# ══════════════════════════════════════════════════════
async def fetch_polymarket_mlb_odds():
    """從後端抓 Polymarket MLB 今日單場勝負賭盤"""
    try:
        import json as _json
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://gamma-api.polymarket.com/events",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": "80",
                    "tag_slug": "baseball",
                    "order": "volume",
                    "ascending": "false",
                },
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = res.json()

        events = data if isinstance(data, list) else data.get("events", [])
        result = {}

        mlb_teams = {
            "Astros","Mariners","Dodgers","Yankees","Braves","Phillies","Mets","Padres",
            "Orioles","Brewers","Twins","Giants","Cardinals","Rangers","Guardians","Rays",
            "Diamondbacks","Tigers","Cubs","Royals","Angels","Reds","Pirates","Marlins",
            "Athletics","Rockies","White Sox","Nationals","Red Sox","Blue Jays"
        }

        for event in events:
            event_title = event.get("title", "")
            found_teams = [t for t in mlb_teams if t in event_title]
            if len(found_teams) < 2:
                continue

            for m in event.get("markets", []):
                question = m.get("question", "")
                if "vs." not in question and " vs " not in question:
                    continue
                if any(x in question.lower() for x in ["spread","total","runs","innings","strikeout","home run"]):
                    continue

                outcomes_raw = m.get("outcomes", "[]")
                prices_raw = m.get("outcomePrices", "[]")

                if isinstance(outcomes_raw, str):
                    try: outcomes = _json.loads(outcomes_raw)
                    except: continue
                else: outcomes = outcomes_raw

                if isinstance(prices_raw, str):
                    try: prices = _json.loads(prices_raw)
                    except: continue
                else: prices = prices_raw

                if len(outcomes) != 2 or len(prices) != 2:
                    continue

                t1, t2 = str(outcomes[0]).strip(), str(outcomes[1]).strip()
                t1_mlb = any(team in t1 for team in mlb_teams)
                t2_mlb = any(team in t2 for team in mlb_teams)
                if not t1_mlb or not t2_mlb:
                    continue

                try:
                    p1, p2 = float(prices[0]), float(prices[1])
                except: continue
                if not (0 < p1 < 1 and 0 < p2 < 1): continue

                # 交易量：優先用 market 層級，再用 event 層級
                m_vol = float(m.get("volume", 0) or m.get("volumeNum", 0) or 0)
                e_vol = float(event.get("volume", 0) or event.get("volume24hr", 0) or 0)
                vol = max(m_vol, e_vol)
                # 找對應完整隊名
                MLB_FULL = {
                    "Astros":"Houston Astros","Mariners":"Seattle Mariners",
                    "Dodgers":"Los Angeles Dodgers","Yankees":"New York Yankees",
                    "Braves":"Atlanta Braves","Phillies":"Philadelphia Phillies",
                    "Mets":"New York Mets","Padres":"San Diego Padres",
                    "Orioles":"Baltimore Orioles","Brewers":"Milwaukee Brewers",
                    "Twins":"Minnesota Twins","Giants":"San Francisco Giants",
                    "Cardinals":"St. Louis Cardinals","Rangers":"Texas Rangers",
                    "Guardians":"Cleveland Guardians","Rays":"Tampa Bay Rays",
                    "Diamondbacks":"Arizona Diamondbacks","Tigers":"Detroit Tigers",
                    "Cubs":"Chicago Cubs","Royals":"Kansas City Royals",
                    "Angels":"Los Angeles Angels","Reds":"Cincinnati Reds",
                    "Pirates":"Pittsburgh Pirates","Marlins":"Miami Marlins",
                    "Athletics":"Athletics","Rockies":"Colorado Rockies",
                    "White Sox":"Chicago White Sox","Nationals":"Washington Nationals",
                    "Red Sox":"Boston Red Sox","Blue Jays":"Toronto Blue Jays",
                }
                full1 = next((v for k,v in MLB_FULL.items() if k in t1), t1)
                full2 = next((v for k,v in MLB_FULL.items() if k in t2), t2)
                result[full1] = {"prob": p1, "probPct": round(p1*100,1), "volume": round(vol), "reliable": vol>=3000}
                result[full2] = {"prob": p2, "probPct": round(p2*100,1), "volume": round(vol), "reliable": vol>=3000}
                break

        return {
            "status": "ok",
            "odds": result,
            "markets": len(result)//2,
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "odds": {}}

@app.get("/api/mlb/stats")
async def get_mlb_stats():
    if not DB_URL: return {"today":{"rate":0,"wins":0,"total":0},"week":{"rate":0,"wins":0,"total":0},"month":{"rate":0,"wins":0,"total":0},"high_conf":{"rate":0,"wins":0,"total":0}}
    conn=await get_db()
    def wr(r):
        if not r or not r["total"]: return {"rate":0,"wins":0,"total":0}
        return {"rate":round((r["wins"] or 0)/r["total"]*100),"wins":int(r["wins"] or 0),"total":r["total"]}
    td=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM mlb_predictions WHERE game_date=CURRENT_DATE AND result IS NOT NULL")
    wk=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM mlb_predictions WHERE game_date>=CURRENT_DATE-interval '7 days' AND result IS NOT NULL")
    mn=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM mlb_predictions WHERE game_date>=CURRENT_DATE-interval '30 days' AND result IS NOT NULL")
    hc=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM mlb_predictions WHERE confidence>=70 AND result IS NOT NULL")
    await conn.close()
    return {"today":wr(td),"week":wr(wk),"month":wr(mn),"high_conf":wr(hc)}

@app.get("/api/mlb/predictions/history")
async def get_mlb_history(days:int=60):
    if not DB_URL: return []
    conn=await get_db()
    try:
        rows=await conn.fetch("SELECT * FROM mlb_predictions WHERE result IS NOT NULL AND game_date>=CURRENT_DATE-($1*INTERVAL '1 day') ORDER BY game_date DESC,confidence DESC",days)
        await conn.close(); return [dict(r) for r in rows]
    except Exception as e:
        await conn.close(); return []

@app.get("/api/mlb/predictions/today")
async def get_mlb_today():
    if not DB_URL: return []
    conn=await get_db()
    rows=await conn.fetch("SELECT * FROM mlb_predictions WHERE game_date=$1 ORDER BY confidence DESC",date.today())
    await conn.close(); return [dict(r) for r in rows]

@app.get("/api/mlb/starters")
async def get_mlb_starters(): return await fetch_mlb_starters()

@app.get("/api/mlb/polymarket")
async def get_mlb_polymarket(): return await fetch_polymarket_mlb_odds()

@app.get("/api/mlb/team-data")
async def get_mlb_team_data():
    result = {}
    for name, d in MLB_TEAM_DATA.items():
        abbr = d.get("abbr","")
        if not abbr: continue
        result[abbr] = {"elo":d.get("elo",1500),"era":d.get("era",4.5),"fip":d.get("fip",4.6),"woba":d.get("woba",0.300),"home_adj":d.get("home_adj",0.04),"recent_adj":d.get("recent_adj",0)}
    return {"status":"ok","data":result}


@app.get("/api/mlb/polymarket/debug")
async def debug_mlb_polymarket():
    """除錯：搜尋今日 MLB 單場比賽 - 試所有可能的 tag"""
    try:
        import json as _json
        results = []
        tags_to_try = ["mlb", "mlb-games", "mlb-daily", "baseball-games", "sports", "daily-baseball"]
        async with httpx.AsyncClient(timeout=20) as client:
            for tag in tags_to_try:
                res = await client.get(
                    "https://gamma-api.polymarket.com/events",
                    params={"active":"true","closed":"false","limit":"5","tag_slug":tag,"order":"volume24hr","ascending":"false"},
                    headers={"User-Agent":"Mozilla/5.0"}
                )
                data = res.json()
                events = data if isinstance(data, list) else data.get("events", [])
                results.append({
                    "tag_slug": tag,
                    "count": len(events),
                    "titles": [ev.get("title","") for ev in events[:3]],
                    "first_tags": [t.get("slug","") for t in (events[0].get("tags",[]) if events else [])],
                    "first_vol24hr": events[0].get("volume24hr") if events else None,
                })
            # 也試直接搜尋 "vs" 關鍵字找今日比賽
            res2 = await client.get(
                "https://gamma-api.polymarket.com/events",
                params={"active":"true","closed":"false","limit":"20","q":"vs","order":"volume24hr","ascending":"false"},
                headers={"User-Agent":"Mozilla/5.0"}
            )
            data2 = res2.json()
            events2 = data2 if isinstance(data2, list) else data2.get("events", [])
            mlb_games = [ev.get("title","") for ev in events2 if any(t in ev.get("title","") for t in ["Astros","Yankees","Dodgers","Mets","Cubs","Red Sox","Padres","Giants","Braves","Phillies","Mariners","Orioles","Brewers","Twins","Rangers","Guardians","Rays","Tigers","Royals","Angels","Reds","Pirates","Marlins","Rockies","Nationals","Blue Jays"])]
            results.append({
                "tag_slug": "q=vs (all sports)",
                "count": len(events2),
                "mlb_game_titles": mlb_games[:10],
            })
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/mlb/trigger/predict")
async def trigger_mlb_predict(): return await fetch_and_predict_mlb() or {"status":"ok"}

@app.post("/api/mlb/trigger/results")
async def trigger_mlb_results(): return await update_mlb_results() or {"status":"ok"}

@app.post("/api/mlb/trigger/stats")
async def trigger_mlb_stats(): return await fetch_mlb_stats()

# ══════════════════════════════════════════════════════
# 排程 + 啟動
# ══════════════════════════════════════════════════════
scheduler = AsyncIOScheduler(timezone=TW)

@app.on_event("startup")
async def startup():
    await init_db()

    # NBA 排程（原版）
    scheduler.add_job(fetch_and_predict,  "cron", hour=8,  minute=0)
    scheduler.add_job(fetch_and_predict,  "cron", hour=15, minute=0)
    scheduler.add_job(update_results,     "cron", hour=2,  minute=0)
    scheduler.add_job(fetch_nba_stats,    "cron", minute=0)
    scheduler.add_job(fetch_espn_injuries,"cron", minute=15)
    scheduler.add_job(fetch_b2b_status,   "cron", minute=30)

    # MLB 排程（新增）
    scheduler.add_job(fetch_and_predict_mlb, "cron", hour=9,  minute=0)
    scheduler.add_job(fetch_and_predict_mlb, "cron", hour=16, minute=0)
    scheduler.add_job(update_mlb_results,    "cron", hour=13, minute=0)
    scheduler.add_job(update_mlb_results,    "cron", hour=14, minute=0)
    scheduler.add_job(fetch_mlb_stats,       "cron", minute=45)
    scheduler.add_job(fetch_mlb_starters,    "cron", hour=8,  minute=30)

    scheduler.start()

    # 啟動時立即更新
    await fetch_nba_stats()
    await fetch_mlb_stats()
    print("✅ NBA + MLB 後端啟動完成")
