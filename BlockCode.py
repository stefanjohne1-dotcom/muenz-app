import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. VERBINDUNGEN ---
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

# --- 2. HILFSFUNKTIONEN ---
def optimiere_bild(upload_file):
    img = Image.open(upload_file)
    img.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()

def analysiere_muenze(img1_bytes, img2_bytes, zustand):
    b64_1 = base64.b64encode(img1_bytes).decode('utf-8')
    b64_2 = base64.b64encode(img2_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    prompt = f"Identifiziere diese Münze. Zustand: {zustand}. Antworte NUR als JSON: {{'name': '...', 'jahr': '...', 'land': '...', 'marktwert': '...€', 'info': '...', 'metall': 'Gold', 'reinheit': 0.9, 'gewicht': 7.0}}"
    
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

# --- 3. APP OBERFLÄCHE ---
st.set_page_config(page_title="Münz-Archiv", layout="centered")

if 'page' not in st.session_state: st.session_state.page = 'home'

# STARTSEITE
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-APP")
    p = get_live_prices()
    st.markdown(f"""<div style="background:#ffc107;padding:20px;border-radius:15px;text-align:center;font-weight:bold;color:#333;">
        AKTUELL: Gold {p['Gold']}€/g | Silber {p['Silber']}€/g</div>""", unsafe_allow_html=True)
    st.write(" ")
if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
    st.session_state.page = 'scanner'
    st.rerun()
    if st.button("📚 SAMMLUNG ANSEHEN"):
        st.session_state.page = 'sammlung'
        st.rerun()

# SCANNER-SEITE
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    zustand = st.select_slider("Wie ist der Zustand?", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    f1 = st.file_uploader("1. FOTO VORDERSEITE", type=["jpg", "jpeg", "png"], key="vorder")
    f2 = st.file_uploader("2. FOTO RÜCKSEITE", type=["jpg", "jpeg", "png"], key="rueck")
    
    if f1 and f2:
        st.success("Beide Fotos bereit! ✅")
        if st.button("JETZT ANALYSIEREN ✨", type="primary"):
            with st.spinner("Experte prüft die Münze..."):
                try:
                    client = init_supabase()
                    img1 = optimiere_bild(f1)
                    img2 = optimiere_bild(f2)
                    
                    res_raw = analysiere_muenze(img1, img2, zustand)
                    d = json.loads(res_raw)
                    
                    # Metallwert-Berechnung
                    p = get_live_prices()
                    g_preis = p.get(d.get('metall', 'Unedel'), 0)
                    m_wert = d.get('gewicht', 0) * d.get('reinheit', 0) * g_preis
                    
                    # Speichern
                    client.table("muenzen").insert({
                        "name": d['name'], "jahr": str(d['jahr']),
                        "land": d['land'], "marktwert": d['marktwert']
                    }).execute()
                    
                    st.balloons()
                    st.markdown(f"""<div style="background:white;padding:20px;border-radius:15px;border-left:10px solid #ffd700;color:#333;">
                        <h3>{d['name']} ({d['jahr']})</h3>
                        <p><b>Sammlerwert:</b> {d['marktwert']}</p>
                        <p><b>Metallwert:</b> {m_wert:.2f}€</p>
                        <p><i>{d['info']}</i></p>
                    </div>""", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Fehler: {e}")
    else:
        st.info("Bitte lade erst beide Fotos hoch, um die Analyse zu starten.")

# SAMMLUNG-SEITE
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
    except Exception as e:
        st.error(f"Datenbank-Fehler: {e}")



