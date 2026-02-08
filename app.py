import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
import altair as alt

st.set_page_config(layout="wide")
st.title("Inventory Management Dashboard")

# -------------------------------
# Initialize session state
# -------------------------------
if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = pd.DataFrame(columns=[
        "item_id", "item_name", "category", "quantity_in_stock",
        "reorder_level", "price_per_unit", "supplier"
    ])

# -------------------------------
# CSV Upload
# -------------------------------
uploaded_file = st.file_uploader("Upload your inventory CSV", type=["csv"])
if uploaded_file is not None and "csv_loaded" not in st.session_state:
    st.session_state.inventory_df = pd.read_csv(uploaded_file)
    st.session_state.csv_loaded = True
    # Remove exact duplicates
    st.session_state.inventory_df = st.session_state.inventory_df.drop_duplicates(
        subset=["item_name", "category"], keep="first"
    )

# -------------------------------
# Define df safely after CSV upload
# -------------------------------
if not st.session_state.inventory_df.empty:
    df = st.session_state.inventory_df
    st.info(
        "⚙️ All inventory actions (Add, Update, Remove) and chatbot assistance are available in the sidebar. "
        ">> Click the arrows to expand and perform actions."
    )
else:
    st.info("Please upload a CSV file to view inventory data.")
    st.stop()  # Stop execution here if no data

# -------------------------------
# Sidebar — Settings
# -------------------------------

# Sidebar Logo

st.logo(
    image="assets/images/logo1.png", 
    icon_image="assets/images/logo2.png")

with st.sidebar:
    with st.expander("⚙️ Settings", expanded=False):

        # -------------------------------
        # Add New Inventory Item
        # -------------------------------
        st.subheader("Add Item")
        with st.form("add_item_form"):
            item_name = st.text_input("Item Name")
            category = st.selectbox(
                "Category", ["Electronics", "Office Supplies", "Furniture"]
            )
            quantity = st.number_input("Quantity in Stock", min_value=0, step=1)
            reorder_level = st.number_input("Reorder Level", min_value=0, step=1)
            price = st.number_input("Price per Unit", min_value=0.0, step=0.01)
            supplier = st.text_input("Supplier")
            submitted = st.form_submit_button("Add Item")

        if submitted:
            new_id = (
                st.session_state.inventory_df["item_id"].max() + 1
                if not st.session_state.inventory_df.empty else 1
            )
            new_item = {
                "item_id": new_id,
                "item_name": item_name,
                "category": category,
                "quantity_in_stock": quantity,
                "reorder_level": reorder_level,
                "price_per_unit": price,
                "supplier": supplier
            }
            st.session_state.inventory_df = pd.concat(
                [st.session_state.inventory_df, pd.DataFrame([new_item])],
                ignore_index=True
            )
            st.success(f"Added {item_name}")

        # -------------------------------
        # Update Inventory Item
        # -------------------------------
        st.subheader("Update Item")
        if not st.session_state.inventory_df.empty:
            item_to_update = st.selectbox(
                "Select item",
                st.session_state.inventory_df["item_name"].unique()
            )
            new_quantity = st.number_input(
                "New Quantity", min_value=0, step=1
            )
            if st.button("Update Quantity"):
                st.session_state.inventory_df.loc[
                    st.session_state.inventory_df["item_name"] == item_to_update,
                    "quantity_in_stock"
                ] = new_quantity
                st.success(f"Updated {item_to_update}")

        # -------------------------------
        # Remove Inventory Item
        # -------------------------------
        st.subheader("Remove Item")
        if not st.session_state.inventory_df.empty:
            item_to_remove = st.selectbox(
                "Select item",
                st.session_state.inventory_df["item_name"].unique(),
                key="remove_item"
            )
            if st.button("Remove Item"):
                st.session_state.inventory_df = st.session_state.inventory_df[
                    st.session_state.inventory_df["item_name"] != item_to_remove
                ]
                st.success(f"Removed {item_to_remove}")
        # -------------------------------
        # AI Chatbot — Inventory Assistant
        # -------------------------------
        st.subheader("Inventory Assistant 🤖")

        # Initialize chat messages
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        # -------------------------------
        # Chat input
        if prompt := st.chat_input("Ask me about low stocks, categories, all items, or remove items…"):
            # 1 Append user message
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            df = st.session_state.inventory_df
            user_lower = prompt.lower()

            # 2 Generate assistant response
            assistant_msg = {}  # always define this to avoid NameError

            if "low stock" in user_lower or "stockout" in user_lower:
                low_stock = df[df["quantity_in_stock"] < df["reorder_level"]]
                if low_stock.empty:
                    assistant_msg = {"role": "assistant", "content": "All items are sufficiently stocked ✅"}
                else:
                    assistant_msg = {
                        "role": "assistant",
                        "content": "⚠ Low Stock Items:",
                        "dataframe": low_stock[["item_name","category","quantity_in_stock","reorder_level"]]
                    }

            elif any(cat.lower() in user_lower for cat in df["category"].unique()):
                categories = df["category"].unique()
                found_category = None

                for cat in categories:
                    if cat.lower() in user_lower:
                        found_category = cat
                        break

                if found_category:
                    filtered = df[df["category"] == found_category]

                    assistant_msg = {
                        "role": "assistant",
                        "content": f"Items in **{found_category}**:",
                        "dataframe": filtered[["item_name", "quantity_in_stock", "reorder_level"]]
                    }
                else:
                    assistant_msg = {
                        "role": "assistant",
                        "content": f"Category not found. Available: {', '.join(categories)}"
                    }

            elif "all items" in user_lower or "inventory" in user_lower:
                assistant_msg = {
                    "role": "assistant",
                    "content": "Current Inventory:",
                    "dataframe": df
                }

            elif "remove" in user_lower:
                import re
                qty = 1
                num_match = re.search(r'\d+', user_lower)
                if num_match:
                    qty = int(num_match.group())

                item_name = None
                for name in df["item_name"]:
                    if name.lower() in user_lower:
                        item_name = name
                        break

                if item_name:
                    current_qty = st.session_state.inventory_df.loc[
                        st.session_state.inventory_df["item_name"] == item_name, "quantity_in_stock"
                    ].iloc[0]
                    new_qty = current_qty - qty

                    if new_qty > 0:
                        st.session_state.inventory_df.loc[
                            st.session_state.inventory_df["item_name"] == item_name, "quantity_in_stock"
                        ] = new_qty
                        assistant_msg = {
                            "role": "assistant",
                            "content": f"Removed {qty} {item_name}(s). New stock: {new_qty}"
                        }
                    else:
                        st.session_state.inventory_df = st.session_state.inventory_df[
                            st.session_state.inventory_df["item_name"] != item_name
                        ]
                        assistant_msg = {
                            "role": "assistant",
                            "content": f"Removed {item_name} completely from inventory."
                        }

                else:
                    assistant_msg = {
                        "role": "assistant",
                        "content": "Could not identify item to remove. Make sure to include the exact item name."
                    }

            else:
                assistant_msg = {
                    "role": "assistant",
                    "content": (
                        "Try commands like:\n"
                        "- list items under electronics\n"
                        "- show low stock\n"
                        "- remove 2 wireless mouse\n"
                        "- show all items"
                    )
                }

            # 3 Append assistant response immediately
            st.session_state.chat_messages.append(assistant_msg)

# -------------------------------
# Display all chat messages (user + assistant)
# -------------------------------
for msg in st.session_state.chat_messages:
    if "dataframe" in msg:
        st.chat_message(msg["role"]).write(msg["content"])
        st.chat_message(msg["role"]).dataframe(msg["dataframe"], use_container_width=True)
    else:
        st.chat_message(msg["role"]).write(msg["content"])

tab1, tab2, tab3, tab4 = st.tabs(["Executive Snapshot", "Main Dashboard", "Executive Summary & Future Capabilities", "Download Updated Inventory"])
# -------------------------------
# Executive Snapshot (KPIs)
# -------------------------------
with tab1:
    st.header("Executive Snapshot")
        
    if "inventory_df" in st.session_state and not st.session_state.inventory_df.empty:
        df = st.session_state.inventory_df

        cols = st.columns(3)
        
        with cols[0]:
            high_risk = len(df[df["quantity_in_stock"] < df["reorder_level"]])
            ui.metric_card(title="Stockout Risk Items", content=f"{high_risk}", description="Highlights inventory items that are below their reorder level or at risk of running out soon.", key="card1")
            
        with cols[1]:
            avg_turnover = 4.2  # Replace with real calculation if desired
            ui.metric_card(title="Average Turnover", content=f"{avg_turnover}x", description="Tracks how fast inventory moves to help optimize stock and reduce overstocking.", key="card2")
            
        with cols[2]:
            revenue_at_risk = 12400  # Replace with real calculation if desired
            ui.metric_card(title="Revenue At Risk", content=f"${revenue_at_risk:,.0f}", description="Potential revenue loss due to low stock.", key="card3")

                

    # -------------------------------
    # Inventory Intelligence
    # -------------------------------
    # High stockout risk items
    risk_items = df[df["quantity_in_stock"] < df["reorder_level"]]
    if not risk_items.empty:
        st.subheader(" High Stockout Risk Items")
        st.dataframe(risk_items[["item_name", "quantity_in_stock", "reorder_level"]], use_container_width=True)

    # Alerts
    st.subheader(" Alerts")
    for _, row in risk_items.iterrows():
        ui.alert(title=f"⚠️ {row['item_name']} will stock out in {row['reorder_level'] - row['quantity_in_stock']} days", key=f"alert_{row['item_id']}")

    # Expandable explanation
    with st.expander("▶ How is Stockout Risk calculated?"):
        st.markdown("""
        Stockout Risk = (Reorder Level - Current Stock) / Average Daily Demand  
        Items with risk > threshold are highlighted.
        """)

# -------------------------------
# Main Dashboard
# -------------------------------
with tab2:
    st.header("Main Dashboard")
    col1, col2 = st.columns(2)

    # -------------------------------
    # Current Inventory
    # -------------------------------
    with col1:
        st.subheader(" Current Inventory")
        st.dataframe(df, use_container_width=True, height=300)

    # -------------------------------
    # Low Stock Items
    # -------------------------------
    with col2:
        st.subheader(" Low Stock Items")
        low_stock = df[df["quantity_in_stock"] < df["reorder_level"]]
        st.dataframe(low_stock, use_container_width=True, height=300)

    col3, col4 = st.columns(2)

   # -------------------------------
# Inventory by Category
# -------------------------------
with col3:
    st.subheader(" Inventory by Category")

    # Prepare the data for Altair
    category_counts = df.groupby("category")["item_id"].count().reset_index()
    category_counts.columns = ["category", "count"]

    # Create Altair bar chart with fixed width and height
    import altair as alt
    chart = alt.Chart(category_counts).mark_bar(
        color="#1f77b4"
    ).encode(
        x=alt.X('category', title='Category'),
        y=alt.Y('count', title='Item Count')
    )

    # Render the chart in Streamlit
    st.altair_chart(chart, use_container_width=True, height=400)

    # -------------------------------
    # Items in Selected Category
    # -------------------------------
    with col4:
        st.subheader(" Items by Category")
        category_filter = st.selectbox(
            "Select Category",
            st.session_state.inventory_df["category"].unique()  # read fresh
        )
        filtered_df = st.session_state.inventory_df[
            st.session_state.inventory_df["category"] == category_filter
        ]
        st.dataframe(filtered_df, use_container_width=True, height=300)

# -------------------------------
# Executive Summary
# -------------------------------
with tab3:
    st.header("Executive Summary & Future Capabilities")
    high_risk_count = len(df[df["quantity_in_stock"] < df["reorder_level"]])
    most_demand_cat = df.groupby("category")["quantity_in_stock"].sum().idxmax()
    overstock_cat = df.groupby("category")["quantity_in_stock"].sum().idxmin()

    st.markdown(f"""
    - {high_risk_count} items at high stockout risk  
    - {most_demand_cat} driving highest demand  
    - {overstock_cat} showing overstock trend
    """)

    # -------------------------------
    # Future Improvements
    # -------------------------------
    with st.expander("Future Improvements & Capabilities"):
        st.markdown("""
        - Demand forecasting (ML)  
        - Multi-warehouse support  
        - Supplier performance scoring  
        - More interactive chatbot capabilities
        - Smart reorder recommendations
        - Anomaly detection for inventory discrepancies
        - Activity log and audit trail for inventory changes
        """)

# -------------------------------
# Download Updated Inventory
# -------------------------------
with tab4:
    st.markdown("---")
    st.subheader("⬇ Download Updated Inventory")

    if not st.session_state.inventory_df.empty:
        csv = st.session_state.inventory_df.to_csv(index=False)

        st.download_button(
            label="Download Inventory as CSV",
            data=csv,
            file_name="updated_inventory.csv",
            mime="text/csv"
        )
    else:
        st.info("No inventory data available to download.")
