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
        st.text_input(
            "Enter Password to Access Reclaim Home:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Enter Password to Access Reclaim Home:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# 3. SECURELY LOAD API KEY
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("API Key missing! Add OPENAI_API_KEY to Streamlit Secrets.")
    st.stop()

# --- APP LOGIC ---

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
    # THIS IS THE LINE THAT WAS BROKEN
    img_file = st.file_uploader("Tap here to Snap Photo", type=['jpg', 'png', 'jpeg'])
    
    if img_file and st.button("Identify Asset 🔍", type="primary"):
        with st.spinner("Analyzing..."):
            data = analyze_image(img_file)
            if data.get('manufacturer') == "Error":
                st.error("Could not identify. Try again.")
            else:
                st.session_state.current_asset = data
                st.session_state.assets.append(data)
                st.success("Identified!")

    if st.session_state.current_asset:
        asset = st.session_state.current_asset
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Make", asset.get('manufacturer'))
        c1.metric("Model", asset.get('model_number'))
        st.info(asset.get('maintenance_alert'))

        symptom = st.text_input("What is wrong?")
        if st.button("Start Diagnosis 🔧"):
            with st.spinner("Checking manuals..."):
                advice = get_diy_advice(asset, symptom)
                msg = f"**Cause:** {advice.get('likely_cause')}\n\n**Safety:** {advice.get('safety_warning')}\n\n**Steps:**"
                for s in advice.get('steps', []): msg += f"\n- {s}"
                st.session_state.chat_history = [{"role": "assistant", "content": msg}]

        for m in st.session_state.chat_history:
            st.chat_message(m["role"]).write(m["content"])

with tab2:
    if st.session_state.assets:
        df = pd.json_normalize(st.session_state.assets)
        st.dataframe(df)
    else:
        st.info("No assets scanned yet.")