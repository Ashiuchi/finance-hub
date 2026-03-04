import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO DE INTERFACE (OBRIGATÓRIO NO TOPO) ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# --- PASSO 2: BLINDAGEM VISUAL AGRESSIVA (CSS) ---
# Esconde o ícone do Git e botões de deploy usando seletores universais
st.markdown("""
    <style>
    /* Esconde o header inteiro onde o ícone do Git reside */
    header[data-testid="stHeader"] {
        visibility: hidden;
        height: 0px;
    }
    /* Esconde links específicos do GitHub caso o header tente reaparecer */
    a[href*="github.com"], .stAppDeployButton {
        display: none !important;
    }
    /* Garante que a seta da sidebar continue visível e funcional */
    [data-testid="stSidebarNav"] {
        visibility: visible !important;
    }
    footer {visibility: hidden;}
    /* Ajusta o espaçamento do topo já que removemos o header */
    .block-container {
        padding-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- PASSO 3: CONEXÃO COM O BANCO DE DADOS ---
try:
    st_supabase = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- PASSO 4: FUNÇÕES DE APOIO ---
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

# --- PASSO 5: SISTEMA DE ACESSO (LOGIN / CADASTRO) ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso")
    tab_log, tab_reg = st.tabs(["Login", "Cadastrar"])
    
    with tab_log:
        e_l = st.text_input("E-mail", key="l_email_v9")
        p_l = st.text_input("Senha", type="password", key="l_pass_v9")
        if st.button("Entrar", key="l_btn_v9"):
            res = st_supabase.table("app_users").select("email").eq("email", e_l).eq("password", p_l).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
            else: st.error("Dados incorretos.")
            
    with tab_reg:
        ne = st.text_input("Novo E-mail", key="r_email_v9")
        np = st.text_input("Senha (mín. 6 chars)", type="password", key="r_pass_v9")
        if st.button("Criar Conta", key="r_btn_v9"):
            if is_valid_email(ne) and len(np) >= 6:
                try:
                    st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
                    st.success("Sucesso! Vá para Login.")
                except: st.error("E-mail já cadastrado.")
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL (LOGOUT) ---
with st.sidebar:
    st.write(f"Logado como: **{u_log}**")
    if st.button("🚪 Sair", key="btn_out_v9", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- PASSO 7: GESTÃO DE TEMPLATES (CRIAR E DELETAR) ---
    st.markdown("---")
    st.subheader("⚙️ Meus Atalhos")
    with st.expander("➕ Novo Template"):
        with st.form("f_new_tmp_v9", clear_on_submit=True):
            tn = st.text_input("Nome")
            tc = st.selectbox("Categoria", ["Alimentação", "Transporte", "Saúde", "Educação", "Salário/Renda"])
            td = st.text_input("Descrição")
            tv = st.number_input("Valor", step=0.01)
            if st.form_submit_button("Criar"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "description": td, "value": tv, "user_email": u_log}]).execute()
                st.rerun()

    try:
        tmp_data = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data
        if tmp_data:
            tdel = st.selectbox("Deletar:", [t['template_name'] for t in tmp_data], key="sel_tmp_v9")
            if st.button("🗑️ Remover"):
                st_supabase.table("templates").delete().eq("template_name", tdel).eq("user_email", u_log).execute()
                st.rerun()
    except: pass

# --- PASSO 8: LANÇAMENTOS E EDIÇÃO (AUTONOMIA TOTAL) ---
st.title("📊 Painel Financeiro")
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add_v9", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        c = st.selectbox("Categoria", ["Alimentação", "Transporte", "Saúde", "Educação", "Salário/Renda"])
        v = st.number_input("Valor", min_value=0.0, step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "category": c, "description": ds, "value": val_f, "user_email": u_log} ]).execute()
            st.rerun()

    st.markdown("---")
    st.subheader("📝 Editar/Excluir")
    id_op = st.number_input("ID do lançamento:", min_value=1, step=1, key="id_op_v9")
    ce1, ce2 = st.columns(2)
    with ce1:
        if st.button("🗑️ Deletar ID", key="btn_del_v9"):
            st_supabase.table("transactions").delete().eq("id", id_op).eq("user_email", u_log).execute()
            st.rerun()
    with ce2:
        if id_op:
            res_v = st_supabase.table("transactions").select("value").eq("id", id_op).eq("user_email", u_log).execute()
            if res_v.data:
                nv = st.number_input("Novo Valor:", value=float(res_v.data[0]['value']), key="nv_v9")
                if st.button("💾 Salvar", key="btn_sv_v9"):
                    st_supabase.table("transactions").update({"value": nv}).eq("id", id_op).execute()
                    st.rerun()

# --- PASSO 9: DASHBOARD E MÉTRICAS ---
try:
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).order("date", desc=True).execute().data
    df = pd.DataFrame(data_res)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['m_y'] = df['date'].dt.strftime('%m/%Y')
        with col2:
            st.subheader("📊 Resumo Mensal")
            m_s = st.selectbox("Mês:", df['m_y'].unique(), key="sel_mes_v9")
            df_m = df[df['m_y'] == m_s]
            e, s = df_m[df_m['value'] > 0]['value'].sum(), df_m[df_m['value'] < 0]['value'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Entradas", f"R$ {e:,.2f}")
            m2.metric("Saídas", f"R$ {abs(s):,.2f}")
            m3.metric("Saldo", f"R$ {e+s:,.2f}")
            st.dataframe(df_m[['id', 'date', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
except: pass