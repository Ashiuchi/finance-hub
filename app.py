import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- SEGURANÇA: LOGIN SIMPLES ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Sand*0515": # Altere para sua senha
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Senha de Acesso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Senha de Acesso", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha incorreta")
        return False
    else:
        return True

if not check_password():
    st.stop()  # Trava a execução do app aqui se não estiver logado

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Finance Hub - Ashiuchi", layout="wide", page_icon="💸")

# --- CONEXÃO COM BANCO DE DADOS ---
# Como estamos começando, ele criará o arquivo 'finance.db' na pasta do projeto
conn = sqlite3.connect('finance.db', check_same_thread=False)
c = conn.cursor()

# Criando a tabela de transações (Data, Categoria, Descrição, Valor)
c.execute('''CREATE TABLE IF NOT EXISTS transactions 
             (id INTEGER PRIMARY KEY, date TEXT, category TEXT, description TEXT, value REAL)''')
conn.commit()

# --- INTERFACE PRINCIPAL ---
st.title("💸 Finance Hub: Gestão de Fluxo")
st.markdown("Foco atual: Controle de Entradas e Saídas")

# --- COLUNAS PARA ENTRADA E RESUMO ---
col_form, col_view = st.columns([1, 2])

with col_form:
    st.subheader("➕ Nova Transação")
    with st.form("entry_form", clear_on_submit=True):
        date = st.date_input("Data", datetime.now())
        description = st.text_input("Descrição (Ex: Almoço, Salário, Internet)")
        category = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        value = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        type_trans = st.radio("Tipo", ["Saída (Gasto)", "Entrada (Receita)"])
        
        submit = st.form_submit_button("Salvar")

    if submit:
        # Lógica: Saídas ficam negativas no banco para facilitar a soma (Saldo)
        final_value = -value if type_trans == "Saída (Gasto)" else value
        c.execute("INSERT INTO transactions (date, category, description, value) VALUES (?,?,?,?)",
                  (date.strftime("%Y-%m-%d"), category, description, final_value))
        conn.commit()
        st.success("Registrado!")
        st.rerun() # Atualiza a tela para mostrar os dados novos

# --- EXIBIÇÃO DOS DADOS ---
df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)

with col_view:
    st.subheader("📊 Histórico e Saldo")
    
    if not df.empty:
        # Cálculo de Saldo Total
        total_balance = df['value'].sum()
        color = "green" if total_balance >= 0 else "red"
        
        st.markdown(f"### Saldo Atual: <span style='color:{color}'>R$ {total_balance:,.2f}</span>", unsafe_allow_html=True)
        
        # Tabela com as últimas 10 transações
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
        
        # Gráfico simples de Gastos por Categoria (apenas valores negativos)
        st.subheader("Gastos por Categoria")
        expenses_df = df[df['value'] < 0].copy()
        expenses_df['value'] = expenses_df['value'].abs() # Para o gráfico ficar positivo
        if not expenses_df.empty:
            st.bar_chart(expenses_df.groupby('category')['value'].sum())
    else:
        st.info("Nenhum registro encontrado. Use o formulário ao lado para começar!")