import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from streamlit_calendar import calendar # Nova biblioteca
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded"
)

# --- PASSO 2: BLINDAGEM E SIDEBAR FIXA ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stSidebar"] { min-width: 260px !important; max-width: 260px !important; }
    [data-testid="stSidebar"] button[title="Collapse sidebar"] { display: none !important; }
    .block-container { padding-top: 1.5rem; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- PASSO 3: CONEXÃO ---
try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except Exception as e:
    st.error(f"Erro: {e}"); st.stop()

# --- PASSO 4: ACESSO ---
if "user_email" not in st.session_state:
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    with t1:
        e_l, p_l = st.text_input("E-mail"), st.text_input("Senha", type="password")
        if st.button("Entrar"):
            res = st_supabase.table("app_users").select("email").eq("email", e_l).eq("password", p_l).execute()
            if res.data: st.session_state["user_email"] = res.data[0]["email"]; st.rerun()
    with t2:
        ne, np = st.text_input("Novo E-mail"), st.text_input("Nova Senha", type="password")
        if st.button("Criar Conta"):
            st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
            st.success("Criado!")
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 5: BARRA LATERAL ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.clear(); st.rerun()
    st.markdown("---")
    st.caption("⚙️ TEMPLATES")
    with st.expander("➕ Novo"):
        with st.form("f_tmp", clear_on_submit=True):
            tn = st.text_input("Nome"); tc = st.selectbox("Cat", ["Alimentação", "Salário", "Infra"])
            tv = st.number_input("Valor", step=0.01)
            if st.form_submit_button("Salvar"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "value": tv, "user_email": u_log}]).execute(); st.rerun()

# --- PASSO 6: LANÇAMENTOS (AGENDAMENTOS) ---
st.title("📊 Gestão & Agendamentos")
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader("📝 Novo Lançamento")
    with st.form("f_add", clear_on_submit=True):
        d = st.date_input("Data (Pode ser futura)", datetime.now())
        ds = st.text_input("Descrição")
        fp = st.selectbox("Pagamento", ["Dinheiro", "Cartão Crédito", "Cartão Débito", "Alimentação"])
        v = st.number_input("Valor", step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Confirmar Agendamento"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([
                {"date": d.strftime("%Y-%m-%d"), "description": ds, "value": val_f, "payment_method": fp, "user_email": u_log}
            ]).execute(); st.rerun()

# --- PASSO 7: VISÃO DE CALENDÁRIO COMERCIAL ---
with c2:
    st.subheader("📅 Calendário de Transações")
    try:
        data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).execute().data
        calendar_events = []
        for item in data_res:
            color = "#ff4b4b" if item['value'] < 0 else "#28a745"
            calendar_events.append({
                "title": f"{item['description']} (R$ {abs(item['value']):.2f})",
                "start": item['date'],
                "color": color
            })
        
        calendar_options = {
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listMonth"},
            "initialView": "dayGridMonth",
        }
        calendar(events=calendar_events, options=calendar_options)
    except Exception as e:
        st.info("Adicione lançamentos para visualizar o calendário.")

# --- PASSO 8: LISTAGEM E ADMINISTRAÇÃO ---
st.markdown("---")
if data_res:
    df = pd.DataFrame(data_res)
    st.subheader("📂 Extrato Detalhado")
    st.dataframe(df[['id', 'date', 'description', 'payment_method', 'value']], use_container_width=True, hide_index=True)