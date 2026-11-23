import os
import json
from datetime import datetime
import pandas as pd
import streamlit as st
from collections import Counter, defaultdict

# ================================================================
# HANOI AI PROFESSIONAL v2.0
# Dynamic Backtest + Formula Accuracy + Weighted Prediction
# ================================================================

CSV_FILE = "history_hanoi.csv"
DAILY_CONFIG_FILE = "daily_numbers.json"
MIN_HISTORY_FOR_DYNAMIC_WEIGHT = 10
RECENT_WINDOW = 30

# ชุดเลขประจำวันตั้งต้นจากไฟล์เดิม
DEFAULT_DAILY_NUMBERS = {
    "Monday": "921468",
    "Tuesday": "124670",
    "Wednesday": "456139",
    "Thursday": "546013",
    "Friday": "978563",
    "Saturday": "823107",
    "Sunday": "234809",
}

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAILY_MODES = ["Manual", "Hybrid", "Dynamic"]

def load_daily_config():
    """โหลดเลขประจำวันและโหมดจาก JSON; หากไม่มีไฟล์ให้ใช้ค่าเริ่มต้น"""
    config = {"mode": "Hybrid", "numbers": DEFAULT_DAILY_NUMBERS.copy()}
    if os.path.exists(DAILY_CONFIG_FILE):
        try:
            with open(DAILY_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config["mode"] = saved.get("mode", "Hybrid")
            if config["mode"] not in DAILY_MODES:
                config["mode"] = "Hybrid"
            saved_numbers = saved.get("numbers", {})
            for day in DAYS_ORDER:
                value = str(saved_numbers.get(day, config["numbers"][day])).strip()
                if value.isdigit() and len(value) == 6:
                    config["numbers"][day] = value
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return config

def save_daily_config(config):
    """บันทึกเลขประจำวันเป็น JSON โดยเก็บเลขเป็นข้อความเพื่อรักษาเลข 0 นำหน้า"""
    payload = {"mode": config.get("mode", "Hybrid"), "numbers": config.get("numbers", {})}
    with open(DAILY_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

DAILY_CONFIG = load_daily_config()

FORMULAS = [
    "Carry Over",
    "±1",
    "Sum Modulo",
    "Cross Sum",
    "Daily 6-Digit",
    "Rotation",
    "Mirror",
    "Shift +2",
    "Double",
    "Sandwich",
]


def zfill_num(value, width):
    try:
        if pd.isna(value):
            return "0" * width
        s = str(value).strip()
        if "." in s:
            s = s.split(".")[0]
        return s.zfill(width)[-width:]
    except Exception:
        return "0" * width


def parse_thai_date(x):
    """แปลง DD/MM/YYYY พ.ศ. เป็น Timestamp ค.ศ. แบบปลอดภัย"""
    try:
        parts = str(x).strip().split("/")
        if len(parts) != 3:
            return pd.NaT
        day, month, year = map(int, parts)
        if year < 100:
            year += 2500
        if year >= 2400:
            year -= 543
        return pd.Timestamp(year=year, month=month, day=day)
    except Exception:
        return pd.NaT


def initialize_csv():
    if not os.path.exists(CSV_FILE):
        initial_data = [
            ["30/09/2569", "95242", "82585", "242", "85"],
            ["29/09/2569", "05651", "08389", "651", "89"],
            ["28/09/2569", "77115", "86908", "115", "08"],
        ]
        pd.DataFrame(initial_data, columns=[
            "date", "special", "first_prize", "top_3", "bottom_2"
        ]).to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
        print(f"สร้าง {CSV_FILE} เริ่มต้นแล้ว")


def normalize_history(df):
    """Normalize text fields and sort chronologically (oldest -> newest)."""
    out = df.copy()
    required = ["date", "special", "first_prize", "top_3", "bottom_2"]
    for col in required:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str).str.strip()

    # Keep leading zeros and fixed digit widths in every prize field.
    for col in ("special", "first_prize"):
        out[col] = out[col].apply(lambda x: zfill_num(x, 5) if x else "")
    out["top_3"] = out["top_3"].apply(lambda x: zfill_num(x, 3) if x else "000")
    out["bottom_2"] = out["bottom_2"].apply(lambda x: zfill_num(x, 2) if x else "00")

    out["dt"] = out["date"].apply(parse_thai_date)
    out = out.dropna(subset=["dt"]).copy()
    out["weekday_en"] = out["dt"].dt.day_name()
    out = out.sort_values("dt", ascending=True, kind="stable").reset_index(drop=True)
    return out


def load_history():
    if not os.path.exists(CSV_FILE):
        initialize_csv()
    df = pd.read_csv(CSV_FILE, dtype=str, keep_default_na=False)
    return normalize_history(df)


def save_history(df):
    out = normalize_history(df)
    out = out[["date", "special", "first_prize", "top_3", "bottom_2"]]
    out.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")


def get_transformations(top_3_str, bottom_2_str="00"):
    t3 = zfill_num(top_3_str, 3)
    b2 = zfill_num(bottom_2_str, 2)
    a, b, c = [int(x) for x in t3]
    d, e = [int(x) for x in b2]

    digits = [a, b, c, d, e]
    carry = {str(x) for x in digits}
    pm1 = {str((x + delta) % 10) for x in digits for delta in (-1, 1)}

    sum_t3 = (a + b + c) % 10
    sum_b2 = (d + e) % 10
    sum_total = (sum_t3 + sum_b2) % 10
    sum_formulas = {str(sum_t3), str(sum_b2), str(sum_total)}

    cross_formulas = {
        str((b + e) % 10),
        str((c + d) % 10),
        str((a + d) % 10),
        str((a + e) % 10),
    }

    rotations = {t3[1:] + t3[0], t3[2] + t3[:2]}
    mirror_map = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9,
                  5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
    mirror = "".join(str(mirror_map[int(x)]) for x in t3)
    shifted = "".join(str((int(x) + 2) % 10) for x in t3)
    doubles = {x * 2 for x in t3}
    sandwiches = {a_str + b_str + a_str
                  for a_str in t3 for b_str in t3 if a_str != b_str}

    return {
        "carry_over": carry,
        "pm1": pm1,
        "sum_formulas": sum_formulas,
        "cross_formulas": cross_formulas,
        "rotations": rotations,
        "mirror": mirror,
        "shifted": shifted,
        "doubles": doubles,
        "sandwiches": sandwiches,
    }


def calculate_dynamic_daily(day, history=None, manual_base=None):
    """คำนวณ Daily Number จาก History โดยไม่แก้ไขค่า Manual ที่บันทึกไว้."""
    base = manual_base or DEFAULT_DAILY_NUMBERS.get(day, "000000")
    if history is None or len(history) < MIN_HISTORY_FOR_DYNAMIC_WEIGHT:
        return base

    recent = history.tail(min(RECENT_WINDOW, len(history)))
    freq = Counter()
    for _, row in recent.iterrows():
        freq.update(str(row["top_3"]))
        freq.update(str(row["bottom_2"]))

    score = {str(i): float(freq[str(i)]) for i in range(10)}
    for digit in base:
        score[digit] += 1.5
    ordered = sorted(score, key=lambda digit: (-score[digit], digit))
    return "".join(ordered[:6])

def daily_number_for_day(day, history=None):
    """คืนค่า Daily Number ตามโหมด Manual / Hybrid / Dynamic ที่ผู้ใช้บันทึกไว้."""
    manual = DAILY_CONFIG.get("numbers", DEFAULT_DAILY_NUMBERS).get(
        day, DEFAULT_DAILY_NUMBERS.get(day, "000000")
    )
    mode = DAILY_CONFIG.get("mode", "Hybrid")
    dynamic = calculate_dynamic_daily(day, history, manual)

    if mode == "Dynamic":
        return dynamic
    if mode == "Hybrid":
        # ให้เลข Manual มาก่อน แล้วเติมเลขที่ไม่ซ้ำจาก Dynamic จนครบ 6 ตัว
        merged = list(dict.fromkeys(manual))
        for digit in dynamic:
            if digit not in merged:
                merged.append(digit)
            if len(merged) == 6:
                break
        return "".join(merged[:6]).ljust(6, "0")
    return manual


def formula_candidates(base_t3, base_b2, next_day, history=None):
    trans = get_transformations(base_t3, base_b2)
    daily = daily_number_for_day(next_day, history)

    candidates = defaultdict(set)
    candidates["Carry Over"].update(trans["carry_over"])
    candidates["±1"].update(trans["pm1"])
    candidates["Sum Modulo"].update(trans["sum_formulas"])
    candidates["Cross Sum"].update(trans["cross_formulas"])
    candidates["Daily 6-Digit"].update(daily)
    candidates["Rotation"].update(set("".join(trans["rotations"])))
    candidates["Mirror"].update(trans["mirror"])
    candidates["Shift +2"].update(trans["shifted"])
    candidates["Double"].update(set("".join(trans["doubles"])))
    candidates["Sandwich"].update(set("".join(trans["sandwiches"])))
    return candidates, daily, trans


def evaluate_formula(formula, trans, daily, actual_t3, actual_b2):
    """วัด Hit แบบละเอียด ไม่ใช้กฎ 'มีเลข 1 ตัวก็ Hit'."""
    t3 = zfill_num(actual_t3, 3)
    b2 = zfill_num(actual_b2, 2)

    if formula == "Carry Over":
        digits = trans["carry_over"]
        return int(any(d in t3 for d in digits)), int(any(d in b2 for d in digits))
    if formula == "±1":
        digits = trans["pm1"]
        return int(any(d in t3 for d in digits)), int(any(d in b2 for d in digits))
    if formula == "Sum Modulo":
        digits = trans["sum_formulas"]
        return int(any(d in t3 for d in digits)), int(any(d in b2 for d in digits))
    if formula == "Cross Sum":
        digits = trans["cross_formulas"]
        return int(any(d in t3 for d in digits)), int(any(d in b2 for d in digits))
    if formula == "Daily 6-Digit":
        return int(any(d in t3 for d in daily)), int(any(d in b2 for d in daily))
    if formula == "Rotation":
        rots = trans["rotations"]
        return int(any(r == t3 for r in rots)), int(any(set(b2).issubset(set(r)) for r in rots))
    if formula == "Mirror":
        return int(any(d in t3 for d in trans["mirror"])), int(any(d in b2 for d in trans["mirror"]))
    if formula == "Shift +2":
        return int(any(d in t3 for d in trans["shifted"])), int(any(d in b2 for d in trans["shifted"]))
    if formula == "Double":
        return int(any(t3[i] == t3[i + 1] for i in range(2))), int(b2[0] == b2[1])
    if formula == "Sandwich":
        return int(t3[0] == t3[2] or t3[0] == t3[1] or t3[1] == t3[2]), 0
    return 0, 0


def exact_pattern_score(formula, trans, daily, actual_t3, actual_b2):
    """คะแนนเสริม 0-1 สำหรับความตรงของ pattern/ตำแหน่ง."""
    t3 = zfill_num(actual_t3, 3)
    b2 = zfill_num(actual_b2, 2)

    if formula == "Rotation":
        if t3 in trans["rotations"]:
            return 1.0, 1.0
    if formula == "Mirror":
        return float(t3 == trans["mirror"]), float(b2 == trans["mirror"][-2:])
    if formula == "Shift +2":
        return float(t3 == trans["shifted"]), float(b2 == trans["shifted"][-2:])
    if formula == "Daily 6-Digit":
        # วัดจำนวน digit ที่อยู่ใน Daily / 3 และ / 2
        return len(set(t3) & set(daily)) / 3.0, len(set(b2) & set(daily)) / 2.0
    return 0.0, 0.0


def backtest_dataframe(df):
    if len(df) < 2:
        return pd.DataFrame()

    rows = []
    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        actual = df.iloc[i]
        day = actual["weekday_en"]
        daily = daily_number_for_day(day, df.iloc[:i])
        trans = get_transformations(prev["top_3"], prev["bottom_2"])

        for formula in FORMULAS:
            hit3, hit2 = evaluate_formula(formula, trans, daily,
                                          actual["top_3"], actual["bottom_2"])
            exact3, exact2 = exact_pattern_score(formula, trans, daily,
                                                 actual["top_3"], actual["bottom_2"])
            rows.append({
                "date": actual["date"],
                "weekday": day,
                "formula": formula,
                "hit_3d": hit3,
                "hit_2d": hit2,
                "exact_3d": exact3,
                "exact_2d": exact2,
            })
    return pd.DataFrame(rows)


def formula_ranking(df):
    bt = backtest_dataframe(df)
    if bt.empty:
        return pd.DataFrame()

    result = []
    total = bt.groupby("formula").size()
    for formula in FORMULAS:
        x = bt[bt["formula"] == formula]
        n = len(x)
        hit3 = x["hit_3d"].sum()
        hit2 = x["hit_2d"].sum()
        avg_exact3 = x["exact_3d"].mean()
        avg_exact2 = x["exact_2d"].mean()
        # Composite ใช้สำหรับจัดอันดับ ไม่ใช่โอกาสถูกรางวัลจริง
        composite = (
            0.40 * (hit3 / n) +
            0.35 * (hit2 / n) +
            0.15 * avg_exact3 +
            0.10 * avg_exact2
        ) * 100
        result.append({
            "Formula": formula,
            "N": n,
            "3D Hit%": round(hit3 / n * 100, 1),
            "2D Hit%": round(hit2 / n * 100, 1),
            "3D Exact%": round(avg_exact3 * 100, 1),
            "2D Exact%": round(avg_exact2 * 100, 1),
            "Composite": round(composite, 1),
        })
    return pd.DataFrame(result).sort_values("Composite", ascending=False).reset_index(drop=True)


def dynamic_weights(df):
    ranking = formula_ranking(df)
    if ranking.empty:
        return {f: 1.0 for f in FORMULAS}

    weights = {}
    for _, row in ranking.iterrows():
        # Base 1.0 + performance premium; จำกัดไม่ให้สูตรเดียวครองระบบ
        w = 0.5 + row["Composite"] / 50.0
        weights[row["Formula"]] = max(0.5, min(3.0, w))
    return weights


def digit_scores(df, next_day):
    if df.empty:
        return {str(i): 0.0 for i in range(10)}, {}, "000000"

    latest = df.loc[df["dt"].idxmax()]
    candidates, daily, trans = formula_candidates(
        latest["top_3"], latest["bottom_2"], next_day, df
    )
    weights = dynamic_weights(df)
    scores = {str(i): 0.0 for i in range(10)}

    for formula in FORMULAS:
        w = weights.get(formula, 1.0)
        for digit in candidates[formula]:
            scores[str(digit)] += w

    # Frequency ล่าสุดเป็นตัวช่วยเล็กน้อย ไม่ให้ history เก่าครองทั้งหมด
    recent = df.tail(min(20, len(df)))
    freq = Counter()
    for _, row in recent.iterrows():
        freq.update(row["top_3"])
        freq.update(row["bottom_2"])
    for d, n in freq.items():
        scores[d] += min(1.0, n / max(10, len(recent) * 3))

    return scores, weights, daily


def generate_prediction(df, next_day):
    if df.empty:
        return None

    latest = df.loc[df["dt"].idxmax()]
    scores, weights, daily = digit_scores(df, next_day)
    ordered = sorted(scores, key=lambda d: (-scores[d], d))
    den = ordered[0]
    rong = ordered[1:4]
    kan = ordered[4:7]

    # 2D เน้น + กลับ
    pairs = []
    for r in rong:
        pairs.extend([den + r, r + den])
    pairs = list(dict.fromkeys(pairs))

    # 3D AI แบบไม่กลับตำแหน่ง:
    # หลักที่ 1 = เลขเด่น, หลักที่ 2 = เลขรอง, หลักที่ 3 = เลขกัน
    # ตัวอย่าง 8 / 2-6-1 / 9-3-4 => 829, 823, 824, 869, ...
    triples = [den + r + k for r in rong for k in kan]
    triples = sorted(
        dict.fromkeys(triples),
        key=lambda x: -(scores[x[0]] + scores[x[1]] + scores[x[2]])
    )[:10]

    doubles = [d + d for d in ordered[:4]]
    sandwiches = [a + b + a for a in ordered[:4] for b in ordered[:4] if a != b]
    sandwiches = sandwiches[:8]

    return {
        "latest": latest,
        "daily": daily,
        "scores": scores,
        "ordered": ordered,
        "den": den,
        "rong": rong,
        "kan": kan,
        "pairs": pairs,
        "triples": triples,
        "doubles": doubles,
        "sandwiches": sandwiches,
        "weights": weights,
    }




# ================================================================
# STREAMLIT WEB APP
# ================================================================
st.set_page_config(
    page_title="หวยฮานอย 2026",
    page_icon="🎯",
    layout="wide",
)

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday",
              "Friday", "Saturday", "Sunday"]
DAY_TH = {
    "Monday": "วันจันทร์",
    "Tuesday": "วันอังคาร",
    "Wednesday": "วันพุธ",
    "Thursday": "วันพฤหัสบดี",
    "Friday": "วันศุกร์",
    "Saturday": "วันเสาร์",
    "Sunday": "วันอาทิตย์",
}


def get_app_history():
    df = load_history()
    if df.empty:
        return df
    return df.sort_values("dt", ascending=True, kind="stable").reset_index(drop=True)


def render_prediction(df):
    if df.empty:
        st.warning("ยังไม่มีข้อมูล กรุณาเพิ่มผลรางวัลในแท็บ อัปเดต / ลบผลรางวัล")
        return

    latest = df.loc[df["dt"].idxmax()]
    suggested_day = (latest["dt"] + pd.Timedelta(days=1)).day_name()
    default_index = DAYS_ORDER.index(suggested_day) if suggested_day in DAYS_ORDER else 0

    col_day, col_base = st.columns([1, 2])
    with col_day:
        selected_day = st.selectbox(
            "เลือกวันสำหรับการวิเคราะห์",
            DAYS_ORDER,
            index=default_index,
            format_func=lambda x: f"{DAY_TH[x]} ({x})",
        )
    with col_base:
        st.info(
            f"**ฐานข้อมูลล่าสุด:** {latest['date']} ({DAY_TH.get(latest['weekday_en'], latest['weekday_en'])})"
            f"  |  3 ตัวบน: **{latest['top_3']}**  |  2 ตัวล่าง: **{latest['bottom_2']}**"
        )

    pred = generate_prediction(df, selected_day)
    if pred is None:
        st.warning("ไม่สามารถสร้างผลวิเคราะห์ได้")
        return

    st.subheader(f"ผลวิเคราะห์ {DAY_TH[selected_day]} — Daily Number: `{pred['daily']}`")
    # แสดงผลวิเคราะห์ 3 บรรทัด โดยวางคะแนนต่อท้ายเลขเด่น
    st.markdown(f"### 🎯 เลขเด่น : {pred['den']}  ({pred['scores'][pred['den']]:.2f})")
    st.markdown(f"### 🥈 เลขรอง : {' - '.join(pred['rong'])}")
    st.markdown(f"### 🛡️ เลขกัน : {' - '.join(pred['kan'])}")

    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown("#### 🔢 ชุด 2 ตัว (ไป-กลับ)")
        st.success("  |  ".join(pred["pairs"]) if pred["pairs"] else "ไม่มีชุดตัวเลข")
        st.markdown("#### 👯 ชุดเลขเบิ้ล")
        st.warning("  |  ".join(pred["doubles"]) if pred["doubles"] else "ไม่มีชุดตัวเลข")
    with right:
        st.markdown("#### 🎰 ชุด 3 ตัว AI (ไม่กลับตำแหน่ง · Top 10)")
        st.info("  |  ".join(pred["triples"][:10]) if pred["triples"] else "ไม่มีชุดตัวเลข")
        st.markdown("#### 🥪 ชุดเลขหาม")
        st.warning("  |  ".join(pred["sandwiches"]) if pred["sandwiches"] else "ไม่มีชุดตัวเลข")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### คะแนนตัวเลข 0–9")
        score_df = pd.DataFrame({
            "เลข": list(pred["scores"].keys()),
            "คะแนน": list(pred["scores"].values()),
        }).sort_values("เลข")
        st.bar_chart(score_df.set_index("เลข"))
    with c2:
        st.markdown("#### Dynamic Formula Weight")
        weight_df = pd.DataFrame(
            [{"Formula": k, "Weight": round(v, 3)}
             for k, v in sorted(pred["weights"].items(), key=lambda x: x[1], reverse=True)]
        )
        st.dataframe(weight_df, use_container_width=True, hide_index=True)

    st.caption("ผลวิเคราะห์เป็นการจัดอันดับจากสูตรและสถิติย้อนหลัง ไม่ใช่การรับประกันผลรางวัล")


def main():
    initialize_csv()

    st.title("🎯 หวยฮานอย 2026")
    st.caption("Manual + Dynamic Hybrid Daily Number | Dynamic Backtest + Formula Accuracy + Weighted Prediction")

    df = get_app_history()
    df_desc = df.sort_values("dt", ascending=False).reset_index(drop=True) if not df.empty else df

    with st.sidebar:
        st.header("📁 จัดการฐานข้อมูล")
        st.metric("จำนวนงวดในระบบ", f"{len(df)} งวด")
        export_df = df_desc.drop(columns=["dt", "weekday_en"], errors="ignore")
        st.download_button(
            "⬇️ ดาวน์โหลด history_hanoi.csv",
            data=export_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name="history_hanoi.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.divider()
        uploaded = st.file_uploader("อัปโหลด CSV เพื่อกู้คืน / แทนที่ฐานข้อมูล", type=["csv"])
        if uploaded is not None:
            try:
                imported = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
                required = ["date", "special", "first_prize", "top_3", "bottom_2"]
                missing = [c for c in required if c not in imported.columns]
                if missing:
                    st.error("ไฟล์ CSV ขาดคอลัมน์: " + ", ".join(missing))
                else:
                    if st.button("ยืนยันนำเข้าและแทนที่ฐานข้อมูล", type="primary"):
                        imported["dt"] = imported["date"].apply(parse_thai_date)
                        imported = imported.dropna(subset=["dt"]).copy()
                        imported["top_3"] = imported["top_3"].apply(lambda x: zfill_num(x, 3))
                        imported["bottom_2"] = imported["bottom_2"].apply(lambda x: zfill_num(x, 2))
                        imported = imported.sort_values("dt", ascending=False)
                        save_history(imported)
                        st.success(f"นำเข้าสำเร็จ {len(imported)} งวด")
                        st.rerun()
            except Exception as exc:
                st.error(f"อ่านไฟล์ CSV ไม่สำเร็จ: {exc}")

        st.info(
            "หมายเหตุ: บน Streamlit Cloud การบันทึก CSV ในพื้นที่แอปอาจไม่ถาวร "
            "ควรดาวน์โหลดสำรองหลังอัปเดตข้อมูล"
        )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔮 Prediction",
        "➕ อัปเดต / ลบผลรางวัล",
        "📊 Ranking & Backtest",
        "📜 History",
        "📅 Daily Numbers",
    ])

    with tab1:
        render_prediction(df)

    with tab2:
        add_col, delete_col = st.columns([3, 2])
        with add_col:
            st.subheader("➕ บันทึกผลรางวัลใหม่")
            if not df.empty:
                next_date = df["dt"].max() + pd.Timedelta(days=1)
                default_date = f"{next_date.day:02d}/{next_date.month:02d}/{next_date.year + 543}"
            else:
                now = datetime.now()
                default_date = f"{now.day:02d}/{now.month:02d}/{now.year + 543}"

            with st.form("add_result_form", clear_on_submit=True):
                date_value = st.text_input("วันที่ (DD/MM/YYYY พ.ศ.)", value=default_date)
                c1, c2 = st.columns(2)
                with c1:
                    special = st.text_input("รางวัลพิเศษ (5 หลัก)", max_chars=5)
                    top3 = st.text_input("เลข 3 ตัวบน (3 หลัก) *", max_chars=3)
                with c2:
                    first_prize = st.text_input("รางวัลที่ 1 (5 หลัก)", max_chars=5)
                    bottom2 = st.text_input("เลข 2 ตัวล่าง (2 หลัก) *", max_chars=2)
                submitted = st.form_submit_button("💾 บันทึกผลรางวัล", type="primary", use_container_width=True)

            if submitted:
                parsed = parse_thai_date(date_value)
                if pd.isna(parsed):
                    st.error("รูปแบบวันที่ไม่ถูกต้อง ตัวอย่าง 06/10/2569")
                elif not top3.strip().isdigit() or not bottom2.strip().isdigit():
                    st.error("กรุณากรอกเลข 3 ตัวบนและ 2 ตัวล่างเป็นตัวเลข")
                elif len(top3.strip()) > 3 or len(bottom2.strip()) > 2:
                    st.error("เลข 3 ตัวบนต้องไม่เกิน 3 หลัก และเลข 2 ตัวล่างต้องไม่เกิน 2 หลัก")
                else:
                    new_row = pd.DataFrame([{
                        "date": date_value.strip(),
                        "special": special.strip(),
                        "first_prize": first_prize.strip(),
                        "top_3": zfill_num(top3, 3),
                        "bottom_2": zfill_num(bottom2, 2),
                    }])
                    raw = df_desc.drop(columns=["dt", "weekday_en"], errors="ignore")
                    raw = pd.concat([new_row, raw], ignore_index=True)
                    raw["dt"] = raw["date"].apply(parse_thai_date)
                    raw = raw.dropna(subset=["dt"]).drop_duplicates(subset=["date"], keep="first")
                    raw = raw.sort_values("dt", ascending=False)
                    save_history(raw)
                    st.success(f"บันทึกผลรางวัลวันที่ {date_value} สำเร็จ")
                    st.rerun()

        with delete_col:
            st.subheader("🗑️ ลบงวดล่าสุด")
            if df_desc.empty:
                st.info("ไม่มีข้อมูลให้ลบ")
            else:
                st.dataframe(
                    df_desc[["date", "top_3", "bottom_2", "weekday_en"]].head(5),
                    use_container_width=True,
                    hide_index=True,
                )
                latest_row = df_desc.iloc[0]
                confirm_delete = st.checkbox(f"ยืนยันลบงวด {latest_row['date']}")
                if st.button("ลบงวดล่าสุด", type="secondary", disabled=not confirm_delete, use_container_width=True):
                    save_history(df_desc.iloc[1:].copy())
                    st.success(f"ลบงวด {latest_row['date']} แล้ว")
                    st.rerun()

    with tab3:
        st.subheader("📊 Formula Ranking")
        if len(df) < 2:
            st.warning("ต้องมีอย่างน้อย 2 งวดเพื่อทำ Backtest")
        else:
            ranking = formula_ranking(df)
            st.dataframe(ranking, use_container_width=True, hide_index=True)
            st.caption(
                "Hit% คือการมีเลขจากสูตรอยู่ในผลจริง; Exact% เป็นคะแนนความตรงของ Pattern "
                "ไม่ใช่โอกาสหรือการรับประกันถูกรางวัล"
            )
            st.divider()
            st.subheader("🔍 Backtest Detail")
            bt = backtest_dataframe(df)
            selected_formulas = st.multiselect("เลือกสูตรที่ต้องการดู", FORMULAS, default=[])
            shown = bt[bt["formula"].isin(selected_formulas)] if selected_formulas else bt
            st.dataframe(shown.iloc[::-1].head(200), use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ ดาวน์โหลด Backtest CSV",
                data=bt.to_csv(index=False, encoding="utf-8-sig"),
                file_name="hanoi_backtest.csv",
                mime="text/csv",
            )

    with tab4:
        st.subheader(f"📜 ประวัติผลรางวัลทั้งหมด ({len(df_desc)} งวด)")
        if df_desc.empty:
            st.info("ยังไม่มีประวัติผลรางวัล")
        else:
            columns = ["date", "weekday_en", "special", "first_prize", "top_3", "bottom_2"]
            st.dataframe(df_desc[columns], use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("📅 ตั้งค่าเลขประจำวัน (Daily Number)")
        st.caption("แก้ไขเลขได้ครบ 6 หลักทุกวัน ระบบจะบันทึกเป็นข้อความเพื่อรักษาเลข 0 ด้านหน้า")

        current_config = load_daily_config()
        with st.form("daily_number_settings_form"):
            mode = st.selectbox(
                "โหมดการทำงาน",
                DAILY_MODES,
                index=DAILY_MODES.index(current_config.get("mode", "Hybrid")),
                help="Manual = ใช้เลขที่กำหนดเอง | Hybrid = ใช้ Manual ก่อนแล้วเติมจาก Dynamic | Dynamic = ให้ AI คำนวณอัตโนมัติ"
            )
            edited_numbers = {}
            cols = st.columns(2)
            for i, day in enumerate(DAYS_ORDER):
                with cols[i % 2]:
                    edited_numbers[day] = st.text_input(
                        DAY_TH[day],
                        value=current_config["numbers"].get(day, DEFAULT_DAILY_NUMBERS[day]),
                        max_chars=6,
                        key=f"daily_edit_{day}"
                    )
            save_daily = st.form_submit_button("💾 บันทึกเลขประจำวัน", type="primary", use_container_width=True)

        if save_daily:
            invalid = [DAY_TH[d] for d, value in edited_numbers.items()
                       if not value.strip().isdigit() or len(value.strip()) != 6]
            if invalid:
                st.error("กรุณากรอกตัวเลขให้ครบ 6 หลัก: " + ", ".join(invalid))
            else:
                new_config = {
                    "mode": mode,
                    "numbers": {d: edited_numbers[d].strip() for d in DAYS_ORDER}
                }
                try:
                    save_daily_config(new_config)
                    st.success("บันทึกเลขประจำวันทั้ง 7 วันเรียบร้อยแล้ว")
                    st.rerun()
                except OSError as exc:
                    st.error(f"ไม่สามารถบันทึกไฟล์ {DAILY_CONFIG_FILE} ได้: {exc}")

        st.divider()
        st.subheader("📊 สรุปเลขที่ใช้งานจริง")
        display_config = load_daily_config()
        summary_rows = []
        for day in DAYS_ORDER:
            manual_value = display_config["numbers"][day]
            dynamic_value = calculate_dynamic_daily(day, df, manual_value)
            active_value = daily_number_for_day(day, df)
            summary_rows.append({
                "วัน": DAY_TH[day],
                "Manual": manual_value,
                "Dynamic": dynamic_value,
                "เลขที่ Prediction ใช้": active_value,
                "โหมด": display_config["mode"]
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ ดาวน์โหลดสำรองการตั้งค่า Daily Number (JSON)",
            data=json.dumps(display_config, ensure_ascii=False, indent=2),
            file_name="daily_numbers.json",
            mime="application/json",
            use_container_width=True
        )
        uploaded_daily = st.file_uploader("กู้คืนการตั้งค่า Daily Number จาก JSON", type=["json"], key="daily_config_upload")
        if uploaded_daily is not None and st.button("นำเข้าการตั้งค่า Daily Number", key="restore_daily_config"):
            try:
                imported_config = json.load(uploaded_daily)
                imported_numbers = imported_config.get("numbers", {})
                if imported_config.get("mode", "Hybrid") not in DAILY_MODES:
                    raise ValueError("โหมดไม่ถูกต้อง")
                if any(not str(imported_numbers.get(d, "")).isdigit() or len(str(imported_numbers.get(d, ""))) != 6 for d in DAYS_ORDER):
                    raise ValueError("ไฟล์ต้องมีเลขครบ 6 หลักสำหรับทั้ง 7 วัน")
                save_daily_config({"mode": imported_config.get("mode", "Hybrid"),
                                   "numbers": {d: str(imported_numbers[d]) for d in DAYS_ORDER}})
                st.success("กู้คืนการตั้งค่าเรียบร้อยแล้ว")
                st.rerun()
            except (ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
                st.error(f"ไฟล์ตั้งค่าไม่ถูกต้อง: {exc}")

        st.info(
            "หมายเหตุ: Streamlit Cloud อาจรีเซ็ตไฟล์ในพื้นที่แอปเมื่อมีการ deploy/restart "
            "แนะนำให้ดาวน์โหลด JSON สำรอง และนำกลับเข้าระบบได้ทุกเมื่อ"
        )


if __name__ == "__main__":
    main()
