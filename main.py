from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
import httpx
import os
from datetime import datetime, date, timedelta
import pytz

app = FastAPI()

# ★ 修正 CORS — 允許所有來源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

TW = pytz.timezone("Asia/Taipei")
DB_URL = os.environ.get("DATABASE_URL", "")
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")

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
    "MIA":[{"player":"吉米·巴特勒","status":"缺陣"}],
    "DAL":[{"player":"盧卡·唐西奇","status":"缺陣"}],
    "BOS":[{"player":"波爾辛吉斯","status":"存疑"}],
    "LAL":[{"player":"勒布朗·詹姆斯","status":"存疑"}],
    "MEM":[{"player":"賈·莫蘭特","status":"存疑"}],
    "PHI":[{"player":"喬爾·恩比德","status":"缺陣"}],
    "OKC":[{"player":"切特·霍姆格倫","status":"存疑"}],
}

def inj_penalty(abbr):
    return sum(4 if i["status"]=="缺陣" else 1.5 for i in INJURIES.get(abbr,[]))

def calc_model(home_en, away_en, bp):
    h=TEAM_DATA.get(home_en,{"elo":1400,"pts":110,"opp":110})
    a=TEAM_DATA.get(away_en,{"elo":1400,"pts":110,"opp":110})
    ha=h.get("abbr",""); aa=a.get("abbr","")
    elo_p=1/(1+10**(-(h["elo"]-a["elo"]+70)/400))
    off_p=0.5+((h["pts"]-a["opp"])-(a["pts"]-h["opp"]))*0.012
    inj=( inj_penalty(aa)-inj_penalty(ha))*0.02
    return max(0.05,min(0.95,elo_p*0.35+off_p*0.25+bp*0.3+0.5*0.1+inj))

async def get_db():
    url = DB_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://","postgresql://",1)
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
            actual_winner TEXT,
            actual_home_score INTEGER,
            actual_away_score INTEGER,
            result BOOLEAN,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    await conn.close()
    print("✅ 資料庫初始化完成")

async def fetch_and_predict():
    if not ODDS_KEY or not DB_URL:
        print("缺少設定"); return
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] 抓取今日賽程...")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res=await client.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds/",
                params={"apiKey":ODDS_KEY,"regions":"us","markets":"h2h,spreads","oddsFormat":"decimal","dateFormat":"iso"})
            data=res.json()
        conn=await get_db()
        today=date.today()
        saved=0
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
            mp=calc_model(hEn,aEn,bp)
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
            exists=await conn.fetchval(
                "SELECT id FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",
                today,hEn,aEn)
            if not exists:
                await conn.execute("""
                    INSERT INTO predictions(game_date,home_team,away_team,predicted_winner,confidence,bet_type,bet_odds,ev_pct,spread_line,model_spread)
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                """,today,hEn,aEn,bet,conf,btype,odds,ev,spLine,ms)
                saved+=1
        await conn.close()
        print(f"✅ 儲存 {saved} 場預測")
        return {"status":"ok","saved":saved}
    except Exception as e:
        print(f"❌ {e}"); return {"status":"error","message":str(e)}

async def update_results():
    if not DB_URL: return
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] 更新比賽結果...")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res=await client.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")
            data=res.json()
        conn=await get_db()
        yesterday=date.today()-timedelta(days=1)
        updated=0
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
                "SELECT id,predicted_winner FROM predictions WHERE game_date=$1 AND home_team=$2 AND away_team=$3",
                yesterday,hName,aName)
            if row:
                await conn.execute(
                    "UPDATE predictions SET actual_winner=$1,actual_home_score=$2,actual_away_score=$3,result=$4 WHERE id=$5",
                    winner,hScore,aScore,row["predicted_winner"]==winner,row["id"])
                updated+=1
        await conn.close()
        print(f"✅ 更新 {updated} 場")
        return {"status":"ok","updated":updated}
    except Exception as e:
        print(f"❌ {e}"); return {"status":"error","message":str(e)}

@app.get("/")
async def root():
    return {"status":"ok","message":"NBA 預測系統後端運作中"}

@app.get("/api/predictions/today")
async def get_today():
    if not DB_URL: return []
    conn=await get_db()
    rows=await conn.fetch("SELECT * FROM predictions WHERE game_date=$1 ORDER BY confidence DESC",date.today())
    await conn.close()
    return [dict(r) for r in rows]

@app.get("/api/predictions/history")
async def get_history(days:int=60):
    if not DB_URL: return []
    conn=await get_db()
    rows=await conn.fetch("""
        SELECT * FROM predictions WHERE result IS NOT NULL
        AND game_date>=CURRENT_DATE-($1::text||' days')::interval
        ORDER BY game_date DESC,confidence DESC
    """,str(days))
    await conn.close()
    return [dict(r) for r in rows]

@app.get("/api/stats")
async def get_stats():
    if not DB_URL: return {"today":{"rate":0,"wins":0,"total":0},"week":{"rate":0,"wins":0,"total":0},"month":{"rate":0,"wins":0,"total":0},"high_conf":{"rate":0,"wins":0,"total":0}}
    conn=await get_db()
    def wr(r):
        if not r or not r["total"]: return {"rate":0,"wins":0,"total":0}
        return {"rate":round((r["wins"] or 0)/r["total"]*100),"wins":r["wins"] or 0,"total":r["total"]}
    td=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE game_date=CURRENT_DATE AND result IS NOT NULL")
    wk=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE game_date>=CURRENT_DATE-interval '7 days' AND result IS NOT NULL")
    mn=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE game_date>=CURRENT_DATE-interval '30 days' AND result IS NOT NULL")
    hc=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions WHERE confidence>=70 AND result IS NOT NULL")
    await conn.close()
    return {"today":wr(td),"week":wr(wk),"month":wr(mn),"high_conf":wr(hc)}

@app.post("/api/trigger/predict")
async def trigger_predict():
    result=await fetch_and_predict()
    return result or {"status":"ok"}

@app.post("/api/trigger/results")
async def trigger_results():
    result=await update_results()
    return result or {"status":"ok"}

scheduler=AsyncIOScheduler(timezone=TW)

@app.on_event("startup")
async def startup():
    await init_db()
    scheduler.add_job(fetch_and_predict,"cron",hour=8,minute=0)
    scheduler.add_job(update_results,"cron",hour=2,minute=0)
    scheduler.start()
    print("✅ 後端啟動完成")
