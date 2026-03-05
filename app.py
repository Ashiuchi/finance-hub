import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from streamlit_calendar import calendar
import plotly.express as px
from datetime import datetime
import re

# --- PASSO 1: CONFIGURAÇÃO ---
st.set_page_config(page_title="Finance Hub - Ashiuchi", layout="wide", page_icon="💸", initial_sidebar_state="expanded")

# --- PASSO 2: VISUAL PREMIUM ---
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

# --- PASSO 3: CONEXÃO SUPABASE ---
try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except Exception as e:
    st.error(f"Erro de Conexão: {e}"); st.stop()

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
            if res.data: st.session_state["user_email"] = res.data[0]["email"]; st.rerun()
    st.stop()

u_log = st.session_state["user_email"]

# --- PASSO 6: BARRA LATERAL (GRÁFICOS + TEMPLATES) ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", key="logout_btn", use_container_width=True):
        st.session_state.clear(); st.rerun()
    
    data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).execute().data
    if data_res:
        df_side = pd.DataFrame(data_res)
        df_gastos = df_side[df_side['value'] < 0].copy()
        if not df_gastos.empty:
            df_gastos['abs_value'] = df_gastos['value'].abs()
            st.markdown("---")
            st.caption("📊 DISTRIBUIÇÃO DE GASTOS")
            fig_p = px.pie(df_gastos, values='abs_value', names='category', hole=0.4)
            fig_p.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_p, use_container_width=True)

    st.markdown("---")
    st.caption("⚙️ GESTÃO DE TEMPLATES")
    with st.expander("➕ Novo Template"):
        with st.form("f_tmp", clear_on_submit=True):
            tn = st.text_input("Nome")
            tc = st.selectbox("Categoria", ["Alimentação", "Venda Scripts", "Transporte", "Certificações"])
            if st.form_submit_button("Salvar Template"):
                st_supabase.table("templates").insert([{"template_name": tn, "category": tc, "user_email": u_log}]).execute(); st.rerun()

# --- PASSO 7: GESTÃO E LANÇAMENTOS (CORRIGIDO) ---
st.title("📊 Painel Administrativo")
c1, c2 = st.columns([1, 2.5])

with c1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        cat = st.selectbox("Categoria", ["Alimentação", "Venda Scripts", "Transporte", "Lazer", "Contas Fixas", "Saúde", "Certificações"])
        fp = st.selectbox("Pagamento", ["Dinheiro", "Cartão Crédito", "Cartão Débito", "Alimentação"])
        v = st.number_input("Valor", min_value=0.0, step=0.01)
        
        # RESTAURADO: Opção de Gasto ou Receita
        t = st.radio("Tipo de Transação", ["Gasto", "Receita"])
        
        if st.form_submit_button("Lançar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([
                {"date": d.strftime("%Y-%m-%d"), "category": cat, "description": ds, 
                 "value": val_f, "payment_method": fp, "user_email": u_log}
            ]).execute(); st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Manutenção")
    id_edit = st.number_input("ID do Registro:", min_value=1, step=1)
    if st.button("🗑️ Deletar Registro"):
        st_supabase.table("transactions").delete().eq("id", id_edit).eq("user_email", u_log).execute(); st.rerun()

# --- PASSO 8: CALENDÁRIO COMERCIAL ---
with c2:
    if data_res:
        evs = [{"title": f"{i['description']} (R$ {abs(i['value']):.2f})", "start": i['date'], "color": "#ff4b4b" if i['value'] < 0 else "#28a745"} for i in data_res]
        calendar(events=evs, options={"height": 500, "headerToolbar": {"right": "dayGridMonth,listMonth"}}, key="cal_main")

# --- PASSO 9: GRÁFICO TENDÊNCIA E EXTRATO (LIMPO) ---
st.markdown("---")
if data_res:
    df = pd.DataFrame(data_res)
    # Formatação de data para evitar milissegundos no gráfico
    df['date_label'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')
    
    st.subheader("📈 Movimentação Mensal")
    fig_b = px.bar(df, x="date_label", y="value", color="payment_method", barmode="group")
    fig_b.update_xaxes(type='category') # Remove a escala de tempo com horas
    fig_b.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis_title=None)
    st.plotly_chart(fig_b, use_container_width=True)
    
    st.dataframe(df[['id', 'date', 'category', 'description', 'payment_method', 'value']], use_container_width=True, hide_index=True)