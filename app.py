import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# --- 2. BLINDAGEM VISUAL (PROTEÇÃO DO CÓDIGO) ---
# Esconde o ícone do GitHub e botões de desenvolvedor, mantendo a seta da sidebar viva.
st.markdown("""
    <style>
    /* Esconde o ícone do GitHub e botões de Deploy/Edit no topo */
    .stAppDeployButton, a[href*="github.com"], .st-emotion-cache-15ec669 {
        display: none !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Garante que o header não esconda a seta de navegação lateral */
    [data-testid="stSidebarNav"] { visibility: visible; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNÇÕES DE APOIO E CONEXÃO ---
def is_valid_email(email):
    """Valida o formato do e-mail via regex."""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

try:
    st_supabase = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Erro de conexão com o banco: {e}")
    st.stop()

# --- 4. SISTEMA DE ACESSO (LOGIN / CADASTRO) ---
if "user_email" not in st.session_state:
    st.query_params.clear() # Blindagem de saldo na URL
    st.title("💸 Finance Hub: Acesso")
    tab_log, tab_reg = st.tabs(["Login", "Criar Conta"])
    
    with tab_log:
        e_in = st.text_input("E-mail", key="auth_email_login")
        p_in = st.text_input("Senha", type="password", key="auth_pass_login")
        if st.button("Entrar", key="btn_login_auth"):
            res = st_supabase.table("app_users").select("email").eq("email", e_in).eq("password", p_in).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
                
    with tab_reg:
        st.subheader("Nova Conta")
        ne_reg = st.text_input("E-mail para Cadastro", key="auth_email_reg")
        if ne_reg and not is_valid_email(ne_reg):
            st.error("⚠️ Formato de e-mail inválido.")
        np_reg = st.text_input("Crie uma Senha (mín. 6 chars)", type="password", key="auth_pass_reg")
        if st.button("Finalizar Cadastro", key="btn_reg_auth"):
            if is_valid_email(ne_reg) and len(np_reg) >= 6:
                try:
                    st_supabase.table("app_users").insert([{"email": ne_reg, "password": np_reg}]).execute()
                    st.success("Conta criada! Vá para a aba Login.")
                except:
                    st.error("E-mail já cadastrado.")
    st.stop()

# --- 5. VARIÁVEIS DE SESSÃO PÓS-LOGIN ---
u_log = st.session_state["user_email"]

# --- 6. BARRA LATERAL: LOGOUT E GESTÃO DE TEMPLATES ---
with st.sidebar:
    st.write(f"Conectado: **{u_log}**")
    if st.button("🚪 Sair da Sessão", key="btn_logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.markdown("---")
    st.subheader("⚙️ Gerenciar Templates")
    try:
        tmp_data = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data
        if tmp_data:
            t_to_del = st.selectbox("Escolha um template para remover:", [t['template_name'] for t in tmp_data], key="sel_tmp_del")
            if st.button("🗑️ Deletar Template", key="btn_tmp_del"):
                st_supabase.table("templates").delete().eq("template_name", t_to_del).eq("user_email", u_log).execute()
                st.rerun()
    except:
        st.caption("Nenhum template encontrado.")

# --- 7. PAINEL PRINCIPAL: FORMULÁRIO E DASHBOARD ---
st.title("📊 Gestão Financeira Cloud")
col_form, col_view = st.columns([1, 2])

with col_form:
    st.subheader("➕ Novo Lançamento")
    with st.form("form_transacao", clear_on_submit=True):
        f_date = st.date_input("Data", datetime.now())
        f_desc = st.text_input("Descrição")
        f_cat = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação", "Certificações", "Salário/Renda"])
        f_val = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        f_tipo = st.radio("Tipo", ["Saída (Gasto)", "Entrada (Receita)"])
        if st.form_submit_button("Sincronizar"):
            final_v = -f_val if f_tipo == "Saída (Gasto)" else f_val
            st_supabase.table("transactions").insert([
                {"date": f_date.strftime("%Y-%m-%d"), "category": f_cat, "description": f_desc, "value": final_v, "user_email": u_log}
            ]).execute()
            st.rerun()

    st.markdown("---")
    st.subheader("📝 Editar ou Excluir Lançamento")
    id_op = st.number_input("Digite o ID do lançamento:", min_value=1, step=1, key="input_id_op")
    c_edit1, c_edit2 = st.columns(2)
    
    with c_edit1:
        if st.button("🗑️ Deletar ID", key="btn_del_id"):
            st_supabase.table("transactions").delete().eq("id", id_op).eq("user_email", u_log).execute()
            st.rerun()
            
    with c_edit2:
        if id_op:
            res_val = st_supabase.table("transactions").select("value").eq("id", id_op).eq("user_email", u_log).execute()
            if res_val.data:
                new_v = st.number_input("Novo Valor:", value=float(res_val.data[0]['value']), key="input_new_val")
                if st.button("💾 Salvar Alteração", key="btn_save_val"):
                    st_supabase.table("transactions").update({"value": new_v}).eq("id", id_op).execute()
                    st.rerun()

# --- 8. VISUALIZAÇÃO E INTELIGÊNCIA MENSAL ---
try:
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).order("date", desc=True).execute().data
    df = pd.DataFrame(data_res)
    if not df.empty:
        df['date'] = pd.to_datetime(df