import streamlit as st
import pandas as pd
import plotly.express as px
import openpyxl  # Pandas ต้องใช้ openpyxl ในการอ่านไฟล์ .xlsm

# ----------------------------------------------------------------------
# 1. ตั้งค่าหน้า Dashboard
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Marketplace Dashboard",
    page_icon="📊",
    layout="wide"  # ใช้พื้นที่หน้าจอเต็มความกว้าง
)

# ----------------------------------------------------------------------
# 2. กำหนดค่าคงที่และฟังก์ชันโหลดข้อมูล
# ----------------------------------------------------------------------

# --- (สำคัญ!) ตั้งชื่อชีตของคุณที่นี่ ---
SHEET_NAME = "MarketplaceData"

# กำหนดสีตามโจทย์
COLOR_MAP = {
    "Canpick": "#00CC66",    # สีสำหรับ Canpick
    "Cannotpick": "#FF5050",   # สีสำหรับ Cannotpick
}

# กำหนดสีสำหรับ Store โดยเฉพาะตามโจทย์
STORE_COLOR_MAP = {
    7888: "#009999", # สีเขียว (ตามโค้ดเดิม)
    7886: "#33CCCC"  # สีเขียวอ่อน (ตามโค้ดเดิม)
}

@st.cache_data  # Cache ข้อมูลไว้ ไม่ต้องโหลดใหม่ทุกครั้งที่ทำอะไร
def load_data(uploaded_file, sheet_name):
    """
    โหลดข้อมูลจากไฟล์ Excel ที่อัปโหลด โดยใช้ตำแหน่งคอลัมน์
    """
    try:
        # **ใช้ตำแหน่งคอลัมน์ (Index) แทนชื่อคอลัมน์ Excel (A=0, B=1, D=3, E=4, H=7, I=8, J=9)**
        use_cols_indices = [0, 1, 3, 4, 7, 8, 9] 
        
        # **กำหนดชื่อคอลัมน์ใหม่ตามลำดับ Index**
        new_column_names = [
            'Seller Center', 'Order ID', 'SKU (TPNB)', 'Description',
            'Remark', 'Store', 'BoxesQty'
        ]
        
        df = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_name,
            engine='openpyxl',
            usecols=use_cols_indices, # ใช้ตำแหน่งคอลัมน์
            header=0 # กำหนดว่า Row แรกเป็น Header
        )
        
        # **กำหนดชื่อคอลัมน์ใหม่โดยตรง**
        df.columns = new_column_names
        
        # แปลง BoxesQty เป็นตัวเลข (เผื่อมีค่าที่ไม่ใช่ตัวเลข)
        df['BoxesQty'] = pd.to_numeric(df['BoxesQty'], errors='coerce').fillna(0).astype(int)

        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame()

# ----------------------------------------------------------------------
# 3. ส่วน Main Logic (รวมการแสดงผล Header และ Logic หลักทั้งหมด)
# ----------------------------------------------------------------------

def main():
    
    # 💥 FIX: สร้าง 2 คอลัมน์หลักสำหรับ Layout ใหม่
    # (คอลัมน์ซ้ายสำหรับ Section 1 & 2, คอลัมน์ขวาสำหรับ Header, Pie, Uploader, Section 3)
    # ให้คอลัมน์ซ้าย (Charts) กว้างกว่าคอลัมน์ขวา (Tables/Uploader)
    left_main_col, right_main_col = st.columns([1.5, 1])

    uploaded_file = None
    df = pd.DataFrame() # กำหนด df เป็น DataFrame ว่างเปล่าล่วงหน้า

    # ------------------------------------------------------------------
    # 💥 คอลัมน์ขวา (Header, Uploader, Pie Chart, Section 3)
    # ------------------------------------------------------------------
    with right_main_col:
        st.markdown("<br>", unsafe_allow_html=True) 
        uploaded_file = st.file_uploader("", type=["xlsx", "xlsm"])

        # โหลดข้อมูลทันทีเมื่อมีการอัปโหลดไฟล์
        if uploaded_file is not None:
            df = load_data(uploaded_file, SHEET_NAME)

        # Pie Chart: ยอดรวม Order ID (ไม่ซ้ำ) แยกตาม Store
        if not df.empty:
            st.markdown("<br>", unsafe_allow_html=True) 

            # 1. เตรียมข้อมูลสำหรับ Pie Chart
            pie_data = df.groupby('Store')['Order ID'].nunique().reset_index()
            pie_data = pie_data.rename(columns={'Order ID': 'Total Order Count'})
            
            # 2. สร้าง Pie Chart
            fig_pie = px.pie(
                pie_data,
                values='Total Order Count',
                names='Store',
                hole=.3, 
                color='Store', 
                color_discrete_map=STORE_COLOR_MAP
            )

            # ตั้งค่า rotation และ sort
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='text',
                texttemplate="%{value:,}<br>(%{percent})", 
                hoverinfo='label+percent+value',
                textfont_size=16,
                rotation=360, 
                sort=False 
            )

            # ย้าย Legend
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
            
            # ปรับรูปแบบ Label (โค้ดซ้ำซ้อนจาก `update_traces` ด้านบน แต่คงไว้ตามไฟล์เดิม)
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent+value',
                texttemplate="%{value:,}<br>(%{percent})",
                hoverinfo='label+percent+value',
                textfont_size=18
            )

            # แสดงผล Pie Chart
            st.plotly_chart(fig_pie, use_container_width=True)
        
        else:
            # แสดงข้อความเมื่อยังไม่มีไฟล์อัปโหลด
            st.info("กรุณาอัปโหลดไฟล์ Excel เพื่อเริ่มแสดงผลแดชบอร์ด", icon="⬆️")
            st.markdown("<br>", unsafe_allow_html=True) 

        # ------------------------------------------------------------------
        # 💥 Section 3: Top 10 (ย้ายมาไว้คอลัมน์ขวา)
        # ------------------------------------------------------------------
        if not df.empty:
            st.divider()

            # ฟังก์ชัน Top 10 รายการ Cannotpick (ต้องกำหนดไว้ก่อนใช้)
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
                
            # สร้างคอลัมน์สำหรับตาราง (ซ้อนภายในคอลัมน์ขวาหลัก)
            col_7888, col_7886 = st.columns(2)
            
            # สร้างตารางสำหรับ Store 7888
            display_top_10(df, 7888, col_7888)
            
            # สร้างตารางสำหรับ Store 7886
            display_top_10(df, 7886, col_7886)


    # ------------------------------------------------------------------
    # 💥 คอลัมน์ซ้าย (Section 1 & 2)
    # ------------------------------------------------------------------
    with left_main_col:
        # ส่วนนี้จะแสดงผลเมื่อ df ถูกโหลดข้อมูลแล้ว (จากคอลัมน์ขวา)
        st.markdown(
            '<h2 style="font-size: 51px;">📊 Marketplace Dashboard</h2>', 
            unsafe_allow_html=True
        )
        if not df.empty:
            
            # ดึงรายชื่อ Store ที่ไม่ซ้ำกัน
            Stores = df['Store'].unique()

            # ------------------------------------------------------------------
            # Section 1: Pending by Store (ย้ายมาไว้คอลัมน์ซ้าย)
            # ------------------------------------------------------------------
            st.header("1. Pending by Store")

            # สร้างคอลัมน์ใน Streamlit ให้เท่ากับจำนวน Store
            bar_cols = st.columns(len(Stores))

            for i, Store in enumerate(Stores):
                with bar_cols[i]:
                    st.subheader(f"Store: {Store}")
                    Store_df = df[df['Store'] == Store]
                    
                    # (โค้ดเตรียมข้อมูล Bar Chart เหมือนเดิม)
                    order_data = Store_df.groupby('Remark')['Order ID'].nunique().reset_index()
                    order_data['Metric'] = 'Order Count'
                    order_data = order_data.rename(columns={'Order ID': 'Value'})
                    box_data = Store_df.groupby('Remark')['BoxesQty'].sum().reset_index()
                    box_data['Metric'] = 'Boxes Qty'
                    box_data = box_data.rename(columns={'BoxesQty': 'Value'})
                    combined_data = pd.concat([order_data, box_data])
                    total_order_count = combined_data[combined_data['Metric'] == 'Order Count']['Value'].sum()
                    total_boxes_qty = combined_data[combined_data['Metric'] == 'Boxes Qty']['Value'].sum()

                    # สร้าง Stacked Bar Chart
                    fig_bar = px.bar(
                        combined_data, x='Metric', y='Value', color='Remark',
                        barmode='stack', color_discrete_map=COLOR_MAP,
                        text='Value', category_orders={"Remark": ["Canpick", "Cannotpick"]}
                    )
                    fig_bar.update_traces(textposition='inside', textangle=0, textfont_size=13)
                    
                    # Annotation (ยอดรวม)
                    fig_bar.add_annotation(
                        x='Order Count', y=total_order_count * 1.05, 
                        text=f"Total Order : {total_order_count:,}", 
                        showarrow=False, font=dict(size=14, color="black", family="Arial")
                    )
                    fig_bar.add_annotation(
                        x='Boxes Qty', y=total_boxes_qty * 1.1, 
                        text=f"Total Boxes : {total_boxes_qty:,}", 
                        showarrow=False, font=dict(size=14, color="black", family="Arial")
                    )
                    
                    y_max = max(total_order_count, total_boxes_qty) * 1.2 
                    fig_bar.update_yaxes(range=[0, y_max])
                    st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            # ------------------------------------------------------------------
            # Section 2: Pending by Seller Center (ย้ายมาไว้คอลัมน์ซ้าย)
            # ------------------------------------------------------------------
            st.header("2. Pending by Seller Center")

            stack_cols = st.columns(len(Stores))

            for i, Store in enumerate(Stores):
                with stack_cols[i]:
                    st.subheader(f"Store: {Store}")
                    Store_df = df[df['Store'] == Store]
                    
                    # (โค้ดเตรียมข้อมูล Stack Chart เหมือนเดิม)
                    stack_data = Store_df.groupby(['Seller Center', 'Remark'])['Order ID'].nunique().reset_index()
                    total_order_by_seller = stack_data.groupby('Seller Center')['Order ID'].sum().reset_index()
                    
                    # สร้าง Stacked Chart
                    fig_stack = px.bar(
                        stack_data, x='Seller Center', y='Order ID', color='Remark',
                        barmode='stack', color_discrete_map=COLOR_MAP,
                        text='Order ID', category_orders={"Remark": ["Canpick", "Cannotpick"]}
                    )
                    fig_stack.update_traces(textposition='inside', textangle=0, textfont_size=13)
                    
                    # Annotation (ยอดรวม)
                    y_max_store = 0
                    for _, row in total_order_by_seller.iterrows():
                        seller = row['Seller Center']
                        total_count = row['Order ID']
                        fig_stack.add_annotation(
                            x=seller, y=total_count * 1.1, 
                            text=f"Total Order : {total_count:,}",
                            showarrow=False, font=dict(size=14, color="black", family="Arial")
                        )
                        if total_count > y_max_store:
                            y_max_store = total_count

                    fig_stack.update_yaxes(range=[0, y_max_store * 1.2])
                    st.plotly_chart(fig_stack, use_container_width=True)
        
        else:
            # คอลัมน์ซ้ายจะว่างเปล่าหากยังไม่อัปโหลดไฟล์
            pass


if __name__ == '__main__':
    main()


