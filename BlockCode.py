import streamlit as st
import requests
import base64
import json
import io
from PIL import Image # NEU: Für die Bildverkleinerung
from supabase import create_client, Client

# --- 1. DATENBANK VERBINDUNG ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- 2. HILFSFUNKTION: BILD VERKLEINERN ---
def verkleinere_bild(upload_file, max_size=1024):
    """Macht das Bild kleiner, damit der Upload schneller geht"""
    image = Image.open(upload_file)
    
    # Verhältnis berechnen, damit das Bild nicht verzerrt wird
    ratio = max_size / float(max_size if max_size > image.size[0] else image.size[0])
    if image.size[0] > max_size:
        new_size = (max_size, int(float(image.size[1]) * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Das verkleinerte Bild wieder in Bytes umwandeln
    byte_arr = io.BytesIO()
    # Als JPEG speichern (spart extrem viel Platz gegenüber PNG)
    image.convert("RGB").save(byte_arr, format='JPEG', quality=85)
    return byte_arr.getvalue()

# --- 3. KI FUNKTION ---
def analysiere_muenze(img1_bytes, img2_bytes, zustand):
    try:
        # Die bereits verkleinerten Bytes in Base64 umwandeln
        b64_1 = base64.b64encode(img1_bytes).decode('utf-8')
        b64_2 = base64.b64encode(img2_bytes).decode('utf-8')
        
        headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
        prompt = f"Identifiziere diese Münze. Zustand: {zustand}. Antworte als JSON: {{'name': '...', 'jahr': '...', 'land': '...', 'metall': '...', 'marktwert': '...€', 'info': '...'}}"
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_1}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_2}"}}
            ]}],
            "response_format": { "type": "json_object" }
        }
        res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        return None

# --- 4. OPTIK & NAVIGATION ---
st.set_page_config(page_title="Papas Münz-Archiv", layout="centered")
st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 80px; border-radius: 15px; font-weight: bold; margin-bottom: 20px; }
    .stButton > button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    .result-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 10px solid #ffd700; color: #333; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'

# HAUPTMENÜ
if st.session_state.page == 'home':
    st.markdown("<h1 style='text-align: center;'>🪙 PAPAS MÜNZ-ARCHIV</h1>", unsafe_allow_html=True)
    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.page = 'scanner'; st.rerun()
    if st.button("📚 MEINE SAMMLUNG"):
        st.session_state.page = 'sammlung'; st.rerun()

# SCANNER
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    
    st.write("### 1. Zustand")
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    st.write("### 2. Fotos")
    f1 = st.file_uploader("Vorderseite (Kamera öffnen)", type=["jpg", "jpeg", "png"])
    if f1:
        st.success("Vorderseite bereit! ✅")
        f2 = st.file_uploader("Rückseite (Kamera öffnen)", type=["jpg", "jpeg", "png"])
        
        if f2:
            st.success("Rückseite bereit! ✅")
            if st.button("ANALYSE STARTEN ✨", type="primary"):
                with st.spinner("Bilder werden optimiert und analysiert..."):
                    # Bilder verkleinern BEVOR sie an die KI gehen
                    img1_small = verkleinere_bild(f1)
                    img2_small = verkleinere_bild(f2)
                    
                    res_raw = analysiere_muenze(img1_small, img2_small, zustand)
                    if res_raw:
                        data = json.loads(res_raw)
                        # Speichern
                        supabase.table("muenzen").insert({
                            "name": data['name'], "jahr": str(data['jahr']),
                            "land": data['land'], "marktwert": data['marktwert']
                        }).execute()
                        
                        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                        st.header(f"{data['name']} ({data['jahr']})")
                        st.write(f"**Marktwert:** {data['marktwert']} | **Land:** {data['land']}")
                        st.success("Gespeichert! ☁️")
                        st.markdown("</div>", unsafe_allow_html=True)

# SAMMLUNG
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    st.title("📚 Album")
    response = supabase.table("muenzen").select("*").order("created_at", desc=True).execute()
    for m in response.data:
        with st.expander(f"{m['name']} ({m['jahr']})"):
            st.write(f"Wert: {m['marktwert']} | Land: {m['land']}")










































