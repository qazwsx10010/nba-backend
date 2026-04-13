# ═══════════════════════════════════════════════════════════════
#  MLB 預測模組（追加在 NBA main.py 最底部，不影響任何 NBA 程式碼）
#  所有路由用 /api/mlb/ 前綴，DB 表獨立為 predictions_mlb
# ═══════════════════════════════════════════════════════════════

MLB_TEAM_DATA = {
    "Arizona Diamondbacks": {"elo": 1560, "runs": 4.8, "opp": 4.5, "abbr": "ARI"},
    "Atlanta Braves":        {"elo": 1620, "runs": 5.1, "opp": 4.2, "abbr": "ATL"},
    "Baltimore Orioles":     {"elo": 1580, "runs": 4.7, "opp": 4.3, "abbr": "BAL"},
    "Boston Red Sox":        {"elo": 1490, "runs": 4.5, "opp": 4.8, "abbr": "BOS"},
    "Chicago Cubs":          {"elo": 1510, "runs": 4.4, "opp": 4.7, "abbr": "CHC"},
    "Chicago White Sox":     {"elo": 1280, "runs": 3.8, "opp": 5.5, "abbr": "CWS"},
    "Cincinnati Reds":       {"elo": 1540, "runs": 4.6, "opp": 4.6, "abbr": "CIN"},
    "Cleveland Guardians":   {"elo": 1570, "runs": 4.5, "opp": 4.2, "abbr": "CLE"},
    "Colorado Rockies":      {"elo": 1300, "runs": 4.2, "opp": 5.8, "abbr": "COL"},
    "Detroit Tigers":        {"elo": 1520, "runs": 4.3, "opp": 4.5, "abbr": "DET"},
    "Houston Astros":        {"elo": 1600, "runs": 4.9, "opp": 4.1, "abbr": "HOU"},
    "Kansas City Royals":    {"elo": 1530, "runs": 4.4, "opp": 4.6, "abbr": "KC"},
    "Los Angeles Angels":    {"elo": 1480, "runs": 4.3, "opp": 4.9, "abbr": "LAA"},
    "Los Angeles Dodgers":   {"elo": 1720, "runs": 5.5, "opp": 3.8, "abbr": "LAD"},
    "Miami Marlins":         {"elo": 1460, "runs": 4.0, "opp": 5.0, "abbr": "MIA"},
    "Milwaukee Brewers":     {"elo": 1560, "runs": 4.6, "opp": 4.3, "abbr": "MIL"},
    "Minnesota Twins":       {"elo": 1570, "runs": 4.7, "opp": 4.3, "abbr": "MIN"},
    "New York Mets":         {"elo": 1530, "runs": 4.5, "opp": 4.6, "abbr": "NYM"},
    "New York Yankees":      {"elo": 1600, "runs": 5.0, "opp": 4.1, "abbr": "NYY"},
    "Oakland Athletics":     {"elo": 1380, "runs": 3.9, "opp": 5.3, "abbr": "OAK"},
    "Philadelphia Phillies": {"elo": 1620, "runs": 5.0, "opp": 4.1, "abbr": "PHI"},
    "Pittsburgh Pirates":    {"elo": 1530, "runs": 4.3, "opp": 4.5, "abbr": "PIT"},
    "San Diego Padres":      {"elo": 1580, "runs": 4.7, "opp": 4.2, "abbr": "SD"},
    "San Francisco Giants":  {"elo": 1480, "runs": 4.2, "opp": 4.8, "abbr": "SF"},
    "Seattle Mariners":      {"elo": 1560, "runs": 4.5, "opp": 4.2, "abbr": "SEA"},
    "St. Louis Cardinals":   {"elo": 1520, "runs": 4.4, "opp": 4.6, "abbr": "STL"},
    "Tampa Bay Rays":        {"elo": 1580, "runs": 4.6, "opp": 4.2, "abbr": "TB"},
    "Texas Rangers":         {"elo": 1560, "runs": 4.7, "opp": 4.4, "abbr": "TEX"},
    "Toronto Blue Jays":     {"elo": 1530, "runs": 4.5, "opp": 4.5, "abbr": "TOR"},
    "Washington Nationals":  {"elo": 1400, "runs": 4.0, "opp": 5.2, "abbr": "WSH"},
}

MLB_TEAM_NAME_NORMALIZE = {
    "LA Angels":     "Los Angeles Angels",
    "LA Dodgers":    "Los Angeles Dodgers",
    "KC Royals":     "Kansas City Royals",
    "NY Yankees":    "New York Yankees",
    "NY Mets":       "New York Mets",
    "SF Giants":     "San Francisco Giants",
    "SD Padres":     "San Diego Padres",
    "TB Rays":       "Tampa Bay Rays",
    "Chi Cubs":      "Chicago Cubs",
    "Chi White Sox": "Chicago White Sox",
    "Athletics":     "Oakland Athletics",
}

def mlb_normalize_team(name):
    return MLB_TEAM_NAME_NORMALIZE.get(name, name)

def mlb_inj_penalty(injuries_list):
    score = 0
    for i in injuries_list:
        pos = i.get("position", "")
        is_pitcher = pos in ("SP", "RP", "P", "CL")
        base = 6 if is_pitcher else 3
        st = i.get("status_type", "")
        if st in ("60-Day IL", "Out"):     score += base
        elif st in ("10-Day IL", "Doubtful"): score += base // 2
        elif st in ("Day-to-Day", "Questionable"): score += 1
    return score

def mlb_calc_model(home_en, away_en, bp, home_inj=None, away_inj=None, home_b2b=False, away_b2b=False):
    h = MLB_TEAM_DATA.get(home_en, {"elo": 1500, "runs": 4.3, "opp": 4.3})
    a = MLB_TEAM_DATA.get(away_en, {"elo": 1500, "runs": 4.3, "opp": 4.3})
    elo_p  = 1 / (1 + 10 ** (-(h["elo"] - a["elo"] + 40) / 400))
    run_diff = (h["runs"] - a["opp"]) - (a["runs"] - h["opp"])
    off_p  = 0.5 + run_diff * 0.04
    hi = mlb_inj_penalty(home_inj or [])
    ai = mlb_inj_penalty(away_inj or [])
    inj_adj  = (ai - hi) * 0.025
    b2b_adj  = (-0.02 if home_b2b else 0) + (0.02 if away_b2b else 0)
    model = elo_p * 0.30 + off_p * 0.20 + bp * 0.40 + 0.5 * 0.10 + inj_adj + b2b_adj
    return max(0.05, min(0.95, model))

# ── MLB DB（獨立資料表）
async def init_db_mlb():
    if not DB_URL: return
    conn = await get_db()   # 沿用 NBA 的 get_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions_mlb (
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
    await conn.close()
    print("✅ MLB DB 初始化完成")

# ── ESPN MLB 傷兵
async def fetch_mlb_injuries():
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries")
            data = res.json()
        injuries = {}
        for td in data.get("injuries", []):
            tn = td.get("team", {}).get("displayName", "")
            if not tn: continue
            players = []
            for item in td.get("injuries", []):
                athlete = item.get("athlete", {})
                players.append({
                    "player":      athlete.get("displayName", ""),
                    "position":    athlete.get("position", {}).get("abbreviation", ""),
                    "status":      item.get("status", ""),
                    "status_type": item.get("type", {}).get("description", ""),
                    "detail":      item.get("shortComment", ""),
                })
            injuries[tn] = players
        return {"status": "ok", "injuries": injuries, "updated": datetime.now(TW).strftime("%Y-%m-%d %H:%M")}
    except Exception as e:
        return {"status": "error", "message": str(e), "injuries": {}}

# ── ESPN MLB B2B
async def fetch_mlb_b2b():
    try:
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
        today_str = date.today().strftime("%Y%m%d")
        async with httpx.AsyncClient(timeout=15) as client:
            ry = await client.get(f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={yesterday}")
            rt = await client.get(f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={today_str}")
        played_yesterday = set()
        for ev in ry.json().get("events", []):
            for comp in ev.get("competitions", []):
                for team in comp.get("competitors", []):
                    played_yesterday.add(team["team"]["displayName"])
        playing_today = {}
        for ev in rt.json().get("events", []):
            for comp in ev.get("competitions", []):
                for team in comp.get("competitors", []):
                    tn = team["team"]["displayName"]
                    playing_today[tn] = tn in played_yesterday
        return {"status": "ok", "b2b": playing_today}
    except Exception as e:
        return {"status": "error", "message": str(e), "b2b": {}}

# ── ESPN MLB Stats 更新
async def fetch_mlb_stats():
    try:
        updated = 0
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://site.api.espn.com/apis/v2/sports/baseball/mlb/standings",
                params={"season": "2026"}
            )
            data = res.json()
        stats = {}
        for conf in data.get("children", []):
            for div in conf.get("children", [conf]):
                for entry in div.get("standings", {}).get("entries", []):
                    tn = mlb_normalize_team(entry.get("team", {}).get("displayName", ""))
                    wins = losses = 0
                    runs = opp = None
                    recent_adj_raw = 0
                    recent_str = ""
                    for stat in entry.get("stats", []):
                        n = stat.get("name", ""); v = stat.get("value", 0); sdv = stat.get("displayValue", "")
                        if n == "wins":
                            try: wins = int(v)
                            except: pass
                        if n == "losses":
                            try: losses = int(v)
                            except: pass
                        if n in ("avgPointsFor", "runsFor", "avgRunsFor"):
                            try:
                                val = round(float(v), 2)
                                if val > 1.0: runs = val
                            except: pass
                        if n in ("avgPointsAgainst", "runsAgainst", "avgRunsAgainst"):
                            try:
                                val = round(float(v), 2)
                                if val > 1.0: opp = val
                            except: pass
                        if n == "Last Ten Games":
                            recent_str = sdv
                            try:
                                if "-" in str(sdv):
                                    p = sdv.split("-"); rw, rl = int(p[0]), int(p[1])
                                else:
                                    rw = int(float(v)); rl = 10 - rw
                                if rw + rl > 0: recent_adj_raw = round((rw/(rw+rl)-0.5)*80)
                            except: recent_adj_raw = 0

                    if tn in MLB_TEAM_DATA and wins + losses > 0:
                        win_pct = wins / (wins + losses)
                        new_elo = round(1500 + (win_pct - 0.5) * 800) + recent_adj_raw
                        MLB_TEAM_DATA[tn]["elo"] = new_elo
                        MLB_TEAM_DATA[tn]["recent_adj"] = recent_adj_raw
                        if runs and runs > 1.0: MLB_TEAM_DATA[tn]["runs"] = runs
                        if opp  and opp  > 1.0: MLB_TEAM_DATA[tn]["opp"]  = opp

                        home_w = home_l = away_w = away_l = 0
                        for stat in entry.get("stats", []):
                            n = stat.get("name", "")
                            if n == "Home":
                                try:
                                    pts = str(stat.get("displayValue","")).split("-")
                                    if len(pts)==2: home_w,home_l=int(pts[0]),int(pts[1])
                                except: pass
                            if n == "Road":
                                try:
                                    pts = str(stat.get("displayValue","")).split("-")
                                    if len(pts)==2: away_w,away_l=int(pts[0]),int(pts[1])
                                except: pass

                        stats[tn] = {
                            "wins": wins, "losses": losses,
                            "win_pct": round(win_pct*100, 1), "elo": new_elo,
                            "runs": MLB_TEAM_DATA[tn]["runs"], "opp": MLB_TEAM_DATA[tn]["opp"],
                            "home_win_pct": round(home_w/(home_w+home_l)*100,1) if home_w+home_l>0 else None,
                            "away_win_pct": round(away_w/(away_w+away_l)*100,1) if away_w+away_l>0 else None,
                            "recent_adj": recent_adj_raw, "recent": recent_str,
                        }
                        updated += 1
                        recent_adj_raw = 0

        print(f"✅ ESPN MLB Stats 更新 {updated} 支球隊")
        return {"status": "ok", "updated": updated, "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── Polymarket MLB 勝率
async def fetch_mlb_polymarket():
    try:
        import json as _json
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                "https://gamma-api.polymarket.com/events",
                params={"active":"true","closed":"false","limit":"100",
                        "tag_slug":"baseball","order":"volume24hr","ascending":"false"},
                headers={"User-Agent":"Mozilla/5.0"}
            )
            data = res.json()
        events = data if isinstance(data, list) else data.get("events", [])
        result = {}
        mlb_teams = {
            "Yankees","Red Sox","Dodgers","Astros","Mets","Cubs","Braves","Cardinals",
            "Phillies","Giants","Mariners","Padres","Rangers","Twins","Guardians",
            "Orioles","Pirates","Angels","Athletics","Marlins","White Sox","Tigers",
            "Brewers","Blue Jays","Rays","Royals","Rockies","Diamondbacks","Nationals","Reds"
        }
        non_mlb = ["KBO","NPB","NBA","NHL","NFL","Premier League","Champions League","UFC","ATP","WTA"]
        for event in events:
            vol = float(event.get("volume24hr",0) or event.get("volume",0) or 0)
            title = event.get("title","")
            if any(kw in title for kw in non_mlb): continue
            found = [t for t in mlb_teams if t in title]
            if len(found) < 2: continue
            for m in event.get("markets",[]):
                q = m.get("question","")
                if "vs." not in q: continue
                if any(x in q.lower() for x in ["spread","total","runs","hits","strikeout","inning","draw"]): continue
                try:
                    outcomes = _json.loads(m.get("outcomes","[]")) if isinstance(m.get("outcomes","[]"),str) else m.get("outcomes",[])
                    prices  = _json.loads(m.get("outcomePrices","[]")) if isinstance(m.get("outcomePrices","[]"),str) else m.get("outcomePrices",[])
                except: continue
                if len(outcomes)!=2 or len(prices)!=2: continue
                t1,t2 = str(outcomes[0]).strip(), str(outcomes[1]).strip()
                if t1 not in mlb_teams or t2 not in mlb_teams: continue
                try: p1,p2 = float(prices[0]),float(prices[1])
                except: continue
                if not(0<p1<1 and 0<p2<1): continue
                result[t1]={"prob":round(p1*100,1),"volume":round(vol),"reliable":vol>=3000}
                result[t2]={"prob":round(p2*100,1),"volume":round(vol),"reliable":vol>=3000}
                break
        return {"status":"ok","odds":result,"markets":len(result)//2,"raw_count":len(events)}
    except Exception as e:
        return {"status":"error","message":str(e),"odds":{}}

# ── MLB 主要預測
async def fetch_and_predict_mlb():
    if not ODDS_KEY or not DB_URL: return {"status":"error","message":"缺少設定"}
    print(f"[{datetime.now(TW).strftime('%Y-%m-%d %H:%M')}] 抓取今日 MLB 賽程...")
    try:
        inj_data = await fetch_mlb_injuries()
        b2b_data = await fetch_mlb_b2b()
        injuries = inj_data.get("injuries", {})
        b2b      = b2b_data.get("b2b", {})

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(
                "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/",
                params={"apiKey":ODDS_KEY,"regions":"us","markets":"h2h,spreads",
                        "oddsFormat":"decimal","dateFormat":"iso"}
            )
            data = res.json()

        conn = await get_db()
        today = date.today(); saved = 0

        for game in data:
            hEn = mlb_normalize_team(game["home_team"])
            aEn = mlb_normalize_team(game["away_team"])
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
            bp = (1/h2hH)/((1/h2hH)+(1/h2hA))
            mp = mlb_calc_model(hEn,aEn,bp,injuries.get(hEn,[]),injuries.get(aEn,[]),b2b.get(hEn,False),b2b.get(aEn,False))
            ms   = (mp-0.5)*8
            conf = max(round(mp*100), round((1-mp)*100))

            if spLine is not None:
                diff = ms - spLine
                if abs(diff)<0.3:
                    bet=hEn if mp>=0.5 else aEn; odds=h2hH if mp>=0.5 else h2hA; btype="勝負線"
                elif diff>0:
                    bet=hEn; odds=spHO or 1.72
                    btype=f"讓分 {spLine}" if spLine<0 else f"吃分 +{spLine}"
                else:
                    bet=aEn; odds=spAO or 1.72
                    asp=-spLine; btype=f"讓分 {asp}" if asp<0 else f"吃分 +{asp}"
            else:
                bet=hEn if mp>=0.5 else aEn; odds=h2hH if mp>=0.5 else h2hA; btype="勝負線"

            ev = (conf/100*odds-1)*100

            exists = await conn.fetchrow(
                "SELECT id,result FROM predictions_mlb WHERE game_date=$1 AND home_team=$2 AND away_team=$3",
                today, hEn, aEn
            )
            if not exists:
                await conn.execute("""
                    INSERT INTO predictions_mlb(game_date,home_team,away_team,predicted_winner,confidence,bet_type,bet_odds,ev_pct,spread_line,model_spread,home_b2b,away_b2b)
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                """, today,hEn,aEn,bet,conf,btype,odds,ev,spLine,ms,b2b.get(hEn,False),b2b.get(aEn,False))
                saved+=1
            elif exists["result"] is None:
                await conn.execute("""
                    UPDATE predictions_mlb SET predicted_winner=$1,confidence=$2,bet_type=$3,
                    bet_odds=$4,ev_pct=$5,spread_line=$6,model_spread=$7,home_b2b=$8,away_b2b=$9
                    WHERE id=$10
                """, bet,conf,btype,odds,ev,spLine,ms,b2b.get(hEn,False),b2b.get(aEn,False),exists["id"])
                saved+=1

        await conn.close()
        print(f"✅ MLB 儲存 {saved} 場")
        return {"status":"ok","saved":saved}
    except Exception as e:
        return {"status":"error","message":str(e)}

# ── MLB 更新結果
async def update_results_mlb():
    if not DB_URL: return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard")
            data = res.json()
        conn = await get_db()
        yesterday = date.today()-timedelta(days=1); updated=0
        for ev in data.get("events",[]):
            comp=ev["competitions"][0]
            if ev["status"]["type"]["state"]!="post": continue
            home=next((c for c in comp["competitors"] if c["homeAway"]=="home"),None)
            away=next((c for c in comp["competitors"] if c["homeAway"]=="away"),None)
            if not home or not away: continue
            hName=mlb_normalize_team(home["team"]["displayName"])
            aName=mlb_normalize_team(away["team"]["displayName"])
            hScore=int(home.get("score",0)); aScore=int(away.get("score",0))
            winner=hName if hScore>aScore else aName
            row=await conn.fetchrow(
                "SELECT id,predicted_winner,bet_type,spread_line FROM predictions_mlb WHERE game_date=$1 AND home_team=$2 AND away_team=$3",
                yesterday,hName,aName)
            if row:
                bt=row["bet_type"] or ""; sl=row["spread_line"]
                if "讓分" in bt and sl is not None:   result=(hScore+sl)>aScore
                elif "吃分" in bt and sl is not None: result=(aScore-sl)>hScore
                else: result=row["predicted_winner"]==winner
                await conn.execute(
                    "UPDATE predictions_mlb SET actual_winner=$1,actual_home_score=$2,actual_away_score=$3,result=$4 WHERE id=$5",
                    winner,hScore,aScore,result,row["id"])
                updated+=1
        await conn.close()
        print(f"✅ MLB 更新 {updated} 場結果")
        return {"status":"ok","updated":updated}
    except Exception as e:
        return {"status":"error","message":str(e)}

# ════ MLB API 路由（全部用 /api/mlb/ 前綴，不與 NBA 衝突）════

@app.get("/api/mlb/")
async def mlb_root():
    return {"status":"ok","message":"MLB 預測模組運作中"}

@app.get("/api/mlb/stats")
async def mlb_stats():
    if not DB_URL: return {"today":{"rate":0,"wins":0,"total":0},"week":{"rate":0,"wins":0,"total":0},"month":{"rate":0,"wins":0,"total":0},"high_conf":{"rate":0,"wins":0,"total":0}}
    conn=await get_db()
    def wr(r):
        if not r or not r["total"]: return {"rate":0,"wins":0,"total":0}
        return {"rate":round((r["wins"] or 0)/r["total"]*100),"wins":int(r["wins"] or 0),"total":r["total"]}
    td=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions_mlb WHERE game_date=CURRENT_DATE AND result IS NOT NULL")
    wk=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions_mlb WHERE game_date>=CURRENT_DATE-interval '7 days' AND result IS NOT NULL")
    mn=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions_mlb WHERE game_date>=CURRENT_DATE-interval '30 days' AND result IS NOT NULL")
    hc=await conn.fetchrow("SELECT COUNT(*) as total,SUM(CASE WHEN result THEN 1 ELSE 0 END) as wins FROM predictions_mlb WHERE confidence>=70 AND result IS NOT NULL")
    await conn.close()
    return {"today":wr(td),"week":wr(wk),"month":wr(mn),"high_conf":wr(hc)}

@app.get("/api/mlb/predictions/today")
async def mlb_today():
    if not DB_URL: return []
    conn=await get_db()
    rows=await conn.fetch("SELECT * FROM predictions_mlb WHERE game_date=$1 ORDER BY confidence DESC",date.today())
    await conn.close(); return [dict(r) for r in rows]

@app.get("/api/mlb/predictions/history")
async def mlb_history(days:int=90):
    if not DB_URL: return []
    conn=await get_db()
    try:
        rows=await conn.fetch("""
            SELECT * FROM predictions_mlb
            WHERE result IS NOT NULL
            AND game_date >= CURRENT_DATE - ($1 * INTERVAL '1 day')
            ORDER BY game_date DESC, confidence DESC
        """, days)
        await conn.close(); return [dict(r) for r in rows]
    except Exception as e:
        await conn.close(); return []

@app.get("/api/mlb/polymarket")
async def mlb_polymarket():
    return await fetch_mlb_polymarket()

@app.get("/api/mlb/injuries")
async def mlb_injuries():
    return await fetch_mlb_injuries()

@app.get("/api/mlb/b2b")
async def mlb_b2b():
    return await fetch_mlb_b2b()

@app.get("/api/mlb/team-data")
async def mlb_team_data():
    result={}
    for name,d in MLB_TEAM_DATA.items():
        abbr=d.get("abbr","")
        if not abbr: continue
        result[abbr]={"elo":d.get("elo",1500),"runs":d.get("runs",4.3),"opp":d.get("opp",4.3),"recent_adj":d.get("recent_adj",0)}
    return {"status":"ok","data":result}

@app.post("/api/mlb/trigger/predict")
async def mlb_trigger_predict():
    return await fetch_and_predict_mlb() or {"status":"ok"}

@app.post("/api/mlb/trigger/results")
async def mlb_trigger_results():
    return await update_results_mlb() or {"status":"ok"}

@app.post("/api/mlb/trigger/stats")
async def mlb_trigger_stats():
    return await fetch_mlb_stats()

# ── MLB Startup（追加，不覆蓋 NBA startup）
@app.on_event("startup")
async def startup_mlb():
    await init_db_mlb()
    # APScheduler 允許在 start() 後繼續 add_job
    scheduler.add_job(fetch_and_predict_mlb, "cron", hour=8,  minute=5)
    scheduler.add_job(fetch_and_predict_mlb, "cron", hour=15, minute=5)
    scheduler.add_job(update_results_mlb,    "cron", hour=14, minute=10)
    scheduler.add_job(fetch_mlb_stats,       "cron", minute=5)
    scheduler.add_job(fetch_mlb_injuries,    "cron", minute=20)
    scheduler.add_job(fetch_mlb_b2b,         "cron", minute=35)
    await fetch_mlb_stats()
    print("✅ MLB 模組啟動完成")
