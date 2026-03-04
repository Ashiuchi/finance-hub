import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import re

# --- 1. FUNÇÕES DE SEGURANÇA E VALIDAÇÃO ---
def is_valid_email(email):
    """Valida o formato do e-mail via Regex."""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

def auth_system():
    """Gerencia Login e Cadastro via Supabase."""
    if "user_email" not in st.session_state:
        st.title("💸 Finance Hub: Acesso Seguro")
        aba_login, aba_cadastro = st.tabs(["Login", "Criar Conta"])

        with aba_login:
            email_log = st.text_input("E-mail", key="email_log")
            senha_log = st.text_input("Senha", type="password", key="senha_log")
            if st.button("Entrar"):
                res = st_supabase.table("app_users").select("*").eq("email", email_log).eq("password", senha_log).execute()
                if res.data:
                    st.session_state["user_email"] = email_log
                    st.rerun()
                else:
                    st.error("Credenciais inválidas ou conta não verificada.")

        with aba_cadastro:
            st.subheader("Nova Conta")
            new_email = st.text_input("E-mail para cadastro", key="new_email")
            if new_email and not is_valid_email(new_email):
                st.error("⚠️ Formato de e-mail inválido.")
            
            new_senha = st.text_input("Crie uma senha (mín. 6 chars)", type="password", key="new_senha")
            conf_senha = st.text_input("Confirme a senha", type="password", key="conf_senha")
            
            if st.button("Finalizar Cadastro"):
                if not is_valid_email(new_email):
                    st.error("E-mail inválido.")
                elif new_senha != conf_senha:
                    st.error("As senhas não coincidem.")
                elif len(new_senha) < 6:
                    st.warning("Senha muito curta.")
                else:
                    try:
                        st_supabase.table("app_users").insert([{"email": new_email, "password": new_senha}]).execute()
                        st.success("Conta criada! Faça login para continuar.")
                    except:
                        st.error("Este e-mail já está cadastrado.")
        return False
    return True

# --- 2. CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="Finance Hub - Ashiuchi", layout="wide", page_icon="💸")

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

if not auth_system():
    st.stop()

# --- 3. VARIÁVEIS DE CONTEXTO ---
user_logado = st.session_state["user_email"]
st.sidebar.write(f"Usuário: **{user_logado}**")
if st.sidebar.button("Sair"):
    del st.session_state["user_email"]
    st.rerun()

# --- 4. INTERFACE PRINCIPAL ---
st.title("💸 Finance Hub: Gestão na Nuvem")
col_form, col_view = st.columns([1, 2])

with col_form:
    st.subheader("➕ Nova Transação")
    with st.form("entry_form", clear_on_submit=True):
        date = st.date_input("Data", datetime.now())
        description = st.text_input("Descrição")
        category = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        value = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        type_trans = st.radio("Tipo", ["Saída (Gasto)", "Entrada (Receita)"])
        submit = st.form_submit_button("Salvar")

    if submit:
        final_value = -value if type_trans == "Saída (Gasto)" else value
        st_supabase.table("transactions").insert([
            {"date": date.strftime("%Y-%m-%d"), "category": category, "description": description, "value": final_value, "user_email": user_logado}
        ]).execute()
        st.success("Sincronizado!")
        st.rerun()

    # --- 5. LANÇAMENTOS RÁPIDOS (TEMPLATES) ---
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
                if st.button(f"📌 {t['template_name']}", use_container_width=True):
                    hoje = datetime.now()
                    dt_final = hoje.replace(day=10).strftime("%Y-%m-%d") if "Aluguel" in t['template_name'] else hoje.strftime("%Y-%m-%d")
                    st_supabase.table("transactions").insert([
                        {"date": dt_final, "category": t['category'], "description": t['description'], "value": t['value'], "user_email": user_logado}
                    ]).execute()
                    st.success("Lançado!")
                    st.rerun()
    
    with st.expander("⚙️ Gerenciar Atalhos"):
        with st.form("new_temp"):
            tn = st.text_input("Nome do Atalho")
            tc = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
            td = st.text_input("Descrição Padrão")
            tv = st.number_input("Valor Padrão", step=0.01)
            if st.form_submit_button("Salvar"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "description": td, "value": tv, "user_email": user_logado}]).execute()
                st.rerun()
        if templates:
            t_del = st.selectbox("Remover:", [t['template_name'] for t in templates])
            if st.button("Excluir Atalho"):
                st_supabase.table("templates").delete().eq("template_name", t_del).eq("user_email", user_logado).execute()
                st.rerun()

# --- 6. PROCESSAMENTO DE DADOS ---
try:
    df = pd.DataFrame(st_supabase.table("transactions").select("*").eq("user_email", user_logado).order("date", desc=True).execute().data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['data_formatada'] = df['date'].dt.strftime('%d/%m/%Y')
        df['month_year'] = df['date'].dt.strftime('%m/%Y')
except:
    df = pd.DataFrame()

# --- 7. DASHBOARD E INTELIGÊNCIA ---
with col_view:
    if not df.empty:
        st.subheader("📊 Inteligência Financeira")
        mes_sel = st.selectbox("Filtrar Período:", df['month_year'].unique())
        df_mes = df[df['month_year'] == mes_sel].copy()
        
        # MÉTRICAS - BLINDADAS (Sem âncora na URL)
        m1, m2, m3 = st.columns(3)
        ent = df_mes[df_mes['value'] > 0]['value'].sum()
        sai = df_mes[df_mes['value'] < 0]['value'].sum()
        saldo = ent + sai
        
        m1.metric("Entradas", f"R$ {ent:,.2f}")
        m2.metric("Saídas", f"R$ {abs(sai):,.2f}")
        m3.metric("Saldo do Mês", f"R$ {saldo:,.2f}", delta=f"{saldo:,.2f}")

        st.markdown("---")
        st.dataframe(df_mes[['id', 'data_formatada', 'category', 'description', 'value']], 
                     use_container_width=True, hide_index=True, column_config={"data_formatada": "Data"})
        
        gastos = df_mes[df_mes['value'] < 0].copy()
        if not gastos.empty:
            gastos['value'] = gastos['value'].abs()
            st.bar_chart(gastos.groupby('category')['value'].sum())
    else:
        st.info("Aguardando dados...")

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