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
LOGIN_URL = "http://10.12.173.84/MarketPlace/Home/Logon"
DOWNLOAD_URL = "http://10.12.173.84/MarketPlace/PickingList/PrintReport"
USERNAME = "30034388"  # (จาก VBA [cite: 344, 356, 326, 186])
PASSWORD = "9"       # (จาก VBA [cite: 344, 356, 326, 186])

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
def fetch_all_data():
    """
    ฟังก์ชันนี้จำลองการทำงานของ VBA Modules 1-4 และ Runmine ทั้งหมด
    โดยใช้ Python requests เพื่อ login, ดาวน์โหลด, และประมวลผลข้อมูล
    """
    
    # 1. สร้าง Session และปิดการตรวจสอบ SSL (สำหรับ IP ภายใน)
    s = requests.Session()
    s.verify = False
    warnings.filterwarnings('ignore', 'Unverified HTTPS request')

    # 2. GET หน้า Login เพื่อดึง Token (เหมือน VBA)
    try:
        login_page_response = s.get(LOGIN_URL)
        login_page_response.raise_for_status()
        soup = BeautifulSoup(login_page_response.text, 'html.parser')
        token = soup.find('input', {'name': '__RequestVerificationToken'})['value']
    except Exception as e:
        st.error(f"❌ [Step 1 FAILED] ไม่สามารถเชื่อมต่อหน้า Login ({LOGIN_URL}) ได้: {e}")
        return pd.DataFrame()

    # 3. POST ข้อมูล Login (เหมือน VBA)
    login_data = {
        '__RequestVerificationToken': token,
        'LoginType': 'UserAuthentication',
        'Username': USERNAME,
        'Password': PASSWORD
    }
    try:
        login_response = s.post(LOGIN_URL, data=login_data)
        login_response.raise_for_status()
        if "MarketPlace/PickingList" not in login_response.url: # ตรวจสอบว่า login สำเร็จ
             st.error(f"❌ [Step 2 FAILED] Login ไม่สำเร็จ! (อาจรหัสผ่านผิด)")
             return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ [Step 2 FAILED] การ Login ล้มเหลว: {e}")
        return pd.DataFrame()
    
    st.success("✅ [Step 1 & 2] Login สำเร็จ!")

    # 4. กำหนด Report 4 ตัวที่ต้องดึง (จาก Modules 1-4)
    reports_to_fetch = [
        {'store': '7888', 'type': '1', 'remark': 'Canpick'},      # Module 1 [cite: 343]
        {'store': '7888', 'type': '2', 'remark': 'Cannotpick'},  # Module 2 [cite: 356]
        {'store': '7886', 'type': '1', 'remark': 'Canpick'},      # Module 3 [cite: 326]
        {'store': '7886', 'type': '2', 'remark': 'Cannotpick'}   # Module 4 [cite: 185]
    ]
    
    all_dataframes = []
    progress_bar = st.progress(0, "เริ่มต้นดาวน์โหลดข้อมูล...")

    # 5. วนลูปดึงข้อมูลทั้ง 4 Report (เหมือน VBA)
    for i, report in enumerate(reports_to_fetch):
        try:
            msg = f"กำลังดาวน์โหลด: {report['remark']} Store {report['store']}..."
            st.write(msg) # แสดงสถานะ
            progress_bar.progress((i+1)/len(reports_to_fetch), msg)

            params = {'typereport': report['type'], 'storeno': report['store']}
            download_response = s.get(DOWNLOAD_URL, params=params)
            download_response.raise_for_status()

            # VBA เริ่ม copy ที่ A3 (header คือแถว 3) [cite: 352, 365, 335, 194]
            # ดังนั้นใน Pandas header=2 (0-indexed)
            df_temp = pd.read_excel(io.BytesIO(download_response.content), header=2)
            
            # VBA Copy A:G (7 คอลัมน์) [cite: 352, 365, 335, 194]
            df_temp = df_temp.iloc[:, 0:7]
            df_temp.columns = ['ColA', 'ColB', 'ColC', 'ColD', 'ColE', 'ColF', 'ColG']
            
            # VBA เติมคอลัมน์ H และ I [cite: 352, 365, 335, 194]
            df_temp['Remark'] = report['remark']
            df_temp['Store'] = int(report['store']) # แปลงเป็นตัวเลขเพื่อความถูกต้อง
            
            all_dataframes.append(df_temp)
            
        except Exception as e:
            st.warning(f"⚠️ ดาวน์โหลด {report['remark']} {report['store']} ล้มเหลว: {e}")

    progress_bar.empty()
    if not all_dataframes:
        st.error("❌ [Step 3 FAILED] ไม่สามารถดาวน์โหลดข้อมูลได้เลย")
        return pd.DataFrame()

    st.success(f"✅ [Step 3] ดาวน์โหลดข้อมูลทั้ง {len(all_dataframes)} ส่วนสำเร็จ!")

    # 6. รวม DataFrame (เหมือน VBA ที่ Paste ลงชีตเดียวกัน)
    df_combined = pd.concat(all_dataframes, ignore_index=True)

    # 7. ลบข้อมูลซ้ำ (เหมือน VBA [cite: 195])
    # VBA ใช้ Columns:=2 (คือ ColB หรือ 'Order ID')
    df_combined = df_combined.drop_duplicates(subset=['ColB'], keep='first')

    # 8. คำนวณ BoxesQty (เหมือนสูตรใน Runmine.txt [cite: 341])
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
    # (จากโค้ดเดิมของคุณ `use_cols_indices = [0, 1, 3, 4, 7, 8, 9]`)
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
    
    st.success("✅ [Step 4] ประมวลผลข้อมูลและคำนวณ BoxesQty สำเร็จ!")
    return df_final


# ----------------------------------------------------------------------
# 3. ส่วน Main Logic (ปรับปรุงใหม่)
# ----------------------------------------------------------------------

def main():
    
    left_main_col, right_main_col = st.columns([1.5, 1])
    df = pd.DataFrame() # กำหนด df ว่างเปล่าล่วงหน้า

    # ------------------------------------------------------------------
    # 💥 คอลัมน์ขวา (ปุ่ม Fetch, Pie Chart, Section 3)
    # ------------------------------------------------------------------
    with right_main_col:
        st.markdown("<br>", unsafe_allow_html=True) 
        
        # 💥 (ใหม่!) แทนที่ File Uploader ด้วยปุ่ม Fetch Data
        if st.button("🚀 Fetch Latest Data", use_container_width=True, help="กดเพื่อดึงข้อมูลล่าสุดจากเว็บ (แทนการรัน Macro)"):
            # ล้าง cache ก่อนดึงใหม่
            st.cache_data.clear()
            
        # พยายามโหลดข้อมูลจาก Cache (ที่อาจถูกสร้างโดยปุ่ม)
        try:
            df = fetch_all_data()
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
            df = pd.DataFrame()


        # Pie Chart: ยอดรวม Order ID (ไม่ซ้ำ) แยกตาม Store
        if not df.empty:
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
        
        else:
            # แสดงข้อความเมื่อยังไม่มีข้อมูล
            st.info("กรุณากดปุ่ม 'Fetch Latest Data' เพื่อเริ่มแสดงผลแดชบอร์ด", icon="⬆️")
            st.markdown("<br>", unsafe_allow_html=True) 

        # ------------------------------------------------------------------
        # 💥 Section 3: Top 10 (เหมือนเดิม)
        # ------------------------------------------------------------------
        if not df.empty:
            st.divider()

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


    # ------------------------------------------------------------------
    # 💥 คอลัมน์ซ้าย (Section 1 & 2) (เหมือนเดิม)
    # ------------------------------------------------------------------
    with left_main_col:
        st.markdown(
            '<h2 style="font-size: 51px;">📊 Marketplace Dashboard</h2>', 
            unsafe_allow_html=True
        )
        if not df.empty:
            
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

            st.divider()

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
        
        else:
            pass


if __name__ == '__main__':
    main()

