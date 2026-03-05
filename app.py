import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from streamlit_calendar import calendar
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO ---
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
try:
    st_supabase = st.connection("supabase", type=SupabaseConnection, 
                                url=st.secrets["connections"]["supabase"]["url"], 
                                key=st.secrets["connections"]["supabase"]["key"])
except: st.error("Erro de Conexão."); st.stop()

# --- ACESSO ---
if "user_email" not in st.session_state:
    el, pl = st.text_input("E-mail"), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = st_supabase.table("app_users").select("email").eq("email", el).eq("password", pl).execute()
        if res.data: st.session_state["user_email"] = res.data[0]["email"]; st.rerun()
    st.stop()

u_log = st.session_state["user_email"]

# --- BUSCA DE DADOS (TABELA ÚNICA) ---
data_res = st_supabase.table("transactions").select("*").eq("user_email", u_log).execute().data
today = datetime.now().date()

# --- SIDEBAR (GRÁFICO DE PIZZA) ---
with st.sidebar:
    st.subheader(f"👤 {u_log}")
    if st.button("🚪 Sair", use_container_width=True): st.session_state.clear(); st.rerun()
    if data_res:
        df_side = pd.DataFrame(data_res)
        df_g = df_side[df_side['value'] < 0].copy()
        if not df_g.empty:
            df_g['abs_v'] = df_g['value'].abs()
            st.markdown("---")
            st.caption("📊 GASTOS POR CATEGORIA")
            fig_p = px.pie(df_g, values='abs_v', names='category', hole=0.4)
            fig_p.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig_p, use_container_width=True)

# --- PAINEL PRINCIPAL ---
st.title("📊 Painel de Controle Unificado")
c1, c2 = st.columns([1, 2.5])

with c1:
    st.subheader("➕ Novo Lançamento")
    default_date = datetime.now()
    if "cal_date" in st.session_state:
        try: default_date = datetime.strptime(st.session_state["cal_date"], "%Y-%m-%d")
        except: pass
    with st.form("f_add", clear_on_submit=True):
        d = st.date_input("Data", default_date)
        ds = st.text_input("Descrição")
        cat = st.selectbox("Categoria", ["Alimentação", "Pet", "Transporte", "Lazer", "miscellaneous"])
        fp = st.selectbox("Pagamento", ["Dinheiro", "Cartão Crédito", "Cartão Débito", "Pix", "Alimentação"])
        v = st.number_input("Valor", step=0.01)
        t = st.radio("Tipo", ["Gasto", "Receita"])
        if st.form_submit_button("Confirmar"):
            val_f = -v if t == "Gasto" else v
            st_supabase.table("transactions").insert([{"date": d.strftime("%Y-%m-%d"), "category": cat, "description": ds, "value": val_f, "payment_method": fp, "user_email": u_log}]).execute(); st.rerun()

with c2:
    events = []
    if data_res:
        for i in data_res:
            event_date = datetime.strptime(i['date'], "%Y-%m-%d").date()
            # LÓGICA DE CORES: Futuro = Amarelo | Hoje/Passado = Vermelho/Verde
            if event_date > today:
                color = "#ffc107" # Amarelo para lançamentos futuros
            else:
                color = "#ff4b4b" if i['value'] < 0 else "#28a745"
            events.append({"title": f"{i['description']} (R$ {abs(i['value']):.2f})", "start": i['date'], "color": color})
    
    cal = calendar(events=events, options={"height": 450, "selectable": True}, key="cal_fin")
    if cal and "callback" in cal and cal["callback"] == "dateClick":
        st.session_state["cal_date"] = cal["dateClick"]["dateStr"].split("T")[0]; st.rerun()

# --- TABELA DE MANUTENÇÃO ÚNICA ---
st.markdown("---")
if data_res:
    df_f = pd.DataFrame(data_res)
    st.subheader("📂 Gestão de Lançamentos (Reais e Futuros)")
    
    # Cálculo de Previsão de Saldo
    total_ent = df_f[df_f['value'] > 0]['value'].sum()
    total_sai = df_f[df_f['value'] < 0]['value'].sum()
    st.metric("Saldo Previsto no Mês (Lançamentos Totais)", f"R$ {total_ent + total_sai:,.2f}", delta=f"R$ {total_ent:,.2f} Entradas")

    edited_df = st.data_editor(
        df_f[['id', 'date', 'category', 'description', 'payment_method', 'value']],
        use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "category": st.column_config.SelectboxColumn("Categoria", options=["Alimentação", "Pet", "Transporte", "Lazer", "miscellaneous"], required=True),
            "payment_method": st.column_config.SelectboxColumn("Pagamento", options=["Dinheiro", "Cartão Crédito", "Cartão Débito", "Pix", "Alimentação"], required=True),
            "date": st.column_config.DateColumn("Data", required=True)
        }, key="ed_unificado"
    )

    if st.button("💾 Sincronizar Tudo"):
        curr_ids = edited_df['id'].tolist()
        for old_id in df_f['id'].tolist():
            if old_id not in curr_ids: st_supabase.table("transactions").delete().eq("id", old_id).execute()
        for _, r in edited_df.iterrows():
            st_supabase.table("transactions").update({"date": str(r['date']), "category": r['category'], "description": r['description'], "payment_method": r['payment_method'], "value": r['value']}).eq("id", r['id']).execute()
        st.success("Painel atualizado!"); st.rerun()