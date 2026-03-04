import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- 1. CONFIGURAÇÃO DE INTERFACE (BLINDAGEM) ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None # Remove link de edição
    }
)

# --- 2. VALIDAÇÃO E CONEXÃO ---
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except Exception as e:
    st.error(f"Erro de conexão técnica: {e}")
    st.stop()

# --- 3. SISTEMA DE LOGIN (FIX: ERRO VERMELHO DE ID) ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    
    with t1:
        e_in = st.text_input("E-mail", key="input_user_login_final")
        p_in = st.text_input("Senha", type="password", key="input_pass_login_final")
        if st.button("Entrar", key="btn_login_final"):
            res = st_supabase.table("app_users").select("email, is_admin").eq("email", e_in).eq("password", p_in).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.session_state["is_admin"] = res.data[0].get("is_admin", False)
                st.rerun()
            else:
                st.error("Dados incorretos.")
    
    with t2:
        ne_in = st.text_input("E-mail para Cadastro", key="input_user_reg_final")
        np_in = st.text_input("Crie uma Senha", type="password", key="input_pass_reg_final")
        if st.button("Criar Conta", key="btn_reg_final"):
            if is_valid_email(ne_in) and len(np_in) >= 6:
                try:
                    st_supabase.table("app_users").insert([{"email": ne_in, "password": np_in}]).execute()
                    st.success("Sucesso! Vá para o Login.")
                except:
                    st.error("E-mail já cadastrado.")
    st.stop()

# --- 4. VARIÁVEIS PÓS-LOGIN ---
u_log = st.session_state["user_email"]
adm = st.session_state.get("is_admin", False)

# --- 5. SIDEBAR E ADMIN (PASSOS 7 E 8) ---
with st.sidebar:
    st.write(f"Usuário: **{u_log}**")
    if st.button("Sair", key="btn_logout_final"):
        st.session_state.clear()
        st.rerun()
    
    if adm:
        st.markdown("---")
        st.header("🛠️ Administração")
        id_del = st.number_input("Excluir ID:", min_value=1, step=1, key="input_admin_del")
        if st.button("Confirmar Exclusão", key="btn_admin_del_confirm"):
            st_supabase.table("transactions").delete().eq("id", id_del).execute()
            st.rerun()

# --- 6. LEITURA E DASHBOARD ---
try:
    df = pd.DataFrame(st_supabase.table("transactions").select("*").eq("user_email", user_logado).order("date", desc=True).execute().data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['data_formatada'] = df['date'].dt.strftime('%d/%m/%Y')
        df['month_year'] = df['date'].dt.strftime('%m/%Y')
except:
    df = pd.DataFrame()

with col_view:
    if not df.empty:
        st.subheader("📊 Resumo Mensal")
        m_sel = st.selectbox("Filtrar Período:", df['month_year'].unique(), key="dash_month_filter")
        df_mes = df[df['month_year'] == m_sel].copy()
        
        c1, c2, c3 = st.columns(3)
        v_ent = df_mes[df_mes['value'] > 0]['value'].sum()
        v_sai = df_mes[df_mes['value'] < 0]['value'].sum()
        c1.metric("Entradas", f"R$ {v_ent:,.2f}")
        c2.metric("Saídas", f"R$ {abs(v_sai):,.2f}")
        c3.metric("Saldo", f"R$ {v_ent+v_sai:,.2f}")

        st.dataframe(df_mes[['id', 'data_formatada', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado para este usuário.")

# --- 7/8. FERRAMENTAS (SIDEBAR) - APENAS ADMIN ---
with st.sidebar:
    st.write(f"Conectado: **{user_logado}**")
    if st.button("Sair", key="btn_global_logout"):
        st.session_state.clear()
        st.rerun()
    
    if is_admin:
        st.markdown("---")
        st.header("🛠️ Administração")
        id_del = st.number_input("Excluir ID:", min_value=1, step=1, key="admin_id_to_delete")
        if st.button("Confirmar Exclusão", key="btn_confirm_admin_del"):
            st_supabase.table("transactions").delete().eq("id", id_del).execute()
            st.warning(f"ID {id_del} removido.")
            st.rerun()