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
        g = requests.get("https://www.goldapi.io/api/XAU/EUR", headers=headers, timeout=5).json()['price_gram_24k']
        s = requests.get("https://www.goldapi.io/api/XAG/EUR", headers=headers, timeout=5).json()['price_gram_24k']
        return {"Gold": round(g, 2), "Silber": round(s, 2)}
    except: return {"Gold": 73.50, "Silber": 0.92}

# --- 2. BILD-VERARBEITUNG ---
def optimiere_bild(upload_file):
    if upload_file is None: return None
    img = Image.open(upload_file)
    img.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=75) # Qualität etwas runter für schnelleren Upload
    return buffer.getvalue()

# --- 3. APP SETUP ---
st.set_page_config(page_title="Münz-Archiv", layout="centered")

# Gedächtnis der App (Session State)
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'foto1_data' not in st.session_state: st.session_state.foto1_data = None
if 'foto2_data' not in st.session_state: st.session_state.foto2_data = None

# --- STARTSEITE ---
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-APP")
    p = get_live_prices()
    st.markdown(f"""<div style="background:#ffc107;padding:15px;border-radius:15px;text-align:center;font-weight:bold;color:#333;">
        LIVE: Gold {p['Gold']}€/g | Silber {p['Silber']}€/g</div>""", unsafe_allow_html=True)
    
    st.write(" ")
if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
   st.session_state.foto1_data = None # Speicher leeren für neuen Scan
   st.session_state.foto2_data = None
   st.session_state.page = 'scanner'
   st.rerun()
if st.button("📚 SAMMLUNG ANSEHEN"):
   st.session_state.page = 'sammlung'
   st.rerun()

# --- SCANNER-SEITE ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    st.subheader("1. Zustand wählen")
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    st.subheader("2. Fotos aufnehmen")
    
    # Foto 1: Vorderseite
    u1 = st.file_uploader("📸 VORDERSEITE (Tippen)", type=["jpg", "jpeg", "png"], key="u1")
    if u1:
        st.session_state.foto1_data = optimiere_bild(u1)
        st.success("Vorderseite erfasst! ✅")

    # Foto 2: Rückseite (Wird immer angezeigt, damit das Handy nicht verwirrt ist)
    u2 = st.file_uploader("📸 RÜCKSEITE (Tippen)", type=["jpg", "jpeg", "png"], key="u2")
    if u2:
        st.session_state.foto2_data = optimiere_bild(u2)
        st.success("Rückseite erfasst! ✅")

    # Analyse-Knopf erscheint erst, wenn beide Fotos im Speicher sind
    if st.session_state.foto1_data and st.session_state.foto2_data:
        st.write("---")
        if st.button("ANALYSE JETZT STARTEN ✨", type="primary"):
            with st.spinner("Experte prüft die Münze..."):
                try:
                    # KI ANALYSE
                    b64_1 = base64.b64encode(st.session_state.foto1_data).decode('utf-8')
                    b64_2 = base64.b64encode(st.session_state.foto2_data).decode('utf-8')
                    
                    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
                    prompt = f"Identifiziere diese Münze. Zustand: {zustand}. Antworte als JSON: {{'name': '...', 'jahr': '...', 'land': '...', 'marktwert': '...€', 'info': '...'}}"
                    
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
                         d = res.json()['choices'][0]['message']['content']
                         data = json.loads(d)
                    
                    # IN SUPABASE SPEICHERN
                        client = init_supabase()
                        client.table("muenzen").insert({
                        "name": data['name'], "jahr": str(data['jahr']),
                        "land": data['land'], "marktwert": data['marktwert']
                    }).execute()
                    
                    st.balloons()
                    st.markdown(f"""<div style="background:white;padding:20px;border-radius:15px;border-left:10px solid #ffd700;color:#333;box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                        <h3>{data['name']} ({data['jahr']})</h3>
                        <p><b>Wert:</b> {data['marktwert']}</p>
                        <p><i>{data['info']}</i></p>
                    </div>""", unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Fehler: {e}")

# --- SAMMLUNG-SEITE ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
        st.title("📚 Die Sammlung")
    try:
        client = init_supabase()
        res = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        if not res.data:
               st.info("Noch keine Schätze gespeichert.")
        for m in res.data:
            with st.expander(f"{m['name']} ({m['jahr']})"):
                st.write(f"Wert: {m['marktwert']} | Land: {m['land']}")
                st.caption(f"Gescannt am: {m['created_at'][:10]}")
    except:
        st.error("Datenbank-Verbindung fehlgeschlagen.")

