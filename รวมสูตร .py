# app.py - Hanoi AI Professional (All-in-One Streamlit App - Multi-CSV by Day)
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
    "Monday": "940627",
    "Tuesday": "017562",
    "Wednesday": "394517",
    "Thursday": "643951",
    "Friday": "974516",
    "Saturday": "820739",
    "Sunday": "470076",
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

def get_csv_file_for_date(date_str):
    """ตรวจสอบวันที่และคืนค่าชื่อไฟล์ CSV ประจำวันนั้นๆ"""
    dt = parse_thai_date(date_str)
    if pd.notna(dt):
        weekday_en = dt.day_name()
        return DAY_CSV_MAP.get(weekday_en, "history_hanoi.csv"), weekday_en
    return "history_hanoi.csv", "Monday"

def initialize_csvs():
    """ตรวจสอบและสร้างไฟล์ CSV ประจำวันเริ่มต้นหากยังไม่มี"""
    for day_en, filename in DAY_CSV_MAP.items():
        if not os.path.exists(filename):
            initial_data = "date,special,first_prize,top_3,bottom_2\n"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(initial_data)

def get_transformations(top_3_str, bottom_2_str="00"):
    """แปลงเลขฐานและสูตรคำนวณทั้งหมด"""
    try:
        clean_t3 = str(top_3_str).split(".")[0].strip().zfill(3)
        clean_b2 = str(bottom_2_str).split(".")[0].strip().zfill(2)
    except Exception:
        clean_t3, clean_b2 = "000", "00"

    digits_t3 = [int(c) for c in clean_t3[-3:]]
    digits_b2 = [int(c) for c in clean_b2[-2:]]
    
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

st.title("🎯 Hanoi AI Professional - ระบบวิเคราะห์หวยฮานอย (แยกไฟล์รายวัน)")
st.write("ระบบวิเคราะห์สถิติและทำนายแนวทางหวยฮานอย จัดเก็บข้อมูลแยกตามวันในสัปดาห์อัตโนมัติ")

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

# เลือกดูข้อมูลตามวัน (สำหรับเมนูประวัติหรือทำนาย)
selected_day_tab = st.sidebar.selectbox(
    "เลือกวันประจำไฟล์ข้อมูล",
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
)
active_csv_file = DAY_CSV_MAP[selected_day_tab]

# โหลดข้อมูล CSV ตามวันที่เลือกใน Sidebar พร้อมรองรับหัวคอลัมน์ภาษาไทยจาก GitHub
try:
    df_main = pd.read_csv(active_csv_file)
    column_mapping = {
        "วันที่": "date",
        "รางวัลที่ 1": "special",
        "รางวัลที่ 2": "first_prize",
        "3 ตัวบน": "top_3",
        "2 ตัวล่าง": "bottom_2"
    }
    df_main = df_main.rename(columns=column_mapping)
except Exception:
    df_main = pd.DataFrame(columns=["date", "special", "first_prize", "top_3", "bottom_2"])

# เมนูที่ 1: อัปเดตผลรางวัล
if menu == "1. อัปเดตผลรางวัล":
    st.header("📝 อัปเดตผลรางวัลหวยฮานอยใหม่")
    
    with st.form("update_form"):
        date_str = st.text_input("ใส่วันที่ (DD/MM/YYYY เช่น 06/10/2569)")
        special = st.text_input("รางวัลพิเศษ (5 หลัก)")
        first_prize = st.text_input("รางวัลที่ 1 (5 หลัก)")
        top_3 = st.text_input("เลข 3 ตัวบน (3 หลัก)")
        bottom_2 = st.text_input("เลข 2 ตัวล่าง (2 หลัก)")
        
        submitted = st.form_submit_button("บันทึกผลรางวัล")
        if submitted:
            if date_str and top_3 and bottom_2:
                target_csv, target_day = get_csv_file_for_date(date_str)
                
                try:
                    target_df = pd.read_csv(target_csv)
                    target_df = target_df.rename(columns={
                        "วันที่": "date", "รางวัลที่ 1": "special", 
                        "รางวัลที่ 2": "first_prize", "3 ตัวบน": "top_3", "2 ตัวล่าง": "bottom_2"
                    })
                except Exception:
                    target_df = pd.DataFrame(columns=["date", "special", "first_prize", "top_3", "bottom_2"])
                
                if not target_df.empty and 'date' in target_df.columns and date_str in target_df['date'].values:
                    st.warning(f"⚠️ มีข้อมูลของวันที่ {date_str} ในไฟล์ของวัน ({target_day}) อยู่แล้ว")
                else:
                    new_row = pd.DataFrame([{
                        "date": date_str,
                        "special": special,
                        "first_prize": first_prize,
                        "top_3": top_3,
                        "bottom_2": bottom_2,
                    }])
                    updated_df = pd.concat([new_row, target_df], ignore_index=True)
                    updated_df.to_csv(target_csv, index=False)
                    st.success(f"✅ บันทึกผลรางวัลลงในไฟล์ประจำวัน **{target_day}** ({target_csv}) สำเร็จเรียบร้อยแล้ว!")
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลวันที่ 3 ตัวบน และ 2 ตัวล่างให้ครบถ้วน")

# เมนูที่ 2: แสดงประวัติทั้งหมด
elif menu == "2. แสดงประวัติ (History)":
    st.header(f"📊 ประวัติผลรางวัลหวยฮานอยย้อนหลัง ({selected_day_tab})")
    st.write(f"📁 กำลังแสดงข้อมูลจากไฟล์: `{active_csv_file}`")
    if not df_main.empty:
        st.dataframe(df_main, use_container_width=True)
    else:
        st.info(f"ยังไม่มีข้อมูลในไฟล์ของวัน {selected_day_tab}")

# เมนูที่ 3: ลบข้อมืองวดล่าสุด
elif menu == "3. ลบข้อมืองวดล่าสุด":
    st.header(f"🗑️ ลบข้อมูลผลรางวัล (งวดล่าสุด - {selected_day_tab})")
    st.write(f"📁 จากไฟล์: `{active_csv_file}`")
    if not df_main.empty and 'date' in df_main.columns:
        st.write("ข้อมืองวดล่าสุดด้านบนสุดที่จะถูกลบ:")
        st.dataframe(df_main.head(1), use_container_width=True)
        
        if st.button("ยืนยันการลบงวดล่าสุด"):
            if len(df_main) > 0:
                df_main = df_main.iloc[1:].reset_index(drop=True)
                df_main.to_csv(active_csv_file, index=False)
                st.success("✅ ลบงวดล่าสุดเรียบร้อยแล้ว")
                st.rerun()
    else:
        st.info("ไม่มีข้อมูลให้ลบในไฟล์นี้")

# เมนูที่ 4: จัดอันดับสูตร
elif menu == "4. Formula Ranking (จัดอันดับสูตร)":
    st.header(f"🏆 จัดอันดับความแม่นยำของสูตร ({selected_day_tab})")
    st.write(f"📁 วิเคราะห์จากไฟล์: `{active_csv_file}`")
    
    if st.button("เริ่มคำนวณสถิติย้อนหลัง"):
        with st.spinner("กำลังประมวลผล Backtest..."):
            if df_main.empty or 'date' not in df_main.columns:
                st.warning("⚠️ ข้อมูลไม่เพียงพอสำหรับการคำนวณย้อนหลังในไฟล์นี้")
            else:
                df = df_main.copy()
                df["dt"] = df["date"].apply(parse_thai_date)
                df = df.dropna(subset=["dt"]).sort_values(by="dt", ascending=True).reset_index(drop=True)
                df["weekday_en"] = df["dt"].dt.day_name()
                
                total = len(df) - 1
                if total <= 0:
                    st.warning("⚠️ ต้องการข้อมูลมากกว่า 1 งวดขึ้นไปสำหรับการคำนวณย้อนหลัง")
                else:
                    scores = {
                        "Carry Over (ดึงเลขเก่า)": 0,
                        "±1 (วิ่ง/รูด)": 0,
                        "Sum Modulo (ผลรวม)": 0,
                        "Cross Sum (สูตรไขว้)": 0,
                        "Daily 6-Digit": 0,
                        "Rotation (โต๊ด)": 0,
                        "Mirror (กระจก)": 0,
                        "Shift (+2)": 0,
                        "Double (เบิ้ล)": 0,
                        "Sandwich (หาม)": 0,
                    }

                    for i in range(1, len(df)):
                        prev = df.iloc[i - 1]
                        row = df.iloc[i]
                        t3 = str(row.get("top_3", "000")).zfill(3)
                        b2 = str(row.get("bottom_2", "00")).zfill(2)
                        base_t3 = str(prev.get("top_3", "000")).zfill(3)
                        base_b2 = str(prev.get("bottom_2", "00")).zfill(2)
                        daily_6 = DAILY_NUMBERS.get(row["weekday_en"], "000000")

                        trans = get_transformations(base_t3, base_b2)

                        if any(str(d) in t3 or str(d) in b2 for d in trans["carry_over"]): scores["Carry Over (ดึงเลขเก่า)"] += 1
                        if any(str(d) in t3 or str(d) in b2 for d in trans["pm1"]): scores["±1 (วิ่ง/รูด)"] += 1
                        if any(str(d) in t3 or str(d) in b2 for d in trans["sum_formulas"]): scores["Sum Modulo (ผลรวม)"] += 1
                        if any(str(d) in t3 or str(d) in b2 for d in trans["cross_formulas"]): scores["Cross Sum (สูตรไขว้)"] += 1
                        if any(c in t3 or c in b2 for c in daily_6): scores["Daily 6-Digit"] += 1
                        if any(rot in t3 for rot in trans["rotations"]) or any(any(c in b2 for c in rot) for rot in trans["rotations"]): scores["Rotation (โต๊ด)"] += 1
                        if any(c in t3 or c in b2 for c in trans["mirror"]): scores["Mirror (กระจก)"] += 1
                        if any(c in t3 or c in b2 for c in trans["shifted"]): scores["Shift (+2)"] += 1
                        if any(dbl in t3 or dbl in b2 for dbl in trans["doubles"]): scores["Double (เบิ้ล)"] += 1
                        if any(snd in t3 for snd in trans["sandwiches"]): scores["Sandwich (หาม)"] += 1

                    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                    
                    result_data = []
                    for rank, (formula, score) in enumerate(ranked, 1):
                        percentage = (score / total) * 100
                        result_data.append({
                            "อันดับ": rank,
                            "ชื่อสูตร": formula,
                            "คะแนนที่ถูก": f"{score}/{total}",
                            "ความแม่นยำ (%)": f"{percentage:.1f}%"
                        })
                    
                    st.table(pd.DataFrame(result_data))

# เมนูที่ 5: ทำนายงวดถัดไป
elif menu == "5. Forward Prediction (ทำนายงวดถัดไป)":
    st.header("🔮 Forward Prediction (ทำนายแนวทางงวดถัดไป)")
    st.write(f"📁 อ้างอิงข้อมืองวดล่าสุดจากไฟล์: `{active_csv_file}` ({selected_day_tab})")
    
    if not df_main.empty and 'date' in df_main.columns:
        latest = df_main.iloc[0]
        if pd.isna(latest['date']) or str(latest['date']).strip() == "":
            st.warning(f"⚠️ ไฟล์ `{active_csv_file}` ยังไม่มีข้อมูลผลรางวัล กรุณาไปเพิ่มข้อมูลในเมนูที่ 1 ก่อน")
        else:
            latest_dt = parse_thai_date(latest['date'])
            
            st.write(f"📅 ข้อมูลงวดล่าสุดวันที่: **{latest['date']}**")
            st.write(f"3 ตัวบน: `{latest.get('top_3', '-')}` | 2 ตัวล่าง: `{latest.get('bottom_2', '-')}`")
            
            if pd.notna(latest_dt):
                next_dt = latest_dt + pd.Timedelta(days=1)
                day_selected = next_dt.day_name()
                st.info(f"📅 ระบบคำนวณวันของงวดถัดไปให้อัตโนมัติ: **{day_selected}** ({next_dt.strftime('%d/%m/%Y')})")
            else:
                day_selected = st.selectbox(
                    "เลือกวันของงวดถัดไป",
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                )
            
            if st.button("ประมวลผลทำนายเลข"):
                daily_6 = DAILY_NUMBERS.get(day_selected, "000000")
                if day_selected == "Saturday":
                    st.warning("⚠️ [AI WARNING] วันเสาร์มีสถิติการออก 'เลขเบิ้ล' และ 'เลขหาม' สูงมาก แนะนำให้ติดชุดกันไว้เสมอ!")
                    
                trans = get_transformations(str(latest.get('top_3', '000')), str(latest.get('bottom_2', '00')))
                carry_list = sorted(list(trans['carry_over']))
                pm1_list = sorted(list(trans['pm1']))
                sum_list = sorted(list(trans['sum_formulas']))
                cross_list = sorted(list(trans['cross_formulas']))
                
                digit_scores = {str(i): 0.0 for i in range(10)}
                for d in daily_6: digit_scores[d] += 2.0
                for d in carry_list: digit_scores[str(d)] += 2.0
                for d in pm1_list: digit_scores[str(d)] += 1.5
                for d in sum_list: digit_scores[d] += 1.5
                for d in cross_list: digit_scores[str(d)] += 1.0
                for d in trans['mirror']: digit_scores[d] += 1.0
                for d in trans['shifted']: digit_scores[d] += 1.0

                sorted_digits = sorted(digit_scores.keys(), key=lambda k: digit_scores[k], reverse=True)
                den = sorted_digits[0]
                rong_list = sorted_digits[1:4]
                gun_list = sorted_digits[4:7]
                
                st.success(f"🎯 **สรุปแนวทางเลขเด่นทำนายงวดถัดไป ({day_selected})**")
                col1, col2, col3 = st.columns(3)
                col1.metric("เด่น", den, f"{digit_scores[den]:.1f} แต้ม")
                col2.metric("รอง", " - ".join(rong_list))
                col3.metric("กัน", " - ".join(gun_list))
                
                suggested_2d = [f"{den}{r}" for r in rong_list] + [f"{r}{den}" for r in rong_list]
                suggested_3d = [f"{den}{rong_list[0]}{rong_list[1]}"]
                suggested_double = [f"{den}{den}", f"{rong_list[0]}{rong_list[0]}"]
                
                st.markdown("---")
                st.write(f"• **ชุด 2 ตัวเน้นๆ (ไป-กลับ) :** {', '.join(suggested_2d)}")
                st.write(f"• **ชุด 3 ตัวบนแนะนำ        :** {', '.join(suggested_3d)}")
                st.write(f"• **ชุด 2 ตัวเบิ้ล (แนะนำ)    :** {', '.join(suggested_double)}")
    else:
        st.info(f"ยังไม่มีข้อมูลในไฟล์ของวัน {selected_day_tab} หรือไฟล์ว่างเปล่า กรุณาอัปเพิ่มในเมนูที่ 1 ก่อน")
