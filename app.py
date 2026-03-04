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

# --- PASSO 2: BLINDAGEM VISUAL (CSS ULTRA-RESTRITIVO) ---
# O segredo aqui é esconder o link que contém "github.com" e a classe específica do botão de deploy
st.markdown("""
    <style>
    /* Esconde o ícone do GitHub especificamente pelo link e pela classe de ícone */
    a[href*="github.com"], .stAppDeployButton, svg[viewBox="0 0 24 24"] path[d*="M12 .297c-6.63"] {
        display: none !important;
    }
    /* Esconde o menu de três pontos e o lápis de edição */
    #MainMenu, .st-emotion-cache-15ec669 {
        visibility: hidden;
    }
    /* Mantém a seta da barra lateral visível e funcional */
    [data-testid="stSidebarNav"] {
        visibility: visible;
    }
    footer {visibility: hidden;}
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

# --- PASSO 4: LOGIN / CADASTRO ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Criar Conta"])
    with t1:
        e_l = st.text_input("E-mail", key="l_e")
        p_l = st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar", key="l_b"):
            res = st_supabase.table("app_users").select("email, is_admin").eq("email", e_l).eq("password", p_l).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.session_state["is_admin"] = res.data[0].get("is_admin", False)
                st.rerun()
            else: st.error("Dados incorretos.")
    with t2:
        ne = st.text_input("Novo E-mail", key="r_e")
        np = st.text_input("Senha (mín. 6 chars)", type="password", key="r_p")
        if st.button("Cadastrar", key="r_b"):
            if is_valid_email(ne) and len(np) >= 6:
                st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
                st.success("Criado! Faça o login.")
    st.stop()

# --- PASSO 5, 6 E 7: VARIÁVEIS, SIDEBAR E ADMIN ---
u_log = st.session_state["user_email"]
adm = st.session_state.get("is_admin", False)

with st.sidebar:
    st.write(f"Usuário: **{u_log}**")
    if st.button("🚪 Sair", key="exit_b", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    if adm:
        st.markdown("---")
        st.header("🛠️ Administração")
        id_del = st.number_input("Excluir ID:", min_value=1, step=1, key="ad_del")
        if st.button("Excluir", key="ad_del_b"):
            st_supabase.table("transactions").delete().eq("id", id_del).execute()
            st.rerun()
        
        st.markdown("---")
        id_ed = st.number_input("Editar ID:", min_value=1, step=1, key="ad_ed")
        if id_ed:
            res_ed = st_supabase.table("transactions").select("*").eq("id", id_ed).execute()
            if res_ed.data:
                nv = st.number_input("Novo Valor:", value=float(res_ed.data[0]['value']), key="ad_nv")
                if st.button("Salvar", key="ad_sv"):
                    st_supabase.table("transactions").update({"value": nv}).eq("id", id_ed).execute()
                    st.rerun()

# --- PASSO 8 E 9: LANÇAMENTOS E DASHBOARD ---
st.title("💸 Painel Financeiro")
col1, col2 = st.columns([1, 2])
with col1:
    with st.form("f_add", clear_on_submit=True):
        d_f = st.date_input("Data", datetime.now())
        ds_f = st.text_input("Descrição")
        cat_f = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        v_f = st.number_input("Valor", min_value=0.0, step=0.01)
        t_f = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            val_final = -v_f if t_f == "Gasto" else v_f
            st_supabase.table("transactions").insert([{"date": d_f.strftime("%Y-%m-%d"), "category": cat_f, "description": ds_f, "value": val_final, "user_email": u_log}]).execute()
            st.rerun()

try:
    data = st_supabase.table("transactions").select("*").eq("user_email", u_log).order("date", desc=True).execute().data
    df = pd.DataFrame(data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['m_y'] = df['date'].dt.strftime('%m/%Y')
        with col2:
            sel_m = st.selectbox("Mês:", df['m_y'].unique(), key="s_m")
            df_m = df[df['m_y'] == sel_m]
            e, s = df_m[df_m['value'] > 0]['value'].sum(), df_m[df_m['value'] < 0]['value'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Entradas", f"R$ {e:,.2f}")
            m2.metric("Saídas", f"R$ {abs(s):,.2f}")
            m3.metric("Saldo", f"R$ {e+s:,.2f}")
            st.dataframe(df_m[['id', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
except: st.info("Sem lançamentos.")