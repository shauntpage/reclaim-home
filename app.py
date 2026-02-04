import streamlit as st
from openai import OpenAI
import base64
import json
import pandas as pd

# --- CONFIGURATION ---
# 🚨 PASTE YOUR KEY INSIDE THE QUOTES BELOW 🚨
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
st.set_page_config(page_title="Reclaim Home Prototype", page_icon="🏠")

# --- FUNCTIONS ---
def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def analyze_image(image_file):
    base64_image = encode_image(image_file)
    prompt = """
    Analyze this appliance image. Return a JSON object with:
    - manufacturer (string)
    - model_number (string)
    - serial_number (string)
    - category (string, e.g. HVAC, Plumbing, Kitchen)
    - maintenance_alert (string, a short proactive tip based on age/type)
    
    If you cannot read a value, use "Unknown". 
    If it is not an appliance, return "Error" in the manufacturer field.
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
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        st.error(f"API Error: {e}")
        return {"manufacturer": "Error"}

def get_diy_advice(model_info, symptom):
    prompt = f"""
    The user has a {model_info.get('manufacturer')} {model_info.get('category')} 
    Model: {model_info.get('model_number')}.
    
    The reported symptom is: "{symptom}".
    
    Provide a JSON response with:
    - likely_cause (string)
    - difficulty_level (string: "Easy", "Medium", or "Call a Pro")
    - estimated_time (string)
    - steps (array of strings, specific troubleshooting steps for this model)
    - safety_warning (string, e.g. "Turn off breaker")
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert handyman AI. Be specific to the model provided."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- APP UI ---
st.title("Reclaim 🏠")
st.caption("Proactive. Preventable. Prepared.")

# Initialize Session State
if 'assets' not in st.session_state:
    st.session_state.assets = []
if 'current_asset' not in st.session_state:
    st.session_state.current_asset = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

tab1, tab2 = st.tabs(["📷 Scan & Fix", "📋 My Inventory"])

with tab1:
    st.write("### 1. Identify")
    
    img_file = st.file_uploader("Tap here to Snap Photo", type=['jpg', 'png', 'jpeg'])

    if img_file:
        if st.button("Identify Asset 🔍", type="primary"):
            with st.spinner("Analyzing specs..."):
                try:
                    data = analyze_image(img_file)
                    if data.get('manufacturer') == "Error":
                        st.error("Could not identify appliance. Try again.")
                    else:
                        st.session_state.current_asset = data
                        st.session_state.assets.append(data)
                        st.session_state.chat_history = [] # Reset chat for new asset
                        st.success("Asset Identified!")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Results Section
    if st.session_state.current_asset:
        asset = st.session_state.current_asset
        
        st.divider()
        
        with st.container(border=True):
            c1, c2 = st.columns(2)
            c1.metric("Make", asset.get('manufacturer', 'Unknown'))
            c1.metric("Model", asset.get('model_number', 'Unknown'))
            st.info(f"💡 {asset.get('maintenance_alert')}")

        st.write("### 2. Troubleshoot")
        
        # Initial Diagnostic Button
        symptom = st.text_input("What is wrong?", placeholder="e.g. leaking water")
        
        if st.button("Start Diagnosis 🔧"):
            if not symptom:
                st.warning("Please describe the problem.")
            else:
                with st.spinner("Consulting manuals..."):
                    advice = get_diy_advice(asset, symptom)
                    
                    # Add the initial advice to chat history so the AI remembers it
                    initial_msg = f"**Diagnosis:** {advice.get('likely_cause')}\n\n"
                    initial_msg += f"**Steps:**\n"
                    for step in advice.get('steps', []):
                        initial_msg += f"- {step}\n"
                    initial_msg += f"\n**Safety:** {advice.get('safety_warning')}"
                    
                    st.session_state.chat_history = [
                        {"role": "assistant", "content": initial_msg}
                    ]

        # --- CHAT INTERFACE ---
        st.write("### 3. Chat with Handyman")
        
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat Input
        if prompt := st.chat_input("Ask a follow-up question..."):
            # 1. Add user message to state
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # 2. Get AI Response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                # Context for the AI
                system_context = f"""
                You are a helpful expert handyman. 
                You are currently helping the user fix a {asset.get('manufacturer')} {asset.get('model_number')}.
                Be concise, safety-conscious, and encouraging.
                """
                
                full_messages = [{"role": "system", "content": system_context}] + st.session_state.chat_history
                
                stream = client.chat.completions.create(
                    model="gpt-4o",
                    messages=full_messages,
                    stream=True
                )
                
                response = st.write_stream(stream)
            
            # 3. Save AI response to state
            st.session_state.chat_history.append({"role": "assistant", "content": response})

with tab2:
    st.write("### Inventory")
    if st.session_state.assets:
        df = pd.json_normalize(st.session_state.assets)
        st.dataframe(df)
    else:
        st.info("No assets scanned yet.")