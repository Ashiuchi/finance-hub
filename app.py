import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Finance Hub - Ashiuchi", layout="wide", page_icon="💸")

# --- CONEXÃO COM SUPABASE ---
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

# --- SISTEMA DE AUTENTICAÇÃO (LOGIN / CADASTRO) ---
def auth_system():
    if "user_email" not in st.session_state:
        st.title("💸 Bem-vindo ao Finance Hub")
        aba_login, aba_cadastro = st.tabs(["Login", "Criar Conta"])

        with aba_login:
            email_log = st.text_input("E-mail", key="email_log")
            senha_log = st.text_input("Senha", type="password", key="senha_log")
            if st.button("Entrar"):
                # Busca usuário no banco
                res = st_supabase.table("app_users").select("*").eq("email", email_log).eq("password", senha_log).execute()
                if res.data:
                    st.session_state["user_email"] = email_log
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

        with aba_cadastro:
            st.subheader("Comece sua gestão hoje")
            new_email = st.text_input("E-mail para cadastro", key="new_email")
            new_senha = st.text_input("Crie uma senha", type="password", key="new_senha")
            conf_senha = st.text_input("Confirme a senha", type="password", key="conf_senha")
            
            if st.button("Finalizar Cadastro"):
                if new_senha != conf_senha:
                    st.error("As senhas não coincidem.")
                elif len(new_senha) < 6:
                    st.warning("A senha deve ter pelo menos 6 caracteres.")
                else:
                    try:
                        st_supabase.table("app_users").insert([{"email": new_email, "password": new_senha}]).execute()
                        st.success("Conta criada! Agora faça o login na aba ao lado.")
                    except:
                        st.error("Este e-mail já está cadastrado.")
        return False
    return True

if not auth_system():
    st.stop()

# --- VARIÁVEIS DO USUÁRIO LOGADO ---
user_logado = st.session_state["user_email"]
st.sidebar.write(f"Logado como: **{user_logado}**")
if st.sidebar.button("Sair"):
    del st.session_state["user_email"]
    st.rerun()

# --- INTERFACE PRINCIPAL ---
st.title(f"📊 Dashboard de {user_logado.split('@')[0].capitalize()}")
col_form, col_view = st.columns([1, 2])

# --- 5. ENTRADA DE DADOS (FILTRADA POR USUÁRIO) ---
with col_form:
    st.subheader("➕ Nova Transação")
    with st.form("entry_form", clear_on_submit=True):
        date = st.date_input("Data", datetime.now())
        description = st.text_input("Descrição")
        category = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        value = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        type_trans = st.radio("Tipo", ["Saída (Gasto)", "Entrada (Receita)"])
        submit = st.form_submit_button("Salvar na Nuvem")

    if submit:
        final_value = -value if type_trans == "Saída (Gasto)" else value
        st_supabase.table("transactions").insert([
            {
                "date": date.strftime("%Y-%m-%d"), 
                "category": category, 
                "description": description, 
                "value": final_value,
                "user_email": user_logado # IDENTIFICA O DONO
            }
        ]).execute()
        st.success("Sincronizado!")
        st.rerun()

# --- 6. LEITURA FILTRADA ---
try:
    # FILTRO ESSENCIAL: eq("user_email", user_logado)
    df = pd.DataFrame(st_supabase.table("transactions").select("*").eq("user_email", user_logado).order("date", desc=True).execute().data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['data_formatada'] = df['date'].dt.strftime('%d/%m/%Y')
        df['month_year'] = df['date'].dt.strftime('%m/%Y')
except:
    df = pd.DataFrame()

# [O restante do código do Dashboard segue a mesma lógica de filtros...]

# --- 7. FERRAMENTAS ADM (SIDEBAR) ---
with st.sidebar:
    st.header("🛠️ Administração")
    
    # Exclusão
    st.subheader("🗑️ Excluir")
    id_del = st.number_input("ID:", min_value=1, step=1, key="del")
    if st.button("Confirmar Exclusão"):
        st_supabase.table("transactions").delete().eq("id", id_del).execute()
        st.rerun()
    
    # Edição
    st.markdown("---")
    st.subheader("📝 Editar")
    id_ed = st.number_input("ID:", min_value=1, step=1, key="ed")
    if id_ed:
        d_at = st_supabase.table("transactions").select("*").eq("id", id_ed).execute().data
        if d_at:
            d = d_at[0]
            nv = st.number_input("Valor:", value=float(d['value']))
            nc = st.selectbox("Cat:", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"], 
                              index=["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"].index(d['category']))
            if st.button("Salvar"):
                st_supabase.table("transactions").update({"value": nv, "category": nc}).eq("id", id_ed).execute()
                st.rerun()