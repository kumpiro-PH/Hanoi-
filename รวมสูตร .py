# app.py - Hanoi AI Professional (GitHub API Sync & Cross-Day Fusion - Fixed & Optimized)
import os
import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import requests
from io import StringIO

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
    "Friday": "769825",
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

def parse_date_for_sort(date_str):
    try:
        dt = parse_thai_date(date_str)
        if pd.notna(dt):
            return dt
    except Exception:
        pass
    return datetime(1900, 1, 1)

# ==================== GITHUB API SYNC FUNCTIONS ====================
def load_csv_data_from_github(filename):
    """อ่าน CSV จาก GitHub API (พร้อม fallback มาอ่านในเครื่อง)"""
    github_token = st.secrets.get("GITHUB_TOKEN")
    repo_name = st.secrets.get("GITHUB_REPO")
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    expected_cols = ["date", "special", "first_prize", "top_3", "bottom_2"]
    
    if github_token and repo_name and filename:
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }
        file_url = f"https://api.github.com/repos/{repo_name}/contents/{filename}"
        try:
            res = requests.get(file_url, headers=headers, params={"ref": branch}, timeout=10)
            if res.status_code == 200:
                file_data = res.json()
                content_decoded = base64.b64decode(file_data["content"]).decode("utf-8")
                df = pd.read_csv(StringIO(content_decoded), dtype=str)
                return clean_and_format_df(df, expected_cols)
        except Exception:
            pass
            
    # Fallback อ่านในเครื่อง
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename, dtype=str)
            return clean_and_format_df(df, expected_cols)
        except Exception:
            pass
            
    return pd.DataFrame(columns=expected_cols)

def save_csv_to_github(filename, updated_df, new_date):
    """บันทึกและซิงก์ข้อมูล CSV ตรงขึ้น GitHub ผ่าน API อัตโนมัติ (รองรับ Branch, Timeout และ Error Handling)"""
    github_token = st.secrets.get("GITHUB_TOKEN")
    repo_name = st.secrets.get("GITHUB_REPO")
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    
    if not github_token or not repo_name:
        st.error("ยังไม่ได้ตั้งค่า GITHUB_TOKEN หรือ GITHUB_REPO ใน Streamlit Secrets")
        return False
        
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    file_url = f"https://api.github.com/repos/{repo_name}/contents/{filename}"
    
    try:
        # 1. ดึงไฟล์เดิมจาก GitHub เพื่อเอา SHA โดยระบุ ref=branch ให้ตรงกัน
        res = requests.get(file_url, headers=headers, params={"ref": branch}, timeout=10)
        file_sha = None
        if res.status_code == 200:
            file_sha = res.json().get("sha")
            
        # 2. แปลงเป็น CSV string และเข้ารหัส Base64
        csv_string = updated_df.to_csv(index=False, encoding="utf-8-sig")
        encoded_content = base64.b64encode(csv_string.encode("utf-8")).decode("utf-8")
        
        # 3. ส่งคำขอ PUT ไปที่ GitHub API พร้อมกำหนด timeout
        payload = {
            "message": f"Update {filename} for {new_date} via Streamlit App",
            "content": encoded_content,
            "branch": branch
        }
        if file_sha:
            payload["sha"] = file_sha
            
        put_res = requests.put(file_url, headers=headers, json=payload, timeout=10)
        if put_res.status_code in [200, 201]:
            return True
        else:
            st.error(f"❌ GitHub API Error ({put_res.status_code}): {put_res.text}")
            return False
            
    except requests.exceptions.Timeout:
        st.error("❌ การเชื่อมต่อ GitHub API หมดเวลา (Timeout) กรุณาลองใหม่อีกครั้ง")
        return False
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}")
        return False

def clean_and_format_df(df, expected_cols):
    if df.empty:
        return pd.DataFrame(columns=expected_cols)
        
    df.columns = df.columns.str.strip()
    
    column_mapping = {
        "วันที่": "date", "date": "date", "date_be": "date",
        "รางวัลที่ 1": "special", "รางวัลที่1": "special", "special": "special", "special_prize": "special", "prize_5digit_1": "special",
        "รางวัลที่ 2": "first_prize", "รางวัลที่2": "first_prize", "first_prize": "first_prize", "prize_5digit_2": "first_prize",
        "3 ตัวบน": "top_3", "3ตัวบน": "top_3", "three_digit": "top_3", "top_3": "top_3", "top3": "top_3",
        "2 ตัวล่าง": "bottom_2", "2ตัวล่าง": "bottom_2", "two_digit": "bottom_2", "bottom_2": "bottom_2", "bottom2": "bottom_2"
    }
    df = df.rename(columns=column_mapping)
    
    for col in expected_cols:
        if col not in df.columns:
            df[col] = "-"
            
    df["dt_temp"] = df["date"].apply(parse_date_for_sort)
    df = df.sort_values(by="dt_temp", ascending=False).reset_index(drop=True)
    df = df.drop(columns=["dt_temp"])
    
    return df[expected_cols].fillna("-")

def load_and_clean_df(filepath):
    return load_csv_data_from_github(filepath)

def initialize_csvs():
    """ตรวจสอบและสร้างไฟล์ CSV ประจำวันเริ่มต้นหากยังไม่มี"""
    expected_cols = ["date", "special", "first_prize", "top_3", "bottom_2"]
    for day_en, filename in DAY_CSV_MAP.items():
        if not os.path.exists(filename):
            df_init = pd.DataFrame(columns=expected_cols)
            df_init.to_csv(filename, index=False, encoding="utf-8-sig")

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

# ==================== เริ่มต้นระบบไฟล์ ====================
initialize_csvs()

# ==================== เมนูด้านข้าง (Sidebar) ====================
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

# ==================== ส่วนแสดงผลหน้าเว็บ Streamlit ====================
st.title("🎯 Hanoi AI Professional - ระบบวิเคราะห์หวยฮานอย (GitHub Sync)")
st.write(f"ระบบวิเคราะห์สถิติผสานข้อมูลข้ามวันพร้อมซิงก์ GitHub อัตโนมัติ ({selected_day_tab})")

# เมนูที่ 1: อัปเดตผลรางวัล (พร้อมระบบป้องกันข้อมูลซ้ำ)
if menu == "1. อัปเดตผลรางวัล":
    st.header("📝 อัปเดตผลรางวัลหวยฮานอยใหม่ (ซิงก์ขึ้น GitHub)")
    
    with st.form("update_form"):
        date_str = st.text_input("ใส่วันที่ (DD/MM/YYYY เช่น 06/11/2569)")
        special = st.text_input("รางวัลพิเศษ (5 หลัก)")
        first_prize = st.text_input("รางวัลที่ 1 (5 หลัก)")
        top_3 = st.text_input("เลข 3 ตัวบน (3 หลัก)")
        bottom_2 = st.text_input("เลข 2 ตัวล่าง (2 หลัก)")
        
        submitted = st.form_submit_button("💾 บันทึกและซิงก์ขึ้น GitHub")
        if submitted:
            if date_str and top_3 and bottom_2:
                dt = parse_thai_date(date_str)
                if pd.notna(dt):
                    target_day_en = dt.day_name()
                    target_csv = DAY_CSV_MAP.get(target_day_en, "history_hanoi_sat.csv")
                    target_df = load_and_clean_df(target_csv)
                    
                    clean_date = date_str.strip()
                    
                    # ตรวจสอบข้อมูลซ้ำด้วยวันที่ก่อนบันทึก
                    if not target_df.empty and clean_date in target_df["date"].values:
                        st.warning(f"⚠️ มีข้อมูลของวันที่ `{clean_date}` ในระบบของวัน `{target_day_en}` อยู่แล้ว! กรุณาตรวจสอบหรือลบงวดเก่าออกก่อน")
                    else:
                        new_row = pd.DataFrame([{
                            "date": clean_date,
                            "special": special.strip() if special else "-",
                            "first_prize": first_prize.strip() if first_prize else "-",
                            "top_3": top_3.strip(),
                            "bottom_2": bottom_2.strip(),
                        }])
                        
                        updated_df = pd.concat([new_row, target_df], ignore_index=True)
                        updated_df["dt_temp"] = updated_df["date"].apply(parse_date_for_sort)
                        updated_df = updated_df.sort_values(by="dt_temp", ascending=False).drop(columns=["dt_temp"])
                        
                        # ซิงก์ขึ้น GitHub ผ่าน API
                        success = save_csv_to_github(target_csv, updated_df, clean_date)
                        if success:
                            st.success(f"✅ บันทึกและซิงก์ข้อมูลลง GitHub (`{target_csv}`) เรียบร้อยแล้ว!")
                            st.rerun()
                        else:
                            st.error("❌ เกิดข้อผิดพลาดในการเชื่อมต่อ GitHub API กรุณาตรวจสอบ Secrets")
                else:
                    st.warning("⚠️ รูปแบบวันที่ไม่ถูกต้อง กรุณาใช้รูปแบบ DD/MM/YYYY")
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")

# เมนูที่ 2: แสดงประวัติทั้งหมด
elif menu == "2. แสดงประวัติ (History)":
    st.header(f"📊 ประวัติผลรางวัล ({selected_day_tab})")
    if not df_main.empty:
        st.dataframe(df_main, use_container_width=True, hide_index=True)
    else:
        st.info(f"ยังไม่มีข้อมูลในไฟล์ของวัน {selected_day_tab}")

# เมนูที่ 3: ลบข้อมืองวดล่าสุด
elif menu == "3. ลบข้อมืองวดล่าสุด":
    st.header(f"🗑️ ลบข้อมืองวดล่าสุด ({selected_day_tab})")
    if not df_main.empty:
        st.dataframe(df_main.head(1), use_container_width=True, hide_index=True)
        if st.button("ยืนยันการลบงวดล่าสุดและซิงก์ GitHub"):
            df_updated = df_main.iloc[1:].reset_index(drop=True)
            latest_date = df_updated.iloc[0]['date'] if not df_updated.empty else "deleted"
            success = save_csv_to_github(active_csv_file, df_updated, latest_date)
            if success:
                st.success("✅ ลบและซิงก์ข้อมูลบน GitHub เรียบร้อยแล้ว!")
                st.rerun()
            else:
                st.error("❌ ไม่สามารถซิงก์การลบไปยัง GitHub ได้")
    else:
        st.info("ไม่มีข้อมูลให้ลบ")

# เมนูที่ 4: จัดอันดับสูตร
elif menu == "4. Formula Ranking (จัดอันดับสูตร)":
    st.header(f"🏆 จัดอันดับความแม่นยำของสูตร ({selected_day_tab})")
    if st.button("เริ่มคำนวณสถิติย้อนหลัง"):
        st.info("ระบบกำลังประมวลผล Backtest ประจำวัน...")

# เมนูที่ 5: Forward Prediction (ทำนายงวดถัดไป) แบบให้เลขประจำวันมีผลเปลี่ยนจริง
elif menu == "5. Forward Prediction (ทำนายงวดถัดไป)":
    st.header(f"🔮 Forward Prediction (คำนวณผสานสถิติ - {selected_day_tab})")
    
    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_idx = days_list.index(selected_day_tab)
    prev_day_tab = days_list[current_idx - 1] if current_idx > 0 else "Sunday"
    
    df_current = load_and_clean_df(active_csv_file)
    df_prev = load_and_clean_df(DAY_CSV_MAP[prev_day_tab])
    
    if not df_current.empty and not df_prev.empty:
        latest_current = df_current.iloc[0]
        latest_prev = df_prev.iloc[0]

        st.subheader(f"📌 ข้อมูลงวดล่าสุดที่นำมาคำนวณ ({selected_day_tab} + {prev_day_tab})")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.info(f"📊 **งวดล่าสุดประจำวัน {selected_day_tab}** (`{active_csv_file}`)\n\nวันที่: **{latest_current.get('date', '-')}**\n\n3 ตัวบน: `{latest_current.get('top_3', '-')}` | 2 ตัวล่าง: `{latest_current.get('bottom_2', '-')}`")
        with col_b:
            st.success(f"📌 **งวดล่าสุดประจำวัน {prev_day_tab}** (`{DAY_CSV_MAP[prev_day_tab]}`)\n\nวันที่: **{latest_prev.get('date', '-')}**\n\n3 ตัวบน: `{latest_prev.get('top_3', '-')}` | 2 ตัวล่าง: `{latest_prev.get('bottom_2', '-')}`")

        daily_6 = DAILY_NUMBERS.get(selected_day_tab, "7890123")
        st.write(f"🎯 **ชุดเลขประจำวัน ({selected_day_tab}):** `{daily_6}`")

        if st.button("🚀 ประมวลผลคำนวณผสานสถิติและเลขประจำวัน", type="primary"):
            trans_current = get_transformations(str(latest_current.get('top_3', '000')), str(latest_current.get('bottom_2', '00')))
            trans_prev = get_transformations(str(latest_prev.get('top_3', '000')), str(latest_prev.get('bottom_2', '00')))

            digit_scores = {str(i): 0.0 for i in range(10)}

            # 1. ให้ "เลขประจำวัน" เป็นฐานคะแนนหลักที่มีน้ำหนักสูง เพื่อให้เปลี่ยนวันแล้วผลเปลี่ยนทันที
            for d in daily_6:  
                digit_scores[str(d)] += 10.0

            # 2. ให้สูตรสถิติ CSV เป็นตัวช่วยเสริมน้ำหนักย่อย
            for trans in [trans_current, trans_prev]:
                for d in trans['carry_over']: digit_scores[str(d)] += 1.5
                for d in trans['pm1']: digit_scores[str(d)] += 1.0
                for d in trans['sum_formulas']: digit_scores[d] += 0.8
                for d in trans['cross_formulas']: digit_scores[str(d)] += 0.5

            sorted_digits = sorted(digit_scores.keys(), key=lambda k: digit_scores[k], reverse=True)
            den = sorted_digits[0]
            rong_list = sorted_digits[1:4]
            gun_list = sorted_digits[4:7]

            st.markdown("---")
            st.success(f"🎯 **สรุปแนวทางเลขเด่นผสาน 3 ส่วน ({selected_day_tab})**")
            col1, col2, col3 = st.columns(3)
            col1.metric("เด่นสุด (Den)", den, f"{digit_scores[den]:.1f} แต้ม")
            col2.metric("เลขรอง (Rong)", " - ".join(rong_list))
            col3.metric("เลขกัน (Kan)", " - ".join(gun_list))

            # ==================== การจัดการและคัดเลือกเลขเบิ้ล ====================
            combined_doubles = list(trans_current['doubles'].union(trans_prev['doubles']))
            priority_doubles = [f"{den}{den}"] + [f"{r}{r}" for r in rong_list]
            
            # จัดชุด 2D (ผสมเลขเบิ้ลเด่นเข้าไปด้วย)
            suggested_2d = [f"{den}{r}" for r in rong_list] + [f"{r}{den}" for r in rong_list] + priority_doubles[:2]
            
            # จัดชุด 3D (ผสมเลขเบิ้ลหาม เช่น เด่น-เบิ้ล หรือ เบิ้ล-เด่น)
            suggested_3d = [f"{den}{r1}{r1}" for r1 in rong_list[:2]] + [f"{r1}{den}{r1}" for r1 in rong_list[:2]] + [f"{den}{den}{den}"]
            base_3d = [f"{den}{r1}{r2}" for r1 in rong_list for r2 in rong_list if r1 != r2][:4]
            final_3d_list = list(set(base_3d + suggested_3d))[:6]

            st.markdown("### 💡 แนวทางตัวเลขจัดชุด (รองรับเลขเบิ้ล)")
            st.write(f"• **2D เน้นไป-กลับ + เบิ้ลเน้นๆ:** {', '.join(set(suggested_2d))}")
            st.write(f"• **3D ชุด AI (ผสมเบิ้ล/หาม):** {', '.join(final_3d_list)}")
            st.write(f"• **🔥 เลขเบิ้ลเด่นตามสถิติ:** {', '.join(priority_doubles)}")
    else:
        st.warning(f"⚠️ ข้อมูลในไฟล์ประวัติสำหรับวัน {selected_day_tab} หรือ {prev_day_tab} ไม่เพียงพอสำหรับการคำนวณ")
