import streamlit as st
from groq import Groq

def get_client():
    """Groq client lazy ga create cheyyali"""
    api_key = st.secrets["GROQ_API_KEY"]
    return Groq(api_key=api_key)

def get_working_model():
    """Available models lo okati auto select chestadi"""
    client = get_client() # Ikkada create chestunnam
    try:
        models = client.models.list().data
        preferred = [
            "llama-3.3-70b-versatile",
            "llama3-70b-8192", 
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant",
            "gemma2-9b-it"
        ]
        available_ids = [m.id for m in models]

        for model in preferred:
            if model in available_ids:
                return model

        if available_ids:
            return available_ids[0]
        else:
            raise Exception("No models available")
    except Exception as e:
        st.error(f"Error fetching models: {e}")
        return "llama-3.1-8b-instant"

def ask_agent(user_question, stream=False):
    client = get_client() # Ikkada kuda create chestunnam
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
