import streamlit as st
from groq import Groq

def get_client():
    if "GROQ_API_KEY" not in st.secrets:
        st.error("GROQ_API_KEY secret ledu!")
        st.stop()
    
    # str() + strip() + repr() - mottam clean chestadi
    api_key = str(st.secrets["GROQ_API_KEY"]).strip().replace('\n','').replace('\r','')
    
    # Debug: screen meda kanipistadi
    st.write("DEBUG Key length:", len(api_key))
    st.write("DEBUG Key start:", api_key[:10])
    
    if len(api_key)!= 56:
        st.error(f"Key length tappu! 56 undali, kani {len(api_key)} undi. Secrets lo extra space/line undi.")
        st.stop()
    
    return Groq(api_key=api_key)

def get_working_model():
    client = get_client()
    try:
        models = client.models.list().data
        preferred = [
            "llama-3.3-70b-versatile",
            "llama3-70b-8192", 
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant"
        ]
        available_ids = [m.id for m in models]
        for model in preferred:
            if model in available_ids:
                return model
        return available_ids[0]
    except Exception:
        return "llama-3.1-8b-instant"

def ask_agent(user_question, stream=False):
    client = get_client()
    messages = [
        {
            "role": "system",
            "content": "You are 'Spicy Cart Agent'. For recipe questions, give markdown table with Item, Quantity, Approx Price (INR). End with [CART_DATA]item:qty:price,..."
        },
        {"role": "user", "content": user_question}
    ]

    chat_completion = client.chat.completions.create(
        messages=messages,
        model=get_working_model(),
        temperature=0.7,
        stream=stream,
    )

    if stream:
        for chunk in chat_completion:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        return chat_completion.choices[0].message.content
