import streamlit as st
import pandas as pd
import requests
import mplfinance as mpf
from datetime import datetime, timedelta

# ════════════════════════════════════════════════
# 設定區（填入你的 Token）
# ════════════════════════════════════════════════
API_TOKEN  = "填你的FinMind Token"
LINE_TOKEN = "填你的LINE Notify Token"   # 沒有可留空

st.set_page_config(page_title="台股職業交易系統", layout="wide")
st.title("🔥 台股職業交易選股系統")
st.caption("基本面 × 籌碼面 × 技術面 × 自動決策")

# ════════════════════════════════════════════════
# API 工具
# ════════════════════════════════════════════════
def get_data(dataset, params):
    url = "https://api.finmindtrade.com/api/v4/data"
    params["token"] = API_TOKEN
    params["dataset"] = dataset
    try:
        res = requests.get(url, params=params, timeout=10).json()
        if "data" not in res or not res["data"]:
            return pd.DataFrame()
        return pd.DataFrame(res["data"])
    except:
        return pd.DataFrame()

# ════════════════════════════════════════════════
# 🌍 大盤儀表板（台股 + 美股）
# ════════════════════════════════════════════════
def get_us_market():
    """抓美股指數（Yahoo Finance 非官方 API，免費無需登入）"""
    symbols = {
        "^NDX":  "那斯達克100",
        "^GSPC": "S&P 500",
        "^DJI":  "道瓊工業",
    }
    results = {}
    for sym, name in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8).json()
            closes = res["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                px   = closes[-1]
                prev = closes[-2]
                chg  = px - prev
                pct  = chg / prev * 100
                results[name] = {"px": px, "chg": chg, "pct": pct}
        except:
            results[name] = None
    return results

def get_tw_index():
    """抓台股加權指數近期資料"""
    try:
        df = get_data("TaiwanStockPrice", {
            "data_id": "TAIEX",
            "start_date": (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        })
        if df.empty:
            return None
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["open"]  = pd.to_numeric(df["open"],  errors="coerce")
        if len(df) >= 2:
            px   = df["close"].iloc[-1]
            prev = df["close"].iloc[-2]
            chg  = px - prev
            pct  = chg / prev * 100
            ma5  = df["close"].tail(5).mean()
            ma20 = df["close"].tail(20).mean()
            return {"px": px, "chg": chg, "pct": pct, "ma5": ma5, "ma20": ma20, "df": df}
    except:
        return None

def render_market_dashboard():
    st.subheader("🌍 大盤即時監控")

    col_tw, col_nd, col_sp, col_dj = st.columns(4)

    # 台股加權
    tw = get_tw_index()
    with col_tw:
        if tw:
            direction = "up" if tw["chg"] >= 0 else "down"
            st.metric(
                label="🇹🇼 台股加權指數",
                value=f"{tw['px']:,.0f}",
                delta=f"{tw['chg']:+.0f} ({tw['pct']:+.2f}%)"
            )
            trend = "✅ 多頭" if tw["ma5"] > tw["ma20"] else "⚠️ 空頭"
            st.caption(f"MA5={tw['ma5']:,.0f}　MA20={tw['ma20']:,.0f}　{trend}")
        else:
            st.metric("🇹🇼 台股加權指數", "讀取中...", "")

    # 美股三大指數
    us = get_us_market()
    us_icons = {"那斯達克100": "🇺🇸 那斯達克100", "S&P 500": "📊 S&P 500", "道瓊工業": "🏭 道瓊工業"}
    for col, (name, icon) in zip([col_nd, col_sp, col_dj], us_icons.items()):
        with col:
            data = us.get(name)
            if data:
                st.metric(
                    label=icon,
                    value=f"{data['px']:,.2f}",
                    delta=f"{data['chg']:+.2f} ({data['pct']:+.2f}%)"
                )
            else:
                st.metric(icon, "讀取中...", "")

    # 大盤走勢圖
    if tw and len(tw["df"]) >= 10:
        with st.expander("📈 台股加權指數走勢（近30日）", expanded=True):
            df_plot = tw["df"].copy().tail(30)
            df_plot.index = pd.to_datetime(df_plot["date"])
            df_plot["high"]   = pd.to_numeric(df_plot.get("high",   df_plot["close"]), errors="coerce")
            df_plot["low"]    = pd.to_numeric(df_plot.get("low",    df_plot["close"]), errors="coerce")
            df_plot["open"]   = pd.to_numeric(df_plot["open"],  errors="coerce")
            df_plot["close"]  = pd.to_numeric(df_plot["close"], errors="coerce")
            df_plot = df_plot[["open","high","low","close"]].dropna()
            df_plot.columns = ["Open","High","Low","Close"]
            try:
                fig, _ = mpf.plot(
                    df_plot, type="line", style="charles",
                    mav=(5, 20), returnfig=True, figsize=(12, 3),
                    title="台股加權指數"
                )
                st.pyplot(fig)
                st.caption("藍線 = MA5　橘線 = MA20")
            except:
                st.line_chart(df_plot["Close"])

    # 那斯達克 vs 台股相關性說明
    with st.expander("💡 那斯達克與台股關係"):
        nd = us.get("那斯達克100")
        if nd:
            nd_signal = "📈 那斯達克上漲" if nd["pct"] >= 0 else "📉 那斯達克下跌"
            tw_impact = "台股電子股今日偏多" if nd["pct"] >= 0 else "台股電子股今日偏空，注意開盤壓力"
            st.info(f"{nd_signal} {nd['pct']:+.2f}%　→　{tw_impact}")
        st.markdown("""
        **那斯達克與台股關聯度極高（相關係數約 0.7～0.85）**
        - 那斯達克大漲 → 台積電、聯發科等科技股通常跟漲
        - 那斯達克大跌 > 2% → 台股隔日開盤通常承壓
        - 美股收盤後看那斯達克期貨，可預判隔日台股開盤方向
        """)

    st.markdown("---")

# ════════════════════════════════════════════════
# LINE 通知
# ════════════════════════════════════════════════
def send_line(msg):
    if not LINE_TOKEN or LINE_TOKEN == "填你的LINE Notify Token":
        return
    try:
        requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {LINE_TOKEN}"},
            data={"message": msg},
            timeout=5
        )
    except:
        pass

# ════════════════════════════════════════════════
# 大盤強弱判斷（過濾大盤弱勢）
# ════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def check_market_ok():
    """
    抓加權指數近20日，判斷大盤是否適合做多
    條件：5日均線 > 20日均線 → 大盤偏多
    """
    try:
        idx = get_data("TaiwanStockPrice", {
            "data_id": "TAIEX",
            "start_date": (datetime.today() - timedelta(days=60)).strftime("%Y-%m-%d")
        })
        if len(idx) < 20:
            return True  # 無法判斷時預設通過
        idx["close"] = pd.to_numeric(idx["close"], errors="coerce")
        ma5  = idx["close"].tail(5).mean()
        ma20 = idx["close"].tail(20).mean()
        return ma5 > ma20
    except:
        return True

# ════════════════════════════════════════════════
# 🔷 1️⃣ 基本面評分（0～3分，權重 30%）
# ════════════════════════════════════════════════
def score_fundamental(stock_id):
    score = 0
    detail = []

    # 營收動能（近3月 > 前3月）
    rev = get_data("TaiwanStockMonthRevenue", {
        "data_id": stock_id,
        "start_date": "2023-01-01"
    })
    if len(rev) >= 6:
        rev["revenue"] = pd.to_numeric(rev["revenue"], errors="coerce")
        r3 = rev.tail(3)["revenue"].mean()
        r6 = rev.tail(6).head(3)["revenue"].mean()
        yoy = rev.tail(1)["revenue"].values[0]
        prev_yr = rev.iloc[-13]["revenue"] if len(rev) >= 13 else 0
        if r3 > r6:
            score += 1
            detail.append("✅ 營收近3月創高")
        else:
            detail.append("❌ 營收未創高")
        if prev_yr > 0 and yoy > prev_yr:
            score += 0.5
            detail.append("✅ 營收年增")

    # EPS + ROE（用股利/財報資料替代）
    fin = get_data("TaiwanStockFinancialStatements", {
        "data_id": stock_id,
        "start_date": "2023-01-01"
    })
    if not fin.empty and "value" in fin.columns:
        try:
            roe_row = fin[fin["type"] == "ReturnOnEquity"]
            if not roe_row.empty:
                roe = pd.to_numeric(roe_row["value"].iloc[-1], errors="coerce")
                if roe and roe > 15:
                    score += 1
                    detail.append(f"✅ ROE {roe:.1f}% > 15%")
                else:
                    detail.append(f"❌ ROE {roe:.1f}% 偏低")
        except:
            pass

    score = min(3, round(score))
    return score, detail

# ════════════════════════════════════════════════
# 🔷 2️⃣ 籌碼面評分（0～4分，權重 40%）🔥核心
# ════════════════════════════════════════════════
def score_chip(stock_id):
    score = 0
    detail = []
    start = (datetime.today() - timedelta(days=20)).strftime("%Y-%m-%d")

    # 外資 + 投信連買
    inst = get_data("TaiwanStockInstitutionalInvestorsBuySell", {
        "data_id": stock_id,
        "start_date": start
    })
    if len(inst) >= 5:
        inst["buy"]  = pd.to_numeric(inst["buy"],  errors="coerce").fillna(0)
        inst["sell"] = pd.to_numeric(inst["sell"], errors="coerce").fillna(0)
        net = inst["buy"] - inst["sell"]
        buy_days = (net > 0).tail(5).sum()
        total_net = net.tail(5).sum()

        if buy_days >= 5:
            score += 2
            detail.append(f"✅ 法人連買{buy_days}天 淨買{int(total_net):,}")
        elif buy_days >= 3:
            score += 1
            detail.append(f"⚠️ 法人買超{buy_days}天")
        else:
            detail.append(f"❌ 法人僅買{buy_days}天")

        # 主力大單吸收（近3日淨買 > 1000張）
        net3 = net.tail(3).sum()
        if net3 > 1000:
            score += 1
            detail.append(f"✅ 主力近3日淨買 {int(net3):,}張")
        else:
            detail.append(f"❌ 主力近3日淨買 {int(net3):,}張")

    # 券資比（軋空潛力）
    margin = get_data("TaiwanStockMarginPurchaseShortSale", {
        "data_id": stock_id,
        "start_date": "2024-01-01"
    })
    if not margin.empty:
        try:
            last = margin.iloc[-1]
            short  = pd.to_numeric(last["ShortSaleTodayBalance"],    errors="coerce") or 0
            margin_buy = pd.to_numeric(last["MarginPurchaseTodayBalance"], errors="coerce") or 1
            ratio = short / margin_buy
            if ratio > 0.3:
                score += 1
                detail.append(f"✅ 券資比 {ratio:.2f}（軋空潛力高）")
            elif ratio > 0.15:
                detail.append(f"⚠️ 券資比 {ratio:.2f}（普通）")
            else:
                detail.append(f"❌ 券資比 {ratio:.2f}（偏低）")
        except:
            pass

    score = min(4, score)
    return score, detail

# ════════════════════════════════════════════════
# 🔷 3️⃣ 技術面評分（0～3分，權重 30%）
# ════════════════════════════════════════════════
def score_technical(stock_id):
    score = 0
    detail = []
    mode = "觀望"  # 進場模式

    price = get_data("TaiwanStockPrice", {
        "data_id": stock_id,
        "start_date": "2024-01-01"
    })

    if len(price) < 30:
        return 0, ["❌ 資料不足"], price, mode

    price["close"]           = pd.to_numeric(price["close"],           errors="coerce")
    price["open"]            = pd.to_numeric(price["open"],            errors="coerce")
    price["high"]            = pd.to_numeric(price["high"],            errors="coerce")
    price["low"]             = pd.to_numeric(price["low"],             errors="coerce")
    price["Trading_Volume"]  = pd.to_numeric(price["Trading_Volume"],  errors="coerce")

    ma5  = price["close"].tail(5).mean()
    ma20 = price["close"].tail(20).mean()
    last_close = price["close"].iloc[-1]
    high_20    = price["close"].tail(20).max()
    low_5      = price["close"].tail(5).min()

    # 均線多頭
    if ma5 > ma20:
        score += 1
        detail.append("✅ 均線多頭（MA5 > MA20）")
    else:
        detail.append("❌ 均線空頭")

    # 突破前高（模式A）
    if last_close >= high_20 * 0.995:
        score += 2
        detail.append("✅ 突破20日前高 → 模式A：突破買")
        mode = "突破買"
    # 回檔不破（模式B）
    elif last_close > low_5 * 1.01 and last_close < ma5 * 1.02:
        score += 1
        detail.append("✅ 回檔量縮不破 → 模式B：回檔買")
        mode = "回檔買"
    else:
        detail.append("❌ 無明顯買點型態")

    # 量能爆發
    v_recent = price["Trading_Volume"].tail(3).mean()
    v_old    = price["Trading_Volume"].tail(10).head(5).mean()
    if v_old > 0 and v_recent > v_old * 1.5:
        score += 1
        detail.append(f"✅ 量能爆發 {v_recent/v_old:.1f}倍")
    else:
        detail.append("❌ 量能未明顯放大")

    score = min(3, score)
    return score, detail, price, mode

# ════════════════════════════════════════════════
# 💰 進出場決策系統
# ════════════════════════════════════════════════
def calc_trade(price, mode):
    last  = price.iloc[-1]
    close = last["close"]
    ma5   = price["close"].tail(5).mean()
    low5  = price["close"].tail(5).min()
    high20 = price["close"].tail(20).max()

    if mode == "突破買":
        entry  = round(high20 * 1.005, 1)   # 突破前高 0.5% 確認
        stop   = round(entry * 0.95,   1)   # 停損 -5%
    else:  # 回檔買 / 觀望
        entry  = round(ma5,            1)   # 5日線附近進場
        stop   = round(low5 * 0.98,    1)   # 跌破近5日低點

    target1 = round(entry * 1.10, 1)        # 目標① +10%
    target2 = round(entry * 1.15, 1)        # 目標② +15%
    risk    = entry - stop
    reward  = target2 - entry
    rr      = round(reward / risk, 1) if risk > 0 else 0

    return entry, stop, target1, target2, rr

# ════════════════════════════════════════════════
# K線圖（標示買點/支撐/壓力）
# ════════════════════════════════════════════════
def draw_kline(price, entry, stop, target, stock_id, name):
    try:
        df = price.copy().tail(60)
        df.index = pd.to_datetime(df["date"])
        df = df[["open","high","low","close","Trading_Volume"]].apply(pd.to_numeric, errors="coerce")
        df.columns = ["Open","High","Low","Close","Volume"]
        df = df.dropna()

        hlines = dict(
            hlines=[entry, stop, target],
            colors=["#00c896","#ff4d6d","#f0b429"],
            linestyle="--",
            linewidths=1
        )

        fig, axes = mpf.plot(
            df,
            type="candle",
            style="charles",
            mav=(5, 20),
            volume=True,
            returnfig=True,
            figsize=(10, 6),
            title=f"{stock_id} {name}",
            hlines=hlines
        )
        return fig
    except Exception as e:
        return None

# ════════════════════════════════════════════════
# 主程式
# ════════════════════════════════════════════════

# ── 大盤儀表板（第一個顯示）──
render_market_dashboard()

# 側邊欄設定
with st.sidebar:
    st.header("⚙️ 篩選設定")
    min_score = st.slider("最低總分門檻", 4, 10, 8)
    min_rr    = st.slider("最低風險報酬比", 1.0, 4.0, 2.0, 0.5)
    check_market = st.checkbox("啟用大盤過濾（大盤弱不出訊號）", value=True)
    use_fund  = st.checkbox("啟用基本面評分", value=True)
    use_chip  = st.checkbox("啟用籌碼面評分", value=True)
    use_tech  = st.checkbox("啟用技術面評分", value=True)
    send_line_notify = st.checkbox("選股完成後傳 LINE", value=False)

    st.markdown("---")
    st.markdown("**分數組成**")
    st.markdown("- 基本面：0～3分（權重30%）")
    st.markdown("- 籌碼面：0～4分（權重40%）")
    st.markdown("- 技術面：0～3分（權重30%）")
    st.markdown("- **總分：0～10分**")

# 大盤過濾
if check_market:
    market_ok = check_market_ok()
    if not market_ok:
        st.error("⚠️ 大盤目前偏空（MA5 < MA20），系統建議今日不出訊號！")
        st.info("💡 若仍想查看個股，請關閉左側「啟用大盤過濾」")
        st.stop()
    else:
        st.success("✅ 大盤偏多，可以正常選股")

if st.button("🚀 開始選股", type="primary"):
    stock_list = get_data("TaiwanStockInfo", {})
    if stock_list.empty:
        st.error("❌ 無法取得股票清單，請確認 FinMind Token")
        st.stop()

    results = []
    total   = len(stock_list)
    prog    = st.progress(0)
    status  = st.empty()

    for i, (_, row) in enumerate(stock_list.iterrows()):
        sid  = str(row.get("stock_id","")).strip()
        name = str(row.get("stock_name","")).strip()

        prog.progress((i+1)/total)
        status.text(f"分析中 {sid} {name}（{i+1}/{total}）")

        # 技術面（必須）
        tech_s, tech_d, price, mode = score_technical(sid)
        if price.empty:
            continue

        # 基本面
        fund_s, fund_d = score_fundamental(sid) if use_fund else (0, [])

        # 籌碼面
        chip_s, chip_d = score_chip(sid) if use_chip else (0, [])

        total_score = (fund_s if use_fund else 0) + \
                      (chip_s if use_chip else 0) + \
                      (tech_s if use_tech else 0)

        if total_score < min_score:
            continue

        # 進出場計算
        entry, stop, target1, target2, rr = calc_trade(price, mode)

        # 風險報酬過濾
        if rr < min_rr:
            continue

        results.append({
            "sid": sid, "name": name,
            "total": total_score,
            "fund": fund_s, "chip": chip_s, "tech": tech_s,
            "mode": mode,
            "entry": entry, "stop": stop,
            "target1": target1, "target2": target2, "rr": rr,
            "fund_d": fund_d, "chip_d": chip_d, "tech_d": tech_d,
            "price": price
        })

    prog.empty(); status.empty()

    if not results:
        st.warning("😔 今日沒有符合條件的股票，明天再試！")
    else:
        results.sort(key=lambda x: x["total"], reverse=True)
        st.success(f"🔥 找到 {len(results)} 檔高品質交易機會！")

        # 顯示結果
        for r in results:
            with st.expander(f"{'🔥' if r['total']>=9 else '📈'} {r['sid']} {r['name']}　⭐{r['total']}/10　型態：{r['mode']}", expanded=(r['total']>=9)):

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("基本面", f"{r['fund']}/3")
                with col2:
                    st.metric("籌碼面", f"{r['chip']}/4")
                with col3:
                    st.metric("技術面", f"{r['tech']}/3")

                st.markdown("---")

                # 決策框
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"""
                    **💰 操作建議（{r['mode']}）**

                    | 項目 | 價格 |
                    |------|------|
                    | 🟢 進場價 | **{r['entry']}** |
                    | 🔴 停損價 | **{r['stop']}** |
                    | 🎯 目標① | **{r['target1']}** (+10%) |
                    | 🏆 目標② | **{r['target2']}** (+15%) |
                    | ⚖️ 風險報酬 | **1 : {r['rr']}** |
                    """)
                with col_b:
                    st.markdown("**📋 條件明細**")
                    for d in r["fund_d"] + r["chip_d"] + r["tech_d"]:
                        st.write(d)

                # K線圖
                fig = draw_kline(r["price"], r["entry"], r["stop"], r["target2"], r["sid"], r["name"])
                if fig:
                    st.pyplot(fig)
                    st.caption("🟢 綠線：進場點　🔴 紅線：停損　🟡 黃線：目標")

        # LINE 通知
        if send_line_notify and results:
            msg = "\n🔥 今日台股交易訊號\n\n"
            for r in results[:5]:
                msg += (
                    f"【{r['sid']} {r['name']}】 ⭐{r['total']}/10\n"
                    f"型態：{r['mode']}\n"
                    f"進場：{r['entry']}　停損：{r['stop']}\n"
                    f"目標①：{r['target1']}　目標②：{r['target2']}\n"
                    f"風險報酬：1:{r['rr']}\n\n"
                )
            send_line(msg)
            st.info("✅ LINE 通知已傳送")

# ════════════════════════════════════════════════
# 使用說明
# ════════════════════════════════════════════════
with st.expander("📖 系統使用說明"):
    st.markdown("""
    ### 評分系統
    - **基本面（0-3分）**：營收創高、年增、ROE > 15%
    - **籌碼面（0-4分）**：法人連買、主力大單、券資比（軋空）
    - **技術面（0-3分）**：均線多頭、突破/回檔型態、量能爆發

    ### 進場模式
    - **突破買**：收盤突破20日前高，量能放大，追強勢股
    - **回檔買**：回測5日線量縮不破，職業交易員最愛，勝率更高

    ### 停損停利規則
    - 停損：進場價 -5%（或跌破近期低點）
    - 目標①：進場價 +10%（出一半）
    - 目標②：進場價 +15%（出剩餘）
    - 移動停利：獲利後跌破5日線 → 全出

    ### 大盤過濾
    - 大盤 MA5 < MA20 時，系統自動停止出訊號
    - 即使個股再強，順勢而為最重要

    ### 風險報酬
    - 設定 ≥ 1:2 才進場，確保長期正期望值
    """)
