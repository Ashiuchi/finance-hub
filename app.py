import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO DE INTERFACE (TOPO DO ARQUIVO) ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# --- PASSO 2: BLINDAGEM VISUAL (CSS FORÇA BRUTA) ---
# Esconde GitHub, botões de Edit/Deploy e limpa o cabeçalho, mantendo a Sidebar
st.markdown("""
    <style>
    /* Esconde o ícone do GitHub e botões de Deploy/Edit no topo */
    [data-testid="stHeader"] {
        display: none !important;
    }
    /* Remove o rodapé "Made with Streamlit" */
    footer {visibility: hidden;}
    /* Garante que o conteúdo não fique colado no topo agora que escondemos o header */
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- PASSO 3: CONEXÃO SUPABASE ---
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- PASSO 4: SISTEMA DE LOGIN ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso Seguro")
    t1, t2 = st.tabs(["Login", "Criar Conta"])
    with t1:
        e_in = st.text_input("E-mail", key="l_email")
        p_in = st.text_input("Senha", type="password", key="l_pass")
        if st.button("Entrar", key="l_btn"):
            res = st_supabase.table("app_users").select("email, is_admin").eq("email", e_in).eq("password", p_in).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.session_state["is_admin"] = res.data[0].get("is_admin", False)
                st.rerun()
            else: st.error("Dados incorretos.")
    with t2:
        ne = st.text_input("Novo E-mail", key="reg_email")
        np = st.text_input("Senha", type="password", key="reg_pass")
        if st.button("Cadastrar", key="reg_btn"):
            if is_valid_email(ne) and len(np) >= 6:
                st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
                st.success("Criado! Faça o login.")
    st.stop()

# --- PASSO 5 E 6: VARIÁVEIS E SIDEBAR ---
u_log = st.session_state["user_email"]
adm = st.session_state.get("is_admin", False)

with st.sidebar:
    st.write(f"Conectado: **{u_log}**")
    if st.button("🚪 Sair", key="logout_btn", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- PASSO 7: FERRAMENTAS ADMIN (EXCLUSÃO E EDIÇÃO) ---
    if adm:
        st.markdown("---")
        st.header("🛠️ Administração")
        # Excluir
        id_del = st.number_input("Excluir ID:", min_value=1, step=1, key="ad_del")
        if st.button("Confirmar Exclusão", key="btn_ad_del"):
            st_supabase.table("transactions").delete().eq("id", id_del).execute()
            st.rerun()
        # Editar
        st.markdown("---")
        id_ed = st.number_input("Editar ID:", min_value=1, step=1, key="ad_ed")
        if id_ed:
            res_ed = st_supabase.table("transactions").select("*").eq("id", id_ed).execute()
            if res_ed.data:
                v = st.number_input("Novo Valor:", value=float(res_ed.data[0]['value']), key="ad_v")
                if st.button("Salvar Edição", key="btn_ad_save"):
                    st_supabase.table("transactions").update({"value": v}).eq("id", id_ed).execute()
                    st.rerun()

# --- PASSO 8: FORMULÁRIO E ATALHOS ---
st.title("💸 Dashboard Financeiro")
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("➕ Novo Registro")
    with st.form("form_f", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        c = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        v = st.number_input("Valor", min_value=0.0, step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            final_v = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "category": c, "description": ds, "value": final_v, "user_email": u_log}]).execute()
            st.rerun()

# --- PASSO 9: VISUALIZAÇÃO E MÉTRICAS ---
try:
    df = pd.DataFrame(st_supabase.table("transactions").select("*").eq("user_email", u_log).order("date", desc=True).execute().data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['month_year'] = df['date'].dt.strftime('%m/%Y')
        with col2:
            st.subheader("📊 Resumo Mensal")
            m = st.selectbox("Mês:", df['month_year'].unique(), key="s_m")
            df_m = df[df['month_year'] == m]
            ent, sai = df_m[df_m['value'] > 0]['value'].sum(), df_m[df_m['value'] < 0]['value'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Entradas", f"R$ {ent:,.2f}")
            c2.metric("Saídas", f"R$ {abs(sai):,.2f}")
            c3.metric("Saldo", f"R$ {ent+sai:,.2f}")
            st.dataframe(df_m[['id', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
except: st.info("Sem dados.")