import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from streamlit_calendar import calendar
import plotly.express as px
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded"
)

# --- PASSO 2: VISUAL PREMIUM (FUNDO FIXO + VIDRO FOSCO) ---
bg_img = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1920&q=80"
st.markdown(f"""
    <style>
    .stApp {{ background-image: url("{bg_img}"); background-attachment: fixed; background-size: cover; }}
    .stApp > header, .stApp > div {{ background-color: rgba(14, 17, 23, 0.85); }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stSidebar"] {{ min-width: 300px !important; max-width: 300px !important; }}
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
    st.error(f"Erro de Conexão: {e}"); st.stop()

# --- PASSO 4: VALIDAÇÃO ---
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

# --- PASSO 5: SISTEMA DE ACESSO (O QUE FOI RESTAURADO) ---
if "user_email" not in st.session_state:
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    
    with t1:
        el = st.text_input("E-mail", key="login_email")
        pl = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar", key="login_btn"):
            res = st_supabase.table("app_users").select("email").eq("email", el).eq("password", pl).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
            else: st.error("Dados incorretos.")
            
    with t2:
        ne = st.text_input("Novo E-mail", key="reg_email")
        np = st.text_input("Senha (mín. 6 chars)", type="password", key="reg_pass")
        if st.button("Criar Conta", key="reg_btn"):
            if is_valid_email(ne) and len(np) >= 6:
                st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
                st.success("Conta criada! Faça login.")
    st.stop() # IMPORTANTE: Impede o carregamento do resto sem login!

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL COM GRÁFICOS ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", key="logout_btn", use_container_width=True):
        st.session_state.clear(); st.rerun()
    
    # Busca dados para o gráfico de Pizza
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).execute().data
    if data_res:
        df_side = pd.DataFrame(data_res)
        df_gastos = df_side[df_side['value'] < 0].copy()
        if not df_gastos.empty:
            df_gastos['abs_value'] = df_gastos['value'].abs()
            st.markdown("---")
            st.caption("📊 DISTRIBUIÇÃO DE GASTOS")
            fig_pizza = px.pie(df_gastos, values='abs_value', names='category', hole=0.4)
            fig_pizza.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), 
                                   paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_pizza, use_container_width=True)

# --- PASSO 7: LANÇAMENTOS E AGENDAMENTOS ---
st.title("📊 Gestão Financeira Premium")
col_form, col_cal = st.columns([1, 2.5])

with col_form:
    st.subheader("➕ Novo Registro")
    with st.form("f_add_entry", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        fp = st.selectbox("Pagamento", ["Dinheiro", "Cartão Crédito", "Cartão Débito", "Alimentação"])
        v = st.number_input("Valor", min_value=0.0, step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Confirmar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([
                {"date": d.strftime("%Y-%m-%d"), "description": ds, "value": val_f, "payment_method": fp, "user_email": u_log}
            ]).execute(); st.rerun()

# --- PASSO 8: CALENDÁRIO COMERCIAL ---
with col_cal:
    if data_res:
        events = [{"title": f"{i['description']} (R$ {abs(i['value']):.2f})", "start": i['date'], "color": "#ff4b4b" if i['value'] < 0 else "#28a745"} for i in data_res]
        calendar(events=events, options={"height": 550, "headerToolbar": {"right": "dayGridMonth,listMonth"}}, key="cal_finance")

# --- PASSO 9: GRÁFICO DE TENDÊNCIA E EXTRATO ---
st.markdown("---")
if data_res:
    df_full = pd.DataFrame(data_res)
    st.subheader("📈 Tendência e Histórico")
    
    # Gráfico de Barras
    fig_bar = px.bar(df_full, x="date", y="value", color="payment_method", title="Movimentação por Método")
    fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Tabela
    st.dataframe(df_full[['id', 'date', 'description', 'payment_method', 'value']], use_container_width=True, hide_index=True)