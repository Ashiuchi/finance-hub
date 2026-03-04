import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# --- 1. SEGURANÇA MULTI-USUÁRIO ---
def check_password():
    if "user_email" not in st.session_state:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Login"):
            # Verifica se o e-mail existe nas secrets e se a senha bate
            if email in st.secrets["users"] and st.secrets["users"][email] == senha:
                st.session_state["user_email"] = email
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
        return False
    return True

if not check_password():
    st.stop()

user_logado = st.session_state["user_email"]
st.sidebar.write(f"Logado como: **{user_logado}**")

# --- 2. FILTRAGEM DE DADOS (Exemplo na Busca) ---
# Agora toda busca leva o filtro do e-mail
res = st_supabase.table("transactions").select("*").eq("user_email", user_logado).execute()

# --- 3. CONEXÃO COM SUPABASE ---
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

# --- 5. ENTRADA DE DADOS ---
with col_form:
    st.subheader("➕ Nova Transação")
    with st.form("entry_form", clear_on_submit=True):
        date = st.date_input("Data", datetime.now())
        description = st.text_input("Descrição")
        category = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
        value = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        type_trans = st.radio("Tipo", ["Saída (Gasto)", "Entrada (Receita)"])
        submit = st.form_submit_button("Salvar na Nuvem")

    if submit:
        final_value = -value if type_trans == "Saída (Gasto)" else value
        st_supabase.table("transactions").insert([
            {"date": date.strftime("%Y-%m-%d"), "category": category, "description": description, "value": final_value}
        ]).execute()
        st.success("Sincronizado!")
        st.rerun()

    # --- 5.1 LANÇAMENTOS RÁPIDOS (TEMPLATES) ---
    st.markdown("---")
    st.subheader("⚡ Lançamentos Rápidos")
    
    try:
        templates = st_supabase.table("templates").select("*").execute().data
    except:
        templates = []

    if templates:
        cols = st.columns(2)
        for i, t in enumerate(templates):
            with cols[i % 2]:
                if st.button(f"📌 {t['template_name']}", use_container_width=True):
                    hoje = datetime.now()
                    # Lógica de Data Fixa (Ex: Aluguel no dia 10)
                    data_final = hoje.replace(day=10).strftime("%Y-%m-%d") if "Aluguel" in t['template_name'] else hoje.strftime("%Y-%m-%d")
                    
                    st_supabase.table("transactions").insert([
                        {"date": data_final, "category": t['category'], "description": t['description'], "value": t['value']}
                    ]).execute()
                    st.success(f"Lançado para dia {data_final}!")
                    st.rerun()
    
    # --- 5.2 CONFIGURAR TEMPLATES ---
    with st.expander("⚙️ Configurar Atalhos"):
        with st.form("new_template"):
            tn = st.text_input("Nome (ex: Aluguel)")
            tc = st.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"])
            td = st.text_input("Descrição Padrão")
            tv = st.number_input("Valor Padrão", step=0.01)
            if st.form_submit_button("Salvar Atalho"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "description": td, "value": tv}]).execute()
                st.rerun()
        
        if templates:
            t_del = st.selectbox("Remover Atalho:", [t['template_name'] for t in templates])
            if st.button("Excluir Atalho"):
                st_supabase.table("templates").delete().eq("template_name", t_del).execute()
                st.rerun()

# --- 6. PROCESSAMENTO E DASHBOARD ---
try:
    df = pd.DataFrame(st_supabase.table("transactions").select("*").order("date", desc=True).execute().data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['data_formatada'] = df['date'].dt.strftime('%d/%m/%Y')
        df['month_year'] = df['date'].dt.strftime('%m/%Y')
except:
    df = pd.DataFrame()

with col_view:
    if not df.empty:
        st.subheader("📊 Inteligência Financeira")
        mes_sel = st.selectbox("Período:", df['month_year'].unique())
        df_mes = df[df['month_year'] == mes_sel].copy()
        
        m1, m2, m3 = st.columns(3)
        ent = df_mes[df_mes['value'] > 0]['value'].sum()
        sai = df_mes[df_mes['value'] < 0]['value'].sum()
        m1.metric("Receitas", f"R$ {ent:,.2f}")
        m2.metric("Gastos", f"R$ {abs(sai):,.2f}")
        m3.metric("Saldo", f"R$ {ent+sai:,.2f}", delta=f"{ent+sai:,.2f}")

        st.dataframe(df_mes[['id', 'data_formatada', 'category', 'description', 'value']], 
                     use_container_width=True, hide_index=True, column_config={"data_formatada": "Data"})
        
        gastos = df_mes[df_mes['value'] < 0].copy()
        if not gastos.empty:
            gastos['value'] = gastos['value'].abs()
            st.bar_chart(gastos.groupby('category')['value'].sum())
    else:
        st.info("Nenhum dado encontrado.")

# --- 7. FERRAMENTAS ADM (SIDEBAR) ---
with st.sidebar:
    st.header("🛠️ Administração")
    
    # Exclusão
    st.subheader("🗑️ Excluir")
    id_del = st.number_input("ID:", min_value=1, step=1, key="del")
    if st.button("Confirmar Exclusão"):
        st_supabase.table("transactions").delete().eq("id", id_del).execute()
        st.rerun()
    
    # Edição
    st.markdown("---")
    st.subheader("📝 Editar")
    id_ed = st.number_input("ID:", min_value=1, step=1, key="ed")
    if id_ed:
        d_at = st_supabase.table("transactions").select("*").eq("id", id_ed).execute().data
        if d_at:
            d = d_at[0]
            nv = st.number_input("Valor:", value=float(d['value']))
            nc = st.selectbox("Cat:", ["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"], 
                              index=["Alimentação", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Educação/Certificações", "Salário/Renda"].index(d['category']))
            if st.button("Salvar"):
                st_supabase.table("transactions").update({"value": nv, "category": nc}).eq("id", id_ed).execute()
                st.rerun()