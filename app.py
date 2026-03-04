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
        # Converter coluna de data para formato datetime do Python
        df['date'] = pd.to_datetime(df['date'])
        # Criar coluna de Mês/Ano para facilitar a filtragem
        df['month_year'] = df['date'].dt.strftime('%m/%Y')
except Exception:
    df = pd.DataFrame()

# --- 7. DASHBOARD COM INTELIGÊNCIA MENSAL ---
with col_view:
    if not df.empty:
        st.subheader("📊 Inteligência Financeira")
        
        # Filtro de Mês na parte superior do dashboard
        meses_disponiveis = df['month_year'].unique()
        mes_selecionado = st.selectbox("Selecione o período para análise:", meses_disponiveis)
        
        # Filtrar DF pelo mês selecionado
        df_mes = df[df['month_year'] == mes_selecionado]
        
        # Cálculos do Mês
        entradas_mes = df_mes[df_mes['value'] > 0]['value'].sum()
        saidas_mes = df_mes[df_mes['value'] < 0]['value'].sum()
        saldo_mes = entradas_mes + saidas_mes
        
        # Exibição de Métricas em Colunas
        m1, m2, m3 = st.columns(3)
        m1.metric("Entradas (Receitas)", f"R$ {entradas_mes:,.2f}")
        m2.metric("Saídas (Gastos)", f"R$ {abs(saidas_mes):,.2f}", delta_color="normal")
        m3.metric("Saldo do Mês", f"R$ {saldo_mes:,.2f}", delta=f"{saldo_mes:,.2f}")

        st.markdown("---")
        st.write(f"**Detalhes de {mes_selecionado}:**")
        st.dataframe(df_mes[['id', 'date', 'category', 'description', 'value']], use_container_width=True, hide_index=True)
        
        # Gráfico de Gastos por Categoria (Apenas do mês selecionado)
        gastos_mes = df_mes[df_mes['value'] < 0].copy()
        if not gastos_mes.empty:
            st.write(f"**Onde você gastou em {mes_selecionado}:**")
            gastos_mes['value'] = gastos_mes['value'].abs()
            st.bar_chart(gastos_mes.groupby('category')['value'].sum())
    else:
        st.info("Nenhum dado na nuvem para analisar.")