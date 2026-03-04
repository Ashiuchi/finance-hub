import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- 1. CONFIGURAÇÃO DE SEGURANÇA MÁXIMA (LOGO NO INÍCIO) ---
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

# --- 2. FUNÇÕES DE SEGURANÇA E VALIDAÇÃO ---
def is_valid_email(email):
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

# --- 3. CONEXÃO SUPABASE ---
try:
    st_supabase = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except:
    st.error("Erro na conexão com a nuvem.")
    st.stop()

# --- 4. SISTEMA DE AUTENTICAÇÃO (LOGIN / CADASTRO) ---
if "user_email" not in st.session_state:
    st.query_params.clear() # Limpa rastro da URL
    st.title("💸 Finance Hub: Acesso")
    aba_login, aba_cadastro = st.tabs(["Login", "Criar Conta"])
    
    with aba_login:
        email_log = st.text_input("E-mail", key="email_log_auth")
        senha_log = st.text_input("Senha", type="password", key="senha_log_auth")
        if st.button("Entrar", key="btn_login_auth"):
            res = st_supabase.table("app_users").select("email, is_admin").eq("email", email_log).eq("password", senha_log).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.session_state["is_admin"] = res.data[0].get("is_admin", False)
                st.rerun()
            else:
                st.error("Dados incorretos.")
    
    with aba_cadastro:
        st.subheader("Nova Conta")
        new_email = st.text_input("E-mail de Cadastro", key="email_reg_auth")
        if new_email and not is_valid_email(new_email):
            st.error("⚠️ Formato de e-mail inválido.")
        new_senha = st.text_input("Senha (mín. 6 chars)", type="password", key="senha_reg_auth")
        conf_senha = st.text_input("Confirme a senha", type="password", key="conf_reg_auth")
        
        if st.button("Cadastrar", key="btn_reg_auth"):
            if is_valid_email(new_email) and new_senha == conf_senha and len(new_senha) >= 6:
                try:
                    st_supabase.table("app_users").insert([{"email": new_email, "password": new_senha}]).execute()
                    st.success("Conta criada! Vá para a aba Login.")
                except:
                    st.error("E-mail já cadastrado.")
            else:
                st.error("Verifique as senhas ou o formato do e-mail.")
    st.stop()

# --- 5. VARIÁVEIS DE SESSÃO PÓS-LOGIN ---
user_logado = st.session_state["user_email"]
is_admin = st.session_state.get("is_admin", False)

# --- 6. DASHBOARD E INTERFACE ---
st.title(f"📊 Dashboard Financeiro")
col_form, col_view = st.columns([1, 2])

with col_form:
    st.subheader("➕ Novo Registro")
    with st.form("entry_form", clear_on_submit=True):
        date = st.date_input("Data", datetime.now())
        desc = st.text_input("Descrição")
        cat = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        val = st.number_input("Valor", min_value=0.0, step=0.01)
        tipo = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar na Nuvem"):
            final_v = -val if tipo == "Gasto" else val
            st_supabase.table("transactions").insert([
                {"date": date.strftime("%Y-%m-%d"), "category": cat, "description": desc, "value": final_v, "user_email": user_logado}
            ]).execute()
            st.rerun()

    # --- 6.1 LANÇAMENTOS RÁPIDOS (TEMPLATES) ---
    st.markdown("---")
    st.subheader("⚡ Atalhos")
    try:
        templates = st_supabase.table("templates").select("*").eq("user_email", user_logado).execute().data
    except:
        templates = []

    if templates:
        cols = st.columns(2)
        for i, t in enumerate(templates):
            with cols[i % 2]:
                if st.button(f"📌 {t['template_name']}", key=f"btn_temp_{i}", use_container_width=True):
                    hoje = datetime.now()
                    dt_final = hoje.replace(day=10).strftime("%Y-%m-%d") if "Aluguel" in t['template_name'] else hoje.strftime("%Y-%m-%d")
                    st_supabase.table("transactions").insert([
                        {"date": dt_final, "category": t['category'], "description": t['description'], "value": t['value'], "user_email": user_logado}
                    ]).execute()
                    st.rerun()

# --- 7. VISUALIZAÇÃO DOS DADOS ---
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
        mes_sel = st.selectbox("Filtrar Período:", df['month_year'].unique(), key="sel_mes_dash")
        df_mes = df[df['month_year'] == mes_sel].copy()
        
        m1, m2, m3 = st.columns(3)
        ent = df_mes[df_mes['value'] > 0]['value'].sum()
        sai = df_mes[df_mes['value'] < 0]['value'].sum()
        m1.metric("Entradas", f"R$ {ent:,.2f}")
        m2.metric("Saídas", f"R$ {abs(sai):,.2f}")
        m3.metric("Saldo", f"R$ {ent+sai:,.2f}")

        st.dataframe(df_mes[['id', 'data_formatada', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
    else:
        st.info("Aguardando registros...")

# --- 8. FERRAMENTAS (SIDEBAR) - APENAS ADMIN ---
with st.sidebar:
    st.write(f"Conectado: **{user_logado}**")
    if st.button("Sair", key="btn_logout_sidebar"):
        st.session_state.clear()
        st.rerun()
    
    if is_admin:
        st.markdown("---")
        st.header("🛠️ Administração")
        id_del = st.number_input("Excluir ID:", min_value=1, step=1, key="admin_del_id")
        if st.button("Confirmar Exclusão", key="btn_admin_del"):
            st_supabase.table("transactions").delete().eq("id", id_del).execute()
            st.rerun()
    else:
        st.info("💡 Modo Usuário: Ferramentas de Admin desabilitadas.")