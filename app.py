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
    client = OpenAI(api_key=st.secrets["MY_NEW_KEY"])
except:
    st.error("API Key missing! Add MY_NEW_KEY to Streamlit Secrets.")
    st.stop()

# --- APP LOGIC ---

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def analyze_image(img_file):
    # Your OpenAI setup should already be here, just update the prompt and return
    client = OpenAI(api_key=st.secrets["MY_NEW_KEY"]) 
    
    prompt = """
    Identify the appliance in this image. You MUST return a JSON object with these keys:
    {
      "manufacturer": "Brand",
      "model_number": "Model String",
      "birth_year": 2018, 
      "avg_lifespan": 15,
      "health_score": 7,
      "replace_vs_repair": "Detailed recommendation based on age vs typical life",
      "modern_alternative": "A current efficient model name",
      "maintenance_alert": "One pro-tip for this specific unit"
    }
    Note: If the exact birth year isn't visible, estimate it based on the design era.
    """

    # Assuming you are using the vision model logic:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img_file.read()).decode()}"}}
        ]}],
        response_format={ "type": "json_object" }
    )
    import json
    return json.loads(response.choices[0].message.content)

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
        model="gpt-5-mini",
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

# --- TAB DEFINITIONS ---
tab1, tab2 = st.tabs(["🔍 Scan Asset", "📋 My Inventory"])

with tab1:
    st.subheader("Mischka Protocol: Active Scan")
    
    # User selects how to provide the image
    input_method = st.radio("Select Input:", ["Camera", "Upload File"], horizontal=True)
    
    if input_method == "Camera":
        img_file = st.camera_input("Scan Appliance Label")
    else:
        img_file = st.file_uploader("Upload Label Photo", type=['jpg', 'png', 'jpeg'])

    # Logic to process the image
    if img_file:
        with st.spinner("Mischka is identifying lifecycle data..."):
            # This calls the upgraded function we built
            asset_data = analyze_image(img_file)
            st.session_state.current_asset = asset_data
            
            # Save to temporary session inventory
            if asset_data not in st.session_state.assets:
                st.session_state.assets.append(asset_data)

    # --- DISPLAY RESULTS (Aligned inside Tab 1) ---
    if st.session_state.current_asset:
        asset = st.session_state.current_asset
        st.divider()
        
        # Identity Row
        c1, c2 = st.columns(2)
        c1.metric("Make", asset.get('manufacturer'))
        c2.metric("Model", asset.get('model_number'))

        # Lifecycle Health Section
        st.write("### 🩺 Home Asset Health")
        
        current_year = 2026
        birth = int(asset.get('birth_year', 2020))
        lifespan = int(asset.get('avg_lifespan', 15))
        age = current_year - birth
        remaining = max(0, lifespan - age)
        health_score = int(asset.get('health_score', 5))
        
        # Visual Progress
        st.progress(health_score / 10, text=f"Health Status: {health_score}/10")
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Age", f"{age} yrs")
        col_b.metric("Avg. Life", f"{lifespan} yrs")
        col_c.metric("Life Left", f"~{remaining} yrs")

        with st.container(border=True):
            st.write("#### 💡 Economic Advice")
            st.warning(f"**Decision:** {asset.get('replace_vs_repair')}")
            st.info(f"**Upgrade:** {asset.get('modern_alternative')}")

with tab2:
    st.subheader("Your Personal Property Ledger")
    if st.session_state.assets:
        # Display the collected items in a clean table
        df = pd.DataFrame(st.session_state.assets)
        st.dataframe(df[['manufacturer', 'model_number', 'birth_year', 'health_score']])
        
        if st.button("Clear Session Vault"):
            st.session_state.assets = []
            st.session_state.current_asset = None
            st.rerun()
    else:
        st.info("Your vault is empty. Scan an item to begin your ledger.")
