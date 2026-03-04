import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# --- 1. FUNÇÃO DE SEGURANÇA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["access_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Senha de Acesso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Senha de Acesso", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha incorreta.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- 2. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Finance Hub - Ashiuchi", layout="wide", page_icon="💸")

# --- 3. CONEXÃO COM SUPABASE (NUVEM) ---
# Ele busca automaticamente as chaves que você colocou nas Secrets do Streamlit
st_supabase = st.connection("supabase", type=SupabaseConnection)

# --- 4. INTERFACE PRINCIPAL ---
st.title("💸 Finance Hub: Gestão na Nuvem")
st.info("Dados sincronizados: PC Trabalho ↔ Celular ↔ Casa")

col_form, col_view = st.columns([1, 2])

# --- 5. FORMULÁRIO DE ENTRADA ---
with col_form:
    st.subheader("➕ Nova Transação")
    with st.form("entry_form", clear_on_submit=True):
        date = st.date_input("Data", datetime.now())
        description = st.text_input("Descrição")
        category = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação", "Salário/Renda"])
        value = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        type_trans = st.radio("Tipo", ["Saída (Gasto)", "Entrada (Receita)"])
        submit = st.form_submit_button("Salvar na Nuvem")

    if submit:
        # CORREÇÃO DA INDENTAÇÃO AQUI:
        final_value = -value if type_trans == "Saída (Gasto)" else value
        
        # Inserindo no Supabase
        st_supabase.table("transactions").insert([
            {
                "date": date.strftime("%Y-%m-%d"), 
                "category": category, 
                "description": description, 
                "value": final_value
            }
        ]).execute()
        
        st.success("Sincronizado!")
        st.rerun()

# --- 6. LEITURA DE DADOS E DASHBOARD ---
# Busca os dados diretamente do Supabase
try:
    response = st_supabase.table("transactions").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(response.data)
except Exception as e:
    st.error(f"Erro ao conectar com o banco: {e}")
    df = pd.DataFrame()

with col_view:
    st.subheader("📊 Histórico Sincronizado")
    
    if not df.empty:
        total_balance = df['value'].sum()
        color = "green" if total_balance >= 0 else "red"
        st.markdown(f"### Saldo Geral: <span style='color:{color}'>R$ {total_balance:,.2f}</span>", unsafe_allow_html=True)
        
        st.dataframe(df.head(15), use_container_width=True, hide_index=True)
        
        # Gráfico
        expenses_df = df[df['value'] < 0].copy()
        if not expenses_df.empty:
            expenses_df['value'] = expenses_df['value'].abs()
            st.bar_chart(expenses_df.groupby('category')['value'].sum())
    else:
        st.info("Nenhum dado na nuvem. Comece a cadastrar!")

# --- 7. FERRAMENTAS ---
with st.sidebar:
    st.subheader("🗑️ Excluir Registro")
    id_del = st.number_input("ID para deletar:", min_value=1, step=1)
    if st.button("Confirmar Exclusão"):
        st_supabase.table("transactions").delete().eq("id", id_del).execute()
        st.warning(f"ID {id_del} removido da nuvem!")
        st.rerun()