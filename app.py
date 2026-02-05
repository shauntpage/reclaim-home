import streamlit as st
import base64
import json
from openai import OpenAI

# --- 1. APP CONFIG & STYLING ---
st.set_page_config(page_title="Reclaim", page_icon="🏠", layout="centered")

# CSS: Massive buttons for mobile + Clean Inputs
st.markdown("""
    <style>
    div.stButton > button { 
        width: 100%; 
        height: 80px; 
        font-size: 24px !important; 
        font-weight: 600;
        border-radius: 20px; 
        margin-bottom: 16px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .stMetric { 
        background-color: #f7f9fc; 
        border: 1px solid #e1e4e8; 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center;
    }
    /* Hide hamburger menu for clean app feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. SECURITY GATE (Mischka26) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == "Mischka26":
        st.session_state.authenticated = True
        del st.session_state.password_input
    else:
        st.error("⛔ Access Denied")

if not st.session_state.authenticated:
    st.title("🔒 Reclaim OS")
    st.caption("Restricted Access // San Leandro Node")
    st.text_input("Enter Passkey:", type="password", key="password_input", on_change=check_password)
    st.stop()  # STOPS the app here until password is correct

# --- 3. STATE INITIALIZATION (Only runs if authenticated) ---
for key in ['assets', 'page', 'chat_history', 'current_asset']:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ['assets', 'chat_history'] else ("home" if key == 'page' else None)

client = OpenAI(api_key=st.secrets["MY_NEW_KEY"])

# --- 4. THE BRAIN ---
def analyze_universal(img_file):
    base64_image = base64.b64encode(img_file.getvalue()).decode('utf-8')
    prompt = """
    Analyze image (Appliance, Vehicle, or Consumable). Return JSON:
    {
      "manufacturer": "Brand", "model_number": "Model", 
      "is_consumable": bool, "health_score": 1-10, 
      "birth_year": 2020, "avg_lifespan": 15,
      "estimated_value": "$500",
      "replace_vs_repair": "Strategy", "reorder_link": "URL",
      "diagnostics": {"primary_fault_prediction": "Fault", "diy_fix_steps": "Steps"}
    }
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- 5. PAGE: HOME (THE MENU) ---
if st.session_state.page == "home":
    st.title("🏠 Reclaim")
    st.caption("Ownership OS")
    
    if st.button("📸 SCAN ASSET"):
        st.session_state.page = "scan"; st.rerun()
        
    if st.button("⚡ FIGJAM"):
        st.session_state.current_asset = {"manufacturer": "Quick", "model_number": "Fix"}
        st.session_state.chat_history = [{"role": "assistant", "content": "FIGJAM Protocol Active. What's broken?"}]
        st.session_state.page = "diagnose"; st.rerun()

    if st.button("📋 MY LEDGER"):
        st.session_state.page = "ledger"; st.rerun()

    if st.session_state.assets:
        val = sum([int(str(a.get('estimated_value', '0')).replace('$','').replace(',','')) for a in st.session_state.assets])
        st.metric("Total Asset Value", f"${val:,}")
