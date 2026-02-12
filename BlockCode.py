import streamlit as st
import requests
import base64
import json

# --- 1. DESIGN & STYLING ---
st.set_page_config(page_title="Papas Münz-Experte", layout="centered")

st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 140px;
        border-radius: 20px;
        font-size: 22px !important;
        font-weight: bold;
        margin-bottom: 20px;
        border: none;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    .stButton > button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    .stButton > button[kind="secondary"] { background-color: #007bff !important; color: white !important; }
    
    .price-tile {
        background-color: #ffc107;
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        border: 2px solid #e0a800;
        color: #333;
    }
    .result-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 15px;
        border-left: 10px solid #ffd700;
        margin-top: 20px;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KI LOGIK ---
def analysiere_muenze(image_file, zustand):
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("API Key fehlt in den Secrets!")
        return None

    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"
    }

    prompt = f"""
    Analysiere diese Münze. Der Benutzer gibt den Zustand als '{zustand}' an.
    Antworte NUR im JSON-Format mit diesen Feldern:
    {{
      "name": "Vollständiger Name der Münze",
      "jahr": "Prägejahr",
      "metall": "Gold, Silber oder Unedel",
      "reinheit": 0.900,
      "gewicht": 7.96,
      "marktwert_min": 0,
      "marktwert_max": 0,
      "info": "Ein Satz zur Geschichte"
    }}
    """

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "response_format": { "type": "json_object" }
    }

response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
return response.json()['choices'][0]['message']['content']

# --- 3. NAVIGATION ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'sammlung' not in st.session_state:
    st.session_state.sammlung = []

# --- HAUPTMENÜ ---
if st.session_state.page == 'home':
    st.markdown("<h1 style='text-align: center;'>🪙 PAPAS MÜNZ-APP</h1>", unsafe_allow_html=True)
    
    if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
        st.session_state.page = 'scanner'
        st.rerun()

    if st.button("📚 MEINE SAMMLUNG", type="secondary"):
        st.session_state.page = 'sammlung'
        st.rerun()

    st.markdown("""
        <div class="price-tile">
            💰 KURSE HEUTE<br>
            <span style='font-size: 16px;'>Gold: ~73€/g | Silber: ~0,90€/g</span>
        </div>
    """, unsafe_allow_html=True)

# --- SCANNER SEITE ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()

    st.subheader("1. Zustand wählen")
    zustand = st.select_slider(
        "Zustand der Münze:",
        options=["Stark abgenutzt", "Schön", "Vorzüglich", "Stempelglanz"]
    )

    foto = st.camera_input("Foto machen")

    if foto:
        with st.spinner("KI analysiert..."):
            try:
                # Hier startet der kritische Bereich
                ergebnis_raw = analysiere_muenze(foto, zustand)
                ergebnis = json.loads(ergebnis_raw)
                
                st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                name = ergebnis.get ´name`, (unbekannte Münze`)
                jahr = ergebnis.get (`jahr`, `- - - `)
                st.header(f"{ergebnis['name']} ({ergebnis['jahr']})")
                
                c1, c2 = st.columns(2)
                c1.metric("Material", f"{ergebnis['metall']}")
                c2.metric("Marktwert", f"{ergebnis['marktwert_min']}€ - {ergebnis['marktwert_max']}€")
                
                info = ergebnis.get(ìnfo`, `keine weiteren Infos verfügbar.`)
                st.info(f"**Hintergrund:** {ergebnis['info']}")
                st.markdown("</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error (Oje Papa, da hat die Erkennung nicht geklappt.`)
                st.warning (`Versuch es bitte noch einmal mit etwas mehr Licht`)
                print(f`Fehler-Log für dich: {e}`)
                
                if st.button("✅ Speichern"):
                    st.session_state.sammlung.append(ergebnis)
                    st.success("Gespeichert!")
            except Exception as e:
                # Das ist der Teil, der gefehlt hat:
                st.error("Fehler bei der Analyse. Bitte nochmal versuchen.")
                st.write(e)

# --- SAMMLUNG SEITE ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    st.title("📚 Deine Sammlung")
    if not st.session_state.sammlung:
st.info("Noch leer.")
    else:
        for m in st.session_state.sammlung:
            with st.expander(f"{m['name']} ({m['jahr']})"):
                st.write(f"Wert: {m['marktwert_min']}-{m['marktwert_max']}€")
                st.write(f"Info: {m['info']}")

