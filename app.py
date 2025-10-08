# app.py — PantryPal Basic (Enhanced)
import streamlit as st
import pandas as pd
from datetime import date, datetime
from pathlib import Path

st.set_page_config(page_title="PantryPal — Basic (Enhanced)", layout="centered")
st.title("PantryPal — Basic (Enhanced) 🥕")

DATA_FILE = Path("pantry_data.csv")

# --- Helper functions ---
def load_data():
    if DATA_FILE.exists():
        try:
            df = pd.read_csv(DATA_FILE, parse_dates=["expiry"])
            # ensure expiry is a date (not datetime)
            df["expiry"] = pd.to_datetime(df["expiry"]).dt.date
            return df.to_dict("records")
        except Exception:
            return []
    return []

def save_data(items):
    df = pd.DataFrame(items)
    # store expiry as ISO format
    if not df.empty and "expiry" in df.columns:
        df["expiry"] = pd.to_datetime(df["expiry"]).dt.date
    df.to_csv(DATA_FILE, index=False)

def normalize_items(items):
    # Ensure correct types and keys
    clean = []
    for it in items:
        name = str(it.get("name", "")).strip()
        qty = int(it.get("quantity", 0)) if it.get("quantity") != "" else 0
        cat = str(it.get("category", "")).strip()
        exp = it.get("expiry")
        if isinstance(exp, str):
            try:
                exp = datetime.fromisoformat(exp).date()
            except Exception:
                try:
                    exp = datetime.strptime(exp, "%Y-%m-%d").date()
                except Exception:
                    exp = date.today()
        if isinstance(exp, datetime):
            exp = exp.date()
        clean.append({"name": name, "quantity": qty, "category": cat, "expiry": exp})
    return clean

# --- Load existing data on startup ---
if "items" not in st.session_state:
    st.session_state.items = normalize_items(load_data())

# --- Add item form ---
with st.form("add_item", clear_on_submit=True):
    st.subheader("Add pantry item")
    c1, c2, c3 = st.columns([3,1,2])
    name = c1.text_input("Item name")
    qty = c2.number_input("Quantity", min_value=1, value=1, step=1)
    category = c3.text_input("Category (e.g., Dairy, Grains, Spices)")

    exp_col, = st.columns([1])
    expiry = st.date_input("Expiry date", value=date.today())

    submitted = st.form_submit_button("Add item")
    if submitted:
        if not name.strip():
            st.warning("Please enter an item name.")
        else:
            st.session_state.items.append({
                "name": name.strip(),
                "quantity": int(qty),
                "category": category.strip(),
                "expiry": expiry
            })
            st.success(f"Added {name.strip()}")
            # auto-save
            save_data(st.session_state.items)

st.markdown("---")

# --- Controls: search, filter, sort ---
st.subheader("Pantry controls")
col_s1, col_s2, col_s3 = st.columns([3,2,2])
search_text = col_s1.text_input("Search by name")
all_categories = sorted({it.get("category","").strip() for it in st.session_state.items if it.get("category","").strip()})
cat_choice = col_s2.selectbox("Filter by category", options=["All"] + all_categories, index=0)
sort_choice = col_s3.selectbox("Sort by", options=["Expiry (soonest)", "Expiry (latest)", "Name A→Z", "Name Z→A", "Quantity descending"], index=0)

# Build filtered list
display_items = st.session_state.items.copy()
if search_text:
    display_items = [it for it in display_items if search_text.lower() in it.get("name","").lower()]
if cat_choice and cat_choice != "All":
    display_items = [it for it in display_items if it.get("category","").lower() == cat_choice.lower()]

# Sorting
def sort_items(items, mode):
    if mode == "Expiry (soonest)":
        return sorted(items, key=lambda x: (x.get("expiry") is None, x.get("expiry") or date.max))
    if mode == "Expiry (latest)":
        return sorted(items, key=lambda x: (x.get("expiry") is None, x.get("expiry") or date.min), reverse=True)
    if mode == "Name A→Z":
        return sorted(items, key=lambda x: x.get("name","").lower())
    if mode == "Name Z→A":
        return sorted(items, key=lambda x: x.get("name","").lower(), reverse=True)
    if mode == "Quantity descending":
        return sorted(items, key=lambda x: x.get("quantity",0), reverse=True)
    return items

display_items = sort_items(display_items, sort_choice)

# --- Display table with checkboxes for deletion ---
st.subheader("Pantry items")
if not display_items:
    st.info("No items to show (or filters removed all items).")
else:
    # We'll show a table-like layout with checkboxes
    remove_selected = []
    cols = st.columns([4,1,2,1])
    cols[0].markdown("**Item name**")
    cols[1].markdown("**Qty**")
    cols[2].markdown("**Category**")
    cols[3].markdown("**Expiry**")
    st.write("")  # spacing

    to_delete_indices = []
    # to keep stable keys use index from original list
    for idx, it in enumerate(display_items):
        # find original index in session list for deletion mapping
        # there may be duplicates; we find first matching with same fields not yet accounted
        row_key = f"del_{idx}_{it.get('name')}_{it.get('expiry')}"
        c1, c2, c3, c4 = st.columns([4,1,2,1])
        c1.write(it.get("name"))
        c2.write(str(it.get("quantity")))
        c3.write(it.get("category") or "-")
        expiry_val = it.get("expiry")
        if isinstance(expiry_val, (date,)):
            c4.write(expiry_val.isoformat())
        else:
            c4.write(str(expiry_val) if expiry_val else "-")
        checked = c4.checkbox("Delete", key=row_key)
        if checked:
            to_delete_indices.append(it)  # store item dict for later matching

    # Buttons for actions
    col_a, col_b, col_c = st.columns([1,1,1])
    if col_a.button("Remove selected"):
        if not to_delete_indices:
            st.warning("No items selected to delete.")
        else:
            # remove items (match by exact dict to avoid accidental removals)
            before = len(st.session_state.items)
            new_items = [it for it in st.session_state.items if it not in to_delete_indices]
            st.session_state.items = new_items
            save_data(st.session_state.items)
            st.success(f"Removed {before - len(new_items)} item(s).")
            st.experimental_rerun()

    if col_b.button("Clear all items"):
        st.session_state.items = []
        if DATA_FILE.exists():
            try:
                DATA_FILE.unlink()
            except Exception:
                pass
        st.success("Cleared all items.")
        st.experimental_rerun()

    if col_c.button("Save to server (pantry_data.csv)"):
        save_data(st.session_state.items)
        st.success("Saved pantry_data.csv on server.")

# --- Dataframe view + download ---
st.markdown("---")
st.subheader("Data view")
if st.session_state.items:
    df_view = pd.DataFrame(normalize_items(st.session_state.items))
    # make expiry ISO strings for display
    df_view["expiry"] = df_view["expiry"].apply(lambda x: x.isoformat() if isinstance(x, date) else str(x))
    st.dataframe(df_view.reset_index(drop=True))
    csv_bytes = df_view.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_bytes, "pantry_export.csv", "text/csv")
else:
    st.info("No stored pantry items yet.")

st.markdown("---")
st.caption("Notes: 'Save to server' writes pantry_data.csv into the app folder. On hosted platforms this file is simple server-side storage and may be cleared on redeploy. For durable storage consider using Google Drive / DB.")
