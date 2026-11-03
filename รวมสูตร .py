import os
import pandas as pd

# ==================== ชื่อไฟล์ฐานข้อมูลหลัก ====================
CSV_FILE = "history_hanoi.csv"

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
    """ฟังก์ชันแปลงวันที่พุทธศักราช (DD/MM/YYYY) เป็น ค.ศ. แบบปลอดภัย"""
    try:
        parts = str(x).strip().split("/")
        if len(parts) != 3:
            return pd.NaT
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        if year < 100:
            year += 2500
        return pd.Timestamp(year=year - 543, month=month, day=day)
    except Exception:
        return pd.NaT

def initialize_csv():
    """ตรวจสอบไฟล์ CSV หากยังไม่มีให้สร้างโครงสร้างเริ่มต้น"""
    if not os.path.exists(CSV_FILE):
        initial_data = """date,special,first_prize,top_3,bottom_2
30/09/2569,95242,82585,242,85
29/09/2569,05651,08389,651,89
28/09/2569,77115,86908,115,08"""
        with open(CSV_FILE, "w", encoding="utf-8") as f:
            f.write(initial_data)

def menu_update_result():
    """1. อัปเดตผลรางวัลใหม่ (แทรกไว้บนสุด)"""
    print("\n--- [1] อัปเดตผลรางวัลหวยฮานอย ---")
    date_str = input("ใส่วันที่ (DD/MM/YYYY เช่น 06/10/2569): ").strip()
    special = input("รางวัลพิเศษ (5 หลัก): ").strip()
    first_prize = input("รางวัลที่ 1 (5 หลัก): ").strip()
    top_3 = input("เลข 3 ตัวบน (3 หลัก): ").strip()
    bottom_2 = input("เลข 2 ตัวล่าง (2 หลัก): ").strip()

    new_row = pd.DataFrame([{
        "date": date_str,
        "special": special,
        "first_prize": first_prize,
        "top_3": top_3,
        "bottom_2": bottom_2,
    }])

    df = pd.read_csv(CSV_FILE)
    df = pd.concat([new_row, df], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)
    print("✅ บันทึกผลรางวัลใหม่สำเร็จเรียบร้อยแล้ว!")

def menu_show_history():
    """2. แสดง History ทั้งหมดแบบเต็มรูปแบบ (ไม่ตัดทอน)"""
    print("\n--- [2] ประวัติผลรางวัลหวยฮานอยย้อนหลังทั้งหมด ---")
    df = pd.read_csv(CSV_FILE)
    
    # ตั้งค่าให้ pandas แสดงข้อมูลทุกแถวและทุกคอลัมน์โดยไม่ตัดทอน
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    print(df.to_string())
    
    # รีเซ็ตค่ากลับเพื่อไม่ให้กระทบกับการแสดงผลส่วนอื่น
    pd.reset_option('display.max_rows')
    pd.reset_option('display.max_columns')

def menu_delete_data():
    """3. ลบข้อมืองวดล่าสุด (แถวแรก)"""
    print("\n--- [3] ลบข้อมูลผลรางวัล ---")
    df = pd.read_csv(CSV_FILE)
    print(df.head(5).to_string())
    choice = input("ต้องการลบงวดล่าสุด (แถวแรก) หรือไม่? (y/n): ").strip().lower()
    if choice == "y":
        df = df.iloc[1:].reset_index(drop=True)
        df.to_csv(CSV_FILE, index=False)
        print("✅ ลบงวดล่าสุดเรียบร้อยแล้ว")

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

def prepare_sorted_df():
    """โหลดและเรียงลำดับข้อมูลจากอดีต -> ปัจจุบัน เพื่อทำ Backtest"""
    df = pd.read_csv(CSV_FILE)
    df["dt"] = df["date"].apply(parse_thai_date)
    df = df.dropna(subset=["dt"])
    df = df.sort_values(by="dt", ascending=True).reset_index(drop=True)
    df["weekday_en"] = df["dt"].dt.day_name()
    return df

def menu_formula_ranking():
    """4. จัดอันดับความแม่นยำของสูตร (Formula Ranking)"""
    print("\n--- [4] Formula Ranking (จัดอันดับสูตรแม่นยำ) ---")
    df = prepare_sorted_df()
    total = len(df) - 1
    if total <= 0:
        print("⚠️ ข้อมูลไม่เพียงพอสำหรับการคำนวณย้อนหลัง")
        return

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
        t3 = str(row["top_3"]).zfill(3)
        b2 = str(row["bottom_2"]).zfill(2)
        base_t3 = str(prev["top_3"]).zfill(3)
        base_b2 = str(prev["bottom_2"]).zfill(2)
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

    print(f"ผลการจัดอันดับจากสถิติจริง {total} งวดล่าสุด:")
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    for rank, (formula, score) in enumerate(ranked, 1):
        percentage = (score / total) * 100
        print(f"{rank:2}. {formula:<22} -> ความแม่นยำ {score:>2}/{total} งวด ({percentage:.1f}%)")

def menu_forward_prediction():
    """6. ทำนายแนวทางงวดถัดไป (Forward Prediction พร้อมระบบ Weighted Score)"""
    print("\n--- [6] Forward Prediction (ทำนายแนวทางงวดถัดไป) ---")
    df = pd.read_csv(CSV_FILE)
    latest = df.iloc[0]
    
    sp_str = str(latest['special']).split('.')[0].zfill(5)
    fp_str = str(latest['first_prize']).split('.')[0].zfill(5)
    t3_str = str(latest['top_3']).split('.')[0].zfill(3)
    b2_str = str(latest['bottom_2']).split('.')[0].zfill(2)
    
    print(f"📅 ข้อมูลงวดล่าสุดวันที่: {latest['date']}")
    print(f"รางวัลพิเศษ: {sp_str} | รางวัลที่ 1: {fp_str}")
    print(f"3 ตัวบน: {t3_str} | 2 ตัวล่าง: {b2_str}")
    
    day_mapping = {
        "1": "Monday", "2": "Tuesday", "3": "Wednesday", "4": "Thursday",
        "5": "Friday", "6": "Saturday", "7": "Sunday"
    }
    
    print("\n[1] Monday | [2] Tuesday | [3] Wednesday | [4] Thursday")
    print("[5] Friday | [6] Saturday | [7] Sunday")
    day_input = input("ระบุวันของงวดถัดไป (ใส่ตัวเลข 1-7): ").strip()
    
    next_day_eng = day_mapping.get(day_input, "Monday")
    daily_6 = DAILY_NUMBERS.get(next_day_eng, "000000")
    
    if next_day_eng == "Saturday":
        print("\n⚠️ [AI WARNING] วันเสาร์มีสถิติการออก 'เลขเบิ้ล' และ 'เลขหาม' สูงมาก แนะนำให้ติดชุดกันไว้เสมอ!")
    
    trans = get_transformations(latest['top_3'], latest['bottom_2'])
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
    
    print("\n" + "="*40)
    print(f"🎯 **สรุปแนวทางเลขเด่นทำนายงวดถัดไป ({next_day_eng})**")
    print("="*40)
    print(f"เด่น: {den}  (คะแนนสูงสุด {digit_scores[den]:.1f} แต้ม)")
    print(f"รอง: {' - '.join(rong_list)}")
    print(f"กัน: {' - '.join(gun_list)}")
    
    suggested_2d = [f"{den}{r}" for r in rong_list] + [f"{r}{den}" for r in rong_list]
    suggested_3d = [f"{den}{rong_list[0]}{rong_list[1]}"]
    suggested_double = [f"{den}{den}", f"{rong_list[0]}{rong_list[0]}"]
    
    print(f"\n• ชุด 2 ตัวเน้นๆ (ไป-กลับ) : {', '.join(suggested_2d)}")
    print(f"• ชุด 3 ตัวบนแนะนำ        : {', '.join(suggested_3d)}")
    print(f"• ชุด 2 ตัวเบิ้ล (แนะนำ)    : {', '.join(suggested_double)}")
    print("="*40)

def main():
    
    while True:
        print("\n==============================")
        print("    HANOI AI PROFESSIONAL      ")
        print("==============================")
        print("1. อัปเดตผลรางวัล")
        print("2. แสดง History ทั้งหมด")
        print("3. ลบข้อมืองวดล่าสุด")
        print("4. Formula Ranking (จัดอันดับสูตร)")
        print("5. Forward Prediction (ทำนายงวดถัดไป)")
        print("0. Exit")
        print("==============================")

        choice = input("เลือกเมนู (0-5): ").strip()

        if choice == "1":
            menu_update_result()
        elif choice == "2":
            menu_show_history()
        elif choice == "3":
            menu_delete_data()
        elif choice == "4":
            menu_formula_ranking()
        elif choice == "5":
            menu_forward_prediction()
        elif choice == "0":
            print("ออกจากระบบเรียบร้อย ขอบคุณที่ใช้งานครับ")
            break
        else:
            print("⚠️ กรุณาเลือกเมนูระหว่าง 0 ถึง 5 เท่านั้น")

if __name__ == "__main__":
    main()
