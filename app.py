import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import time
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Marcia Theodoro - Sistema Gestão Total", page_icon="👗", layout="wide")

st.markdown("""
    <style>
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    .intro-container { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 80vh; text-align: center; }
    .intro-title { font-size: 5rem; font-family: 'serif'; color: #8b5e3c; animation: blink 1.5s infinite; letter-spacing: 5px; text-transform: uppercase; }
    .intro-subtitle { font-size: 2rem; color: #a68a64; letter-spacing: 10px; text-transform: uppercase; animation: blink 1.5s infinite; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #fcfaf8; color: #8b5e3c; text-align: center; padding: 10px; font-weight: bold; z-index: 100; }
    .stTabs [aria-selected="true"] { background-color: #8b5e3c !important; color: white !important; }
    [data-testid="stMetricValue"] { color: #8b5e3c !important; font-size: 1.8rem; }
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
    v = supabase.table("vendas").select("*").order("data", desc=True).execute()
    c = supabase.table("clientes").select("*").order("nome").execute()
    p = supabase.table("produtos").select("*").order("codigo").execute()
    par = supabase.table("parcelas").select("*").execute()
    return pd.DataFrame(v.data), pd.DataFrame(c.data), pd.DataFrame(p.data), pd.DataFrame(par.data)

# --- 4. FUNÇÕES DE PDF ---
def gerar_pdf_financeiro(df_cli, df_parc, tipo="Consolidado"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    titulo = f"RELATÓRIO FINANCEIRO {'CONSOLIDADO' if tipo == 'Consolidado' else 'COMPLETO'}"
    pdf.cell(0, 10, titulo, ln=True, align='C')
    pdf.set_font("helvetica", '', 10)
    pdf.cell(0, 10, f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)

    if tipo == "Consolidado":
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(80, 10, "Cliente", 1, 0, 'C', True)
        pdf.cell(50, 10, "WhatsApp", 1, 0, 'C', True)
        pdf.cell(60, 10, "Total Pendente (R$)", 1, 1, 'C', True)
        for _, cli in df_cli.iterrows():
            dev = df_parc[(df_parc['cliente_id'] == cli['id']) & (df_parc['pago'] == False)]['valor_parcela'].sum()
            if dev > 0:
                pdf.cell(80, 10, str(cli['nome']), 1)
                pdf.cell(50, 10, str(cli['telefone']), 1)
                pdf.cell(60, 10, f"{dev:,.2f}", 1, 1, 'R')
    else:
        for _, cli in df_cli.iterrows():
            pdf.set_font("helvetica", 'B', 12)
            pdf.cell(0, 10, f"Cliente: {cli['nome']} - Tel: {cli['telefone']}", ln=True)
            pdf.set_font("helvetica", 'B', 9)
            pdf.cell(40, 8, "Vencimento", 1); pdf.cell(80, 8, "Parcela", 1); pdf.cell(30, 8, "Valor", 1); pdf.cell(40, 8, "Status", 1, 1)
            pdf.set_font("helvetica", '', 9)
            parc_cli = df_parc[df_parc['cliente_id'] == cli['id']].sort_values('data_vencimento')
            for _, p in parc_cli.iterrows():
                dt = pd.to_datetime(p['data_vencimento']).strftime('%d/%m/%Y')
                st_parc = "PAGO" if p['pago'] else "PENDENTE"
                pdf.cell(40, 8, dt, 1); pdf.cell(80, 8, f"Parc {p['numero_parcela']}", 1); pdf.cell(30, 8, f"{p['valor_parcela']:.2f}", 1); pdf.cell(40, 8, st_parc, 1, 1)
            pdf.ln(5)
    return bytes(pdf.output())

# --- 5. CARREGAMENTO ---
df_v, df_c, df_p, df_par = load_data()

# --- 6. INTERFACE ---
tab_dash, tab_venda, tab_financeiro, tab_clientes, tab_estoque = st.tabs(["📊 Dashboard", "🛒 Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque"])

# --- ABA DASHBOARD ---
with tab_dash:
    st.header("📊 Resumo Estratégico")
    if not df_v.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento", f"R$ {df_v['valor'].sum():,.2f}")
        c2.metric("A Receber", f"R$ {df_par[df_par['pago']==False]['valor_parcela'].sum():,.2f}")
        c3.metric("Ticket Médio", f"R$ {(df_v['valor'].sum()/len(df_v)):,.2f}")
        st.plotly_chart(px.bar(df_v.groupby('metodo_pagamento')['valor'].sum().reset_index(), x='valor', y='metodo_pagamento', orientation='h', color_discrete_sequence=['#8b5e3c']), use_container_width=True)

# --- ABA VENDAS (COM CARRINHO E EDIÇÃO/EXCLUSÃO) ---
with tab_venda:
    st.header("🛍️ Carrinho e Vendas Realizadas")
    v1, v2 = st.columns([1, 2])
    with v1:
        st.subheader("Carrinho")
        it = st.selectbox("Peça", [f"{r['codigo']} - {r['nome']}" for _, r in df_p.iterrows()])
        it_d = df_p[df_p['codigo'] == it.split(" - ")[0]].iloc[0]
        pr = st.number_input("Preço", value=float(it_d['preco_venda']))
        qt = st.number_input("Qtd", min_value=1, step=1)
        if st.button("➕ Adicionar"):
            st.session_state.carrinho.append({"cod": it_d['codigo'], "nome": it_d['nome'], "qtd": qt, "tot": pr*qt})
            st.rerun()
        if st.session_state.carrinho:
            st.write(pd.DataFrame(st.session_state.carrinho))
            if st.button("🗑️ Limpar"): st.session_state.carrinho = []; st.rerun()
            with st.form("f_venda"):
                cli = st.selectbox("Cliente", list(df_c['nome'].unique()))
                met = st.selectbox("Pagamento", ["Crediário", "Pix", "Dinheiro", "Cartão"])
                parc_n = st.number_input("Parcelas", min_value=1)
                venc1 = st.date_input("1º Vencimento")
                if st.form_submit_button("✅ FINALIZAR"):
                    tot_v = sum(i['tot'] for i in st.session_state.carrinho)
                    txt_i = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho])
                    vid = supabase.table("vendas").insert({"item": txt_i, "valor": tot_v, "metodo_pagamento": met}).execute().data[0]['id']
                    for i in range(parc_n):
                        dt_v = pd.to_datetime(venc1) + pd.DateOffset(months=i)
                        supabase.table("parcelas").insert({"venda_id": vid, "cliente_id": df_c[df_c['nome']==cli]['id'].values[0], "valor_parcela": tot_v/parc_n, "data_vencimento": dt_v.strftime('%Y-%m-%d'), "pago": (met in ["Pix", "Dinheiro"]), "numero_parcela": i+1, "metodo_pagamento": met}).execute()
                    st.session_state.carrinho = []; st.success("Venda salva!"); st.rerun()

    with v2:
        st.subheader("Histórico e Correções")
        for idx, row in df_v.iterrows():
            with st.expander(f"Venda {row['id']} - {row['item']} (R$ {row['valor']:.2f})"):
                n_it = st.text_input("Editar Itens", value=row['item'], key=f"it_{row['id']}")
                n_vl = st.number_input("Editar Valor", value=float(row['valor']), key=f"vl_{row['id']}")
                c_e, c_d = st.columns(2)
                if c_e.button("💾 Atualizar", key=f"up_v_{row['id']}"):
                    supabase.table("vendas").update({"item": n_it, "valor": n_vl}).eq("id", row['id']).execute(); st.rerun()
                if c_d.button("🗑️ Excluir Venda", key=f"del_v_{row['id']}"):
                    supabase.table("vendas").delete().eq("id", row['id']).execute(); st.rerun()

# --- ABA FINANCEIRO (RELATÓRIOS CONSOLIDADO/COMPLETO) ---
with tab_financeiro:
    st.header("📉 Gestão Financeira")
    tipo_rel = st.radio("Tipo de Relatório Geral", ["Consolidado", "Completo"], horizontal=True)
    st.download_button(f"📥 Baixar Relatório {tipo_rel}", gerar_pdf_financeiro(df_c, df_par, tipo_rel), f"financeiro_{tipo_rel.lower()}.pdf")
    st.divider()
    cli_f = st.selectbox("Selecionar Cliente para Baixa/Edição", ["--"] + list(df_c['nome'].unique()))
    if cli_f != "--":
        parc_c = pd.merge(df_par, df_c[['id', 'nome']], left_on='cliente_id', right_on='id', suffixes=('_p', '_c'))
        df_cli = parc_c[parc_c['nome'] == cli_f].sort_values('data_vencimento')
        for _, r in df_cli.iterrows():
            with st.container():
                c_a, c_b, c_c = st.columns([3, 1, 1])
                c_a.write(f"Parc {r['numero_parcela']} - {pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')} - R$ {r['valor_parcela']:.2f}")
                if not r['pago'] and c_b.button("Receber", key=f"bx_{r['id_p']}"):
                    supabase.table("parcelas").update({"pago": True}).eq("id", r['id_p']).execute(); st.rerun()
                if c_c.button("🗑️", key=f"del_p_{r['id_p']}"):
                    supabase.table("parcelas").delete().eq("id", r['id_p']).execute(); st.rerun()

# --- ABA CLIENTES (EDITAR/DELETAR) ---
with tab_clientes:
    st.header("👤 Gestão de Clientes")
    with st.form("c_cli"):
        n, t, cp = st.text_input("Nome"), st.text_input("Whats"), st.text_input("CPF")
        if st.form_submit_button("Salvar"):
            supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": cp}).execute(); st.rerun()
    for _, cli in df_c.iterrows():
        with st.expander(f"Cliente: {cli['nome']}"):
            en = st.text_input("Nome", value=cli['nome'], key=f"cn_{cli['id']}")
            et = st.text_input("WhatsApp", value=cli['telefone'], key=f"ct_{cli['id']}")
            ec = st.text_input("CPF", value=cli['cpf'], key=f"cc_{cli['id']}")
            c1, c2 = st.columns(2)
            if c1.button("💾 Atualizar", key=f"cu_{cli['id']}"):
                supabase.table("clientes").update({"nome": en, "telefone": et, "cpf": ec}).eq("id", cli['id']).execute(); st.rerun()
            if c2.button("🗑️ Excluir", key=f"cd_{cli['id']}"):
                supabase.table("clientes").delete().eq("id", cli['id']).execute(); st.rerun()

# --- ABA ESTOQUE (EDITAR/DELETAR) ---
with tab_estoque:
    st.header("📦 Gestão de Estoque")
    with st.form("c_prod"):
        e1, e2, e3, e4 = st.columns(4)
        c_c = e1.text_input("Cód"); c_n = e2.text_input("Peça"); c_p = e3.number_input("Preço"); c_q = e4.number_input("Qtd")
        if st.form_submit_button("Cadastrar"):
            supabase.table("produtos").insert({"codigo": c_c, "nome": c_n, "preco_venda": c_p, "quantidade_estoque": c_q}).execute(); st.rerun()
    for _, pr in df_p.iterrows():
        with st.expander(f"Cód {pr['codigo']} - {pr['nome']}"):
            en = st.text_input("Nome", value=pr['nome'], key=f"pn_{pr['id']}")
            ep = st.number_input("Preço", value=float(pr['preco_venda']), key=f"pp_{pr['id']}")
            eq = st.number_input("Qtd", value=int(pr['quantidade_estoque']), key=f"pq_{pr['id']}")
            c1, c2 = st.columns(2)
            if c1.button("💾 Atualizar", key=f"pu_{pr['id']}"):
                supabase.table("produtos").update({"nome": en, "preco_venda": ep, "quantidade_estoque": eq}).eq("id", pr['id']).execute(); st.rerun()
            if c2.button("🗑️ Excluir", key=f"pd_{pr['id']}"):
                supabase.table("produtos").delete().eq("id", pr['id']).execute(); st.rerun()

st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
