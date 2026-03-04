import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- 1. CONFIGURAÇÃO DE SEGURANÇA MÁXIMA ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
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
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- 3. SISTEMA DE AUTENTICAÇÃO (COM IDS ÚNICOS) ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    
    with t1:
        e_login = st.text_input("E-mail", key="in_email_login")
        p_login = st.text_input("Senha", type="password", key="in_pass_login")
        if st.button("Entrar", key="btn_auth_login"):
            res = st_supabase.table("app_users").select("email, is_admin").eq("email", e_login).eq("password", p_login).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.session_state["is_admin"] = res.data[0].get("is_admin", False)
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    
    with t2:
        ne_reg = st.text_input("E-mail para Cadastro", key="in_email_reg")
        np_reg = st.text_input("Crie uma Senha", type="password", key="in_pass_reg")
        cp_reg = st.text_input("Confirme a Senha", type="password", key="in_pass_conf_reg")
        if st.button("Criar Conta", key="btn_auth_reg"):
            if is_valid_email(ne_reg) and np_reg == cp_reg and len(np_reg) >= 6:
                try:
                    st_supabase.table("app_users").insert([{"email": ne_reg, "password": np_reg}]).execute()
                    st.success("Conta criada! Vá para o Login.")
                except:
                    st.error("E-mail já cadastrado.")
            else:
                st.error("Verifique os dados informados.")
    st.stop()

# --- 4. VARIÁVEIS PÓS-LOGIN ---
user_logado = st.session_state["user_email"]
is_admin = st.session_state.get("is_admin", False)

# --- 5. DASHBOARD PRINCIPAL ---
st.title(f"📊 Dashboard Financeiro")
col_form, col_view = st.columns([1, 2])

with col_form:
    st.subheader("➕ Novo Registro")
    with st.form("main_entry_form", clear_on_submit=True):
        f_date = st.date_input("Data", datetime.now())
        f_desc = st.text_input("Descrição")
        f_cat = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        f_val = st.number_input("Valor", min_value=0.0, step=0.01)
        f_tipo = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            final_v = -f_val if f_tipo == "Gasto" else f_val
            st_supabase.table("transactions").insert([
                {"date": f_date.strftime("%Y-%m-%d"), "category": f_cat, "description": f_desc, "value": final_v, "user_email": user_logado}
            ]).execute()
            st.rerun()

    # --- 5.1 LANÇAMENTOS RÁPIDOS ---
    st.markdown("---")
    st.subheader("⚡ Atalhos")
    try:
        templates = st_supabase.table("templates").select("*").eq("user_email", user_logado).execute().data
        if templates:
            cols = st.columns(2)
            for i, t in enumerate(templates):
                with cols[i % 2]:
                    if st.button(f"📌 {t['template_name']}", key=f"btn_shortcut_{i}", use_container_width=True):
                        hoje = datetime.now()
                        dt_f = hoje.replace(day=10).strftime("%Y-%m-%d") if "Aluguel" in t['template_name'] else hoje.strftime("%Y-%m-%d")
                        st_supabase.table("transactions").insert([
                            {"date": dt_f, "category": t['category'], "description": t['description'], "value": t['value'], "user_email": user_logado}
                        ]).execute()
                        st.rerun()
    except:
        pass

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