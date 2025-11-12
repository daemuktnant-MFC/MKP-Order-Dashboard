import streamlit as st
import pandas as pd
import plotly.express as px
import openpyxl
import requests  # 👈 (เพิ่มใหม่)
from bs4 import BeautifulSoup  # 👈 (เพิ่มใหม่)
import io  # 👈 (เพิ่มใหม่)
import numpy as np  # 👈 (เพิ่มใหม่)
import warnings  # 👈 (เพิ่มใหม่)

# ----------------------------------------------------------------------
# 1. ตั้งค่าหน้า Dashboard
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Marketplace Dashboard",
    page_icon="📊",
    layout="wide"
)

# ----------------------------------------------------------------------
# 2. กำหนดค่าคงที่และฟังก์ชันโหลดข้อมูล (ปรับปรุงใหม่)
# ----------------------------------------------------------------------

# --- (สำคัญ!) ตั้งค่าการ Login และ URL (จาก VBA) ---
LOGIN_URL = "https://10.12.173.84/MarketPlace/Home/Logon"
DOWNLOAD_URL = "https://10.12.173.84/MarketPlace/PickingList/PrintReport"
USERNAME = "30034388"  # (จาก VBA)
PASSWORD = "9"     # (จาก VBA)

# กำหนดสีตามโจทย์ (เหมือนเดิม)
COLOR_MAP = {
    "Canpick": "#0066FF",
    "Cannotpick": "#FF9966",
}
STORE_COLOR_MAP = {
    7888: "#009999",
    7886: "#33CCCC"
}

# ----------------------------------------------------------------------
# 💥 (ใหม่!) ฟังก์ชันนี้ถูกสร้างขึ้นมาแทนที่ VBA ทั้งหมด
# ----------------------------------------------------------------------
@st.cache_data(ttl=600)  # Cache ข้อมูลไว้ 10 นาที
# 💥 (อัปเดต!) เพิ่ม '_' ที่ log_placeholder เพื่อบอก Streamlit ให้ข้ามการ Caching
def fetch_all_data(_log_placeholder):
    """
    ฟังก์ชันนี้จำลองการทำงานของ VBA Modules 1-4... (อัปเดตเพิ่ม Referer)
    """

    # 1. สร้าง Session และปิดการตรวจสอบ SSL (สำหรับ IP ภายใน)
    s = requests.Session()
    s.verify = False

    # (ใหม่!) เพิ่ม Header User-Agent เพื่อปลอมเป็นเบราว์เซอร์
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'
    }
    s.headers.update(headers)
    # -----------------------------------------------------------

    warnings.filterwarnings('ignore', 'Unverified HTTPS request')

    # 2. GET หน้า Login เพื่อดึง Token (เหมือน VBA)
    try:
        login_page_response = s.get(LOGIN_URL)
        login_page_response.raise_for_status()
        soup = BeautifulSoup(login_page_response.text, 'html.parser')
        token = soup.find('input', {'name': '__RequestVerificationToken'})['value']
    except Exception as e:
        # 💥 (อัปเดต!) เขียน Error ลงใน placeholder แทน
        _log_placeholder.error(f"❌ [Step 1 FAILED] ไม่สามารถเชื่อมต่อหน้า Login ({LOGIN_URL}) ได้: {e}")
        return pd.DataFrame()

    # 3. POST ข้อมูล Login (เหมือน VBA)
    login_data = {
        '__RequestVerificationToken': token,
        'LoginType': 'UserAuthentication',
        'Username': USERNAME,
        'Password': PASSWORD
    }

    # (อัปเดต!) เพิ่ม 'Referer' header สำหรับการ POST โดยเฉพาะ
    post_headers = {
        'Referer': LOGIN_URL
    }

    try:
        # (อัปเดต!) ส่ง headers ที่อัปเดตไปพร้อมกับ POST
        login_response = s.post(LOGIN_URL, data=login_data, headers=post_headers)
        login_response.raise_for_status()

        # (อัปเดต!) แก้ไขเงื่อนไขการตรวจสอบ Login
        if "MarketPlace" not in login_response.url or "Logon" in login_response.url:
             # 💥 (อัปเดต!) เขียน Error ลงใน placeholder แทน
             _log_placeholder.error(f"❌ [Step 2 FAILED] Login ไม่สำเร็จ! (อาจรหัสผ่านผิด หรือ Server ปฏิเสธ)")
             _log_placeholder.warning(f"Debug: Server redirect ไปที่ URL: {login_response.url}")
             return pd.DataFrame()

    except Exception as e:
        # 💥 (อัปเดต!) เขียน Error ลงใน placeholder แทน
        _log_placeholder.error(f"❌ [Step 2 FAILED] การ Login ล้มเหลว: {e}")
        return pd.DataFrame()

    # 💥 (อัปเดต!) เขียน Success ลงใน placeholder แทน
    _log_placeholder.success("✅ [Step 1 & 2] Login สำเร็จ!")

    # 4. กำหนด Report 4 ตัวที่ต้องดึง (จาก Modules 1-4)
    reports_to_fetch = [
        {'store': '7888', 'type': '1', 'remark': 'Canpick'},      # Module 1
        {'store': '7888', 'type': '2', 'remark': 'Cannotpick'},  # Module 2
        {'store': '7886', 'type': '1', 'remark': 'Canpick'},      # Module 3
        {'store': '7886', 'type': '2', 'remark': 'Cannotpick'}   # Module 4
    ]

    all_dataframes = []
    # 💥 (อัปเดต!) เขียน Progress Bar ลงใน placeholder แทน
    progress_bar = _log_placeholder.progress(0, "เริ่มต้นดาวน์โหลดข้อมูล...")

    # 5. วนลูปดึงข้อมูลทั้ง 4 Report (เหมือน VBA)
    for i, report in enumerate(reports_to_fetch):
        try:
            msg = f"กำลังดาวน์โหลด: {report['remark']} Store {report['store']}..."
            # 💥 (อัปเดต!) เขียน Status ลงใน placeholder แทน
            _log_placeholder.write(msg)
            progress_bar.progress((i+1)/len(reports_to_fetch), msg)

            params = {'typereport': report['type'], 'storeno': report['store']}
            download_response = s.get(DOWNLOAD_URL, params=params)
            download_response.raise_for_status()

            # VBA เริ่ม copy ที่ A3 (header คือแถว 3)
            # ดังนั้นใน Pandas header=2 (0-indexed)
            df_temp = pd.read_excel(io.BytesIO(download_response.content), header=2)

            # VBA Copy A:G (7 คอลัมน์)
            df_temp = df_temp.iloc[:, 0:7]
            df_temp.columns = ['ColA', 'ColB', 'ColC', 'ColD', 'ColE', 'ColF', 'ColG']

            # VBA เติมคอลัมน์ H และ I
            df_temp['Remark'] = report['remark']
            df_temp['Store'] = int(report['store']) # แปลงเป็นตัวเลขเพื่อความถูกต้อง

            all_dataframes.append(df_temp)

        except Exception as e:
            # 💥 (อัปเดต!) เขียน Warning ลงใน placeholder แทน
            _log_placeholder.warning(f"⚠️ ดาวน์โหลด {report['remark']} {report['store']} ล้มเหลว: {e}")

    progress_bar.empty()
    if not all_dataframes:
        # 💥 (อัปเดต!) เขียน Error ลงใน placeholder แทน
        _log_placeholder.error("❌ [Step 3 FAILED] ไม่สามารถดาวน์โหลดข้อมูลได้เลย")
        return pd.DataFrame()

    # 💥 (อัปเดต!) เขียน Success ลงใน placeholder แทน
    _log_placeholder.success(f"✅ [Step 3] ดาวน์โหลดข้อมูลทั้ง {len(all_dataframes)} ส่วนสำเร็จ!")

    # 6. รวม DataFrame (เหมือน VBA ที่ Paste ลงชีตเดียวกัน)
    df_combined = pd.concat(all_dataframes, ignore_index=True)

    # 7. ลบข้อมูลซ้ำ (เหมือน VBA)
    # VBA ใช้ Columns:=2 (คือ ColB หรือ 'Order ID')
    df_combined = df_combined.drop_duplicates(subset=['ColB'], keep='first')

    # 8. คำนวณ BoxesQty (เหมือนสูตรใน Runmine.txt)
    # สูตร VBA: =IF(RC[-3]/RC[-4]<1,RC[-3],RC[-3]/RC[-4])
    # คือ: J = IF(G/F < 1, G, G/F)

    col_f_num = pd.to_numeric(df_combined['ColF'], errors='coerce')
    col_g_num = pd.to_numeric(df_combined['ColG'], errors='coerce')

    # แทนค่า 0 ใน ColF ด้วย NaN เพื่อป้องกันหารด้วย 0
    col_f_safe = col_f_num.replace(0, np.nan)

    ratio = col_g_num / col_f_safe

    # ใช้ np.where เพื่อจำลอง IF
    df_combined['ColJ_BoxesQty'] = np.where(
        ratio < 1,  # เงื่อนไข (G/F < 1)
        col_g_num,  # ถ้าจริง (ใช้ G)
        ratio       # ถ้าเท็จ (ใช้ G/F)
    )

    # ถ้าเกิด NaN (เช่น F=0 หรือ G/F < 1 เป็นเท็จ) ให้ใช้ค่าจาก ColG แทน
    df_combined['ColJ_BoxesQty'] = df_combined['ColJ_BoxesQty'].fillna(col_g_num)


    # 9. เปลี่ยนชื่อคอลัมน์ให้ตรงกับที่ Dashboard คาดหวัง
    df_final = df_combined.rename(columns={
        'ColA': 'Seller Center', # Index 0
        'ColB': 'Order ID',      # Index 1
        'ColD': 'SKU (TPNB)',    # Index 3
        'ColE': 'Description',   # Index 4
        'Remark': 'Remark',      # Index 7 (VBA Col H)
        'Store': 'Store',        # Index 8 (VBA Col I)
        'ColJ_BoxesQty': 'BoxesQty' # Index 9 (VBA Col J)
    })

    # 10. เลือกเฉพาะคอลัมน์ที่ Dashboard ต้องการใช้
    final_columns = [
        'Seller Center', 'Order ID', 'SKU (TPNB)', 'Description',
        'Remark', 'Store', 'BoxesQty'
    ]
    df_final = df_final[final_columns]

    # 11. ทำความสะอาดข้อมูลครั้งสุดท้าย (เหมือนโค้ดเดิม)
    df_final['BoxesQty'] = pd.to_numeric(df_final['BoxesQty'], errors='coerce').fillna(0).astype(int)

    # 💥 (อัปเดต!) เขียน Success ลงใน placeholder แทน
    _log_placeholder.success("✅ [Step 4] ประมวลผลข้อมูลและคำนวณ BoxesQty สำเร็จ!")
    return df_final


# ----------------------------------------------------------------------
# 3. ส่วน Main Logic (💥 ปรับปรุงใหม่ทั้งหมด 💥)
# ----------------------------------------------------------------------

def main():

    # --- (ROW 1: Title and Button) ---
    col_title, col_button_space = st.columns([1.5, 1])
    with col_title:
        st.markdown(
            '<h2 style="font-size: 51px;">📊 Marketplace Dashboard</h2>',
            unsafe_allow_html=True
        )
    with col_button_space:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_button_clicked = st.button("🚀 Fetch Latest Data", use_container_width=True, help="กดเพื่อดึงข้อมูลล่าสุดจากเว็บ (แทนการรัน Macro)")

    df = pd.DataFrame() # กำหนด df ว่างเปล่าล่วงหน้า

    # --- (กำหนด Layout ของกราฟไว้ล่วงหน้า) ---
    
    # --- (ROW 2: Section 1 and Pie Chart) ---
    sec1_col_left, sec1_col_right = st.columns([1.5, 1])
    
    # --- (ROW 3: Section 2 and Section 3) ---
    st.divider() # เพิ่มเส้นคั่นระหว่างแถว
    sec2_col_left, sec2_col_right = st.columns([1.5, 1])

    # --- (ROW 4: Log Area) ---
    st.divider() # เพิ่มเส้นคั่น
    st.header("4. สถานะการดึงข้อมูล (Log)")
    log_container = st.container(border=True) # สร้าง container เปล่าๆ

    # ------------------------------------------------------------------
    # 💥 Logic การ Fetch และแสดงผล
    # ------------------------------------------------------------------

    # ถ้ายังไม่กดปุ่ม ให้แสดง Info ใน Log
    if not fetch_button_clicked:
        log_container.info("กรุณากดปุ่ม 'Fetch Latest Data' เพื่อเริ่มแสดงผลแดชบอร์ด", icon="⬆️")

    # ถ้ากดปุ่มแล้ว
    if fetch_button_clicked:
        try:
            # ล้าง cache ก่อนดึงใหม่
            st.cache_data.clear()
            # 💥 (อัปเดต!) ส่ง log_container เข้าไปในฟังก์ชัน
            df = fetch_all_data(log_container)
        except Exception as e:
            log_container.error(f"เกิดข้อผิดพลาดร้ายแรงในการโหลดข้อมูล: {e}")
            df = pd.DataFrame()

    # ------------------------------------------------------------------
    # 💥 ส่วนแสดงผลกราฟ (จะทำงานเมื่อ df มีข้อมูล)
    # ------------------------------------------------------------------
    if not df.empty:

        # --- (แสดงผลใน ROW 2: Section 1 and Pie) ---
        with sec1_col_left:
            Stores = df['Store'].unique()
            # (โค้ดส่วน Section 1... เหมือนเดิมทุกประการ)
            st.header("1. Pending by Store")
            bar_cols = st.columns(len(Stores))

            for i, Store in enumerate(Stores):
                with bar_cols[i]:
                    st.subheader(f"Store: {Store}")
                    Store_df = df[df['Store'] == Store]

                    order_data = Store_df.groupby('Remark')['Order ID'].nunique().reset_index()
                    order_data['Metric'] = 'Order Count'
                    order_data = order_data.rename(columns={'Order ID': 'Value'})
                    box_data = Store_df.groupby('Remark')['BoxesQty'].sum().reset_index()
                    box_data['Metric'] = 'Boxes Qty'
                    box_data = box_data.rename(columns={'BoxesQty': 'Value'})
                    combined_data = pd.concat([order_data, box_data])
                    total_order_count = combined_data[combined_data['Metric'] == 'Order Count']['Value'].sum()
                    total_boxes_qty = combined_data[combined_data['Metric'] == 'Boxes Qty']['Value'].sum()

                    fig_bar = px.bar(
                        combined_data, x='Metric', y='Value', color='Remark',
                        barmode='stack', color_discrete_map=COLOR_MAP,
                        text='Value', category_orders={"Remark": ["Canpick", "Cannotpick"]}
                    )
                    fig_bar.update_traces(textposition='inside', textangle=0, textfont_size=11)

                    fig_bar.add_annotation(
                        x='Order Count', y=total_order_count * 1.05,
                        text=f"Total Order : {total_order_count:,}",
                        showarrow=False, font=dict(size=14, color="black", family="Arial Black")
                    )
                    fig_bar.add_annotation(
                        x='Boxes Qty', y=total_boxes_qty * 1.1,
                        text=f"Total Boxes : {total_boxes_qty:,}",
                        showarrow=False, font=dict(size=14, color="black", family="Arial Black")
                    )

                    y_max = max(total_order_count, total_boxes_qty) * 1.2
                    fig_bar.update_yaxes(range=[0, y_max])
                    st.plotly_chart(fig_bar, use_container_width=True)

        with sec1_col_right:
            # เพิ่ม <br> เพื่อให้ Pie Chart เริ่มในระดับเดียวกับ Header 1
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True) 
            
            # (โค้ดส่วน Pie Chart... เหมือนเดิมทุกประการ)
            pie_data = df.groupby('Store')['Order ID'].nunique().reset_index()
            pie_data = pie_data.rename(columns={'Order ID': 'Total Order Count'})

            fig_pie = px.pie(
                pie_data,
                values='Total Order Count',
                names='Store',
                hole=.3,
                color='Store',
                color_discrete_map=STORE_COLOR_MAP
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='text',
                texttemplate="%{value:,}<br>(%{percent})",
                hoverinfo='label+percent+value',
                textfont_size=16,
                rotation=360,
                sort=False
            )
            fig_pie.update_layout(
                margin=dict(t=0, b=0, l=0, r=0),
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=0.5,
                    xanchor="right",
                    x=-0.2
                )
            )
            fig_pie.update_traces(
                textposition='inside',
                textinfo='percent+value',
                texttemplate="%{value:,}<br>(%{percent})",
                hoverinfo='label+percent+value',
                textfont_size=18
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- (แสดงผลใน ROW 3: Section 2 and Section 3) ---
        with sec2_col_left:
            Stores = df['Store'].unique()
            # (โค้ดส่วน Section 2... เหมือนเดิมทุกประการ)
            st.header("2. Pending by Seller Center")
            stack_cols = st.columns(len(Stores))

            for i, Store in enumerate(Stores):
                with stack_cols[i]:
                    st.subheader(f"Store: {Store}")
                    Store_df = df[df['Store'] == Store]

                    stack_data = Store_df.groupby(['Seller Center', 'Remark'])['Order ID'].nunique().reset_index()
                    total_order_by_seller = stack_data.groupby('Seller Center')['Order ID'].sum().reset_index()

                    fig_stack = px.bar(
                        stack_data, x='Seller Center', y='Order ID', color='Remark',
                        barmode='stack', color_discrete_map=COLOR_MAP,
                        text='Order ID', category_orders={"Remark": ["Canpick", "Cannotpick"]}
                    )
                    fig_stack.update_traces(textposition='inside', textangle=0, textfont_size=11)

                    y_max_store = 0
                    for _, row in total_order_by_seller.iterrows():
                        seller = row['Seller Center']
                        total_count = row['Order ID']
                        fig_stack.add_annotation(
                            x=seller, y=total_count * 1.1,
                            text=f"Total Order : {total_count:,}",
                            showarrow=False, font=dict(size=14, color="black", family="Arial Black")
                        )
                        if total_count > y_max_store:
                            y_max_store = total_count

                    fig_stack.update_yaxes(range=[0, y_max_store * 1.2])
                    st.plotly_chart(fig_stack, use_container_width=True)

        with sec2_col_right:
            # (โค้ดส่วน Section 3... เหมือนเดิมทุกประการ)
            
            # 💥 (สำคัญ!) ต้องนิยามฟังก์ชัน helper นี้ก่อนเรียกใช้
            def display_top_10(df_all, store_id, title_col):
                # (โค้ดฟังก์ชัน display_top_10 เหมือนเดิม)
                cant_pick_store_df = df_all[
                    (df_all['Remark'] == "Cannotpick") &
                    (df_all['Store'].astype(str) == str(store_id))
                ]
                with title_col:
                    st.subheader(f"Store {store_id} (Top 10 Cannotpick)")
                    if cant_pick_store_df.empty:
                        st.info(f"ไม่พบข้อมูล 'Cannotpick' สำหรับ Store {store_id}")
                        return
                    top_data = cant_pick_store_df.groupby(['SKU (TPNB)', 'Description'])['BoxesQty'].sum().reset_index()
                    top_data = top_data.sort_values(by='BoxesQty', ascending=False).head(10).reset_index(drop=True)
                    top_data.index = top_data.index + 1
                    top_data = top_data.rename_axis('Rank')
                    st.dataframe(
                        top_data,
                        use_container_width=True,
                        column_config={"BoxesQty": st.column_config.NumberColumn("BoxesQty", format="%d")}
                    )

            st.header("3. Top 10 รายการ 'Cannotpick' (แยกตาม Store)")
            col_7888, col_7886 = st.columns(2)
            display_top_10(df, 7888, col_7888)
            display_top_10(df, 7886, col_7886)


if __name__ == '__main__':
    main()
