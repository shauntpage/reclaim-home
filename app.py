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

tab1, tab2 = st.tabs(["📷 Scan & Fix", "📋 My Inventory"])

with tab1:
    # --- NEW CAMERA + UPLOAD LOGIC ---
    input_method = st.radio("Choose Input:", ["Camera", "Upload"], horizontal=True)
    
    img_file = None
    if input_method == "Camera":
        img_file = st.camera_input("Snap a photo of the serial tag or receipt")
    else:
        img_file = st.file_uploader("Upload from gallery", type=['jpg', 'png', 'jpeg'])
    
    # Process the image automatically if captured via camera, or via button for upload
    if img_file:
        trigger_scan = False
        if input_method == "Camera":
            # On mobile, camera_input triggers a refresh immediately upon snap
            trigger_scan = True
        else:
            trigger_scan = st.button("Identify Asset 🔍", type="primary")

        if trigger_scan:
            with st.spinner("Mischka Protocol: Analyzing..."):
                data = analyze_image(img_file)
                
                if data.get('manufacturer') == "Error":
                    st.error(f"❌ AI Error: {data.get('details')}")
                else:
                    st.session_state.current_asset = data
                    st.session_state.assets.append(data)
                    st.success("Identified!")

    # --- REST OF YOUR DIAGNOSIS UI ---
          if st.session_state.current_asset:
                asset = st.session_state.current_asset
                st.divider()
                
                # Identity Row
                c1, c2 = st.columns(2)
                c1.metric("Make", asset.get('manufacturer'))
                c2.metric("Model", asset.get('model_number'))
        
                # --- HEALTH & LIFECYCLE SECTION ---
                st.subheader("🩺 Home Asset Health")
                
                # Math for the Metrics
                current_year = 2026
                birth = int(asset.get('birth_year', 2020))
                lifespan = int(asset.get('avg_lifespan', 15))
                age = current_year - birth
                remaining = max(0, lifespan - age)
                health_score = int(asset.get('health_score', 5))
                health_percent = health_score / 10
        
                # Visual Health Progress Bar
                bar_color = "green" if health_score > 7 else "orange" if health_score > 4 else "red"
                st.progress(health_percent, text=f"Overall Health: {health_score}/10")
                
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Age", f"{age} yrs")
                col_b.metric("Avg. Life", f"{lifespan} yrs")
                col_c.metric("Life Left", f"~{remaining} yrs")
        
                # The Economic Advisor Box
                with st.container(border=True):
                    st.write("#### 💡 Mischka Protocol Insight")
                    st.warning(f"**Decision:** {asset.get('replace_vs_repair')}")
                    st.info(f"**Modern Upgrade:** {asset.get('modern_alternative')}")
                    st.success(f"**Pro Tip:** {asset.get('maintenance_alert')}")

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




