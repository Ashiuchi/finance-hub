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

# --- PASSO 2: BLINDAGEM VISUAL (CSS DE SEGURANÇA) ---
# Foco: Esconder o ícone do GitHub por seletores de link e classe, antes e depois do login.
st.markdown("""
    <style>
    /* Esconde o link do repositório no cabeçalho pelo destino do link */
    a[href*="github.com"], .stAppDeployButton {
        display: none !important;
    }
    /* Remove o rodapé e o menu de opções padrão */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    /* Garante que a seta para expandir/recolher a barra lateral continue funcionando */
    [data-testid="stSidebarNav"] { visibility: visible; }
    </style>
    """, unsafe_allow_html=True)

# --- PASSO 3: CONEXÃO COM O BANCO DE DADOS ---
try:
    st_supabase = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Erro de infraestrutura: {e}")
    st.stop()

# --- PASSO 4: FUNÇÕES DE APOIO ---
def is_valid_email(email):
    """Valida o formato do e-mail para integridade dos dados."""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

# --- PASSO 5: SISTEMA DE AUTENTICAÇÃO (LOGIN / CADASTRO) ---
if "user_email" not in st.session_state:
    st.query_params.clear() 
    st.title("💸 Finance Hub: Acesso")
    tab_log, tab_reg = st.tabs(["Login", "Cadastrar"])
    
    with tab_log:
        email_l = st.text_input("E-mail", key="login_email_final")
        pass_l = st.text_input("Senha", type="password", key="login_pass_final")
        if st.button("Entrar", key="btn_login_final"):
            res = st_supabase.table("app_users").select("email").eq("email", email_l).eq("password", pass_l).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
            else: st.error("Dados incorretos.")
            
    with tab_reg:
        new_e = st.text_input("E-mail para Cadastro", key="reg_email_final")
        new_p = st.text_input("Crie uma Senha (mín. 6 chars)", type="password", key="reg_pass_final")
        if st.button("Finalizar Cadastro", key="btn_reg_final"):
            if is_valid_email(new_e) and len(new_p) >= 6:
                try:
                    st_supabase.table("app_users").insert([{"email": new_e, "password": new_p}]).execute()
                    st.success("Conta criada! Vá para Login.")
                except: st.error("E-mail já cadastrado.")
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL (USUÁRIO E LOGOUT) ---
with st.sidebar:
    st.write(f"Usuário: **{u_log}**")
    if st.button("🚪 Sair", key="btn_logout_final", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- PASSO 7: GESTÃO DE TEMPLATES (CRIAR E DELETAR) ---
    st.markdown("---")
    st.subheader("⚙️ Configurar Atalhos")
    with st.expander("➕ Novo Template"):
        with st.form("form_new_template", clear_on_submit=True):
            name_t = st.text_input("Nome do Atalho (ex: Internet)")
            cat_t = st.selectbox("Categoria", ["Alimentação", "Transporte", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
            desc_t = st.text_input("Descrição padrão")
            val_t = st.number_input("Valor padrão", step=0.01)
            if st.form_submit_button("Criar"):
                st_supabase.table("templates").insert([{"template_name": name_t, "category": cat_t, "description": desc_t, "value": val_t, "user_email": u_log}]).execute()
                st.rerun()

    try:
        tmp_data = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data
        if tmp_data:
            t_del = st.selectbox("Remover Template:", [t['template_name'] for t in tmp_data], key="sel_del_template")
            if st.button("🗑️ Deletar Template"):
                st_supabase.table("templates").delete().eq("template_name", t_del).eq("user_email", u_log).execute()
                st.rerun()
    except: pass

# --- PASSO 8: ÁREA DE LANÇAMENTOS E EDIÇÃO (AUTONOMIA) ---
st.title("📊 Painel de Gestão Financeira")
c1, c2 = st.columns([1, 2])

with c1:
    st.subheader("➕ Novo Registro")
    with st.form("form_main_add", clear_on_submit=True):
        d_f = st.date_input("Data", datetime.now())
        ds_f = st.text_input("Descrição")
        cat_f = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        v_f = st.number_input("Valor", min_value=0.0, step=0.01)
        t_f = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Salvar"):
            val_final = -v_f if t_f == "Gasto" else v_f
            st_supabase.table("transactions").insert([{"date": d_f.strftime("%Y-%m-%d"), "category": cat_f, "description": ds_f, "value": val_final, "user_email": u_log}]).execute()
            st.rerun()

    if tmp_data:
        st.markdown("---")
        st.subheader("⚡ Atalhos Rápidos")
        cols = st.columns(2)
        for i, t in enumerate(tmp_data):
            with cols[i % 2]:
                if st.button(f"📌 {t['template_name']}", key=f"btn_quick_{i}", use_container_width=True):
                    st_supabase.table("transactions").insert([{"date": datetime.now().strftime("%Y-%m-%d"), "category": t['category'], "description": t['description'], "value": t['value'], "user_email": u_log}]).execute()
                    st.rerun()

    st.markdown("---")
    st.subheader("📝 Editar/Excluir")
    id_op = st.number_input("ID do lançamento:", min_value=1, step=1, key="input_id_operation")
    ce1, ce2 = st.columns(2)
    with ce1:
        if st.button("🗑️ Deletar ID", key="btn_del_operation"):
            st_supabase.table("transactions").delete().eq("id", id_op).eq("user_email", u_log).execute()
            st.rerun()
    with ce2:
        if id_op:
            res_v = st_supabase.table("transactions").select("value").eq("id", id_op).eq("user_email", u_log).execute()
            if res_v.data:
                nv = st.number_input("Novo Valor:", value=float(res_v.data[0]['value']), key="input_new_value_op")
                if st.button("💾 Salvar", key="btn_save_operation"):
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
            m_s = st.selectbox("Filtrar Mês:", df['m_y'].unique(), key="selectbox_month_filter")
            df_m = df[df['m_y'] == m_s]
            ent, sai = df_m[df_m['value'] > 0]['value'].sum(), df_m[df_m['value'] < 0]['value'].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Entradas", f"R$ {ent:,.2f}")
            m2.metric("Saídas", f"R$ {abs(sai):,.2f}")
            m3.metric("Saldo", f"R$ {ent+sai:,.2f}")
            st.dataframe(df_m[['id', 'date', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
except: pass