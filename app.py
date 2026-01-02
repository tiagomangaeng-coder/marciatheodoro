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

# --- 3. CONEXÃO E FUNÇÕES DE DADOS ---
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# Função com cache desativado para garantir dados novos após vendas
def load_all_data():
    vendas = supabase.table("vendas").select("*").order("data", desc=True).execute()
    clientes = supabase.table("clientes").select("*").execute()
    produtos = supabase.table("produtos").select("*").execute()
    parcelas = supabase.table("parcelas").select("*").execute()
    return pd.DataFrame(vendas.data), pd.DataFrame(clientes.data), pd.DataFrame(produtos.data), pd.DataFrame(parcelas.data)

# --- 4. FUNÇÕES DE PDF (PADRÃO BRASILEIRO) ---
def gerar_pdf_financeiro_geral(df_cli, df_parc):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    pdf.cell(0, 10, "MÁRCIA THEODORO - RELATÓRIO FINANCEIRO GERAL", ln=True, align='C')
    pdf.set_font("helvetica", '', 10)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(80, 10, "Nome do Cliente", 1, 0, 'C', True)
    pdf.cell(50, 10, "Telefone", 1, 0, 'C', True)
    pdf.cell(60, 10, "Saldo Devedor (R$)", 1, 1, 'C', True)
    for _, cli in df_cli.sort_values('nome').iterrows():
        divida = df_parc[(df_parc['cliente_id'] == cli['id']) & (df_parc['pago'] == False)]['valor_parcela'].sum()
        pdf.cell(80, 10, str(cli['nome']), 1)
        pdf.cell(50, 10, str(cli['telefone']), 1)
        pdf.cell(60, 10, f"{divida:,.2f}", 1, 1, 'R')
    return bytes(pdf.output())

def gerar_pdf_cliente(nome, df_parc_cli):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    pdf.cell(0, 10, f"EXTRATO: {nome}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(40, 10, "Vencimento", 1); pdf.cell(80, 10, "Parcela", 1); pdf.cell(30, 10, "Valor", 1); pdf.cell(40, 10, "Status", 1, 1)
    pdf.set_font("helvetica", '', 10)
    for _, r in df_parc_cli.iterrows():
        data_br = pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')
        pdf.cell(40, 10, data_br, 1)
        pdf.cell(80, 10, f"Parc {r['numero_parcela']}", 1)
        pdf.cell(30, 10, f"{r['valor_parcela']:.2f}", 1)
        pdf.cell(40, 10, "PAGO" if r['pago'] else "PENDENTE", 1, 1)
    return bytes(pdf.output())

# --- 5. CARREGAMENTO INICIAL ---
df_vendas, df_clientes, df_produtos, df_parcelas = load_all_data()

# --- 6. INTERFACE ---
tab_dash, tab_venda, tab_financeiro, tab_clientes, tab_estoque = st.tabs(["📊 Dashboard", "🛒 Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque"])

# --- ABA: DASHBOARD (INTEGRAÇÃO TOTAL) ---
with tab_dash:
    st.header("📊 Resumo em Tempo Real")
    if not df_vendas.empty:
        df_vendas['data_br'] = pd.to_datetime(df_vendas['data']).dt.strftime('%d/%m/%Y')
        col1, col2, col3 = st.columns(3)
        col1.metric("Faturamento Total", f"R$ {df_vendas['valor'].sum():,.2f}")
        col2.metric("Vendas Realizadas", len(df_vendas))
        
        # Gráfico Horizontal
        fig = px.bar(df_vendas.groupby('metodo_pagamento')['valor'].sum().reset_index(), 
                     x='valor', y='metodo_pagamento', orientation='h', title="Faturamento por Método", color_discrete_sequence=['#8b5e3c'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada para exibir no Dashboard.")

# --- ABA: VENDA (CARRINHO E ATUALIZAÇÃO) ---
with tab_venda:
    st.header("🛒 Ponto de Venda")
    colv1, colv2 = st.columns([1, 2])
    with colv1:
        if not df_produtos.empty:
            lista_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
            p_sel = st.selectbox("Selecione a Peça", lista_p)
            p_dat = df_produtos[df_produtos['codigo'] == p_sel.split(" - ")[0]].iloc[0]
            v_un = st.number_input("Preço Unitário (R$)", value=float(p_dat['preco_venda']))
            q_it = st.number_input("Quantidade", min_value=1, value=1)
            if st.button("➕ Adicionar ao Carrinho"):
                if q_it <= p_dat['quantidade_estoque']:
                    st.session_state.carrinho.append({"codigo": p_dat['codigo'], "nome": p_dat['nome'], "qtd": q_it, "valor_total": v_un * q_it})
                    st.rerun()
                else: st.error("Estoque insuficiente!")
    with colv2:
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            st.table(df_cart[['nome', 'qtd', 'valor_total']])
            total_v = df_cart['valor_total'].sum()
            st.markdown(f"### Total: R$ {total_v:,.2f}")
            if st.button("🗑️ Esvaziar Carrinho"): st.session_state.carrinho = []; st.rerun()
            
            with st.form("fechar_venda_final"):
                cli_v = st.selectbox("Vender para:", list(df_clientes['nome'].unique()) if not df_clientes.empty else [])
                met = st.selectbox("Forma de Pagamento", ["Crediário", "Pix", "Dinheiro", "Cartão"])
                par = st.number_input("Número de Parcelas", min_value=1, value=1)
                dat_1 = st.date_input("Data do 1º Vencimento", value=date.today())
                if st.form_submit_button("✅ CONFIRMAR E ATUALIZAR"):
                    # 1. Salva Venda
                    itens_txt = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho])
                    res_v = supabase.table("vendas").insert({"item": itens_txt, "valor": total_v, "metodo_pagamento": met}).execute()
                    v_id = res_v.data[0]['id']
                    # 2. Gera Parcelas e Baixa Estoque
                    for i in range(par):
                        v_venc = pd.to_datetime(dat_1) + pd.DateOffset(months=i)
                        supabase.table("parcelas").insert({
                            "venda_id": v_id, "cliente_id": df_clientes[df_clientes['nome']==cli_v]['id'].values[0],
                            "valor_parcela": total_v/par, "data_vencimento": v_venc.strftime('%Y-%m-%d'),
                            "pago": True if met in ["Pix", "Dinheiro"] else False, "numero_parcela": i+1, "metodo_pagamento": met
                        }).execute()
                    for item in st.session_state.carrinho:
                        q_atual = df_produtos[df_produtos['codigo']==item['codigo']]['quantidade_estoque'].values[0]
                        supabase.table("produtos").update({"quantidade_estoque": int(q_atual - item['qtd'])}).eq("codigo", item['codigo']).execute()
                    
                    st.session_state.carrinho = []
                    st.success("Venda processada! Relatórios atualizados.")
                    time.sleep(1)
                    st.rerun()

# --- ABA: FINANCEIRO (FORMATO BRASILEIRO) ---
with tab_financeiro:
    st.header("📉 Financeiro")
    if not df_clientes.empty:
        st.download_button("📥 Baixar Relatório Geral de Devedores (PDF)", gerar_pdf_financeiro_geral(df_clientes, df_parcelas), "financeiro_geral.pdf")
        st.divider()
        df_fin = pd.merge(df_parcelas, df_clientes[['id', 'nome']], left_on='cliente_id', right_on='id', how='left', suffixes=('_parc', '_cli'))
        cli_sel = st.selectbox("Ver Extrato de Cliente", ["--"] + list(df_clientes['nome'].unique()))
        if cli_sel != "--":
            df_cli = df_fin[df_fin['nome'] == cli_sel].sort_values('data_vencimento')
            st.download_button("📥 Baixar Extrato PDF", gerar_pdf_cliente(cli_sel, df_cli), f"extrato_{cli_sel}.pdf")
            for _, r in df_cli.iterrows():
                dt_br = pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')
                c1, c2 = st.columns([3, 1])
                c1.write(f"Venc: {dt_br} | Parc {r['numero_parcela']} | **R$ {r['valor_parcela']:.2f}** | {'✅ PAGO' if r['pago'] else '⏳ PENDENTE'}")
                if not r['pago'] and c2.button("Baixa", key=f"bx_{r['id_parc']}"):
                    supabase.table("parcelas").update({"pago": True}).eq("id", r['id_parc']).execute(); st.rerun()

# --- ABA: CLIENTES E ESTOQUE ---
with tab_clientes:
    with st.form("cad_cli"):
        n, t, c = st.text_input("Nome"), st.text_input("WhatsApp"), st.text_input("CPF")
        if st.form_submit_button("Salvar Cliente"):
            supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": c}).execute(); st.rerun()
    st.dataframe(df_clientes[['nome', 'telefone', 'cpf']], use_container_width=True)

with tab_estoque:
    with st.form("cad_est"):
        cp, np = st.text_input("Cód"), st.text_input("Peça")
        pv, qi = st.number_input("Preço"), st.number_input("Qtd", min_value=0)
        if st.form_submit_button("Cadastrar"):
            supabase.table("produtos").insert({"codigo": cp, "nome": np, "preco_venda": pv, "quantidade_estoque": qi}).execute(); st.rerun()
    st.dataframe(df_produtos, use_container_width=True)

st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
