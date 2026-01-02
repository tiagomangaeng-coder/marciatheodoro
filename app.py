import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import time
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Marcia Theodoro - Gestão Pro", page_icon="👗", layout="wide")

st.markdown("""
    <style>
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    .intro-container { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 80vh; text-align: center; }
    .intro-title { font-size: 5rem; font-family: 'serif'; color: #8b5e3c; animation: blink 1.5s infinite; letter-spacing: 5px; text-transform: uppercase; }
    .intro-subtitle { font-size: 2rem; color: #a68a64; letter-spacing: 10px; text-transform: uppercase; animation: blink 1.5s infinite; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #fcfaf8; color: #8b5e3c; text-align: center; padding: 10px; font-weight: bold; z-index: 100; }
    .stTabs [aria-selected="true"] { background-color: #8b5e3c !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE ABERTURA ---
if 'intro_visto' not in st.session_state:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div class="intro-container"><div class="intro-title">Márcia Theodoro</div><div class="intro-subtitle">Boutique</div></div>', unsafe_allow_html=True)
    time.sleep(5)
    st.session_state['intro_visto'] = True
    placeholder.empty()
    st.rerun()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- 3. CONEXÃO E DADOS ---
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

def load_data():
    try:
        v = supabase.table("vendas").select("*").order("data", desc=True).execute()
        c = supabase.table("clientes").select("*").order("nome").execute()
        p = supabase.table("produtos").select("*").order("codigo").execute()
        par = supabase.table("parcelas").select("*").execute()
        return pd.DataFrame(v.data), pd.DataFrame(c.data), pd.DataFrame(p.data), pd.DataFrame(par.data)
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 4. FUNÇÕES DE PDF ---
def gerar_pdf_financeiro(df_cli, df_parc, tipo="Consolidado"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    titulo = f"RELATÓRIO FINANCEIRO {tipo.upper()}"
    pdf.cell(0, 10, titulo, ln=True, align='C')
    pdf.set_font("helvetica", '', 10)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)

    if tipo == "Consolidado":
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(80, 10, "Cliente", 1, 0, 'C', True)
        pdf.cell(50, 10, "WhatsApp", 1, 0, 'C', True)
        pdf.cell(60, 10, "Total Pendente (R$)", 1, 1, 'C', True)
        if not df_cli.empty:
            for _, cli in df_cli.iterrows():
                dev = df_parc[(df_parc['cliente_id'] == cli['id']) & (df_parc['pago'] == False)]['valor_parcela'].sum() if not df_parc.empty else 0
                if dev > 0:
                    pdf.cell(80, 10, str(cli['nome']), 1)
                    pdf.cell(50, 10, str(cli['telefone']), 1)
                    pdf.cell(60, 10, f"{dev:,.2f}", 1, 1, 'R')
    else:
        if not df_cli.empty:
            for _, cli in df_cli.iterrows():
                parc_cli = df_parc[df_parc['cliente_id'] == cli['id']].sort_values('data_vencimento') if not df_parc.empty else pd.DataFrame()
                if not parc_cli.empty:
                    pdf.set_font("helvetica", 'B', 12)
                    pdf.cell(0, 10, f"Cliente: {cli['nome']}", ln=True)
                    for _, p in parc_cli.iterrows():
                        dt = pd.to_datetime(p['data_vencimento']).strftime('%d/%m/%Y')
                        pdf.set_font("helvetica", '', 10)
                        pdf.cell(40, 8, dt, 1); pdf.cell(80, 8, f"Parc {p['numero_parcela']}", 1); pdf.cell(40, 8, f"{p['valor_parcela']:.2f}", 1, 1)
                    pdf.ln(5)
    return bytes(pdf.output())

# --- 5. CARREGAMENTO ---
df_v, df_c, df_p, df_par = load_data()

# --- 6. INTERFACE ---
tab_venda, tab_financeiro, tab_clientes, tab_estoque, tab_dash = st.tabs(["🛒 Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque", "📊 Dashboard"])

# --- ABA VENDAS ---
with tab_venda:
    st.header("🛍️ PDV")
    c_add, c_res = st.columns([1, 1.5])
    with c_add:
        if not df_p.empty:
            it_l = [f"{r['codigo']} - {r['nome']}" for _, r in df_p.iterrows()]
            it_s = st.selectbox("Produto", it_l)
            peca = df_p[df_p['codigo'] == it_s.split(" - ")[0]].iloc[0]
            pr_u = st.number_input("Preço", value=float(peca['preco_venda']))
            qt_v = st.number_input("Quantidade", min_value=1, step=1)
            if st.button("➕ Adicionar"):
                st.session_state.carrinho.append({"cod": peca['codigo'], "nome": peca['nome'], "qtd": int(qt_v), "pr": pr_u, "tot": pr_u * qt_v})
                st.rerun()
    with c_res:
        if st.session_state.carrinho:
            df_ct = pd.DataFrame(st.session_state.carrinho)
            st.table(df_ct[['nome', 'qtd', 'pr', 'tot']])
            total_v = df_ct['tot'].sum()
            if st.button("🗑️ Limpar"): st.session_state.carrinho = []; st.rerun()
            with st.form("fechar"):
                cli_v = st.selectbox("Cliente", list(df_c['nome'].unique()) if not df_c.empty else [])
                met = st.selectbox("Metodo", ["Crediário", "Pix", "Dinheiro", "Cartão"])
                par = st.number_input("Parcelas", min_value=1, value=1)
                dat = st.date_input("1º Vencimento", value=date.today())
                if st.form_submit_button("✅ FINALIZAR"):
                    txt_i = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho])
                    vid = supabase.table("vendas").insert({"item": txt_i, "valor": total_v, "metodo_pagamento": met}).execute().data[0]['id']
                    for n in range(par):
                        dv = pd.to_datetime(dat) + pd.DateOffset(months=n)
                        supabase.table("parcelas").insert({"venda_id": vid, "cliente_id": df_c[df_c['nome']==cli_v]['id'].values[0], "valor_parcela": total_v/par, "data_vencimento": dv.strftime('%Y-%m-%d'), "pago": (met in ["Pix", "Dinheiro"]), "numero_parcela": n+1, "metodo_pagamento": met}).execute()
                    st.session_state.carrinho = []; st.success("Venda salva!"); time.sleep(1); st.rerun()

# --- ABA FINANCEIRO ---
with tab_financeiro:
    st.header("📉 Financeiro")
    t_r = st.radio("Relatório Geral", ["Consolidado", "Completo"], horizontal=True)
    if not df_c.empty:
        st.download_button(f"📥 Baixar Relatório", gerar_pdf_financeiro(df_c, df_par, t_r), "relatorio.pdf")
    st.divider()
    ops = ["--"] + list(df_c['nome'].unique()) if not df_c.empty else ["--"]
    cli_f = st.selectbox("Ver Extrato", ops)
    if cli_f != "--":
        df_f = pd.merge(df_par, df_c[['id', 'nome']], left_on='cliente_id', right_on='id', suffixes=('_p', '_c'))
        df_cli = df_f[df_f['nome'] == cli_f].sort_values('data_vencimento')
        for _, r in df_cli.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.write(f"{pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')} - R$ {r['valor_parcela']:.2f}")
            if not r['pago'] and c2.button("Baixa", key=f"bx_{r['id_p']}"):
                supabase.table("parcelas").update({"pago": True}).eq("id", r['id_p']).execute(); st.rerun()

# --- ABA CLIENTES ---
with tab_clientes:
    st.header("👤 Clientes")
    with st.form("c_cli", clear_on_submit=True):
        n = st.text_input("Nome")
        t = st.text_input("Whats")
        if st.form_submit_button("Salvar"):
            supabase.table("clientes").insert({"nome": n, "telefone": t}).execute(); st.rerun()
    st.dataframe(df_c, use_container_width=True)

# --- ABA ESTOQUE (ONDE O ERRO OCORREU) ---
with tab_estoque:
    st.header("📦 Estoque")
    with st.form("cad_e", clear_on_submit=True):
        e1, e2, e3, e4 = st.columns(4)
        cp = e1.text_input("Cód")
        np = e2.text_input("Peça")
        pv = e3.number_input("Preço", min_value=0.0)
        qi = e4.number_input("Qtd", min_value=0)
        
        if st.form_submit_button("Cadastrar Produto"):
            if cp and np:
                try:
                    # Garantindo que os dados numéricos sejam enviados como números
                    novo_produto = {
                        "codigo": str(cp),
                        "nome": str(np),
                        "preco_venda": float(pv),
                        "quantidade_estoque": int(qi)
                    }
                    supabase.table("produtos").insert(novo_produto).execute()
                    st.success("Produto cadastrado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")
            else:
                st.warning("Preencha Código e Nome.")
    
    if not df_p.empty:
        for _, pr in df_p.iterrows():
            with st.expander(f"{pr['codigo']} - {pr['nome']}"):
                if st.button("🗑️ Excluir", key=f"del_{pr['id']}"):
                    supabase.table("produtos").delete().eq("id", pr['id']).execute(); st.rerun()

# --- ABA DASHBOARD ---
with tab_dash:
    if not df_v.empty:
        st.metric("Faturamento", f"R$ {df_v['valor'].sum():,.2f}")
        st.plotly_chart(px.bar(df_v.groupby('metodo_pagamento')['valor'].sum().reset_index(), x='valor', y='metodo_pagamento', orientation='h', color_discrete_sequence=['#8b5e3c']), use_container_width=True)

st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
