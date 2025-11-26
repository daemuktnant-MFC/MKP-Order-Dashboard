import streamlit as st
import pandas as pd
import plotly.express as px
import openpyxl
import requests
from bs4 import BeautifulSoup
import io
import numpy as np
import warnings
from requests.adapters import HTTPAdapter # 👈 (เพิ่มใหม่)
from urllib3.util.retry import Retry      # 👈 (เพิ่มใหม่)

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
USERNAME = "30034388" 
PASSWORD = "9"      

# กำหนดสีตามโจทย์
COLOR_MAP = {
    "Canpick": "#0066FF",
    "Cannotpick": "#FF9966",
}
STORE_COLOR_MAP = {
    7888: "#009999",
    7886: "#33CCCC"
}

# ----------------------------------------------------------------------
# 💥 (แก้ไข!) ฟังก์ชันดึงข้อมูล เพิ่มการแก้ Proxy และ Timeout
# ----------------------------------------------------------------------
@st.cache_data(ttl=600)
def fetch_all_data(_log_placeholder):
    """
    ฟังก์ชันนี้จำลองการทำงานของ VBA Modules 1-4... (อัปเดตแก้ Proxy/Timeout)
    """

    # 1. สร้าง Session
    s = requests.Session()
    
    # 🚨 FIX 1: ปิดการใช้ System Proxy (เพื่อให้วิ่งตรงหา IP 10.x.x.x ได้)
    s.trust_env = False 
    
    # 🚨 FIX 2: ปิดการตรวจสอบ SSL
    s.verify = False
    
    # 🚨 FIX 3: เพิ่มระบบ Retry (ลองใหม่ 3 ครั้งถ้าต่อไม่ติด)
    retry_strategy = Retry(
        total=3,
        backoff_factor=1, # รอ 1 วินาทีก่อนลองใหม่
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    s.mount("https://", adapter)
    s.mount("http://", adapter)

    # Header User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'
    }
    s.headers.update(headers)
    
    warnings.filterwarnings('ignore', 'Unverified HTTPS request')

    # กำหนด Timeout (วินาที)
    TIMEOUT_SEC = 15

    # 2. GET หน้า Login เพื่อดึง Token
    try:
        # ใส่ timeout เพื่อไม่ให้ค้างยาว
        login_page_response = s.get(LOGIN_URL, timeout=TIMEOUT_SEC)
        login_page_response.raise_for_status()
        soup = BeautifulSoup(login_page_response.text, 'html.parser')
        
        # ตรวจสอบว่ามี Token ไหม
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        if not token_input:
             _log_placeholder.error(f"❌ [Step 1 FAILED] ไม่พบ Token ในหน้า Login (อาจเข้าผิดหน้า หรือต้อง VPN)")
             return pd.DataFrame()
             
        token = token_input['value']

    except requests.exceptions.ConnectTimeout:
        _log_placeholder.error(f"❌ [Step 1 FAILED] เชื่อมต่อ Server ไม่ได้ (Timeout) กรุณาตรวจสอบว่าต่อ VPN หรือสาย LAN บริษัทแล้วหรือยัง?")
        return pd.DataFrame()
    except Exception as e:
        _log_placeholder.error(f"❌ [Step 1 FAILED] ไม่สามารถเชื่อมต่อหน้า Login ได้: {e}")
        return pd.DataFrame()

    # 3. POST ข้อมูล Login
    login_data = {
        '__RequestVerificationToken': token,
        'LoginType': 'UserAuthentication',
        'Username': USERNAME,
        'Password': PASSWORD
    }

    post_headers = {
        'Referer': LOGIN_URL
    }

    try:
        login_response = s.post(LOGIN_URL, data=login_data, headers=post_headers, timeout=TIMEOUT_SEC)
        login_response.raise_for_status()

        if "MarketPlace" not in login_response.url or "Logon" in login_response.url:
             _log_placeholder.error(f"❌ [Step 2 FAILED] Login ไม่สำเร็จ! (Username/Password ผิด หรือ Server ปฏิเสธ)")
             return pd.DataFrame()

    except Exception as e:
        _log_placeholder.error(f"❌ [Step 2 FAILED] การ Login ล้มเหลว: {e}")
        return pd.DataFrame()

    _log_placeholder.success("✅ [Step 1 & 2] Login สำเร็จ!")

    # 4. กำหนด Report 4 ตัว
    reports_to_fetch = [
        {'store': '7888', 'type': '1', 'remark': 'Canpick'},
        {'store': '7888', 'type': '2', 'remark': 'Cannotpick'},
        {'store': '7886', 'type': '1', 'remark': 'Canpick'},
        {'store': '7886', 'type': '2', 'remark': 'Cannotpick'}
    ]

    all_dataframes = []
    progress_bar = _log_placeholder.progress(0, "เริ่มต้นดาวน์โหลดข้อมูล...")

    # 5. วนลูปดึงข้อมูล
    for i, report in enumerate(reports_to_fetch):
        try:
            msg = f"กำลังดาวน์โหลด: {report['remark']} Store {report['store']}..."
            _log_placeholder.write(msg)
            progress_bar.progress((i+1)/len(reports_to_fetch), msg)

            params = {'typereport': report['type'], 'storeno': report['store']}
            
            # ใส่ timeout ตอนโหลดไฟล์ด้วย
            download_response = s.get(DOWNLOAD_URL, params=params, timeout=TIMEOUT_SEC)
            download_response.raise_for_status()

            df_temp = pd.read_excel(io.BytesIO(download_response.content), header=2)
            df_temp = df_temp.iloc[:, 0:7]
            df_temp.columns = ['ColA', 'ColB', 'ColC', 'ColD', 'ColE', 'ColF', 'ColG']
            df_temp['Remark'] = report['remark']
            df_temp['Store'] = int(report['store'])

            all_dataframes.append(df_temp)

        except Exception as e:
            _log_placeholder.warning(f"⚠️ ดาวน์โหลด {report['remark']} {report['store']} ล้มเหลว: {e}")

    progress_bar.empty()
    if not all_dataframes:
        _log_placeholder.error("❌ [Step 3 FAILED] ไม่สามารถดาวน์โหลดข้อมูลได้เลย")
        return pd.DataFrame()

    _log_placeholder.success(f"✅ [Step 3] ดาวน์โหลดข้อมูลทั้ง {len(all_dataframes)} ส่วนสำเร็จ!")

    # 6. รวม DataFrame
    df_combined = pd.concat(all_dataframes, ignore_index=True)

    # 7. ลบข้อมูลซ้ำ
    df_combined = df_combined.drop_duplicates(subset=['ColB'], keep='first')

    # 8. คำนวณ BoxesQty
    col_f_num = pd.to_numeric(df_combined['ColF'], errors='coerce')
    col_g_num = pd.to_numeric(df_combined['ColG'], errors='coerce')
    col_f_safe = col_f_num.replace(0, np.nan)
    ratio = col_g_num / col_f_safe

    df_combined['ColJ_BoxesQty'] = np.where(
        ratio < 1,
        col_g_num,
        ratio
    )
    df_combined['ColJ_BoxesQty'] = df_combined['ColJ_BoxesQty'].fillna(col_g_num)

    # 9. เปลี่ยนชื่อคอลัมน์
    df_final = df_combined.rename(columns={
        'ColA': 'Seller Center', 
        'ColB': 'Order ID',
        'ColD': 'SKU (TPNB)',
        'ColE': 'Description',
        'Remark': 'Remark',
        'Store': 'Store',
        'ColJ_BoxesQty': 'BoxesQty'
    })

    # 10. เลือกเฉพาะคอลัมน์ที่ใช้
    final_columns = [
        'Seller Center', 'Order ID', 'SKU (TPNB)', 'Description',
        'Remark', 'Store', 'BoxesQty'
    ]
    df_final = df_final[final_columns]
    df_final['BoxesQty'] = pd.to_numeric(df_final['BoxesQty'], errors='coerce').fillna(0).astype(int)

    _log_placeholder.success("✅ [Step 4] ประมวลผลข้อมูลและคำนวณ BoxesQty สำเร็จ!")
    return df_final


# ----------------------------------------------------------------------
# 3. ส่วน Main Logic
# ----------------------------------------------------------------------

def main():

    col_title, col_button_space = st.columns([1.5, 1])
    with col_title:
        st.markdown(
            '<h2 style="font-size: 51px;">📊 Marketplace Dashboard</h2>',
            unsafe_allow_html=True
        )
    with col_button_space:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_button_clicked = st.button("🚀 Fetch Latest Data", use_container_width=True, help="กดเพื่อดึงข้อมูลล่าสุดจากเว็บ (แทนการรัน Macro)")

    df = pd.DataFrame()

    sec1_col_left, sec1_col_right = st.columns([1.5, 1])
    st.divider()
    sec2_col_left, sec2_col_right = st.columns([1.5, 1])

    st.divider()
    st.header("4. สถานะการดึงข้อมูล (Log)")
    log_container = st.container(border=True)

    if not fetch_button_clicked:
        log_container.info("กรุณากดปุ่ม 'Fetch Latest Data' เพื่อเริ่มแสดงผลแดชบอร์ด", icon="⬆️")

    if fetch_button_clicked:
        try:
            st.cache_data.clear()
            df = fetch_all_data(log_container)
        except Exception as e:
            log_container.error(f"เกิดข้อผิดพลาดร้ายแรงในการโหลดข้อมูล: {e}")
            df = pd.DataFrame()

    if not df.empty:

        with sec1_col_left:
            Stores = df['Store'].unique()
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
                    # จัดรูปแบบตัวเลขให้มี comma
                    text_labels = ['{:,.0f}'.format(val) for val in combined_data['Value']]
                    fig_bar.update_traces(text=text_labels)

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
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True) 
            
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
                textinfo='percent+value',
                texttemplate="%{value:,}<br>(%{percent})",
                hoverinfo='label+percent+value',
                textfont_size=18,
                rotation=360,
                sort=False
            )
            fig_pie.update_layout(
                margin=dict(t=0, b=0, l=0, r=0),
                showlegend=True,
                legend=dict(orientation="v", yanchor="top", y=0.5, xanchor="right", x=-0.2)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with sec2_col_left:
            Stores = df['Store'].unique()
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
                    
                    text_labels_stack = ['{:,.0f}'.format(val) for val in stack_data['Order ID']]
                    fig_stack.update_traces(text=text_labels_stack, textposition='inside', textangle=0, textfont_size=11)

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
            
            def display_top_10(df_all, store_id, title_col):
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
