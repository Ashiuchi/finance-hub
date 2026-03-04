import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. FUNÇÃO DE SEGURANÇA (AUTENTICAÇÃO) ---
def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    def password_entered():
        # Compara a senha digitada com a Secret configurada no Streamlit Cloud 
        if st.session_state["password"] == st.secrets["access_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Remove da memória por segurança 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Exibição inicial do campo de senha 
        st.text_input("Senha de Acesso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Caso a senha esteja incorreta 
        st.text_input("Senha de Acesso", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha incorreta. Tente novamente.")
        return False
    else:
        # Senha correta, libera o acesso 
        return True

# --- 2. EXECUÇÃO DA TRAVA (MUITO IMPORTANTE) ---
# Se a função retornar False, o st.stop() trava o script aqui mesmo.
if not check_password():
    st.stop()

# --- 3. CONFIGURAÇÃO DA PÁGINA (SÓ RODA SE PASSAR PELA SENHA) ---
st.set_page_config(page_title="Finance Hub - Ashiuchi", layout="wide", page_icon="💸")

# --- 4. CONEXÃO COM BANCO DE DADOS ---
conn = sqlite3.connect('finance.db', check_same_thread=False)
c = conn.cursor()

# Criação da tabela de transações 
c.execute('''CREATE TABLE IF NOT EXISTS transactions 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT, description TEXT, value REAL)''')
conn.commit()

# --- 5. INTERFACE PRINCIPAL ---
st.title("💸 Finance Hub: Gestão de Fluxo")
st.markdown("Foco atual: Controle de Entradas e Saídas ")
st.markdown("---")

# Colunas para organizar o Layout 
col_form, col_view = st.columns([1, 2])

# --- 6. FORMULÁRIO DE ENTRADA ---
with col_form:
    st.subheader("➕ Nova Transação")
    with st.form("entry_form", clear_on_submit=True):
        date = st.date_input("Data", datetime.now())
        description = st.text_input("Descrição (Ex: Almoço, Salário, Internet) ")
        category = st.selectbox("Categoria", [
            "Alimentação", "Transporte", "Lazer", "Contas Fixas", 
            "Saúde", "Educação/Certificações", "Salário/Renda"
        ])
        value = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        type_trans = st.radio("Tipo", ["Saída (Gasto)", "Entrada (Receita)"])
        
        submit = st.form_submit_button("Salvar")

    if submit:
        # Saídas ficam negativas para facilitar cálculos 
        final_value = -value if type_trans == "Saída (Gasto)" else value
        c.execute("INSERT INTO transactions (date, category, description, value) VALUES (?,?,?,?)",
                  (date.strftime("%Y-%m-%d"), category, description, final_value))
        conn.commit()
        st.success("Registrado com sucesso!")
        st.rerun()

# --- 7. EXIBIÇÃO E DASHBOARD ---
df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)

with col_view:
    st.subheader("📊 Histórico e Saldo")
    
    if not df.empty:
        total_balance = df['value'].sum()
        color = "green" if total_balance >= 0 else "red"
        
        st.markdown(f"### Saldo Atual: <span style='color:{color}'>R$ {total_balance:,.2f}</span>", unsafe_allow_html=True)
        st.dataframe(df.head(15), use_container_width=True, hide_index=True)

        # --- SEÇÃO DE EXCLUSÃO ---
        st.markdown("---")
        st.subheader("🗑️ Excluir Registro")
        with st.expander("Clique para expandir e excluir"):
            id_to_delete = st.number_input("Digite o ID da transação para excluir:", min_value=1, step=1)
            if st.button("Confirmar Exclusão"):
                c.execute("DELETE FROM transactions WHERE id = ?", (id_to_delete,))
                conn.commit()
                st.warning(f"Registro ID {id_to_delete} removido!")
                st.rerun()
        
        # Gráfico de Gastos por Categoria 
        st.subheader("Distribuição de Gastos")
        expenses_df = df[df['value'] < 0].copy()
        if not expenses_df.empty:
            expenses_df['value'] = expenses_df['value'].abs()
            st.bar_chart(expenses_df.groupby('category')['value'].sum())
    else:
        st.info("Nenhum registro encontrado. Comece pelo formulário!")

# --- 9. GESTÃO DE DADOS (EXCLUIR REGISTRO) ---
st.markdown("---")
with st.expander("🛠️ Ferramentas de Administrador"):
    st.subheader("Excluir Transação Específica")
    # Busca o ID para garantir que o usuário saiba o que está deletando
    id_para_deletar = st.number_input("Informe o ID da transação:", min_value=1, step=1)
    
    if st.button("Confirmar Exclusão", type="secondary"):
        # Verifica se o ID existe antes de tentar deletar
        c.execute("SELECT id FROM transactions WHERE id = ?", (id_para_deletar,))
        if c.fetchone():
            c.execute("DELETE FROM transactions WHERE id = ?", (id_para_deletar,))
            conn.commit()
            st.success(f"Registro {id_para_deletar} removido com sucesso!")
            st.rerun()
        else:
            st.error("ID não encontrado no banco de dados.")

    st.markdown("---")
    if st.button("⚠️ LIMPAR TODO O BANCO DE DADOS"):
        c.execute("DELETE FROM transactions")
        conn.commit()
        st.warning("Todos os dados foram apagados.")
        st.rerun()