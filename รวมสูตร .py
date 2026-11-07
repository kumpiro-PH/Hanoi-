# app.py - Hanoi AI Professional (Robust Column Mapping & Cross-Day Fusion)
import os
import streamlit as st
import pandas as pd

# ==================== ตั้งค่าหน้าเว็บ ====================
st.set_page_config(page_title="Hanoi AI Professional", page_icon="🎯", layout="wide")

# ==================== กำหนดชื่อไฟล์ CSV ตามวันในสัปดาห์ ====================
DAY_CSV_MAP = {
    "Monday": "history_hanoi_mon.csv",
    "Tuesday": "history_hanoi_tue.csv",
    "Wednesday": "history_hanoi_wed.csv",
    "Thursday": "history_hanoi_thu.csv",
    "Friday": "history_hanoi_fri.csv",
    "Saturday": "history_hanoi_sat.csv",
    "Sunday": "history_hanoi_sun.csv",
}

# ==================== ชุดเลขประจำวัน 6 ตัวตามสถิติ ====================
DAILY_NUMBERS = {
    "Monday": "459781",
    "Tuesday": "986304",
    "Wednesday": "698741",
    "Thursday": "421590",
    "Friday": "761438",
    "Saturday": "094572",
    "Sunday": "768304",
}

def parse_thai_date(x):
    """ฟังก์ชันแปลงวันที่พุทธศักราช/ค.ศ. (DD/MM/YYYY) เป็น ค.ศ. แบบปลอดภัย"""
    try:
        parts = str(x).strip().split("/")
        if len(parts) != 3:
            return pd.NaT
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        
        if year > 2400:
            year -= 543
        elif year < 100:
            year += 2000
            
        return pd.Timestamp(year=year, month=month, day=day)
    except Exception:
        return pd.NaT

def initialize_csvs():
    """ตรวจสอบและสร้างไฟล์ CSV ประจำวันเริ่มต้นหากยังไม่มี"""
    headers = "date,special,first_prize,top_3,bottom_2\n"
    for day_en, filename in DAY_CSV_MAP.items():
        if not os.path.exists(filename):
            with open(filename, "w", encoding="utf-8") as f:
                f.write(headers)

def load_and_clean_df(filepath):
    """ฟังก์ชันช่วยโหลด CSV และรองรับทุกชื่อคอลัมน์ พร้อมจัดเรียงวันที่จากใหม่ไปเก่า"""
    expected_cols = ["date", "special", "first_prize", "top_3", "bottom_2"]
    try:
        if not os.path.exists(filepath):
            return pd.DataFrame(columns=expected_cols)
        
        df = pd.read_csv(filepath, dtype=str)
        if df.empty:
            return pd.DataFrame(columns=expected_cols)
            
        df.columns = df.columns.str.strip()
        
        # Mapping ครอบคลุมทุกรูปแบบคอลัมน์ที่เป็นไปได้
        column_mapping = {
            "วันที่": "date",
            "date": "date",
            "รางวัลที่ 1": "special",
            "รางวัลที่1": "special",
            "special": "special",
            "prize_5digit_1": "special",
            "รางวัลที่ 2": "first_prize",
            "รางวัลที่2": "first_prize",
            "first_prize": "first_prize",
            "prize_5digit_2": "first_prize",
            "3 ตัวบน": "top_3",
            "3ตัวบน": "top_3",
            "three_digit": "top_3",
            "top_3": "top_3",
            "2 ตัวล่าง": "bottom_2",
            "2ตัวล่าง": "bottom_2",
            "two_digit": "bottom_2",
            "bottom_2": "bottom_2"
        }
        df = df.rename(columns=column_mapping)
        
        for col in expected_cols:
            if col not in df.columns:
                df[col] = "-"
                
        df["dt_temp"] = df["date"].apply(parse_thai_date)
        df = df.sort_values(by="dt_temp", ascending=False).reset_index(drop=True)
        df = df.drop(columns=["dt_temp"])
                
        return df[expected_cols].fillna("-")
    except Exception:
        return pd.DataFrame(columns=expected_cols)

def get_transformations(top_3_str, bottom_2_str="00"):
    """แปลงเลขฐานและสูตรคำนวณทั้งหมด"""
    try:
        clean_t3 = str(top_3_str).split(".")[0].strip().zfill(3)
        clean_b2 = str(bottom_2_str).split(".")[0].strip().zfill(2)
    except Exception:
        clean_t3, clean_b2 = "000", "00"

    digits_t3 = [int(c) if c.isdigit() else 0 for c in clean_t3[-3:]]
    digits_b2 = [int(c) if c.isdigit() else 0 for c in clean_b2[-2:]]
    
    carry_over = set(digits_t3 + digits_b2)

    pm1 = set()
    for dig in digits_t3 + digits_b2:
        pm1.add((dig + 1) % 10)
        pm1.add((dig - 1) % 10)

    sum_t3 = sum(digits_t3) % 10
    sum_b2 = sum(digits_b2) % 10
    sum_total = (sum_t3 + sum_b2) % 10
    sum_formulas = {str(sum_t3), str(sum_b2), str(sum_total)}

    cross_sum_1 = (digits_t3[1] + digits_b2[1]) % 10
    cross_sum_2 = (digits_t3[2] + digits_b2[0]) % 10
    cross_formulas = {str(cross_sum_1), str(cross_sum_2)}

    rotations = {
        f"{digits_t3[1]}{digits_t3[2]}{digits_t3[0]}",
        f"{digits_t3[2]}{digits_t3[0]}{digits_t3[1]}",
    }
    mirror_map = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
    mirrored = "".join([str(mirror_map[d]) for d in digits_t3])
    shifted = "".join([str((d + 2) % 10) for d in digits_t3])
    
    doubles = {f"{d}{d}" for d in digits_t3}
    sandwiches = {f"{d1}{d2}{d1}" for d1 in digits_t3 for d2 in digits_t3 if d1 != d2}

    return {
        "carry_over": carry_over,
        "pm1": pm1,
        "sum_formulas": sum_formulas,
        "cross_formulas": cross_formulas,
        "rotations": rotations,
        "mirror": mirrored,
        "shifted": shifted,
        "doubles": doubles,
        "sandwiches": sandwiches
    }

# ==================== ส่วนแสดงผลหน้าเว็บ Streamlit ====================

initialize_csvs()

st.title("🎯 Hanoi AI Professional - ระบบวิเคราะห์หวยฮานอย (Cross-Day Fusion)")
st.write("ระบบวิเคราะห์สถิติผสานข้อมูลข้ามวัน: ศุกร์ล่าสุด + เสาร์ล่าสุด + ชุดเลขประจำวันเสาร์")

# เมนูด้านข้าง (Sidebar)
menu = st.sidebar.selectbox(
    "เลือกเมนูการใช้งาน",
    [
        "1. อัปเดตผลรางวัล",
        "2. แสดงประวัติ (History)",
        "3. ลบข้อมืองวดล่าสุด",
        "4. Formula Ranking (จัดอันดับสูตร)",
        "5. Forward Prediction (ทำนายงวดถัดไป)"
    ]
)

selected_day_tab = st.sidebar.selectbox(
    "เลือกวันประจำไฟล์ข้อมูล",
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
)
active_csv_file = DAY_CSV_MAP[selected_day_tab]
df_main = load_and_clean_df(active_csv_file)

# เมนูที่ 1: อัปเดตผลรางวัล
if menu == "1. อัปเดตผลรางวัล":
    st.header("📝 อัปเดตผลรางวัลหวยฮานอยใหม่")
    
    with st.form("update_form"):
        date_str = st.text_input("ใส่วันที่ (DD/MM/YYYY เช่น 06/11/2569)")
        special = st.text_input("รางวัลพิเศษ (5 หลัก)")
        first_prize = st.text_input("รางวัลที่ 1 (5 หลัก)")
        top_3 = st.text_input("เลข 3 ตัวบน (3 หลัก)")
        bottom_2 = st.text_input("เลข 2 ตัวล่าง (2 หลัก)")
        
        submitted = st.form_submit_button("บันทึกผลรางวัล")
        if submitted:
            if date_str and top_3 and bottom_2:
                dt = parse_thai_date(date_str)
                if pd.notna(dt):
                    target_day_en = dt.day_name()
                    target_csv = DAY_CSV_MAP.get(target_day_en, "history_hanoi_sat.csv")
                    target_df = load_and_clean_df(target_csv)
                    
                    new_row = pd.DataFrame([{
                        "date": date_str.strip(),
                        "special": special.strip() if special else "-",
                        "first_prize": first_prize.strip() if first_prize else "-",
                        "top_3": top_3.strip(),
                        "bottom_2": bottom_2.strip(),
                    }])
                    
                    updated_df = pd.concat([new_row, target_df], ignore_index=True)
                    updated_df["dt_temp"] = updated_df["date"].apply(parse_thai_date)
                    updated_df = updated_df.sort_values(by="dt_temp", ascending=False).drop(columns=["dt_temp"])
                    updated_df.to_csv(target_csv, index=False)
                    
                    st.success(f"✅ บันทึกผลลงไฟล์ **{target_day_en}** (`{target_csv}`) เรียบร้อยแล้ว!")
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")

# เมนูที่ 2: แสดงประวัติทั้งหมด
elif menu == "2. แสดงประวัติ (History)":
    st.header(f"📊 ประวัติผลรางวัล ({selected_day_tab})")
    if not df_main.empty:
        st.dataframe(df_main, use_container_width=True)
    else:
        st.info(f"ยังไม่มีข้อมูลในไฟล์ของวัน {selected_day_tab}")

# เมนูที่ 3: ลบข้อมืองวดล่าสุด
elif menu == "3. ลบข้อมืองวดล่าสุด":
    st.header(f"🗑️ ลบข้อมืองวดล่าสุด ({selected_day_tab})")
    if not df_main.empty:
        st.dataframe(df_main.head(1), use_container_width=True)
        if st.button("ยืนยันการลบงวดล่าสุด"):
            df_main = df_main.iloc[1:].reset_index(drop=True)
            df_main.to_csv(active_csv_file, index=False)
            st.success("✅ ลบงวดล่าสุดเรียบร้อยแล้ว!")
            st.rerun()
    else:
        st.info("ไม่มีข้อมูลให้ลบ")

# เมนูที่ 4: จัดอันดับสูตร
elif menu == "4. Formula Ranking (จัดอันดับสูตร)":
    st.header(f"🏆 จัดอันดับความแม่นยำของสูตร ({selected_day_tab})")
    if st.button("เริ่มคำนวณสถิติย้อนหลัง"):
        st.info("ระบบกำลังประมวลผล Backtest ประจำวัน...")

# เมนูที่ 5: Forward Prediction (ดึงงวดศุกร์ล่าสุด + เสาร์ล่าสุด มาคำนวณร่วมกัน)
elif menu == "5. Forward Prediction (ทำนายงวดถัดไป)":
    st.header(f"🔮 Forward Prediction (คำนวณผสานสถิติ - {selected_day_tab})")
    
    df_fri = load_and_clean_df(DAY_CSV_MAP["Friday"])
    df_sat = load_and_clean_df(DAY_CSV_MAP["Saturday"])
    
    if not df_fri.empty and not df_sat.empty:
        latest_fri = df_fri.iloc[0]  # งวดล่าสุดวันศุกร์ (06/11/2569)
        latest_sat = df_sat.iloc[0]  # งวดล่าสุดวันเสาร์ (31/10/2569)

        st.subheader("📌 ข้อมูลงวดล่าสุดที่นำมาคำนวณ (ศุกร์ + เสาร์)")
        col_a, col_b = st.columns(2)
        with col_a:
            st.info(f"📊 **งวดล่าสุดประจำวัน Friday (`history_hanoi_fri.csv`)**\n\nวันที่: **{latest_fri.get('date', '-')}**\n\n3 ตัวบน: `{latest_fri.get('top_3', '-')}` | 2 ตัวล่าง: `{latest_fri.get('bottom_2', '-')}`")
        with col_b:
            st.success(f"📌 **งวดล่าสุดประจำวัน Saturday (`history_hanoi_sat.csv`)**\n\nวันที่: **{latest_sat.get('date', '-')}**\n\n3 ตัวบน: `{latest_sat.get('top_3', '-')}` | 2 ตัวล่าง: `{latest_sat.get('bottom_2', '-')}`")

        daily_6 = DAILY_NUMBERS.get(selected_day_tab, "7890123")
        st.write(f"🎯 **ชุดเลขประจำวัน ({selected_day_tab}):** `{daily_6}`")

        if st.button("🚀 ประมวลผลคำนวณผสานสถิติ 3 ส่วน"):
            if selected_day_tab == "Saturday":
                st.warning("⚠️ [AI WARNING] วันเสาร์มีสถิติการออก 'เลขเบิ้ล' และ 'เลขหาม' สูงมาก แนะนำให้ติดชุดกันไว้เสมอ!")

            trans_fri = get_transformations(str(latest_fri.get('top_3', '000')), str(latest_fri.get('bottom_2', '00')))
            trans_sat = get_transformations(str(latest_sat.get('top_3', '000')), str(latest_sat.get('bottom_2', '00')))

            digit_scores = {str(i): 0.0 for i in range(10)}

            for d in daily_6: 
                digit_scores[d] += 2.0

            for d in trans_fri['carry_over']: digit_scores[str(d)] += 1.5
            for d in trans_fri['pm1']: digit_scores[str(d)] += 1.2
            for d in trans_fri['sum_formulas']: digit_scores[d] += 1.2
            for d in trans_fri['cross_formulas']: digit_scores[str(d)] += 1.0

            for d in trans_sat['carry_over']: digit_scores[str(d)] += 1.5
            for d in trans_sat['pm1']: digit_scores[str(d)] += 1.2
            for d in trans_sat['sum_formulas']: digit_scores[d] += 1.2
            for d in trans_sat['cross_formulas']: digit_scores[str(d)] += 1.0

            sorted_digits = sorted(digit_scores.keys(), key=lambda k: digit_scores[k], reverse=True)
            den = sorted_digits[0]
            rong_list = sorted_digits[1:4]
            gun_list = sorted_digits[4:7]

            st.markdown("---")
            st.success(f"🎯 **สรุปแนวทางเลขเด่นผสาน 3 ส่วน ({selected_day_tab})**")
            col1, col2, col3 = st.columns(3)
            col1.metric("เด่นสุด", den, f"{digit_scores[den]:.1f} แต้ม")
            col2.metric("เลขรอง", " - ".join(rong_list))
            col3.metric("เลขกัน", " - ".join(gun_list))

            suggested_2d = [f"{den}{r}" for r in rong_list] + [f"{r}{den}" for r in rong_list]
            suggested_3d = [f"{den}{rong_list[0]}{rong_list[1]}"]
            suggested_double = [f"{den}{den}", f"{rong_list[0]}{rong_list[0]}"]

            st.write(f"• **ชุด 2 ตัวเน้นๆ (ไป-กลับ) :** {', '.join(suggested_2d)}")
            st.write(f"• **ชุด 3 ตัวบนแนะนำ :** {', '.join(suggested_3d)}")
            st.write(f"• **ชุด 2 ตัวเบิ้ล (แนะนำ) :** {', '.join(suggested_double)}")
    else:
        st.warning("⚠️ ข้อมูลในไฟล์ `history_hanoi_fri.csv` หรือ `history_hanoi_sat.csv` ไม่เพียงพอสำหรับการคำนวณ")
