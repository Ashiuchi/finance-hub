import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# 1. Configuração inicial (esconde menus antes do login)
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="collapsed",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# 2. Conexão e Validação
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except:
    st.error("Falha na conexão com o banco de dados.")
    st.stop()

# 3. Sistema de Autenticação
if "user_email" not in st.session_state:
    st.query_params.clear() # Limpa rastro da URL
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    
    with t1:
        e = st.text_input("E-mail")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            # Busca e já identifica se é ADMIN no login
            res = st_supabase.table("app_users").select("email, is_admin").eq("email", e).eq("password", p).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.session_state["is_admin"] = res.data[0].get("is_admin", False)
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    
    with t2:
        ne = st.text_input("Novo E-mail")
        np = st.text_input("Senha", type="password")
        if st.button("Criar Conta"):
            if is_valid_email(ne) and len(np) >= 6:
                st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
                st.success("Sucesso! Faça o login.")
    st.stop()

# 4. Variáveis de Sessão
user_logado = st.session_state["user_email"]
is_admin = st.session_state.get("is_admin", False)

# 5. Interface de Admin (Passos 7 e 8) na Sidebar
with st.sidebar:
    st.write(f"Conectado como: **{user_logado}**")
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()
    
    if is_admin:
        st.markdown("---")
        st.header("🛠️ Administração")
        id_del = st.number_input("Excluir ID:", min_value=1, step=1)
        if st.button("Confirmar Exclusão"):
            st_supabase.table("transactions").delete().eq("id", id_del).execute()
            st.rerun()
    else:
        st.info("💡 Modo de Usuário: Edição desabilitada.")

# 6. Dashboard Principal
st.title(f"📊 Dashboard Financeiro")
# (Lógica de exibição de saldos usando st.metric e tabelas filtradas pelo user_email)

# --- 6. INTERFACE DE LANÇAMENTO E DASHBOARD ---
st.title(f"📊 Dashboard: {user_logado.split('@')[0].capitalize()}")
col_form, col_view = st.columns([1, 2])

with col_form:
    st.subheader("➕ Novo Registro")
    with st.form("entry_form", clear_on_submit=True):
        date = st.date_input("Data", datetime.now())
        desc = st.text_input("Descrição")
        cat = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        val = st.number_input("Valor", min_value=0.0, step=0.01)
        tipo = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            final_v = -val if tipo == "Gasto" else val
            st_supabase.table("transactions").insert([
                {"date": date.strftime("%Y-%m-%d"), "category": cat, "description": desc, "value": final_v, "user_email": user_logado}
            ]).execute()
            st.rerun()

# --- 7. FERRAMENTAS EXCLUSIVAS PARA ADMIN ---
with st.sidebar:
    st.write(f"Logado como: {user_logado}")
    if st.button("Sair"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    
    if is_admin:
        st.markdown("---")
        st.header("🛠️ Ferramentas Admin")
        
        # Excluir
        st.subheader("🗑️ Excluir por ID")
        id_del = st.number_input("ID:", min_value=1, step=1)
        if st.button("Confirmar Exclusão"):
            st_supabase.table("transactions").delete().eq("id", id_del).execute()
            st.rerun()
        
        # Editar
        st.subheader("📝 Editar por ID")
        id_ed = st.number_input("ID Editar:", min_value=1, step=1)
        if id_ed:
            res = st_supabase.table("transactions").select("*").eq("id", id_ed).execute()
            if res.data:
                d = res.data[0]
                new_v = st.number_input("Novo Valor:", value=float(d['value']))
                if st.button("Salvar Edição"):
                    st_supabase.table("transactions").update({"value": new_v}).eq("id", id_ed).execute()
                    st.rerun()
    else:
        st.info("Visualização restrita a dados pessoais.")

# --- 8. ADMINISTRAÇÃO (SIDEBAR) ---
with st.sidebar:
    st.markdown("---")
    st.header("🛠️ Administração")
    
    # EXCLUSÃO
    st.subheader("🗑️ Excluir Registro")
    id_del = st.number_input("ID para deletar:", min_value=1, step=1, key="del_sidebar")
    if st.button("Confirmar Exclusão", key="btn_del_sidebar"):
        st_supabase.table("transactions").delete().eq("id", id_del).eq("user_email", user_logado).execute()
        st.warning(f"ID {id_del} removido.")
        st.rerun()
    
    # EDIÇÃO
    st.markdown("---")
    st.subheader("📝 Editar Registro")
    id_ed = st.number_input("ID para editar:", min_value=1, step=1, key="ed_sidebar")
    if id_ed:
        d_at = st_supabase.table("transactions").select("*").eq("id", id_ed).eq("user_email", user_logado).execute().data
        if d_at:
            d = d_at[0]
            nv = st.number_input("Novo Valor:", value=float(d['value']))
            nc = st.selectbox("Nova Categoria:", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"], 
                              index=["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"].index(d['category']))
            if st.button("Salvar Alterações"):
                st_supabase.table("transactions").update({"value": nv, "category": nc}).eq("id", id_ed).eq("user_email", user_logado).execute()
                st.success("Atualizado!")
                st.rerun()