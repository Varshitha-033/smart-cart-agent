import streamlit as st
from groq import Groq
import urllib.parse

st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒", layout="wide")

# ===== PRICE FLOOR =====
MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80
}

# ===== INGREDIENTS DATABASE =====
INGREDIENTS_MAP = {
    "biryani": [
        "Basmati Rice 1kg",
        "Chicken 500g",
        "Biryani Masala",
        "Onions 500g",
        "Curd 500ml",
        "Ghee 200ml",
        "Mint Leaves",
        "Coriander Leaves"
    ],
    "burger": [
        "Burger Buns 4pc",
        "Chicken Patty 4pc",
        "Cheese Slices",
        "Lettuce",
        "Tomato 500g",
        "Mayonnaise",
        "Ketchup"
    ],
    "pizza": [
        "Pizza Base 2pc",
        "Pizza Sauce",
        "Mozzarella Cheese 200g",
        "Capsicum 250g",
        "Onion 500g",
        "Sweet Corn 200g",
        "Oregano",
        "Chilli Flakes"
    ],
    "thali": [
        "Rice 1kg",
        "Toor Dal 500g",
        "Vegetables Mix 1kg",
        "Curd 500ml",
        "Chapati Flour 1kg",
        "Pickle",
        "Papad"
    ]
}

def calculate_price(item, qty):
    item_lower = item.lower().strip()
    base_price = 100
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break
    return base_price * int(qty)

def create_blinkit_cart_link(ingredients_list):
    """Multiple items tho Blinkit search link create chestadi"""
    # Blinkit multi-search format: https://blinkit.com/s/?q=item1,item2,item3
    query = ",".join(ingredients_list)
    encoded_query = urllib.parse.quote(query)
    return f"https://blinkit.com/s/?q={encoded_query}"

# ===== GROQ FOR QUANTITIES =====
def get_ingredients_with_qty(item, qty):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    base_ingredients = INGREDIENTS_MAP.get(item.lower(), ["Rice 1kg", "Dal 500g", "Oil 1L"])

    prompt = f"""For {qty} person {item}, give quantity for each ingredient.
Base ingredients: {base_ingredients}
Total budget: ₹{calculate_price(item, qty)}

Return ONLY in this format, one per line:
Item Name - Quantity

Example:
Basmati Rice - 500g
Chicken - 250g

No extra text. Indian portions."""

    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400
    )
    return response.choices[0].message.content

# ===== UI =====
st.title("🛒 Smart Cart Agent")
st.subheader("Ingredients List + Blinkit Cart Link Generator")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    item = st.selectbox(
        "Select Meal",
        options=list(MIN_PRICE_PER_PERSON.keys()),
        format_func=lambda x: x.title()
    )

with col2:
    qty = st.number_input("People", min_value=1, max_value=20, value=1)

with col3:
    st.write("")
    generate_btn = st.button("Generate Cart 🛍️", use_container_width=True, type="primary")

if generate_btn:
    total = calculate_price(item, qty)

    st.divider()

    # Price Display
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Meal", item.title())
    with c2:
        st.metric("People", qty)
    with c3:
        st.metric("Min Total", f"₹{total}")

    st.divider()

    # Ingredients List
    st.subheader("📝 Ingredients List")

    with st.spinner("Calculating ingredients..."):
        try:
            ingredients_text = get_ingredients_with_qty(item, qty)
            st.code(ingredients_text, language=None)

            # Extract item names for Blinkit link
            ingredients_for_link = []
            for line in ingredients_text.split('\n'):
                if '-' in line:
                    item_name = line.split('-')[0].strip()
                    ingredients_for_link.append(item_name)

            # Blinkit Cart Link
            if ingredients_for_link:
                cart_link = create_blinkit_cart_link(ingredients_for_link[:6]) # First 6 items

                st.success("✅ Cart Ready!")
                st.link_button(
                    "🛍️ Add All to Blinkit Cart",
                    cart_link,
                    use_container_width=True,
                    type="primary"
                )

                st.caption(f"Link includes: {', '.join(ingredients_for_link[:6])}")

        except Exception as e:
            st.error(f"AI failed. Using default list.")
            default_items = INGREDIENTS_MAP.get(item.lower(), ["Rice", "Dal"])
            for ing in default_items:
                st.write(f"- {ing}")

            cart_link = create_blinkit_cart_link(default_items)
            st.link_button("🛍️ Open Blinkit", cart_link, use_container_width=True)

# ===== SIDEBAR =====
with st.sidebar:
    st.header("💰 Base Prices")
    for food, price in MIN_PRICE_PER_PERSON.items():
        st.markdown(f"**{food.title()}**: ₹{price}/person")

    st.divider()
    st.info("**How it works:**\n1. Select meal + people\n2. Get ingredients list\n3. Click Blinkit link\n4. All items pre-filled in search")

    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")

# ===== FOOTER =====
st.divider()
st.subheader("Quick Start")
q1, q2, q3, q4 = st.columns(4)

quick_items = [
    ("2 Biryani", "biryani", 2),
    ("1 Burger", "burger", 1),
    ("3 Pizza", "pizza", 3),
    ("4 Thali", "thali", 4)
]

for col, (label, itm, q) in zip([q1, q2, q3, q4], quick_items):
    with col:
        if st.button(label, use_container_width=True):
            st.session_state.quick = (itm, q)
            st.rerun()

if "quick" in st.session_state:
    item, qty = st.session_state.quick
    total = calculate_price(item, qty)
    st.success(f"**{item.title()} x {qty} = ₹{total}** - Click Generate Cart above")
    del st.session_state.quick
