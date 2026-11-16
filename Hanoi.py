import os
import pandas as pd
import streamlit as st
from collections import Counter, defaultdict
from datetime import datetime

# ================================================================
# PAGE CONFIG
# ================================================================
st.set_page_config(
    page_title="Hanoi AI Professional v2.0",
    page_icon="🎯",
    layout="wide",
)

# ================================================================
# CONSTANTS & CONFIG
# ================================================================
CSV_FILE = "history_hanoi.csv"
MIN_HISTORY_FOR_DYNAMIC_WEIGHT = 10
RECENT_WINDOW = 30

DEFAULT_DAILY_NUMBERS = {
    "Monday": "194286",
    "Tuesday": "194286",
    "Wednesday": "431560",
    "Thursday": "541609",
    "Friday": "865032",
    "Saturday": "319820",
    "Sunday": "325984",
}

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

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ================================================================
# CORE LOGIC FUNCTIONS
# ================================================================
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
        pd.DataFrame(
            initial_data,
            columns=["date", "special", "first_prize", "top_3", "bottom_2"]
        ).to_csv(CSV_FILE, index=False, encoding="utf-8-sig")


def load_history():
    if not os.path.exists(CSV_FILE):
        initialize_csv()
    df = pd.read_csv(CSV_FILE, dtype=str).fillna("")
    required = ["date", "special", "first_prize", "top_3", "bottom_2"]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    df["dt"] = df["date"].apply(parse_thai_date)
    df = df.dropna(subset=["dt"]).copy()
    df["top_3"] = df["top_3"].apply(lambda x: zfill_num(x, 3))
    df["bottom_2"] = df["bottom_2"].apply(lambda x: zfill_num(x, 2))
    df["weekday_en"] = df["dt"].dt.day_name()
    return df


def save_history(df):
    out = df.copy()
    for col in ["dt", "weekday_en"]:
        if col in out.columns:
            out = out.drop(columns=[col])
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


def daily_number_for_day(day, history=None):
    """
    สร้าง Daily Number แยกตามวันจาก 30 งวดล่าสุดของวันนั้นเท่านั้น
    ใช้ 3 ตัวบน + 2 ตัวล่าง และผสาน Frequency, Position, Recency
    """
    if history is None or history.empty:
        return "000000"

    day_history = history.copy()
    if "weekday_en" not in day_history.columns:
        if "dt" in day_history.columns:
            day_history["weekday_en"] = day_history["dt"].dt.day_name()
        else:
            return "000000"

    day_history = day_history[day_history["weekday_en"] == day].copy()
    if day_history.empty:
        return "000000"

    if "dt" in day_history.columns:
        day_history = day_history.sort_values("dt", ascending=False)
    recent = day_history.head(RECENT_WINDOW)

    freq = Counter()
    recency = Counter()
    position_counts = {pos: Counter() for pos in range(5)}

    for age, (_, row) in enumerate(recent.iterrows()):
        digits = zfill_num(row.get("top_3", ""), 3) + zfill_num(row.get("bottom_2", ""), 2)
        decay = 0.90 ** age
        for pos, char in enumerate(digits):
            freq[char] += 1
            recency[char] += decay
            position_counts[pos][char] += 1

    max_freq = max(freq.values()) if freq else 1
    max_recency = max(recency.values()) if recency else 1

    scores = {}
    for digit in "0123456789":
        pos_scores = []
        for pos in range(5):
            max_at_pos = max(position_counts[pos].values()) if position_counts[pos] else 1
            pos_scores.append(position_counts[pos][digit] / max_at_pos)
        position_score = sum(pos_scores) / 5
        scores[digit] = (
            0.40 * (freq[digit] / max_freq)
            + 0.25 * position_score
            + 0.35 * (recency[digit] / max_recency)
        )

    ranked = sorted("0123456789", key=lambda d: (-scores[d], -freq[d], -recency[d], d))
    return "".join(ranked[:6])


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
            hit3, hit2 = evaluate_formula(
                formula, trans, daily, actual["top_3"], actual["bottom_2"]
            )
            exact3, exact2 = exact_pattern_score(
                formula, trans, daily, actual["top_3"], actual["bottom_2"]
            )
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
    for formula in FORMULAS:
        x = bt[bt["formula"] == formula]
        n = len(x)
        hit3 = x["hit_3d"].sum()
        hit2 = x["hit_2d"].sum()
        avg_exact3 = x["exact_3d"].mean()
        avg_exact2 = x["exact_2d"].mean()
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
        w = 0.5 + row["Composite"] / 50.0
        weights[row["Formula"]] = max(0.5, min(3.0, w))
    return weights


def digit_scores(df, next_day):
    if df.empty:
        return {str(i): 0.0 for i in range(10)}, {}, "000000"

    latest = df.iloc[-1]
    candidates, daily, trans = formula_candidates(
        latest["top_3"], latest["bottom_2"], next_day, df
    )
    weights = dynamic_weights(df)
    
    # เพิ่มน้ำหนักให้สูตร Daily 6-Digit ตามวันที่เลือก
    if "Daily 6-Digit" in weights:
        weights["Daily 6-Digit"] *= 3.5

    scores = {str(i): 0.0 for i in range(10)}

    for formula in FORMULAS:
        w = weights.get(formula, 1.0)
        for digit in candidates[formula]:
            scores[str(digit)] += w

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

    latest = df.iloc[-1]
    scores, weights, daily = digit_scores(df, next_day)

    # Daily Number contributes to the ranking before Main / Secondary / Backup
    for d in daily:
        if d in scores:
            scores[d] += 8.0

    ordered = sorted(scores, key=lambda d: (-scores[d], d))
    den = ordered[0]
    rong = ordered[1:4]
    kan = ordered[4:7]

    # All number sets below are derived from the ranked Main / Secondary / Backup digits.
    # Keep the priority order and remove duplicates.
    core_digits = list(dict.fromkeys([den] + rong + kan))
    support_digits = list(dict.fromkeys(rong + kan))

    # 2D: pair Main with every Secondary / Backup digit, both straight and reversed.
    pairs = []
    for digit in support_digits:
        pairs.extend([den + digit, digit + den])
    pairs = list(dict.fromkeys(pairs))

    # Doubles: repeat each digit in the Main / Secondary / Backup pool.
    doubles = [digit * 2 for digit in core_digits]

    # 3D AI Top 10: build permutations from the same ranked digit pool.
    # Score each candidate by the combined strength of its three digits.
    triple_candidates = set()
    for a in core_digits:
        for b in core_digits:
            for c in core_digits:
                if len({a, b, c}) >= 2:
                    triple_candidates.add(a + b + c)

    triples = sorted(
        triple_candidates,
        key=lambda number: (
            -(scores[number[0]] + scores[number[1]] + scores[number[2]]),
            number
        )
    )[:10]

    # Sandwiches: ABA patterns formed only from Main / Secondary / Backup digits.
    sandwich_candidates = {
        a + b + a
        for a in core_digits
        for b in core_digits
        if a != b
    }
    sandwiches = sorted(
        sandwich_candidates,
        key=lambda number: (
            -(scores[number[0]] * 2 + scores[number[1]]),
            number
        )
    )[:8]

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
# STREAMLIT UI
# ================================================================
def main():
    initialize_csv()

    st.title("🎯 HANOI AI PROFESSIONAL v2.0")
    st.caption("Weekday-specific Dynamic Daily Number + Backtest + Weighted Prediction")

    with st.sidebar:
        st.header("📁 จัดการฐานข้อมูล (CSV)")
        df_current = load_history().sort_values("dt", ascending=False)
        st.metric("จำนวนงวดในระบบ", f"{len(df_current)} งวด")

        raw_csv = df_current.drop(columns=["dt", "weekday_en"], errors="ignore").to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="⬇️ ดาวน์โหลด history_hanoi.csv",
            data=raw_csv,
            file_name="history_hanoi.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.divider()

        uploaded_file = st.file_uploader("⬆️ อัปโหลดไฟล์ CSV เพื่อกู้คืนข้อมูล", type=["csv"])
        if uploaded_file is not None:
            try:
                up_df = pd.read_csv(uploaded_file, dtype=str).fillna("")
                required = ["date", "special", "first_prize", "top_3", "bottom_2"]
                if all(col in up_df.columns for col in required):
                    save_history(up_df)
                    st.success("✅ นำเข้าข้อมูล CSV สำเร็จ!")
                    st.rerun()
                else:
                    st.error(f"❌ ไฟล์ต้องมีคอลัมน์: {', '.join(required)}")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")

        st.info("💡 **คำแนะนำ:** บน Streamlit Cloud ข้อมูลอาจถูกรีเซ็ตหากแอปหยุดทำงานเป็นเวลานาน ควรดาวน์โหลดไฟล์ CSV เก็บไว้หลังอัปเดตผลรางวัล")

    df_asc = load_history().sort_values("dt").reset_index(drop=True)
    df_desc = df_asc.sort_values("dt", ascending=False).reset_index(drop=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔮 วิเคราะห์งวดถัดไป (Prediction)",
        "➕ อัปเดต / ลบผลรางวัล",
        "📊 จัดอันดับสูตร (Ranking & Backtest)",
        "📜 ประวัติผลรางวัล (History)",
        "📅 เลขประจำวัน (Daily 6-Digit)",
    ])

    with tab1:
        if df_asc.empty:
            st.warning("⚠️ ไม่มีข้อมูลในระบบ กรุณาเพิ่มข้อมูลในแท็บ 'อัปเดต / ลบผลรางวัล'")
        else:
            latest = df_asc.iloc[-1]
            next_dt = latest["dt"] + pd.Timedelta(days=1)
            default_next_day = next_dt.day_name()
            default_idx = DAYS_ORDER.index(default_next_day) if default_next_day in DAYS_ORDER else 0

            col_sel, col_base = st.columns([1, 2])
            with col_sel:
                selected_day = st.selectbox(
                    "เลือกวันของงวดถัดไป",
                    DAYS_ORDER,
                    index=default_idx,
                )
            with col_base:
                st.info(
                    f"**ฐานข้อมูลล่าสุด:** วันที่ `{latest['date']}` ({latest['weekday_en']}) | "
                    f"3 ตัวบน: **`{latest['top_3']}`** | 2 ตัวล่าง: **`{latest['bottom_2']}`**"
                )

            pred = generate_prediction(df_asc, selected_day)

            st.subheader(f"สรุปแนวทางประจำวัน {selected_day} (Daily: `{pred['daily']}`)")

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(
                    label="🎯 เด่น (Main Digit)",
                    value=pred["den"],
                    delta=f"Score: {pred['scores'][pred['den']]:.2f}",
                )
            with m2:
                st.metric(
                    label="🥈 รอง (Secondary)",
                    value=" - ".join(pred["rong"]),
                )
            with m3:
                st.metric(
                    label="🛡️ กัน (Backup)",
                    value=" - ".join(pred["kan"]),
                )

            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🔢 ชุด 2 ตัว (เน้นไป-กลับ)")
                st.success(" ,  ".join(pred["pairs"]))

                st.markdown("#### 👯 ชุดเบิ้ล (Doubles)")
                st.warning(" ,  ".join(pred["doubles"]))

            with c2:
                st.markdown("#### 🎰 ชุด 3 ตัว (AI Top 10)")
                st.info(" ,  ".join(pred["triples"][:10]))

                st.markdown("#### 🥪 ชุดหาม (Sandwiches)")
                st.warning(" ,  ".join(pred["sandwiches"]))

            st.divider()

            g1, g2 = st.columns(2)
            with g1:
                st.markdown("#### 📈 คะแนนความน่าจะเป็นรายตัวเลข (0-9)")
                score_df = pd.DataFrame({
                    "Digit": list(pred["scores"].keys()),
                    "Score": list(pred["scores"].values())
                }).sort_values("Digit")
                st.bar_chart(score_df.set_index("Digit"))

            with g2:
                st.markdown("#### ⚖️ Dynamic Formula Weights")
                weight_df = pd.DataFrame([
                    {"Formula": k, "Weight": round(v, 2)}
                    for k, v in sorted(pred["weights"].items(), key=lambda x: x[1], reverse=True)
                ])
                st.dataframe(weight_df, use_container_width=True, hide_index=True)

    with tab2:
        col_add, col_del = st.columns([3, 2])

        with col_add:
            st.subheader("➕ บันทึกผลรางวัลงวดใหม่")
            with st.form("add_result_form", clear_on_submit=True):
                if not df_asc.empty:
                    sug_dt = df_asc.iloc[-1]["dt"] + pd.Timedelta(days=1)
                    sug_date_str = f"{sug_dt.day:02d}/{sug_dt.month:02d}/{sug_dt.year + 543}"
                else:
                    now = datetime.now()
                    sug_date_str = f"{now.day:02d}/{now.month:02d}/{now.year + 543}"

                date_str = st.text_input("วันที่ (DD/MM/YYYY พ.ศ.)", value=sug_date_str)
                c_in1, c_in2 = st.columns(2)
                with c_in1:
                    special = st.text_input("รางวัลพิเศษ (5 หลัก)", max_chars=5, placeholder="เช่น 95242")
                    top_3 = st.text_input("เลข 3 ตัวบน (3 หลัก) *", max_chars=3, placeholder="เช่น 242")
                with c_in2:
                    first_prize = st.text_input("รางวัลที่ 1 (5 หลัก)", max_chars=5, placeholder="เช่น 82585")
                    bottom_2 = st.text_input("เลข 2 ตัวล่าง (2 หลัก) *", max_chars=2, placeholder="เช่น 85")

                submitted = st.form_submit_button("💾 บันทึกผลรางวัล", use_container_width=True, type="primary")
                if submitted:
                    parsed_dt = parse_thai_date(date_str)
                    if pd.isna(parsed_dt):
                        st.error("❌ รูปแบบวันที่ไม่ถูกต้อง กรุณาใส่เป็น DD/MM/YYYY (พ.ศ.) เช่น 06/10/2569")
                    elif not top_3.isdigit() or not bottom_2.isdigit():
                        st.error("❌ กรุณากรอกเลข 3 ตัวบน และ 2 ตัวล่าง เป็นตัวเลขให้ครบถ้วน")
                    else:
                        new_row = pd.DataFrame([{
                            "date": date_str.strip(),
                            "special": special.strip(),
                            "first_prize": first_prize.strip(),
                            "top_3": zfill_num(top_3, 3),
                            "bottom_2": zfill_num(bottom_2, 2),
                        }])
                        raw = df_desc.drop(columns=["dt", "weekday_en"], errors="ignore")
                        raw = pd.concat([new_row, raw], ignore_index=True)
                        raw = raw.drop_duplicates(subset=["date"], keep="first")
                        raw["dt"] = raw["date"].apply(parse_thai_date)
                        raw = raw.sort_values("dt", ascending=False)
                        save_history(raw)
                        st.success(f"✅ บันทึกผลรางวัลงวดวันที่ {date_str} เรียบร้อยแล้ว!")
                        st.rerun()

        with col_del:
            st.subheader("🗑️ ลบข้อมูลงวดล่าสุด")
            if df_desc.empty:
                st.info("ไม่มีข้อมูลให้ลบ")
            else:
                st.write("รายการล่าสุด 5 งวด:")
                st.dataframe(
                    df_desc[["date", "top_3", "bottom_2", "weekday_en"]].head(5),
                    use_container_width=True,
                    hide_index=True,
                )
                latest_del = df_desc.iloc[0]
                if st.button(f"❌ ลบงวดล่าสุด ({latest_del['date']})", type="secondary", use_container_width=True):
                    df_after_del = df_desc.iloc[1:].copy()
                    save_history(df_after_del)
                    st.success(f"ลบงวดวันที่ {latest_del['date']} เรียบร้อยแล้ว")
                    st.rerun()

    with tab3:
        st.subheader("📊 ผลทดสอบย้อนหลังและจัดอันดับสูตร (Formula Ranking)")
        if len(df_asc) < 2:
            st.warning("⚠️ ข้อมูลไม่เพียงพอ ต้องมีอย่างน้อย 2 งวดขึ้นไปเพื่อทำการ Backtest")
        else:
            ranking_df = formula_ranking(df_asc)
            st.dataframe(
                ranking_df.style.highlight_max(subset=["Composite", "3D Hit%", "2D Hit%"], color="#1e4620"),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "หมายเหตุ: `Hit%` คือการมีเลขจากสูตรอยู่ในผลจริง; `Exact%` เป็นคะแนนความตรงของ Pattern (ไม่ใช่การรับประกันถูกรางวัล)"
            )

            st.divider()
            st.subheader("🔍 รายละเอียดการทดสอบย้อนหลังรายงวด (Backtest Detail)")
            bt_df = backtest_dataframe(df_asc)
            
            filter_formula = st.multiselect(
                "กรองตามสูตร (ว่างไว้ = แสดงทั้งหมด)",
                options=FORMULAS,
                default=[]
            )
            if filter_formula:
                bt_display = bt_df[bt_df["formula"].isin(filter_formula)]
            else:
                bt_display = bt_df

            st.dataframe(
                bt_display.iloc[::-1].head(100),
                use_container_width=True,
                hide_index=True,
            )

    with tab4:
        st.subheader(f"📜 ประวัติผลรางวัลทั้งหมด ({len(df_desc)} งวด)")
        cols = ["date", "weekday_en", "special", "first_prize", "top_3", "bottom_2"]
        st.dataframe(df_desc[cols], use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("📅 ชุดเลขประจำวัน (Daily 6-Digit)")
        daily_rows = []
        for day in DAYS_ORDER:
            daily_rows.append({
                "Day": day,
                "Daily Number (คำนวณจากวันนั้น)": daily_number_for_day(day, df_asc),
            })
        st.table(pd.DataFrame(daily_rows))

        if len(df_asc) >= MIN_HISTORY_FOR_DYNAMIC_WEIGHT:
            st.success(f"✅ ระบบคำนวณ Daily Number แยกตามวัน จาก 3 ตัวบน + 2 ตัวล่าง โดยใช้ไม่เกิน {RECENT_WINDOW} งวดล่าสุดของวันนั้น")
        else:
            st.info("ℹ️ ระบบใช้ข้อมูลที่มีอยู่ของแต่ละวัน หากยังมีไม่ครบ 30 งวด จะแสดงผลจากจำนวนงวดที่มีจริง")


if __name__ == "__main__":
    main()
