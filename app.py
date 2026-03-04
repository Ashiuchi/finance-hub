import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# --- PASSO 2: SEGURANÇA DO CÓDIGO (CSS CIRÚRGICO) ---
# Alvo: Apenas o link que aponta para o GitHub, sem afetar a seta da sidebar ou outros menus.
st.markdown("""
    <style>
    /* Esconde apenas o link/ícone que contém o redirecionamento para o GitHub */
    a[href*="github.com"] {
        display: none !important;
    }
    /* Remove o rodapé padrão */
    footer {visibility: hidden;}
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
    st.error(f"Erro de infraestrutura: {e}")
    st.stop()

# --- PASSO 4: FUNÇÕES DE APOIO ---
def is_valid_email(email):
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

# --- PASSO 5: SISTEMA DE AUTENTICAÇÃO ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    
    with t1:
        e_l = st.text_input("E-mail", key="l_email")
        p_l = st.text_input("Senha", type="password", key="l_pass")
        if st.button("Entrar", key="l_btn"):
            res = st_supabase.table("app_users").select("email").eq("email", e_l).eq("password", p_l).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
            else: st.error("Dados incorretos.")
            
    with t2:
        ne = st.text_input("E-mail para Cadastro", key="r_email")
        np = st.text_input("Crie uma Senha", type="password", key="r_pass")
        if st.button("Criar Conta", key="r_btn"):
            if is_valid_email(ne) and len(np) >= 6:
                try:
                    st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
                    st.success("Conta criada! Vá para Login.")
                except: st.error("E-mail já cadastrado.")
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL (USUÁRIO E LOGOUT) ---
with st.sidebar:
    st.write(f"Usuário: **{u_log}**")
    if st.button("🚪 Sair", key="btn_out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- PASSO 7: GESTÃO DE TEMPLATES ---
    st.markdown("---")
    st.subheader("⚙️ Meus Templates")
    with st.expander("➕ Novo Template"):
        with st.form("f_new_tmp", clear_on_submit=True):
            tn = st.text_input("Nome (ex: Internet)")
            tc = st.selectbox("Categoria", ["Alimentação", "Transporte", "Contas Fixas", "Saúde", "Educação", "Salário/Renda"])
            td = st.text_input("Descrição padrão")
            tv = st.number_input("Valor padrão", step=0.01)
            if st.form_submit_button("Criar"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "description": td, "value": tv, "user_email": u_log}]).execute()
                st.rerun()

    try:
        tmp_data = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data
        if tmp_data:
            tdel = st.selectbox("Remover:", [t['template_name'] for t in tmp_data], key="sel_tmp_del")
            if st.button("🗑️ Deletar Template"):
                st_supabase.table("templates").delete().eq("template_name", tdel).eq("user_email", u_log).execute()
                st.rerun()
    except: pass

# --- PASSO 8: LANÇAMENTOS E FERRAMENTAS ---
st.title("📊 Painel Financeiro")
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        c = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação", "Salário/Renda"])
        v = st.number_input("Valor", min_value=0.0, step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "category": c, "description": ds, "value": val_f, "user_email": u_log}]).execute()
            st.rerun()

    if tmp_data:
        st.markdown("---")
        st.subheader("⚡ Atalhos")
        cols = st.columns(2)
        for i, t in enumerate(tmp_data):
            with cols[i % 2]:
                if st.button(f"📌 {t['template_name']}", key=f"t_btn_{i}", use_container_width=True):
                    st_supabase.table("transactions").insert([{"date": datetime.now().strftime("%Y-%m-%d"), "category": t['category'], "description": t['description'], "value": t['value'], "user_email": u_log}]).execute()
                    st.rerun()

    st.markdown("---")
    st.subheader("📝 Editar/Excluir")
    id_op = st.number_input("ID do lançamento:", min_value=1, step=1, key="id_op")
    ce1, ce2 = st.columns(2)
    with ce1:
        if st.button("🗑️ Deletar ID"):
            st_supabase.table("transactions").delete().eq("id", id_op).eq("user_email", u_log).execute()
            st.rerun()
    with ce2:
        if id_op:
            res_v = st_supabase.table("transactions").select("value").eq("id", id_op).eq("user_email", u_log).execute()
            if res_v.data:
                nv = st.number_input("Novo Valor:", value=float(res_v.data[0]['value']), key="nv_input")
                if st.button("💾 Salvar"):
                    st_supabase.table("transactions").update({"value": nv}).eq("id", id_op).execute()
                    st.rerun()

# --- PASSO 9: VISUALIZAÇÃO E DASHBOARD ---
try:
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).order("date", desc=True).execute().data
    df = pd.DataFrame(data_res)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['m_y'] = df['date'].dt.strftime('%m/%Y')
        with col2:
            st.subheader("📊 Resumo Mensal")
            m_s = st.selectbox("Mês:", df['m_y'].unique())
            df_m = df[df['m_y'] == m_s]
            e, s = df_m[df_m['value'] > 0]['value'].sum(), df_m[df_m['value'] < 0]['value'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Entradas", f"R$ {e:,.2f}")
            m2.metric("Saídas", f"R$ {abs(s):,.2f}")
            m3.metric("Saldo", f"R$ {e+s:,.2f}")
            st.dataframe(df_m[['id', 'date', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
except: pass