import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from streamlit_calendar import calendar
import plotly.express as px # Nova biblioteca para gráficos
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded"
)

# --- PASSO 2: VISUAL PREMIUM (FUNDA FIXO + VIDRO FOSCO) ---
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

# --- PASSO 3: CONEXÃO ---
try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except Exception as e:
    st.error(f"Erro: {e}"); st.stop()

# --- PASSO 4: ACESSO ---
if "user_email" not in st.session_state:
    st.title("💸 Finance Hub: Acesso"); st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 5: BARRA LATERAL COM GRÁFICOS ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.clear(); st.rerun()
    
    # Busca dados para o gráfico
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).execute().data
    if data_res:
        df_side = pd.DataFrame(data_res)
        df_gastos = df_side[df_side['value'] < 0].copy()
        df_gastos['abs_value'] = df_gastos['value'].abs()
        
        st.markdown("---")
        st.caption("📊 DISTRIBUIÇÃO DE GASTOS")
        fig = px.pie(df_gastos, values='abs_value', names='category', 
                     hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), 
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    with st.expander("➕ Novo Template"):
        with st.form("f_tmp", clear_on_submit=True):
            tn = st.text_input("Nome"); tc = st.selectbox("Cat", ["Alimentação", "Venda Scripts", "Infra"])
            if st.form_submit_button("Salvar"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "user_email": u_log}]).execute(); st.rerun()

# --- PASSO 6: LANÇAMENTOS ---
st.title("📊 Gestão Financeira Premium")
c1, c2 = st.columns([1, 2.5])
with c1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        fp = st.selectbox("Pagamento", ["Dinheiro", "Cartão Crédito", "Cartão Débito", "Alimentação"])
        v = st.number_input("Valor", step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Confirmar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "description": ds, "value": val_f, "payment_method": fp, "user_email": u_log}]).execute(); st.rerun()

# --- PASSO 7: CALENDÁRIO COMERCIAL ---
with c2:
    if data_res:
        events = [{"title": f"{i['description']} (R$ {abs(i['value']):.2f})", "start": i['date'], "color": "#ff4b4b" if i['value'] < 0 else "#28a745"} for i in data_res]
        calendar(events=events, options={"height": 550}, key="calendar")

# --- PASSO 8: RESUMO EM BARRAS (ABAIXO) ---
st.markdown("---")
if data_res:
    st.subheader("📈 Tendência por Categoria")
    df_bar = pd.DataFrame(data_res)
    fig_bar = px.bar(df_bar, x="date", y="value", color="category", barmode="group", title="Entradas e Saídas Diárias")
    fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
    st.plotly_chart(fig_bar, use_container_width=True)

# --- PASSO 9: EXTRATO ---
st.dataframe(pd.DataFrame(data_res)[['id', 'date', 'description', 'payment_method', 'value']], use_container_width=True, hide_index=True)