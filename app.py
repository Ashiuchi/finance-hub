import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from streamlit_calendar import calendar
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded"
)

# --- PASSO 2: BLINDAGEM VISUAL, SIDEBAR FIXA E IMAGEM DE FUNDO ---
# Substitua a URL abaixo pela imagem de sua preferência (ex: algo sobre tecnologia ou finanças).
bg_img_url = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1920&q=80"

st.markdown(f"""
    <style>
    /* 1. Imagem de Fundo */
    .stApp {{
        background-image: url("{bg_img_url}");
        background-attachment: fixed;
        background-size: cover;
    }}
    
    /* 2. Sobreposição para melhorar contraste (Vidro Fosco) */
    .stApp > header, .stApp > div {{
        background-color: rgba(14, 17, 23, 0.85); 
    }}

    /* 3. Blindagem de Interface */
    header[data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stSidebar"] {{ min-width: 260px !important; max-width: 260px !important; }}
    [data-testid="stSidebar"] button[title="Collapse sidebar"] {{ display: none !important; }}
    
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- PASSO 3: CONEXÃO SUPABASE ---
try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except Exception as e:
    st.error(f"Erro: {e}"); st.stop()

# --- PASSO 4: VALIDAÇÃO ---
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

# --- PASSO 5: ACESSO ---
if "user_email" not in st.session_state:
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    with t1:
        e_l, p_l = st.text_input("E-mail", key="l_e"), st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar", key="l_btn"):
            res = st_supabase.table("app_users").select("email").eq("email", e_l).eq("password", p_l).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL FIXA ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", key="btn_out", use_container_width=True):
        st.session_state.clear(); st.rerun()
    
    st.markdown("---")
    st.caption("⚙️ MEUS TEMPLATES")
    with st.expander("➕ Novo Template"):
        with st.form("f_tmp", clear_on_submit=True):
            tn = st.text_input("Nome")
            tc = st.selectbox("Cat", ["Alimentação", "Transporte", "Certificações", "Salário/Renda"])
            td, tv = st.text_input("Desc."), st.number_input("Valor", step=0.01)
            if st.form_submit_button("Salvar"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "description": td, "value": tv, "user_email": u_log}]).execute()
                st.rerun()

# --- PASSO 7: PAINEL DE CONTROLE (REGISTRO) ---
st.title("📊 Gestão & Fluxo de Caixa")
c1, c2 = st.columns([1, 2.5])

with c1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add_main", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        fp = st.selectbox("Pagamento", ["Dinheiro", "Cartão Crédito", "Cartão Débito", "Alimentação"])
        v = st.number_input("Valor", min_value=0.0, step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Confirmar Lançamento"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([
                {"date": d.strftime("%Y-%m-%d"), "description": ds, "value": val_f, "payment_method": fp, "user_email": u_log}
            ]).execute(); st.rerun()

# --- PASSO 8: CALENDÁRIO COMERCIAL (VISUALIZAÇÃO) ---
with c2:
    st.subheader("📅 Calendário de Transações")
    try:
        data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).execute().data
        if data_res:
            events = []
            for item in data_res:
                color = "#ff4b4b" if item['value'] < 0 else "#28a745"
                events.append({"title": f"{item['description']} (R$ {abs(item['value']):.2f})", "start": item['date'], "backgroundColor": color, "borderColor": color})
            calendar(events=events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listMonth"}, "initialView": "dayGridMonth", "height": 600}, key="finance_calendar")
    except: st.info("Adicione lançamentos.")

# --- PASSO 9: EXTRATO CONSOLIDADO ---
st.markdown("---")
if data_res:
    df = pd.DataFrame(data_res)
    st.subheader("📂 Extrato Detalhado")
    st.dataframe(df[['id', 'date', 'description', 'payment_method', 'value']], use_container_width=True, hide_index=True)