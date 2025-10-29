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
    "Canpick": "#0066FF",    # สีสำหรับ Canpick
    "Cannotpick": "#FF9966"   # สีสำหรับ Cannotpick
}

@st.cache_data  # Cache ข้อมูลไว้ ไม่ต้องโหลดใหม่ทุกครั้งที่ทำอะไร
def load_data(uploaded_file, sheet_name):
    """
    โหลดข้อมูลจากไฟล์ Excel ที่อัปโหลด โดยใช้ตำแหน่งคอลัมน์
    """
    try:
        # **ใช้ตำแหน่งคอลัมน์ (Index) แทนชื่อคอลัมน์ Excel (A=0, B=1, D=3, H=7, I=8, J=9)**
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
        
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame()

# ----------------------------------------------------------------------
# 3. ส่วน Main Logic (รวมการแสดงผล Header และ Logic หลักทั้งหมด)
# ----------------------------------------------------------------------

def main():
    # 💥 แก้ไข: ใช้ st.columns เพื่อวาง Title และ File Uploader ในบรรทัดเดียวกัน
    title_col, upload_col = st.columns([1.5, 1]) # เปลี่ยนเป็น [1.5, 1] เพื่อให้ upload กว้างขึ้นกว่า [1, 3]

    uploaded_file = None
    with title_col:
        # ใช้ Title ในคอลัมน์แรก
        st.header("📊 Marketplace Dashboard") 

    with upload_col:
        # ใช้ File Uploader ในคอลัมน์ที่สอง
        st.markdown("<br>", unsafe_allow_html=True) # คืนค่าช่องว่างเพื่อให้ตรงกับ header
        uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xlsm"])

    # --- ส่วนที่ 2: ตรวจสอบว่ามีการอัปโหลดไฟล์แล้วหรือยัง ---
    if uploaded_file is not None:
        
        # โหลดข้อมูลจากไฟล์ที่อัปโหลด
        df = load_data(uploaded_file, SHEET_NAME)

        if not df.empty:
            
            # ดึงรายชื่อ Store ที่ไม่ซ้ำกัน
            Stores = df['Store'].unique()

            st.divider()

            # ------------------------------------------------------------------
            # 1. Bar Chart: รวมข้อมูล Order ID (ไม่ซ้ำ) และ BoxesQty ใน 1 ชาร์ตต่อ Store
            # ------------------------------------------------------------------
            st.header("1. Pending by Store")

            # สร้างคอลัมน์ใน Streamlit ให้เท่ากับจำนวน Store
            bar_cols = st.columns(len(Stores))

            for i, Store in enumerate(Stores):
                with bar_cols[i]:
                    st.subheader(f"Store: {Store}")

                    # กรองข้อมูลเฉพาะ Store นี้
                    Store_df = df[df['Store'] == Store]

                    # 1.1 เตรียมข้อมูล: นับ Order ID และรวม BoxesQty

                    # นับจำนวน Order ID (ไม่ซ้ำ)
                    order_data = Store_df.groupby('Remark')['Order ID'].nunique().reset_index()
                    order_data['Metric'] = 'Order Count'
                    order_data = order_data.rename(columns={'Order ID': 'Value'})

                    # รวมยอด BoxesQty
                    box_data = Store_df.groupby('Remark')['BoxesQty'].sum().reset_index()
                    box_data['Metric'] = 'Boxes Qty'
                    box_data = box_data.rename(columns={'BoxesQty': 'Value'})

                    # รวม DataFrame ทั้งสองเข้าด้วยกัน
                    combined_data = pd.concat([order_data, box_data])
                    
                    # 💥 NEW: คำนวณยอดรวมสำหรับ Annotation (ต้องทำก่อนสร้าง fig)
                    total_order_count = combined_data[combined_data['Metric'] == 'Order Count']['Value'].sum()
                    total_boxes_qty = combined_data[combined_data['Metric'] == 'Boxes Qty']['Value'].sum()

                    # สร้าง Stacked Bar Chart
                    fig_bar = px.bar(
                        combined_data,
                        x='Metric',             
                        y='Value',               
                        color='Remark',         
                        title=f"Total Order & Total Boxess",
                        barmode='stack',        
                        color_discrete_map=COLOR_MAP,
                        text='Value',
                        category_orders={"Remark": ["Canpick", "Cannotpick"]}
                    )

                    # ปรับรูปแบบข้อความบนแท่งชาร์ต
                    fig_bar.update_traces(
                        textposition='inside',
                        # 💥 แก้ไข: ตั้งค่าเป็น 0 เพื่อให้ตัวเลขเป็นแนวตั้ง
                        textangle=0, 
                        # textfont=dict(size=11), # ไม่จำเป็นเมื่อใช้ textfont_size
                        textfont_size=11
                    )
                    
                    # 💥 NEW: เพิ่ม Annotation (ยอดรวม) ด้านบนแต่ละ Bar 💥

                    # 1. Annotation สำหรับ Order Count
                    fig_bar.add_annotation(
                        x='Order Count',
                        y=total_order_count * 1.05, 
                        text=f"Total: {total_order_count:,}", 
                        showarrow=False,
                        font=dict(size=14, color="black", family="Arial Black")
                    )

                    # 2. Annotation สำหรับ Boxes Qty
                    fig_bar.add_annotation(
                        x='Boxes Qty',
                        y=total_boxes_qty * 1.1, 
                        text=f"Total: {total_boxes_qty:,}", 
                        showarrow=False,
                        font=dict(size=14, color="black", family="Arial Black")
                    )
                    
                    # ปรับแกน Y ให้สูงขึ้นเพื่อรองรับ Annotation
                    y_max = max(total_order_count, total_boxes_qty) * 1.2 
                    fig_bar.update_yaxes(range=[0, y_max])


                    st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            # ------------------------------------------------------------------
            # 2. Stack chart 2 ชุด แยก Store, แยก Seller Center, นับ Order ID (ไม่ซ้ำ)
            # ------------------------------------------------------------------
            st.header("2. Pending by Seller Center")

            # สร้างคอลัมน์ใน Streamlit ให้เท่ากับจำนวน Store
            stack_cols = st.columns(len(Stores))

            for i, Store in enumerate(Stores):
                with stack_cols[i]:
                    st.subheader(f"Store: {Store}")

                    # กรองข้อมูลเฉพาะ Store นี้
                    Store_df = df[df['Store'] == Store]
                    
                    # เตรียมข้อมูล: Group by Seller Center และ Remark, แล้วนับ Order ID (ไม่ซ้ำ)
                    stack_data = Store_df.groupby(['Seller Center', 'Remark'])['Order ID'].nunique().reset_index()
                    
                    # 💥 NEW: คำนวณยอดรวม Order ID ต่อ Seller Center สำหรับ Annotation
                    total_order_by_seller = stack_data.groupby('Seller Center')['Order ID'].sum().reset_index()
                    
                    # สร้าง Stacked Chart
                    fig_stack = px.bar(
                        stack_data,
                        x='Seller Center',
                        y='Order ID',
                        color='Remark',
                        title=f"Total Order by Seller",
                        barmode='stack',  
                        color_discrete_map=COLOR_MAP,
                        text='Order ID',
                        category_orders={"Remark": ["Canpick", "Cannotpick"]}
                    )
                    
                    # ปรับรูปแบบข้อความบนแท่งชาร์ต
                    fig_stack.update_traces(
                        textposition='inside',
                        # 💥 แก้ไข: ตั้งค่าเป็น 0 เพื่อให้ตัวเลขเป็นแนวตั้ง
                        textangle=0,  
                        # textfont=dict(size=11), # ไม่จำเป็นเมื่อใช้ textfont_size
                        textfont_size=11
                    )
                    
                    # 💥 NEW: เพิ่ม Annotation (ยอดรวม) ด้านบนแต่ละ Bar (Chart 2) 💥
                    y_max_store = 0
                    for _, row in total_order_by_seller.iterrows():
                        seller = row['Seller Center']
                        total_count = row['Order ID']
                        
                        fig_stack.add_annotation(
                            x=seller,
                            y=total_count * 1.1, # ตำแหน่งเหนือยอดรวมเล็กน้อย
                            text=f"Total: {total_count:,}",
                            showarrow=False,
                            font=dict(size=14, color="black", family="Arial Black")
                        )
                        if total_count > y_max_store:
                            y_max_store = total_count

                    # ปรับแกน Y ให้สูงขึ้นเพื่อรองรับ Annotation
                    fig_stack.update_yaxes(range=[0, y_max_store * 1.2])
                    
                    st.plotly_chart(fig_stack, use_container_width=True)

            st.divider()

            # ------------------------------------------------------------------
            # 3. ตาราง Top 10 รายการ Cannotpick (แยกตาม Store)
            # ------------------------------------------------------------------
            st.header("3. Top 10 รายการ 'Cannotpick' (แยกตาม Store)")

            # สร้างฟังก์ชันสำหรับสร้างตาราง Top 10
            def display_top_10(df_all, store_id, title_col):
                # 1. กรองเฉพาะรายการ "Cannotpick" และ Store ที่กำหนด
                cant_pick_store_df = df_all[
                    (df_all['Remark'] == "Cannotpick") & 
                    (df_all['Store'].astype(str) == str(store_id)) # แปลงเป็น string เพื่อความแน่นอน
                ]

                with title_col:
                    st.subheader(f"Store {store_id} (Top 10 Cannotpick)")
                    
                    if cant_pick_store_df.empty:
                        st.info(f"ไม่พบข้อมูล 'Cannotpick' สำหรับ Store {store_id}")
                        return

                    # 2. จัดกลุ่ม, รวมยอด BoxesQty, และคงค่า Description ที่ไม่ซ้ำกัน
                    top_data = cant_pick_store_df.groupby(['SKU (TPNB)', 'Description'])['BoxesQty'].sum().reset_index()
                    
                    # 3. จัดเรียงและเอา 10 อันดับแรก
                    top_data = top_data.sort_values(by='BoxesQty', ascending=False).head(10).reset_index(drop=True)
                    
                    # 4. จัดรูปแบบและแสดงผล
                    top_data.index = top_data.index + 1
                    top_data = top_data.rename_axis('Rank')
                    
                    # แปลง BoxesQty ให้เป็นจำนวนเต็ม (ถ้าจำเป็น) และเพิ่มเครื่องหมาย ,
                    st.dataframe(
                        top_data, 
                        use_container_width=True,
                        column_config={
                             "BoxesQty": st.column_config.NumberColumn(
                                 "BoxesQty", format="%d" # แสดงเป็นจำนวนเต็ม ไม่มีทศนิยม
                             )
                         }
                    )
            
            # แสดงตารางแยก 2 คอลัมน์
            col_7888, col_7886 = st.columns(2)
            
            # สร้างตารางสำหรับ Store 7888
            display_top_10(df, 7888, col_7888)
            
            # สร้างตารางสำหรับ Store 7886
            display_top_10(df, 7886, col_7886)

        else:

            # กรณีโหลดข้อมูลไม่สำเร็จ (df.empty เป็น True)
            st.error("ไม่สามารถประมวลผลข้อมูลได้ กรุณาตรวจสอบไฟล์และชื่อชีต")

    else:
        # --- ส่วนที่ 3: แสดงข้อความหากยังไม่อัปโหลดไฟล์ ---
        st.info("กรุณาอัปโหลดไฟล์ Excel เพื่อเริ่มแสดงผลแดชบอร์ด")


if __name__ == '__main__':
    main()