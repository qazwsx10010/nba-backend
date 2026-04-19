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

def inj_penalty(injuries_list):
    return sum(4 if i.get("status_type")=="Out" else 2 if i.get("status_type")=="Doubtful" else 1 for i in injuries_list)

def calc_model(home_en, away_en, bp, home_inj=None, away_inj=None, home_b2b=False, away_b2b=False):
    h=TEAM_DATA.get(home_en,{"elo":1400,"pts":110,"opp":110})
    a=TEAM_DATA.get(away_en,{"elo":1400,"pts":110,"opp":110})
    ha=h.get("abbr",""); aa=a.get("abbr","")
    elo_p=1/(1+10**(-(h["elo"]-a["elo"]+70)/400))
    off_p=0.5+((h["pts"]-a["opp"])-(a["pts"]-h["opp"]))*0.012
    hi=inj_penalty(home_inj or [])
    ai=inj_penalty(away_inj or [])
    inj_adj=(ai-hi)*0.02
    b2b_adj=(-0.05 if home_b2b else 0)+(0.05 if away_b2b else 0)
    model=elo_p*0.35+off_p*0.25+bp*0.3+0.5*0.1+inj_adj+b2b_adj
    return max(0.05,min(0.95,model))

async def get_db():
    url=DB_URL
    if url.startswith("postgres://"): url=url.replace("postgres://","postgresql://",1)
    return await asyncpg.connect(url)

async def init_db():
    if not DB_URL: return
    conn=await get_db()
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
    await conn.close()

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
                status=item.get("status","")
                status_type=item.get("type",{}).get("description","")
                players.append({
                    "player": athlete.get("displayName",""),
                    "position": athlete.get("position",{}).get("abbreviation",""),
                    "status": status,
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
                    n = stat.get("name","")
                    v = stat.get("value", 0)
                    sdv = stat.get("displayValue","")
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
                                p = sdv.split("-")
                                rw, rl = int(p[0]), int(p[1])
                            else:
                                rw = int(float(v)); rl = 10 - rw
                            if rw + rl > 0:
                                recent_adj_raw = round((rw/(rw+rl) - 0.5) * 100)
                        except:
                            recent_adj_raw = 0

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
                        if n in ("homeWins","homeRecord") and "-" not in str(stat.get("value","")):
                            try: home_w=int(stat.get("value",0))
                            except: pass
                        if n=="homeLosses":
                            try: home_l=int(stat.get("value",0))
                            except: pass
                        if n in ("roadWins","awayWins"):
                            try: away_w=int(stat.get("value",0))
                            except: pass
                        if n in ("roadLosses","awayLosses"):
                            try: away_l=int(stat.get("value",0))
                            except: pass
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
                        "wins": wins, "losses": losses,
                        "win_pct": round(win_pct*100, 1), "elo": new_elo,
                        "pts": TEAM_DATA[team_name]["pts"],
                        "opp": TEAM_DATA[team_name]["opp"],
                        "home_win_pct": home_win_pct,
                        "away_win_pct": away_win_pct,
                        "recent_adj": recent_adj_raw,
                        "recent": recent_str
                    }
                    updated += 1
                    recent_adj_raw = 0

        return {"status": "ok", "updated": updated, "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def fetch_polymarket_odds():
    try:
        import json as _json
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://gamma-api.polymarket.com/events",
                params={
                    "active": "true",
                    "closed": "false",
                    "limit": "300", 
                    "tag_slug": "basketball",
                    "order": "volume24hr",
                    "ascending": "false",
                },
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = res.json()

        events = data if isinstance(data, list) else data.get("events", [])
        
        # 建立一個大倉庫，用來收集同一場比賽的所有盤口
        global_markets = {}
        result = {}

        def resolve_team(name):
            n = str(name).strip().upper()
            abbr = {
                "ATL":"Hawks","BOS":"Celtics","BKN":"Nets","CHA":"Hornets","CHI":"Bulls",
                "CLE":"Cavaliers","DAL":"Mavericks","DEN":"Nuggets","DET":"Pistons","GSW":"Warriors",
                "HOU":"Rockets","IND":"Pacers","LAC":"Clippers","LAL":"Lakers","MEM":"Grizzlies",
                "MIA":"Heat","MIL":"Bucks","MIN":"Timberwolves","NOP":"Pelicans","NYK":"Knicks",
                "OKC":"Thunder","ORL":"Magic","PHI":"76ers","PHX":"Suns","POR":"Trail Blazers",
                "SAC":"Kings","SAS":"Spurs","TOR":"Raptors","UTA":"Jazz","WAS":"Wizards",
                "SA":"Spurs","NY":"Knicks","NO":"Pelicans","LA":"Lakers","GS":"Warriors",
                "PHOENIX":"Suns","OKLAHOMA":"Thunder","PHILLY":"76ers","SIXERS":"76ers"
            }
            if n in abbr: return abbr[n]
            # 模糊比對
            for f in ["Hawks", "Celtics", "Nets", "Hornets", "Bulls", "Cavaliers", "Mavericks", "Nuggets", "Pistons", "Warriors", "Rockets", "Pacers", "Clippers", "Lakers", "Grizzlies", "Heat", "Bucks", "Timberwolves", "Pelicans", "Knicks", "Thunder", "Magic", "76ers", "Suns", "Trail Blazers", "Kings", "Spurs", "Raptors", "Jazz", "Wizards"]:
                if f.upper() in n: return f
            return None

        # 【終極掃描邏輯】：把所有的 Event 裡面的所有 Market 都翻一遍
        for event in events:
            event_vol = float(event.get("volume", 0) or event.get("volume24hr", 0) or 0)

            for m in event.get("markets", []):
                q = m.get("question", "").upper()
                
                # 排除大小分、單節勝負等雜魚
                if any(x in q for x in ["SPREAD", "TOTAL", "OVER", "UNDER", "MARGIN", "RACE", "HALF", "QUARTER", "FIRST", "LEAD", "POINTS", "REBOUNDS", "ASSISTS"]):
                    continue

                outcomes_raw = m.get("outcomes", "[]")
                prices_raw = m.get("outcomePrices", "[]")

                try: outcomes = _json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                except: continue
                try: prices = _json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                except: continue

                if len(outcomes) != 2 or len(prices) != 2:
                    continue

                t1_raw, t2_raw = str(outcomes[0]).upper(), str(outcomes[1]).upper()

                # 排除帶有加減號的讓分盤
                if any(c in t1_raw for c in ["+", "-", "."]) or any(c in t2_raw for c in ["+", "-", "."]):
                    continue

                t1 = resolve_team(t1_raw)
                t2 = resolve_team(t2_raw)

                # 確定是兩支乾淨的 NBA 球隊
                if not t1 or not t2 or t1 == t2:
                    continue

                try: p1, p2 = float(prices[0]), float(prices[1])
                except: continue
                if not (0 < p1 < 1 and 0 < p2 < 1): continue

                m_vol = float(m.get("volume", 0) or 0)
                m_liq = float(m.get("liquidity", 0) or 0)
                
                # 計算這個盤口的「權重分數」：流動性 + 單盤成交 + 事件總成交
                score = m_vol + m_liq + event_vol

                # 把兩支隊伍名字排序，當作這場比賽的「唯一識別碼」
                teams = sorted([t1, t2])
                matchup_key = f"{teams[0]}_vs_{teams[1]}"

                # 【核心機制】：同場比賽，只保留分數最高（資金最大）的那個盤口
                if matchup_key not in global_markets or score > global_markets[matchup_key]['score']:
                    display_vol = max(event_vol, m_vol, m_liq)
                    global_markets[matchup_key] = {
                        "score": score,
                        "t1": t1, "p1": p1,
                        "t2": t2, "p2": p2,
                        "display_vol": display_vol
                    }

        # 掃描完畢！把大倉庫裡過濾好的「最肥盤口」寫入結果
        for data in global_markets.values():
            vol = data["display_vol"]
            result[data["t1"]] = {"prob": round(data["p1"]*100, 1), "volume": round(vol), "reliable": vol >= 5000}
            result[data["t2"]] = {"prob": round(data["p2"]*100, 1), "volume": round(vol), "reliable": vol >= 5000}

        return {
            "status": "ok",
            "odds": result,
            "markets": len(global_markets)
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "odds": {}}

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
            normal=latest.get("normal",{})
            handi=latest.get("handi",{})
            total_data=latest.get("total",{})
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
    try:
        inj_data=await fetch_espn_injuries()
        b2b_data=await fetch_b2b_status()
        injuries=inj_data.get("injuries",{})
        b2b=b2b_data.get("b2b",{})

        async with httpx.AsyncClient(timeout=30) as client:
            res=await client.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
                params={"apiKey":ODDS_KEY,"regions":"us","markets":"h2h,spreads","oddsFormat":"decimal","dateFormat":"iso"})
            data=res.json()
        conn=await get_db()
        today=date.today(); saved=0
        for game in data:
            hEn=normalize_team(game["home_team"])
            aEn=normalize_team(game["away_team"])
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
            home_inj=injuries.get(hEn,[])
            away_inj=injuries.get(aEn,[])
            home_b2b=b2b.get(hEn,False)
            away_b2b=b2b.get(aEn,False)
            mp=calc_model(hEn,aEn,bp,home_inj,away_inj,home_b2b,away_b2b)
            ms=(mp-0.5)*28
            conf=max(round(mp*100),round((1-mp)*100))
            if spLine is not None:
                diff=ms-spLine
                if abs(diff)<0.5:
                    bet=hEn if mp>=0.5 else aEn; odds=h2hH if mp>=0.5 else h2hA; btype="不讓分"
                elif diff>0:
                    bet=hEn; odds=spHO or 1.72
                    btype=f"讓分 {spLine}" if spLine<0 else f"吃分 +{spLine}"
                else:
                    bet=aEn; odds=spAO or 1.72
                    away_spread=-spLine
                    btype=f"讓分 {away_spread}" if away_spread<0 else f"吃分 +{away_spread}"
            else:
                bet=hEn if mp>=0.5 else aEn; odds=h2hH if mp>=0.5 else h2hA; btype="不讓分"
            ev=(conf/100*odds-1)*100
            exists=await conn.fetchrow("SELECT id,result FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",today,hEn,aEn)
            if not exists:
                await conn.execute("""
                    INSERT INTO predictions(game_date,home_team,away_team,predicted_winner,confidence,bet_type,bet_odds,ev_pct,spread_line,model_spread,home_b2b,away_b2b)
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                """,today,hEn,aEn,bet,conf,btype,odds,ev,spLine,ms,home_b2b,away_b2b)
                saved+=1
            elif exists["result"] is None:
                await conn.execute("""
                    UPDATE predictions SET predicted_winner=$1,confidence=$2,bet_type=$3,
                    bet_odds=$4,ev_pct=$5,spread_line=$6,model_spread=$7,home_b2b=$8,away_b2b=$9
                    WHERE id=$10
                """,bet,conf,btype,odds,ev,spLine,ms,home_b2b,away_b2b,exists["id"])
                saved+=1
        await conn.close()
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
            row=await conn.fetchrow(
                "SELECT id,predicted_winner,bet_type,spread_line FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",
                yesterday,hName,aName)
            if row:
                bet_type=row["bet_type"] or ""
                spread_line=row["spread_line"]
                predicted=row["predicted_winner"]

                if "讓分" in bet_type and spread_line is not None:
                    result = (hScore + spread_line) > aScore
                elif "吃分" in bet_type and spread_line is not None:
                    result = (aScore - spread_line) > hScore
                else:
                    result = predicted == winner

                await conn.execute(
                    "UPDATE predictions SET actual_winner=$1,actual_home_score=$2,actual_away_score=$3,result=$4 WHERE id=$5",
                    winner,hScore,aScore,result,row["id"])
                updated+=1
        await conn.close()
        return {"status":"ok","updated":updated}
    except Exception as e:
        return {"status":"error","message":str(e)}

@app.get("/")
async def root(): return {"status":"ok","message":"NBA 預測系統後端運作中","version":"v3.2-polymarket-100percent"}

@app.get("/api/b2b")
async def get_b2b(): return await fetch_b2b_status()

@app.get("/api/team-data")
async def get_team_data():
    result = {}
    for name, d in TEAM_DATA.items():
        abbr = d.get("abbr","")
        if not abbr: continue
        result[abbr] = {
            "elo": d.get("elo", 1400),
            "pts": d.get("pts", 110),
            "opp": d.get("opp", 110),
            "pace": d.get("pace", 99),
            "recent_adj": d.get("recent_adj", 0),
        }
    return {"status": "ok", "data": result}

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
        rows=await conn.fetch("""
            SELECT * FROM predictions 
            WHERE result IS NOT NULL 
            AND game_date >= CURRENT_DATE - ($1 * INTERVAL '1 day')
            ORDER BY game_date DESC, confidence DESC
        """, days)
        await conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        await conn.close()
        return []

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
async def trigger_nba_stats(): return await fetch_nba_stats()

scheduler=AsyncIOScheduler(timezone=TW)

@app.on_event("startup")
async def startup():
    await init_db()
    scheduler.add_job(fetch_and_predict,"cron",hour=8,minute=0)
    scheduler.add_job(fetch_and_predict,"cron",hour=15,minute=0)
    scheduler.add_job(update_results,"cron",hour=2,minute=0)
    scheduler.add_job(fetch_nba_stats,"cron",minute=0)
    scheduler.add_job(fetch_espn_injuries,"cron",minute=15)
    scheduler.add_job(fetch_b2b_status,"cron",minute=30)
    scheduler.start()
    await fetch_nba_stats()
