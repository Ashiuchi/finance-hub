import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from streamlit_calendar import calendar
import plotly.express as px
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(
    page_title="Finance Hub - Ashiuchi", 
    layout="wide", 
    page_icon="💸",
    initial_sidebar_state="expanded"
)

# --- PASSO 2: VISUAL PREMIUM (FUNDO FIXO) ---
bg_img = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1920&q=80"
st.markdown(f"""
    <style>
    .stApp {{ background-image: url("{bg_img}"); background-attachment: fixed; background-size: cover; }}
    .stApp > header, .stApp > div {{ background-color: rgba(14, 17, 23, 0.85); }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stSidebar"] {{ min-width: 300px !important; max-width: 300px !important; }}
    [data-testid="stSidebar"] button[title="Collapse sidebar"] {{ display: none !important; }}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- PASSO 3: CONEXÃO SUPABASE (CORREÇÃO DO ERRO) ---
# Adicionamos novamente a passagem explícita das credenciais para evitar o ConnectionRefused
try:
    st_supabase = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Erro de infraestrutura: Verifique os Secrets no Streamlit Cloud.")
    st.stop()

# --- PASSO 4: VALIDAÇÃO ---
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

# --- PASSO 5: SISTEMA DE ACESSO ---
if "user_email" not in st.session_state:
    st.title("💸 Finance Hub: Acesso")
    t1, t2 = st.tabs(["Login", "Cadastrar"])
    with t1:
        el, pl = st.text_input("E-mail", key="l_e"), st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar"):
            res = st_supabase.table("app_users").select("email").eq("email", el).eq("password", pl).execute()
            if res.data:
                st.session_state["user_email"] = res.data[0]["email"]
                st.rerun()
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL (GRÁFICOS E NOVO TEMPLATE) ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.clear(); st.rerun()
    
    # Busca dados para o gráfico e calendário
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).execute().data
    temp_res = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data

    if data_res:
        df_side = pd.DataFrame(data_res)
        df_g = df_side[df_side['value'] < 0].copy()
        if not df_g.empty:
            df_g['abs_v'] = df_g['value'].abs()
            st.markdown("---")
            st.caption("📊 DISTRIBUIÇÃO DE GASTOS")
            fig_p = px.pie(df_g, values='abs_v', names='category', hole=0.4)
            fig_p.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_p, use_container_width=True)

    # RESTAURAÇÃO: CRIAÇÃO DE TEMPLATES NA SIDEBAR
    st.markdown("---")
    st.caption("⚙️ MEUS TEMPLATES")
    with st.expander("➕ Criar Novo Template"):
        with st.form("f_tmp_side", clear_on_submit=True):
            tn = st.text_input("Nome do Template")
            tc = st.selectbox("Categoria", ["Alimentação", "Venda Scripts", "Transporte", "Certificações", "Infra"])
            tv = st.number_input("Valor Padrão", step=0.01)
            if st.form_submit_button("Salvar"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "value": tv, "user_email": u_log}]).execute()
                st.rerun()

# --- PASSO 7: PAINEL DE CONTROLE (NOVO REGISTRO) ---
st.title("📊 Gestão e Planejamento")
c1, c2 = st.columns([1, 2.5])

with c1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add_main", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        cat = st.selectbox("Categoria", ["Alimentação", "Venda Scripts", "Transporte", "Certificações", "Infra"])
        fp = st.selectbox("Pagamento", ["Dinheiro", "Cartão Crédito", "Cartão Débito", "Pix"])
        v = st.number_input("Valor", min_value=0.0, step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Lançar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "category": cat, "description": ds, "value": val_f, "payment_method": fp, "user_email": u_log}]).execute(); st.rerun()

# --- PASSO 8: CALENDÁRIO COMERCIAL (COM TEMPLATES) ---
with c2:
    events = []
    if data_res:
        for i in data_res:
            events.append({"title": f"✅ {i['description']}", "start": i['date'], "color": "#ff4b4b" if i['value'] < 0 else "#28a745"})
    
    if temp_res:
        for t in temp_res:
            # Exibe os templates no dia de hoje como sugestão visual
            events.append({"title": f"📝 Sugestão: {t['template_name']}", "start": datetime.now().strftime("%Y-%m-%d"), "color": "#ffc107"})
            
    calendar(events=events, options={"height": 450}, key="cal_finance_vfinal")

# --- PASSO 9: TABELA EDITÁVEL (EXTRATO + DROPDOWN) ---
st.markdown("---")
if data_res:
    df_ed = pd.DataFrame(data_res)
    st.subheader("📂 Extrato Editável")
    
    edited_df = st.data_editor(
        df_ed[['id', 'date', 'category', 'description', 'payment_method', 'value']],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "category": st.column_config.SelectboxColumn("Categoria", options=["Alimentação", "Pet", "Transporte", "Lazer", "miscellaneous"], required=True),
            "payment_method": st.column_config.SelectboxColumn("Pagamento", options=["Dinheiro", "Cartão Crédito", "Cartão Débito", "Pix", "Alimentação"], required=True)
        },
        key="editor_central"
    )

    if st.button("💾 Sincronizar Alterações"):
        # Sincroniza deleções
        curr_ids = edited_df['id'].tolist()
        for old_id in df_ed['id'].tolist():
            if old_id not in curr_ids:
                st_supabase.table("transactions").delete().eq("id", old_id).execute()
        
        # Sincroniza edições
        for _, row in edited_df.iterrows():
            st_supabase.table("transactions").update({
                "date": str(row['date']), "category": row['category'],
                "description": row['description'], "payment_method": row['payment_method'], "value": row['value']
            }).eq("id", row['id']).execute()
        st.success("Alterações salvas!")
        st.rerun()