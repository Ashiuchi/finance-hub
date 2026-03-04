import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO DE INTERFACE (ORDEM OBRIGATÓRIA) ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# --- PASSO 2: BLINDAGEM VISUAL (CSS DE SEGURANÇA MÁXIMA) ---
# Alvo: Esconde o ícone do GitHub e o botão Deploy, mas preserva a seta da sidebar.
st.markdown("""
    <style>
    /* Esconde o link do GitHub e o botão de deploy pelo seletor de link */
    .stAppDeployButton, a[href*="github.com"] {
        display: none !important;
    }
    /* Esconde o ícone do GitHub pela geometria do desenho (SVG) */
    svg[viewBox="0 0 24 24"] path[d*="M12 .297c-6.63"] {
        display: none !important;
    }
    /* Remove rodapé e menu de 3 pontos */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    /* Garante visibilidade da seta para abrir/fechar a barra lateral */
    [data-testid="stSidebarNav"] { visibility: visible !important; }
    </style>
    """, unsafe_allow_html=True)

# --- PASSO 3: CONEXÃO COM O BANCO ---
try:
    st_supabase = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Erro de conexão técnica: {e}")
    st.stop()

# --- PASSO 4: VALIDAÇÃO DE DADOS ---
def is_valid_email(email):
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

# --- PASSO 5: SISTEMA DE ACESSO ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    with t1:
        e_in, p_in = st.text_input("E-mail", key="l_email"), st.text_input("Senha", type="password", key="l_pass")
        if st.button("Entrar", key="l_btn"):
            res = st_supabase.table("app_users").select("email").eq("email", e_in).eq("password", p_in).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
            else: st.error("Dados incorretos.")
    with t2:
        ne, np = st.text_input("Novo E-mail", key="r_email"), st.text_input("Senha", type="password", key="r_pass")
        if st.button("Criar Conta", key="r_btn"):
            if is_valid_email(ne) and len(np) >= 6:
                st_supabase.table("app_users").insert([{"email": ne, "password": np}]).execute()
                st.success("Conta criada! Vá para Login.")
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL (CONTEÚDO) ---
with st.sidebar:
    st.write(f"Conectado: **{u_log}**")
    if st.button("🚪 Sair", key="btn_out_final", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- PASSO 7: GESTÃO DE TEMPLATES (CRIAR/DELETAR) ---
    st.markdown("---")
    st.subheader("⚙️ Meus Atalhos")
    with st.expander("➕ Novo Template"):
        with st.form("form_new_tmp", clear_on_submit=True):
            tn = st.text_input("Nome")
            tc = st.selectbox("Categoria", ["Alimentação", "Transporte", "Saúde", "Certificações", "Salário/Renda"])
            td, tv = st.text_input("Descrição"), st.number_input("Valor", step=0.01)
            if st.form_submit_button("Salvar Template"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "description": td, "value": tv, "user_email": u_log}]).execute()
                st.rerun()
    try:
        tmp_data = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data
        if tmp_data:
            t_del = st.selectbox("Remover:", [t['template_name'] for t in tmp_data], key="sel_t_del")
            if st.button("🗑️ Deletar Template"):
                st_supabase.table("templates").delete().eq("template_name", t_del).eq("user_email", u_log).execute()
                st.rerun()
    except: pass

# --- PASSO 8: ÁREA DE LANÇAMENTOS E EDIÇÃO ---
st.title("📊 Painel Financeiro")
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add_entry", clear_on_submit=True):
        d, ds = st.date_input("Data", datetime.now()), st.text_input("Descrição")
        c = st.selectbox("Categoria", ["Alimentação", "Transporte", "Contas Fixas", "Saúde", "Educação", "Salário/Renda"])
        v, t = st.number_input("Valor", min_value=0.0, step=0.01), st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "category": c, "description": ds, "value": val_f, "user_email": u_log}]).execute()
            st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Administração (Editar/Excluir)")
    id_op = st.number_input("ID do lançamento:", min_value=1, step=1, key="id_edit_op")
    ce1, ce2 = st.columns(2)
    with ce1:
        if st.button("🗑️ Deletar ID"):
            st_supabase.table("transactions").delete().eq("id", id_op).eq("user_email", u_log).execute()
            st.rerun()
    with ce2:
        if id_op:
            res_val = st_supabase.table("transactions").select("value").eq("id", id_op).eq("user_email", u_log).execute()
            if res_val.data:
                nv = st.number_input("Novo Valor:", value=float(res_val.data[0]['value']), key="nv_edit_op")
                if st.button("💾 Salvar"):
                    st_supabase.table("transactions").update({"value": nv}).eq("id", id_op).execute()
                    st.rerun()

# --- PASSO 9: DASHBOARD E VISUALIZAÇÃO ---
try:
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).order("date", desc=True).execute().data
    df = pd.DataFrame(data_res)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['m_y'] = df['date'].dt.strftime('%m/%Y')
        with col2:
            st.subheader("📊 Resumo Mensal")
            m_sel = st.selectbox("Mês:", df['m_y'].unique())
            df_m = df[df['m_y'] == m_sel]
            e, s = df_m[df_m['value'] > 0]['value'].sum(), df_m[df_m['value'] < 0]['value'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Entradas", f"R$ {e:,.2f}"); m2.metric("Saídas", f"R$ {abs(s):,.2f}"); m3.metric("Saldo", f"R$ {e+s:,.2f}")
            st.dataframe(df_m[['id', 'date', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
except: pass