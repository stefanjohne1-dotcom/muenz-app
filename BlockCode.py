import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. DATENBANK & PREISE ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_live_prices():
    if "GOLD_API_KEY" not in st.secrets: return {"Gold": 73.50, "Silber": 0.92}
    try:
        headers = {"x-access-token": st.secrets["GOLD_API_KEY"]}
        g = requests.get("https://www.goldapi.io/api/XAU/EUR", headers=headers).json()['price_gram_24k']
        s = requests.get("https://www.goldapi.io/api/XAG/EUR", headers=headers).json()['price_gram_24k']
        return {"Gold": round(g, 2), "Silber": round(s, 2)}
    except: return {"Gold": 73.50, "Silber": 0.92}

# --- 2. BILD-OPTIMIERUNG ---
def optimiere_bild(upload_file):
    img = Image.open(upload_file)
    img.thumbnail((1024, 1024)) # Verkleinert das Bild auf max 1024px
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()

# --- 3. KI ANALYSE ---
def analysiere_muenze(img1_bytes, img2_bytes, zustand):
    b64_1 = base64.b64encode(img1_bytes).decode('utf-8')
    b64_2 = base64.b64encode(img2_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    prompt = f"Identifiziere diese Münze. Zustand: {zustand}. Antworte NUR als JSON: {{'name': '...', 'jahr': '...', 'land': '...', 'metall': 'Gold' oder 'Silber' oder 'Unedel', 'reinheit': 0.9, 'gewicht': 7.0, 'marktwert': '...€', 'info': '...'}}"
    
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

# --- 4. APP OBERFLÄCHE ---
st.set_page_config(page_title="Münz-Archiv", layout="centered")

# Navigation
if 'page' not in st.session_state: st.session_state.page = 'home'

if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-APP")
    p = get_live_prices()
st.info(f"Gold: {p['Gold']}€/g | Silber: {p["Silber"]}€/g")
    
    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.page = 'scanner'
        st.rerun()
    if st.button("📚 SAMMLUNG ANSEHEN"):
        st.session_state.page = 'sammlung'
        st.rerun()

elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    # Datei-Uploader (öffnet am Handy die echte Kamera)
    f1 = st.file_uploader("1. FOTO VORDERSEITE", type=["jpg", "jpeg", "png"], key="front")
    f2 = st.file_uploader("2. FOTO RÜCKSEITE", type=["jpg", "jpeg", "png"], key="back")
    
    if f1 and f2:
        if st.button("JETZT ANALYSIEREN ✨", type="primary"):
            with st.spinner("KI wertet aus..."):
                try:
                    supabase = init_supabase()
                    # Bilder verarbeiten
                    img1 = optimiere_bild(f1)
                    img2 = optimiere_bild(f2)
                    
                    # KI fragen
                    ergebnis_raw = analysiere_muenze(img1, img2, zustand)
                    d = json.loads(ergebnis_raw)
                    
                    # In Datenbank speichern
                    supabase.table("muenzen").insert({
                        "name": d['name'], "jahr": str(d['jahr']),
                        "land": d['land'], "marktwert": d['marktwert']
                    }).execute()
                    
                    # Anzeige
                    st.success("Erfolgreich erkannt!")
                    st.subheader(f"{d['name']} ({d['jahr']})")
                    st.write(f"**Marktwert:** {d['marktwert']}")
                    st.write(f"**Info:** {d['info']}")
                except Exception as e:
                    st.error(f"Fehler: {e}")

elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    st.title("📚 Sammlung")
    try:
        supabase = init_supabase()
        res = supabase.table("muenzen").select("*").order("created_at", desc=True).execute()
        for m in res.data:
            with st.expander(f"{m['name']} ({m['jahr']})"):
                st.write(f"Wert: {m['marktwert']} | Land: {m['land']}")
    except:
        st.write("Noch keine Münzen gespeichert.")
