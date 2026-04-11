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

# ESPN 球隊 ID 對照（用於抓傷兵和賽程）
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
    ha=h.get("abbr",""); aa=a.get("abbr","")
    elo_p=1/(1+10**(-(h["elo"]-a["elo"]+70)/400))
    off_p=0.5+((h["pts"]-a["opp"])-(a["pts"]-h["opp"]))*0.012
    # 傷兵調整
    hi=inj_penalty(home_inj or [])
    ai=inj_penalty(away_inj or [])
    inj_adj=(ai-hi)*0.02
    # B2B 調整（-5% 勝率）
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
    print("✅ DB 初始化完成")

# ── ESPN 真實傷兵 API
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

# ── ESPN B2B 偵測（看昨天有沒有比賽）
async def fetch_b2b_status():
    try:
        yesterday=(date.today()-timedelta(days=1)).strftime("%Y%m%d")
        today=date.today().strftime("%Y%m%d")
        async with httpx.AsyncClient(timeout=15) as client:
            res_y=await client.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}")
            res_t=await client.get(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={today}")
        yd=res_y.json(); td=res_t.json()
        # 昨天打球的隊伍
        played_yesterday=set()
        for ev in yd.get("events",[]):
            for comp in ev.get("competitions",[]):
                for team in comp.get("competitors",[]):
                    played_yesterday.add(team["team"]["displayName"])
        # 今天打球的隊伍
        playing_today={}
        for ev in td.get("events",[]):
            for comp in ev.get("competitions",[]):
                for team in comp.get("competitors",[]):
                    tn=team["team"]["displayName"]
                    playing_today[tn]=tn in played_yesterday
        return {"status":"ok","b2b":playing_today}
    except Exception as e:
        return {"status":"error","message":str(e),"b2b":{}}

# ── NBA Stats API 更新球隊數據
async def fetch_nba_stats():
    """抓取 NBA 官方球隊數據，更新 ELO 和得失分"""
    NBA_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "x-nba-stats-origin": "stats",
        "x-nba-stats-token": "true",
        "Origin": "https://www.nba.com",
        "Referer": "https://www.nba.com/",
        "Connection": "keep-alive",
    }
    try:
        async with httpx.AsyncClient(timeout=30, headers=NBA_HEADERS, follow_redirects=True) as client:
            res = await client.get(
                "https://stats.nba.com/stats/leaguedashteamstats",
                params={
                    "MeasureType": "Base",
                    "PerMode": "PerGame",
                    "Season": "2025-26",
                    "SeasonType": "Regular Season",
                    "LastNGames": 0,
                    "DateFrom": "",
                    "DateTo": "",
                    "GameScope": "",
                    "PlayerExperience": "",
                    "PlayerPosition": "",
                    "StarterBench": "",
                    "LeagueID": "00",
                }
            )
            if res.status_code != 200:
                return {"status": "error", "message": f"HTTP {res.status_code}"}
            data = res.json()

        headers = data["resultSets"][0]["headers"]
        rows = data["resultSets"][0]["rowSet"]
        stats = {}
        for row in rows:
            d = dict(zip(headers, row))
            team_name = d.get("TEAM_NAME", "")
            pts = round(d.get("PTS", 110), 1)
            # 嘗試取得失分（NBA Stats 可能叫不同名稱）
            opp_pts = round(d.get("OPP_PTS", d.get("DEFRTG", 110)), 1)
            w = d.get("W", 0)
            l = d.get("L", 0)
            stats[team_name] = {
                "pts": pts,
                "opp_pts": opp_pts,
                "wins": w,
                "losses": l,
                "win_pct": round(w/(w+l)*100) if (w+l) > 0 else 50,
            }

        # 更新後端 TEAM_DATA（存入暫存，影響後續預測）
        updated = 0
        for team_name, s in stats.items():
            if team_name in TEAM_DATA:
                TEAM_DATA[team_name]["pts"] = s["pts"]
                if s["opp_pts"] > 80:  # 確認是合理數值
                    TEAM_DATA[team_name]["opp"] = s["opp_pts"]
                updated += 1

        return {"status": "ok", "stats": stats, "updated": updated, "total_teams": len(stats)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── Polymarket NBA 勝率（後端抓，解決 CORS 問題）
async def fetch_polymarket_odds():
    """從後端抓 Polymarket NBA 賽事勝率，解決前端 CORS 限制"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                "https://clob.polymarket.com/markets",
                params={"tag_slug": "nba", "active": "true", "closed": "false", "limit": "50", "order": "volume", "ascending": "false"}
            )
            data = res.json()

        markets = data if isinstance(data, list) else data.get("markets", [])
        result = {}
        for m in markets:
            q = m.get("question", "")
            tokens = m.get("tokens", [])
            volume = float(m.get("volume", 0))
            if len(tokens) == 2 and " vs " in q and volume > 1000:
                parts = q.replace(" to win?", "").replace("?", "").split(" vs ")
                if len(parts) == 2:
                    t1, t2 = parts[0].strip(), parts[1].strip()
                    p1 = float(tokens[0].get("price", 0))
                    p2 = float(tokens[1].get("price", 0))
                    if p1 > 0 and p2 > 0:
                        total = p1 + p2
                        result[t1] = round(p1/total*100, 1)
                        result[t2] = round(p2/total*100, 1)
        return {"status": "ok", "odds": result, "markets": len(result)//2}
    except Exception as e:
        return {"status": "error", "message": str(e), "odds": {}}

# ── 台灣運彩讓分
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
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] 抓取今日賽程...")
    try:
        # 同時抓傷兵和B2B
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
            hEn=game["home_team"]; aEn=game["away_team"]
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
                if abs(diff)<0.5: bet=hEn if mp>=0.5 else aEn; odds=h2hH if mp>=0.5 else h2hA; btype="不讓分"
                elif diff>0: bet=hEn; odds=spHO or 1.72; btype=f"讓分 {spLine}"
                else: bet=aEn; odds=spAO or 1.72; btype=f"吃分 +{abs(spLine)}"
            else:
                bet=hEn if mp>=0.5 else aEn; odds=h2hH if mp>=0.5 else h2hA; btype="不讓分"
            ev=(conf/100*odds-1)*100
            exists=await conn.fetchval("SELECT id FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",today,hEn,aEn)
            if not exists:
                await conn.execute("""
                    INSERT INTO predictions(game_date,home_team,away_team,predicted_winner,confidence,bet_type,bet_odds,ev_pct,spread_line,model_spread,home_b2b,away_b2b)
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                """,today,hEn,aEn,bet,conf,btype,odds,ev,spLine,ms,home_b2b,away_b2b)
                saved+=1
        await conn.close()
        print(f"✅ 儲存 {saved} 場")
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
            row=await conn.fetchrow("SELECT id,predicted_winner FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",yesterday,hName,aName)
            if row:
                await conn.execute("UPDATE predictions SET actual_winner=$1,actual_home_score=$2,actual_away_score=$3,result=$4 WHERE id=$5",
                    winner,hScore,aScore,row["predicted_winner"]==winner,row["id"])
                updated+=1
        await conn.close()
        return {"status":"ok","updated":updated}
    except Exception as e:
        return {"status":"error","message":str(e)}

# ── API 路由
@app.get("/")
async def root(): return {"status":"ok","message":"NBA 預測系統後端運作中"}

@app.get("/api/injuries")
async def get_injuries(): return await fetch_espn_injuries()

@app.get("/api/b2b")
async def get_b2b(): return await fetch_b2b_status()

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
    scheduler.add_job(update_results,"cron",hour=2,minute=0)
    # NBA Stats 每週一早上9點更新
    scheduler.add_job(fetch_nba_stats,"cron",day_of_week="mon",hour=9,minute=0)
    scheduler.start()
    print("✅ 後端啟動完成")
