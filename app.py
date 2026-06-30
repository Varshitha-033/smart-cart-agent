import streamlit as st
from groq import Groq
import urllib.parse

st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒", layout="wide")

MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80,
    "dosa": 60
}

# ===== INGREDIENTS WITH SCALING =====
INGREDIENTS_MAP = {
    "biryani": {
        "Basmati Rice": {"base": 250, "unit": "g"},
        "Chicken": {"base": 250, "unit": "g"},
        "Biryani Masala": {"base": 1, "unit": "packet"},
        "Onions": {"base": 150, "unit": "g"},
        "Curd": {"base": 100, "unit": "ml"},
        "Ghee": {"base": 50, "unit": "ml"},
        "Mint Leaves": {"base": 1, "unit": "bunch"},
        "Coriander Leaves": {"base": 1, "unit": "bunch"}
    },
    "burger": {
        "Burger Buns": {"base": 1, "unit": "pc"},
        "Chicken Patty": {"base": 1, "unit": "pc"},
        "Cheese Slices": {"base": 1, "unit": "pc"},
        "Lettuce": {"base": 20, "unit": "g"},
        "Tomato": {"base": 50, "unit": "g"},
        "Mayonnaise": {"base": 1, "unit": "packet"},
        "Ketchup": {"base": 1, "unit": "packet"}
    },
    "pizza": {
        "Pizza Base": {"base": 1, "unit": "pc"},
        "Pizza Sauce": {"base": 1, "unit": "packet"},
        "Mozzarella Cheese": {"base": 100, "unit": "g"},
        "Capsicum": {"base": 50, "unit": "g"},
        "Onion": {"base": 50, "unit": "g"},
        "Sweet Corn": {"base": 50, "unit": "g"},
        "Oregano": {"base": 1, "unit": "packet"},
        "Chilli Flakes": {"base": 1, "unit": "packet"}
    },
    "thali": {
        "Rice": {"base": 200, "unit": "g"},
        "Toor Dal": {"base": 100, "unit": "g"},
        "Vegetables Mix": {"base": 200, "unit": "g"},
        "Curd": {"base": 100, "unit": "ml"},
        "Chapati Flour": {"base": 150, "unit": "g"},
        "Pickle": {"base": 1, "unit": "bottle"},
        "Papad": {"base": 1, "unit": "packet"}
    },
    "dosa": {
        "Dosa Batter": {"base": 500, "unit": "g"},
        "Potato": {"base": 250, "unit": "g"},
        "Onion": {"base": 100, "unit": "g"},
        "Coconut Chutney Mix": {"base": 1, "unit": "packet"},
        "Sambar Powder": {"base": 1, "unit": "packet"},
        "Oil": {"base": 100, "unit": "ml"}
    }
}

def calculate_price(item, qty):
    base_price = 100
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item.lower():
            base_price = min_val
            break
    return base_price * int(qty)

def create_blinkit_link(item_name):
    """Single item ki Blinkit search link"""
    encoded = urllib.parse.quote(item_name)
    return f"https://blinkit.com/s/?q={encoded}"

def get_scaled_ingredients(item, qty):
    """All ingredients with proper scaling"""
    base_items = INGREDIENTS_MAP.get(item.lower(), {})
    scaled_data = []

    for ing, data in base_items.items():
        scaled_qty = data["base"] * qty
        unit = data["unit"]

        # Format nicely
        if unit == "g" and scaled_qty >= 1000:
            qty_str = f"{scaled_qty/1000:.1f}kg"
        elif unit == "ml" and scaled_qty >= 1000:
            qty_str = f"{scaled_qty/1000:.1f}L"
        elif unit in ["packet", "pc", "bunch", "bottle"]:
            qty_str = f"{int(scaled_qty)} {unit}"
        else:
            qty_str = f"{int(scaled_qty)}{unit}"

        scaled_data.append({
            "name": ing,
            "qty": qty_str,
            "link": create_blinkit_link(ing)
        })

    return scaled_data

# ===== UI =====
st.title("🛒 Smart Cart Agent")
st.subheader("All Ingredients + Individual Blinkit Links")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    item = st.selectbox("Select Meal", options=list(MIN_PRICE_PER_PERSON.keys()), format_func=lambda x: x.title())

with col2:
    qty = st.number_input("People", min_value=1, max_value=20, value=2)

with col3:
    st.write("")
    generate_btn = st.button("Generate Cart 🛍️", use_container_width=True, type="primary")

if generate_btn:
    total = calculate_price(item, qty)

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Meal", item.title())
    with c2:
        st.metric("People", qty)
    with c3:
        st.metric("Min Total", f"₹{total}")

    st.divider()
    st.subheader("📝 Ingredients List - Click to Add")

    ingredients = get_scaled_ingredients(item, qty)

    # Table format with individual links
    for ing in ingredients:
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.write(f"**{ing['name']}**")
        with col2:
            st.write(ing['qty'])
        with col3:
            st.link_button("🛍️ Add to Cart", ing['link'], use_container_width=True)

    st.divider()

    # Master cart link - ALL items
    all_items = [ing['name'] for ing in ingredients]
    master_link = create_blinkit_link(",".join(all_items))

    st.success(f"✅ **{len(ingredients)} items ready** for {qty} person {item.title()}")
    st.link_button(
        "🛒 Add ALL Items to Blinkit at Once",
        master_link,
        use_container_width=True,
        type="primary"
    )
    st.caption("Or click individual 'Add to Cart' buttons above")

# ===== SIDEBAR =====
with st.sidebar:
    st.header("💰 Base Prices")
    for food, price in MIN_PRICE_PER_PERSON.items():
        st.markdown(f"**{food.title()}**: ₹{price}/person")

    st.divider()
    st.info("**New Features:**\n- All ingredients shown\n- Individual Blinkit link per item\n- Auto-scaled quantities\n- Master 'Add All' button")

    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")
