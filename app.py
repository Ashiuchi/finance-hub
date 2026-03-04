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
    initial_sidebar_state="expanded", # Garante que inicie aberta
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# --- PASSO 2: BLINDAGEM VISUAL E SIDEBAR ESTÁTICA (CSS) ---
st.markdown("""
    <style>
    /* 1. Remove o Header (Fim do Git, Fork e da setinha nativa) */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 2. Trava a Sidebar para nunca fechar e remove o botão de recolher */
    [data-testid="stSidebar"] {
        min-width: 260px !important;
        max-width: 260px !important;
    }
    [data-testid="stSidebarNav"] button {
        display: none !important; 
    }
    
    /* 3. Ajuste de margem superior para o conteúdo não bater no topo */
    .block-container {
        padding-top: 1.5rem;
    }
    
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- PASSO 3: CONEXÃO SUPABASE ---
try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except Exception as e:
    st.error(f"Erro de infraestrutura: {e}")
    st.stop()

# --- PASSO 4: VALIDAÇÃO DE DADOS ---
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

# --- PASSO 5: SISTEMA DE ACESSO ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    with t1:
        e_l, p_l = st.text_input("E-mail", key="l_e"), st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar", key="l_b"):
            res = st_supabase.table("app_users").select("email").eq("email", e_l).eq("password", p_l).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
            else: st.error("Dados incorretos.")
    with t2:
        ne, np = st.text_input("Novo E-mail", key="r_e"), st.text_input("Senha", type="password", key="r_p")
        if st.button("Criar Conta", key="r_btn"):
            if is_valid_email(ne) and len(np) >= 6:
                st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
                st.success("Conta criada!")
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL ESTÁTICA (CONTEÚDO) ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", key="btn_logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- PASSO 7: GESTÃO DE TEMPLATES ---
    st.markdown("---")
    st.caption("⚙️ MEUS TEMPLATES")
    with st.expander("➕ Novo Template"):
        with st.form("f_new_tmp", clear_on_submit=True):
            tn = st.text_input("Nome")
            tc = st.selectbox("Categoria", ["Alimentação", "Transporte", "Saúde", "Certificações", "Salário/Renda"])
            td, tv = st.text_input("Desc."), st.number_input("Valor", step=0.01)
            if st.form_submit_button("Salvar"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "description": td, "value": tv, "user_email": u_log}]).execute()
                st.rerun()
    try:
        tmp_data = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data
        if tmp_data:
            tdel = st.selectbox("Remover:", [t['template_name'] for t in tmp_data])
            if st.button("🗑️ Deletar Template"):
                st_supabase.table("templates").delete().eq("template_name", tdel).eq("user_email", u_log).execute()
                st.rerun()
    except: pass

# --- PASSO 8: ÁREA DE ADMINISTRAÇÃO E LANÇAMENTOS ---
st.title("📊 Painel de Controle")
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add_entry", clear_on_submit=True):
        d, ds = st.date_input("Data", datetime.now()), st.text_input("Descrição")
        cat = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Certificações", "Salário/Renda"])
        v, t = st.number_input("Valor", min_value=0.0, step=0.01), st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "category": cat, "description": ds, "value": val_f, "user_email": u_log}]).execute()
            st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Editar/Excluir")
    id_op = st.number_input("ID do lançamento:", min_value=1, step=1)
    if st.button("🗑️ Deletar Registro"):
        st_supabase.table("transactions").delete().eq("id", id_op).eq("user_email", u_log).execute()
        st.rerun()
    if id_op:
        res_v = st_supabase.table("transactions").select("value").eq("id", id_op).eq("user_email", u_log).execute()
        if res_v.data:
            nv = st.number_input("Novo Valor:", value=float(res_v.data[0]['value']))
            if st.button("💾 Salvar Alteração"):
                st_supabase.table("transactions").update({"value": nv}).eq("id", id_op).execute()
                st.rerun()

# --- PASSO 9: DASHBOARD E MÉTRICAS ---
try:
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).order("date", desc=True).execute().data
    df = pd.DataFrame(data_res)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['m_y'] = df['date'].dt.strftime('%m/%Y')
        with c2:
            st.subheader("📊 Resumo Mensal")
            m_s = st.selectbox("Selecione o Mês:", df['m_y'].unique())
            df_m = df[df['m_y'] == m_s]
            ent, sai = df_m[df_m['value'] > 0]['value'].sum(), df_m[df_m['value'] < 0]['value'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Entradas", f"R$ {ent:,.2f}")
            m2.metric("Saídas", f"R$ {abs(sai):,.2f}")
            m3.metric("Saldo", f"R$ {ent+sai:,.2f}")
            st.dataframe(df_m[['id', 'date', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
except: pass