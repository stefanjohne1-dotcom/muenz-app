import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. DATENBANK VERBINDUNG ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- 2. HILFSFUNKTIONEN: PREISE & BILD-OPTIMIERUNG ---

def get_live_prices():
    """Holt die echten Börsenkurse für Gold und Silber in Euro"""
    if "GOLD_API_KEY" not in st.secrets:
        return {"Gold": 73.50, "Silber": 0.92} # Fallback-Werte
    try:
        headers = {"x-access-token": st.secrets["GOLD_API_KEY"], "Content-Type": "application/json"}
g = requests.get("https://www.goldapi.io/api/XAU/EUR", headers=headers).json()['price_gram_24k']
s = requests.get("https://www.goldapi.io/api/XAG/EUR", headers=headers).json()['price_gram_24k']
        return {"Gold": round(g, 2), "Silber": round(s, 2)}
    except:
        return {"Gold": 73.50, "Silber": 0.92}

def verkleinere_bild(upload_file, max_size=1024):
    """Macht das Handyfoto klein & schnell für den Upload"""
    image = Image.open(upload_file)
    ratio = max_size / float(max_size if max_size > image.size[0] else image.size[0])
    if image.size[0] > max_size:
        new_size = (max_size, int(float(image.size[1]) * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    byte_arr = io.BytesIO()
    image.convert("RGB").save(byte_arr, format='JPEG', quality=85)
    return byte_arr.getvalue()

def analysiere_muenze_profi(img1_bytes, img2_bytes, zustand):
    """Schickt Bilder an die KI für eine Experten-Analyse"""
    if "OPENAI_API_KEY" not in st.secrets:
        return None
    try:
        b64_1 = base64.b64encode(img1_bytes).decode('utf-8')
        b64_2 = base64.b64encode(img2_bytes).decode('utf-8')
        headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
        prompt = f"""
        Identifiziere diese Münze präzise. Zustand: {zustand}.
        Antworte NUR als JSON:
        {{
          "name": "Name", "jahr": "Jahr", "land": "Land", "metall": "Gold oder Silber oder Unedel",
          "reinheit": 0.900, "gewicht": 7.96, "auflage": "Stückzahl",
          "marktwert_sammler": "Spanne in €",
          "geschichte": "Historischer Hintergrund",
          "merkmale": "Besonderheiten/Fehlprägungen"
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
    except:
        return None

# --- 3. OPTIK & STYLING ---
st.set_page_config(page_title="Papas Münz-Archiv", layout="centered")
st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 80px; border-radius: 15px; font-size: 18px !important; font-weight: bold; margin-bottom: 20px; }
    .stButton > button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    .price-tile { background-color: #ffc107; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; color: #333; margin-bottom: 20px; border: 2px solid #e0a800; }
    .result-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 10px solid #ffd700; color: #333; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'home'

# HAUPTMENÜ
if st.session_state.page == 'home':
    st.markdown("<h1 style='text-align: center;'>🪙 PAPAS MÜNZ-ARCHIV</h1>", unsafe_allow_html=True)
    
    # Live-Kurse auf Startseite
    p = get_live_prices()
    st.markdown(f'<div class="price-tile">📊 BÖRSENKURSE HEUTE<br>Gold: {p["Gold"]}€/g | Silber: {p["Silber"]}€/g</div>', unsafe_allow_html=True)

    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.page = 'scanner'; st.rerun()
    if st.button("📚 MEINE SAMMLUNG"):
        st.session_state.page = 'sammlung'; st.rerun()

# SCANNER
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    
    st.subheader("1. Zustand")
    zustand = st.select_slider("Wie erhalten?", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    st.subheader("2. Fotos (Tippe für Kamera)")
    f1 = st.file_uploader("Vorderseite", type=["jpg", "jpeg", "png"])
    if f1:
        f2 = st.file_uploader("Rückseite", type=["jpg", "jpeg", "png"])
        if f2:
            if st.button("EXPERTEN-ANALYSE STARTEN ✨", type="primary"):
                with st.spinner("Bilder werden optimiert und analysiert..."):
                    # Optimierung
                    img1_small = verkleinere_bild(f1)
                    img2_small = verkleinere_bild(f2)
                    
                    res_raw = analysiere_muenze_profi(img1_small, img2_small, zustand)
                    if res_raw:
                        d = json.loads(res_raw)
                        p = get_live_prices()
                        
                        # Metallwert-Berechnung
                        gramm_preis = p.get(d['metall'], 0)
                        m_wert = d['gewicht'] * d['reinheit'] * gramm_preis
                        
                        # Datenbank-Speicherung
                        supabase.table("muenzen").insert({
                            "name": d['name'], "jahr": str(d['jahr']),
                            "land": d['land'], "marktwert": d['marktwert_sammler']
                        }).execute()
                        
                        # Ergebnis-Karte
                        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                        st.header(f"{d['name']} ({d['jahr']})")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write("**Börsen-Metallwert:**")
                            st.subheader(f"{m_wert:.2f} €")
                        with c2:
                            st.write("**Sammler-Marktwert:**")
                            st.subheader(f"{d['marktwert_sammler']}")
                        
                        st.divider()
                        st.write(f"📜 **Geschichte:** {d['geschichte']}")
                        st.info(f"🔍 **Sammler-Tipp:** {d['merkmale']}")
                        st.success("Erfolgreich gespeichert! ☁️")
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.error("Fehler bei der Analyse.")

# SAMMLUNG
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    st.title("📚 Deine Schätze")
    response = supabase.table("muenzen").select("*").order("created_at", desc=True).execute()
    for m in response.data:
        with st.expander(f"{m['name']} ({m['jahr']})"):
            st.write(f"Wert: {m['marktwert']} | Land: {m['land']}")
            st.caption(f"Datum: {m['created_at'][:10]}")
