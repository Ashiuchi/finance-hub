import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from streamlit_calendar import calendar
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO E VISUAL ---
st.set_page_config(page_title="Finance Hub - Ashiuchi", layout="wide", initial_sidebar_state="expanded")

bg_img = "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1920&q=80"
st.markdown(f"""
    <style>
    .stApp {{ background-image: url("{bg_img}"); background-attachment: fixed; background-size: cover; }}
    .stApp > header, .stApp > div {{ background-color: rgba(14, 17, 23, 0.85); }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
st_supabase = st.connection("supabase", type=SupabaseConnection)

# --- ACESSO ---
if "user_email" not in st.session_state:
    el, pl = st.text_input("E-mail"), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = st_supabase.table("app_users").select("email").eq("email", el).eq("password", pl).execute()
        if res.data: st.session_state["user_email"] = res.data[0]["email"]; st.rerun()
    st.stop()

u_log = st.session_state["user_email"]

# --- BUSCA DE DADOS (TRANSAÇÕES + TEMPLATES) ---
data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).execute().data
temp_res = st_supabase.table("templates").select("*").eq("user_email", u_log).execute().data

# --- BARRA LATERAL (GRÁFICOS) ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", use_container_width=True): st.session_state.clear(); st.rerun()
    
    if data_res:
        df_side = pd.DataFrame(data_res)
        df_g = df_side[df_side['value'] < 0].copy()
        if not df_g.empty:
            df_g['abs_v'] = df_g['value'].abs()
            fig_p = px.pie(df_g, values='abs_v', names='category', hole=0.4)
            fig_p.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_p, use_container_width=True)

# --- PAINEL PRINCIPAL ---
st.title("📊 Gestão Integrada")
c1, c2 = st.columns([1, 2.5])

with c1:
    st.subheader("➕ Novo Registro")
    with st.form("f_add", clear_on_submit=True):
        d = st.date_input("Data", datetime.now())
        ds = st.text_input("Descrição")
        cat = st.selectbox("Categoria", ["Alimentação", "Venda Scripts", "Transporte", "Certificações", "Infra"])
        fp = st.selectbox("Pagamento", ["Dinheiro", "Cartão Crédito", "Cartão Débito", "Pix"])
        v = st.number_input("Valor", step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Lançar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "category": cat, "description": ds, "value": val_f, "payment_method": fp, "user_email": u_log}]).execute(); st.rerun()

# --- CALENDÁRIO (INCORPORANDO TEMPLATES) ---
with c2:
    events = []
    # Transações Reais
    if data_res:
        for i in data_res:
            events.append({"title": f"✅ {i['description']}", "start": i['date'], "color": "#ff4b4b" if i['value'] < 0 else "#28a745"})
    
    # Templates (Previsão) - Aparecem no dia atual para sinalizar disponibilidade
    if temp_res:
        for t in temp_res:
            events.append({"title": f"📝 Sugestão: {t['template_name']}", "start": datetime.now().strftime("%Y-%m-%d"), "color": "#ffc107"})
            
    calendar(events=events, options={"height": 450}, key="cal_main")

# --- TABELA EDITÁVEL COM DROPDOWN ---
st.markdown("---")
if data_res:
    df_ed = pd.DataFrame(data_res)
    st.subheader("📂 Extrato e Manutenção")
    
    # Configuração de Colunas com Dropdown
    edited_df = st.data_editor(
        df_ed[['id', 'date', 'category', 'description', 'payment_method', 'value']],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "category": st.column_config.SelectboxColumn(
                "Categoria",
                options=["Alimentação", "Venda Scripts", "Transporte", "Certificações", "Infra"],
                required=True,
            ),
            "payment_method": st.column_config.SelectboxColumn(
                "Pagamento",
                options=["Dinheiro", "Cartão Crédito", "Cartão Débito", "Pix"],
                required=True,
            )
        },
        key="editor"
    )

    if st.button("💾 Sincronizar Alterações"):
        # Sincronização de Deletados e Editados (Lógica simplificada para performance)
        curr_ids = edited_df['id'].tolist()
        for old_id in df_ed['id'].tolist():
            if old_id not in curr_ids:
                st_supabase.table("transactions").delete().eq("id", old_id).execute()
        
        for _, row in edited_df.iterrows():
            st_supabase.table("transactions").update({
                "date": str(row['date']), "category": row['category'],
                "description": row['description'], "payment_method": row['payment_method'], "value": row['value']
            }).eq("id", row['id']).execute()
        st.rerun()