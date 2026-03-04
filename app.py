import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- 1. CONFIGURAÇÃO DE INTERFACE E BLINDAGEM VISUAL ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="collapsed",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# Injeção de CSS para esconder ferramentas de desenvolvedor e o ícone do GitHub
st.markdown("""
    <style>
    /* Esconde botões de deploy e links do GitHub */
    .stAppDeployButton, a[href*="github.com"], .st-emotion-cache-15ec669 {
        display: none !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES DE APOIO ---
def is_valid_email(email):
    """Valida o formato do e-mail para evitar registros 'sujos'."""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

# --- 3. CONEXÃO COM A NUVEM (SUPABASE) ---
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

# --- 4. SISTEMA DE AUTENTICAÇÃO (LOGIN / CADASTRO) ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso Seguro")
    tab_log, tab_reg = st.tabs(["Login", "Criar Conta"])
    
    with tab_log:
        e_in = st.text_input("E-mail", key="auth_email_login_final")
        p_in = st.text_input("Senha", type="password", key="auth_pass_login_final")
        if st.button("Entrar", key="auth_btn_login_final"):
            res = st_supabase.table("app_users").select("email, is_admin").eq("email", e_in).eq("password", p_in).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.session_state["is_admin"] = res.data[0].get("is_admin", False)
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    
    with tab_reg:
        st.subheader("Nova Conta")
        ne_reg = st.text_input("E-mail para Cadastro", key="auth_email_reg_final")
        if ne_reg and not is_valid_email(ne_reg):
            st.error("⚠️ Formato de e-mail inválido.")
        np_reg = st.text_input("Crie uma Senha (mín. 6 chars)", type="password", key="auth_pass_reg_final")
        cp_reg = st.text_input("Confirme a Senha", type="password", key="auth_pass_conf_reg_final")
        
        if st.button("Finalizar Cadastro", key="auth_btn_reg_final"):
            if is_valid_email(ne_reg) and np_reg == cp_reg and len(np_reg) >= 6:
                try:
                    st_supabase.table("app_users").insert([{"email": ne_reg, "password": np_reg}]).execute()
                    st.success("Conta criada! Vá para a aba Login.")
                except:
                    st.error("Este e-mail já está em uso.")
            else:
                st.error("Verifique os dados (E-mail válido e senha mínima de 6 caracteres).")
    st.stop()

# --- 5. VARIÁVEIS DE SESSÃO PÓS-LOGIN ---
u_log = st.session_state["user_email"]
adm = st.session_state.get("is_admin", False)

# --- 6. BARRA LATERAL (SIDEBAR) E ADMINISTRAÇÃO ---
with st.sidebar:
    st.set_page_config(..., initial_sidebar_state="expanded")
    st.write(f"Usuário: **{u_log}**")
    
    # Botão de Logout com destaque
    if st.button("🚪 Sair da Sessão", key="btn_logout_final", use_container_width=True):
        st.session_state.clear() # Limpa todas as variáveis de segurança
        st.rerun() # Recarrega para a tela de login limpa
    
    # Seção de Admin (Apenas se is_admin for True no Supabase)
    if adm:
        st.markdown("---")
        st.header("🛠️ Administração")
        # ... (restante do código de exclusão e edição)

# --- 7. DASHBOARD PRINCIPAL ---
st.title(f"📊 Dashboard Financeiro")
col_form, col_view = st.columns([1, 2])

# --- 8. FORMULÁRIO E LANÇAMENTOS RÁPIDOS ---
with col_form:
    st.subheader("➕ Novo Registro")
    with st.form("form_registro_final", clear_on_submit=True):
        f_date = st.date_input("Data", datetime.now())
        f_desc = st.text_input("Descrição")
        f_cat = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        f_val = st.number_input("Valor", min_value=0.0, step=0.01)
        f_tipo = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            final_v = -f_val if f_tipo == "Gasto" else f_val
            st_supabase.table("transactions").insert([
                {"date": f_date.strftime("%Y-%m-%d"), "category": f_cat, "description": f_desc, "value": final_v, "user_email": u_log}
            ]).execute()
            st.rerun()

    st.markdown("---")
    st.subheader("⚡ Lançamentos Rápidos")
    try:
        templates = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data
        if templates:
            cols = st.columns(2)
            for i, t in enumerate(templates):
                with cols[i % 2]:
                    if st.button(f"📌 {t['template_name']}", key=f"btn_shortcut_{i}_final", use_container_width=True):
                        hoje = datetime.now()
                        # Regra do Aluguel no dia 10
                        dt_f = hoje.replace(day=10).strftime("%Y-%m-%d") if "Aluguel" in t['template_name'] else hoje.strftime("%Y-%m-%d")
                        st_supabase.table("transactions").insert([
                            {"date": dt_f, "category": t['category'], "description": t['description'], "value": t['value'], "user_email": u_log}
                        ]).execute()
                        st.rerun()
    except:
        st.caption("Nenhum atalho configurado.")

# --- 9. VISUALIZAÇÃO E INTELIGÊNCIA ---
try:
    df = pd.DataFrame(st_supabase.table("transactions").select("*").eq("user_email", u_log).order("date", desc=True).execute().data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['data_formatada'] = df['date'].dt.strftime('%d/%m/%Y')
        df['month_year'] = df['date'].dt.strftime('%m/%Y')
except:
    df = pd.DataFrame()

with col_view:
    if not df.empty:
        st.subheader("📊 Resumo Mensal")
        m_sel = st.selectbox("Selecione o Período:", df['month_year'].unique(), key="select_periodo_dash")
        df_mes = df[df['month_year'] == m_sel].copy()
        
        c1, c2, c3 = st.columns(3)
        v_ent = df_mes[df_mes['value'] > 0]['value'].sum()
        v_sai = df_mes[df_mes['value'] < 0]['value'].sum()
        c1.metric("Entradas", f"R$ {v_ent:,.2f}")
        c2.metric("Saídas", f"R$ {abs(v_sai):,.2f}")
        c3.metric("Saldo do Mês", f"R$ {v_ent+v_sai:,.2f}")

        st.dataframe(df_mes[['id', 'data_formatada', 'category', 'description', 'value']], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("Inicie seus lançamentos para ver o gráfico e o resumo.")