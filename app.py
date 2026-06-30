import streamlit as st
import re

# ===== CONFIG =====
st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒", layout="wide")

# ===== PRICE FLOOR - EKKADA CHANGE CHEYALI =====
MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80,
    "roll": 90,
    "chicken": 180,
    "mutton": 250,
    "dosa": 60,
    "idli": 40
}

DEFAULT_PRICE = 100

# ===== PRICE CALCULATOR =====
def calculate_item_price(item_name, qty=1):
    """Minimum price enforce chestadi. No API needed."""
    if not item_name:
        return DEFAULT_PRICE * qty
    
    item_lower = item_name.lower().strip()
    
    # 1. Base price find chey
    base_price = DEFAULT_PRICE
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break
    
    # 2. Quantity multiply
    total = base_price * int(qty)
    return int(total)

# ===== PARSE USER INPUT =====
def parse_query(query):
    """'2 biryani' nunchi qty=2, item=biryani teestadi"""
    query = query.lower().strip()
    
    # Number extract chey
    qty_match = re.search(r'\d+', query)
    qty = int(qty_match.group()) if qty_match else 1
    
    # Item extract chey - number teesi migilindi
    item = re.sub(r'\d+', '', query).strip()
    item = item.replace("person", "").replace("people", "").strip()
    
    if not item:
        item = "meal"
    
    return item, qty

# ===== STREAMLIT UI =====
st.title("🛒 Smart Cart Agent - AI Grocery Planner")
st.caption("Kaggle Capstone 2026 | Biryani ₹150 | Burger ₹99 minimum per person")

# Session state
if "history" not in st.session_state:
    st.session_state.history = []

# Input
col1, col2 = st.columns([3, 1])
with col1:
    user_input = st.text_input(
        "What do you want?", 
        placeholder="Ex: 2 biryani, 1 burger, 3 people pizza",
        label_visibility="collapsed"
    )
with col2:
    calc_btn = st.button("Calculate 💰", use_container_width=True, type="primary")

# Calculate
if calc_btn and user_input:
    item, qty = parse_query(user_input)
    price = calculate_item_price(item, qty)
    
    result = f"**{item.title()} x {qty} person** = **₹{price}**"
    st.session_state.history.insert(0, result)
    
    st.success(result)
    st.balloons()

# Show History
if st.session_state.history:
    st.divider()
    st.subheader("📋 Calculation History")
    for i, record in enumerate(st.session_state.history[:10]):
        st.markdown(f"{i+1}. {record}")

# ===== SIDEBAR - PRICE LIST =====
with st.sidebar:
    st.header("💰 Base Price List")
    st.caption("Minimum per person - No API")
    
    for item, price in MIN_PRICE_PER_PERSON.items():
        st.markdown(f"**{item.title()}**: ₹{price}")
    
    st.divider()
    st.info("**How it works:**\n1. Type item + qty\n2. Get instant price\n3. Biryani always ₹150+\n4. Burger always ₹99+")
    
    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")
    st.link_button("View GitHub", "https://github.com/varshithagudisa/smart-cart-agent")

# ===== FOOTER =====
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Biryani Base", "₹150")
with col2:
    st.metric("Burger Base", "₹99")
with col3:
    st.metric("Pizza Base", "₹199")
