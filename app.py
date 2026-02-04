import streamlit as st
from openai import OpenAI
import base64
import json
import pandas as pd

# 1. PAGE SETUP
st.set_page_config(page_title="Reclaim Home Prototype", page_icon="🏠")

# 2. THE BOUNCER (PASSWORD CHECK)
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # Check if the password is set in the cloud secrets
    if "APP_PASSWORD" not in st.secrets:
        st.error("Setup Error: Please add APP_PASSWORD to your Streamlit Secrets.")
        return False

    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Clear the box
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "Enter Password to Access Reclaim Home:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input again
        st.text_input(
            "Enter Password to Access Reclaim Home:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()  # STOP HERE if password is not entered

# 3. SECURELY LOAD API KEY
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("API Key missing! Add OPENAI_API_KEY to Streamlit Secrets.")
    st.stop()

# --- APP LOGIC STARTS HERE ---

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def analyze_image(image_file):
    base64_image = encode_image(image_file)
    prompt = """
    Analyze this appliance image. Return a JSON object with:
    - manufacturer (string)
    - model_number (string)
    - category (string)
    - maintenance_alert (string, proactive tip)
    If you cannot read a value, use "Unknown". 
    If not an appliance, return "Error".
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are the Reclaim Home AI. Return ONLY JSON."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"manufacturer": "Error", "details": str(e)}

def get_diy_advice(model_info, symptom):
    prompt = f"""
    The user has a {model_info.get('manufacturer')} {model_info.get('category')} 
    Model: {model_info.get('model_number')}.
    Symptom: "{symptom}".
    
    Return JSON with:
    - likely_cause (string)
    - steps (array of strings)
    - safety_warning (string)
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are an expert handyman AI."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- UI LAYOUT ---
st.title("Reclaim 🏠")

if 'assets' not in st.session_state: st.session_state.assets = []
if 'current_asset' not in st.session_state: st.session_state.current_asset = None
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

tab1, tab2 = st.tabs(["📷 Scan & Fix", "📋 My Inventory"])

with tab1:
    img_file = st.file_