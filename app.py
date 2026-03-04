import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# --- 1. FUNÇÃO DE SEGURANÇA (AUTENTICAÇÃO) ---
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

# --- 3. CONEXÃO COM SUPABASE ---
# Usando a forma explícita para evitar o erro de "URL not provided"
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

# --- 4. INTERFACE PRINCIPAL ---
st.title("💸 Finance Hub: Gestão na Nuvem")
st.markdown("Dados sincronizados: PC Trabalho ↔ Celular")

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
        final_value = -value if type_trans == "Saída (Gasto)" else value
        try:
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
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

# --- 6. LEITURA E PROCESSAMENTO DE DADOS ---
try:
    response = st_supabase.table("transactions").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        # Converter para datetime
        df['date'] = pd.to_datetime(df['date'])
        # Criar a coluna de exibição formatada (Apenas Data, sem 00:00:00)
        df['data_formatada'] = df['date'].dt.strftime('%d/%m/%Y')
        # Criar coluna de Mês/Ano para o filtro
        df['month_year'] = df['date'].dt.strftime('%m/%Y')
except Exception:
    df = pd.DataFrame()

# --- 7. DASHBOARD COM INTELIGÊNCIA MENSAL ---
with col_view:
    if not df.empty:
        st.subheader("📊 Inteligência Financeira")
        
        # Filtro de Mês
        meses_disponiveis = df['month_year'].unique()
        mes_selecionado = st.selectbox("Selecione o período para análise:", meses_disponiveis)
        
        # Filtrar DF pelo mês selecionado
        df_mes = df[df['month_year'] == mes_selecionado].copy()
        
        # Cálculos do Mês
        entradas_mes = df_mes[df_mes['value'] > 0]['value'].sum()
        saidas_mes = df_mes[df_mes['value'] < 0]['value'].sum()
        saldo_mes = entradas_mes + saidas_mes
        
        # Exibição de Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Receitas", f"R$ {entradas_mes:,.2f}")
        m2.metric("Gastos", f"R$ {abs(saidas_mes):,.2f}")
        m3.metric("Saldo Líquido", f"R$ {saldo_mes:,.2f}", delta=f"{saldo_mes:,.2f}")

        st.markdown("---")
        st.write(f"**Extrato de {mes_selecionado}:**")
        
        # Exibindo a 'data_formatada' em vez da data bruta com zeros
        st.dataframe(
            df_mes[['id', 'data_formatada', 'category', 'description', 'value']], 
            use_container_width=True, 
            hide_index=True,
            column_config={"data_formatada": "Data"} # Renomeia a coluna na visualização
        )
        
        # Gráfico Mensal
        gastos_mes = df_mes[df_mes['value'] < 0].copy()
        if not gastos_mes.empty:
            st.write(f"**Gastos por Categoria em {mes_selecionado}:**")
            gastos_mes['value'] = gastos_mes['value'].abs()
            st.bar_chart(gastos_mes.groupby('category')['value'].sum())
    else:
        st.info("Nenhum dado na nuvem para analisar.")

# --- 8. FERRAMENTAS DE ADM (SIDEBAR) - RECUPERADA ---
with st.sidebar:
    st.markdown("---")
    st.header("🛠️ Administração")
    st.subheader("🗑️ Excluir Registro")
    
    # Input para o ID
    id_del = st.number_input("ID para excluir:", min_value=1, step=1, key="del_id_final")
    
    if st.button("Confirmar Exclusão", key="btn_del_final"):
        try:
            # Comando para deletar no Supabase
            st_supabase.table("transactions").delete().eq("id", id_del).execute()
            st.warning(f"O registro ID {id_del} foi removido com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")

st.markdown("---")
st.subheader("📝 Editar Registro")
    
# Input para buscar o ID que deseja editar
id_edit = st.number_input("ID para editar:", min_value=1, step=1, key="edit_id")
    
if id_edit:
    # Busca os dados atuais desse ID no Supabase
    res_edit = st_supabase.table("transactions").select("*").eq("id", id_edit).execute()
        
    if res_edit.data:
        dados_atuais = res_edit.data[0]
        st.info(f"Editando: {dados_atuais['description']}")
        
        # Campos preenchidos com os valores atuais
        new_val = st.number_input("Novo Valor:", value=float(dados_atuais['value']), key="new_val")
        new_cat = st.selectbox("Nova Categoria:", [
            "Alimentação", "Transporte", "Lazer", "Contas Fixas", 
            "Saúde", "Educação/Certificações", "Salário/Renda"
        ], index=["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"].index(dados_atuais['category']), key="new_cat")
            
        if st.button("Salvar Alterações", key="btn_update"):
            # Comando UPDATE no Supabase
            st_supabase.table("transactions").update({
                "value": new_val,
                "category": new_cat
            }).eq("id", id_edit).execute()
                
            st.success(f"Registro {id_edit} atualizado!")
            st.rerun()
    else:
        st.caption("ID não encontrado para edição.")