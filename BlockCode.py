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
        g = requests.get("https://www.goldapi.io/api/XAU/EUR", headers=headers, timeout=5).json()['price_gram_24k']
        s = requests.get("https://www.goldapi.io/api/XAG/EUR", headers=headers, timeout=5).json()['price_gram_24k']
        return {"Gold": round(g, 2), "Silber": round(s, 2)}
    except: return {"Gold": 73.50, "Silber": 0.92}

# --- 2. BILD-OPTIMIERUNG ---
def optimiere_bild(upload_file):
    img = Image.open(upload_file)
    img.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()

# --- 3. KI EXPERTEN-ANALYSE ---
def analysiere_muenze_profi(img1_bytes, img2_bytes, zustand):
    b64_1 = base64.b64encode(img1_bytes).decode('utf-8')
    b64_2 = base64.b64encode(img2_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    
    prompt = f"""
    Identifiziere diese Münze präzise (Vorder- und Rückseite). Zustand: {zustand}.
    Antworte NUR als JSON:
    {{
      "name": "Name der Münze", "jahr": "Jahr", "land": "Land",
      "metall": "Gold oder Silber oder Unedel", "reinheit": 0.900,
      "gewicht": "7.96", "groesse": "22mm", "auflage": "1.2 Mio",
      "marktwert": "450€", "besonderheiten": "Keine", "info": "Historie..."
    }}
    """
    
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

# --- 4. APP SETUP ---
st.set_page_config(page_title="Papas Münz-Archiv", layout="centered")

if 'page' not in st.session_state: st.session_state.page = 'home'

# HOME
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-APP")
    p = get_live_prices()
    st.markdown(f'<div style="background:#ffc107;padding:15px;border-radius:15px;text-align:center;font-weight:bold;">Gold: {p["Gold"]}€/g | Silber: {p["Silber"]}€/g</div>', unsafe_allow_html=True)
    
if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
   st.session_state.page = 'scanner'; st.rerun()
if st.button("📚 MEINE SAMMLUNG"):
   st.session_state.page = 'sammlung'; st.rerun()

# SCANNER
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    f1 = st.file_uploader("1. Vorderseite", type=["jpg","jpeg","png"], key="v")
    f2 = st.file_uploader("2. Rückseite", type=["jpg","jpeg","png"], key="r")
    
    if f1 and f2:
        if st.button("EXPERTE FRAGEN ✨", type="primary"):
            with st.spinner("Analyse läuft..."):
                try:
                    res = json.loads(analysiere_muenze_profi(optimiere_bild(f1), optimiere_bild(f2), zustand))
                    client = init_supabase()
                    client.table("muenzen").insert({
                        "name": res['name'], "jahr": str(res['jahr']), "land": res['land'],
                        "metall": res['metall'], "reinheit": res['reinheit'],
                        "gewicht": str(res['gewicht']), "groesse": res['groesse'],
                        "auflage": res['auflage'], "marktwert": res['marktwert'],
                        "besonderheiten": res['besonderheiten'], "info": res['info']
                    }).execute()
                    st.success("Erkannt und gespeichert!")
                    st.json(res)
                except Exception as e: st.error(f"Fehler: {e}")

# SAMMLUNG (DETAILLIERT & LÖSCHBAR)
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    st.title("📚 Deine Schätze")
    
    prices = get_live_prices()
    try:
        client = init_supabase()
        res = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        
        for m in res.data:
            with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                # Aktuellen Metallwert berechnen
                kurs = prices.get(m['metall'], 0)
                try:
                    gew_val = float(m['gewicht'].replace('g','').strip())
                    m_wert = gew_val * float(m['reinheit'] or 0) * kurs
                    st.write(f"📈 **Aktueller Metallwert:** {m_wert:.2f}€")
                except: pass
                
                st.write(f"💰 **Sammler-Marktwert:** {m['marktwert']}")
                st.write(f"🌍 **Land:** {m['land']} | 🛠️ **Material:** {m['metall']}")
                st.write(f"⚖️ **Gewicht:** {m['gewicht']}g | 📏 **Größe:** {m['groesse']}")
                st.write(f"📉 **Auflage:** {m['auflage']}")
                st.write(f"✨ **Besonderheit:** {m['besonderheiten']}")
                st.info(f"📜 **Hintergrund:** {m['info']}")
                
                if st.button(f"🗑️ Löschen", key=f"del_{m['id']}"):
                    client.table("muenzen").delete().eq("id", m['id']).execute()
                    st.rerun()
    except Exception as e: st.error(f"Datenbank-Fehler: {e}")
