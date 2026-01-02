import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime
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

# Inicializa o Carrinho
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- 3. CONEXÃO E DADOS ---
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

def get_data(tabela):
    res = supabase.table(tabela).select("*").execute()
    return pd.DataFrame(res.data)

# --- 4. FUNÇÕES DE PDF ---
def gerar_pdf_cliente(nome, df_parc):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    pdf.cell(0, 10, "MÁRCIA THEODORO BOUTIQUE - EXTRATO INDIVIDUAL", ln=True, align='C')
    pdf.set_font("helvetica", '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Cliente: {nome}", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 10, "Vencimento", 1, 0, 'C', True)
    pdf.cell(80, 10, "Parcela", 1, 0, 'C', True)
    pdf.cell(30, 10, "Valor", 1, 0, 'C', True)
    pdf.cell(40, 10, "Status", 1, 1, 'C', True)
    total_devedor = 0
    for _, r in df_parc.iterrows():
        pdf.cell(40, 10, str(r['data_vencimento']), 1, 0, 'C')
        pdf.cell(80, 10, f"Parc {r['numero_parcela']}", 1, 0, 'C')
        pdf.cell(30, 10, f"R$ {r['valor_parcela']:.2f}", 1, 0, 'C')
        pdf.cell(40, 10, "PAGO" if r['pago'] else "PENDENTE", 1, 1, 'C')
        if not r['pago']: total_devedor += r['valor_parcela']
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL PENDENTE: R$ {total_devedor:.2f}", align='R')
    return bytes(pdf.output())

def gerar_pdf_geral_clientes(df_clientes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    pdf.cell(0, 10, "MÁRCIA THEODORO BOUTIQUE - LISTA GERAL DE CLIENTES", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(80, 10, "Nome", 1, 0, 'C'); pdf.cell(50, 10, "Telefone", 1, 0, 'C'); pdf.cell(60, 10, "CPF", 1, 1, 'C')
    pdf.set_font("helvetica", '', 10)
    for _, r in df_clientes.sort_values('nome').iterrows():
        pdf.cell(80, 10, str(r['nome']), 1); pdf.cell(50, 10, str(r['telefone']), 1); pdf.cell(60, 10, str(r['cpf']), 1, 1)
    return bytes(pdf.output())

# --- 5. CARREGAMENTO ---
df_clientes = get_data("clientes")
df_produtos = get_data("produtos")
df_parcelas = get_data("parcelas")
df_vendas = get_data("vendas")

# --- 6. INTERFACE ---
st.title("👗 Marcia Theodoro - Sistema Pro")
tab_venda, tab_financeiro, tab_clientes, tab_estoque, tab_dash = st.tabs(["🛒 Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque", "📊 Dashboard"])

# --- ABA: VENDAS ---
with tab_venda:
    st.header("🛍️ Realizar Venda")
    col_v1, col_v2 = st.columns([1, 2])
    
    with col_v1:
        st.subheader("Adicionar Itens")
        if not df_produtos.empty:
            lista_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
            prod_sel = st.selectbox("Escolha o Produto", lista_p)
            p_data = df_produtos[df_produtos['codigo'] == prod_sel.split(" - ")[0]].iloc[0]
            
            valor_un = st.number_input("Preço Unitário (R$)", value=float(p_data['preco_venda']))
            qtd_item = st.number_input("Quantidade", min_value=1, value=1)
            
            if st.button("➕ Adicionar ao Carrinho"):
                if qtd_item > p_data['quantidade_estoque']: st.error("Estoque insuficiente!")
                else:
                    st.session_state.carrinho.append({"codigo": p_data['codigo'], "nome": p_data['nome'], "qtd": qtd_item, "valor_total": valor_un * qtd_item})
                    st.toast("Adicionado!"); st.rerun()
        else: st.warning("Cadastre produtos.")

    with col_v2:
        st.subheader("Carrinho / Finalização")
        if st.session_state.carrinho:
            st.table(pd.DataFrame(st.session_state.carrinho)[['nome', 'qtd', 'valor_total']])
            total_v = sum(i['valor_total'] for i in st.session_state.carrinho)
            st.markdown(f"### Total: R$ {total_v:.2f}")
            
            if st.button("🗑️ Limpar"): st.session_state.carrinho = []; st.rerun()
                
            st.divider()
            if not df_clientes.empty:
                with st.form("fechar_venda"):
                    cli_dic = {r['nome']: r['id'] for _, r in df_clientes.sort_values('nome').iterrows()}
                    cli_venda = st.selectbox("Selecione o Cliente", list(cli_dic.keys()))
                    metodo = st.selectbox("Forma de Pagamento", ["Crediário", "Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"])
                    parc = st.number_input("Número de Parcelas", min_value=1, value=1)
                    data_v = st.date_input("Data do 1º Vencimento", value=datetime.now())
                    
                    if st.form_submit_button("✅ FINALIZAR VENDA"):
                        itens_txt = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho])
                        v_id = supabase.table("vendas").insert({"item": itens_txt, "valor": total_v, "metodo_pagamento": metodo}).execute().data[0]['id']
                        
                        v_parc = total_v / parc
                        for i in range(parc):
                            venc = pd.to_datetime(data_v) + pd.DateOffset(months=i)
                            pago_st = True if metodo in ["Pix", "Dinheiro"] else False
                            supabase.table("parcelas").insert({"venda_id": v_id, "cliente_id": cli_dic[cli_venda], "valor_parcela": v_parc, "data_vencimento": venc.strftime('%Y-%m-%d'), "pago": pago_st, "numero_parcela": i+1, "metodo_pagamento": metodo}).execute()
                        
                        for item in st.session_state.carrinho:
                            est_at = df_produtos[df_produtos['codigo'] == item['codigo']]['quantidade_estoque'].values[0]
                            supabase.table("produtos").update({"quantidade_estoque": int(est_at - item['qtd'])}).eq("codigo", item['codigo']).execute()
                        
                        st.session_state.carrinho = []; st.success("Venda realizada!"); time.sleep(1); st.rerun()
            else: st.error("Cadastre clientes.")
        else: st.info("Carrinho vazio.")

# --- ABAS FINANCEIRO, CLIENTES, ESTOQUE E DASHBOARD ---
with tab_financeiro:
    st.header("📉 Financeiro")
    if not df_parcelas.empty and not df_clientes.empty:
        df_f = pd.merge(df_parcelas, df_clientes[['id', 'nome']], left_on='cliente_id', right_on='id', how='left', suffixes=('_p', '_c'))
        cli_sel = st.selectbox("Filtrar Cliente", ["--"] + list(df_clientes['nome'].unique()))
        if cli_sel != "--":
            df_cli = df_f[df_f['nome'] == cli_sel].sort_values('data_vencimento')
            st.download_button("📥 PDF Extrato", gerar_pdf_cliente(cli_sel, df_cli), f"extrato_{cli_sel}.pdf")
            for _, r in df_cli.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"Venc: {r['data_vencimento']} | Parc {r['numero_parcela']} | **R$ {r['valor_parcela']:.2f}** | {'✅ PAGO' if r['pago'] else '⏳ PENDENTE'}")
                if not r['pago'] and col2.button("Baixa", key=f"bx_{r['id_p']}"):
                    supabase.table("parcelas").update({"pago": True}).eq("id", r['id_p']).execute(); st.rerun()

with tab_clientes:
    st.header("👤 Clientes")
    with st.form("c_cli", clear_on_submit=True):
        n, t, c = st.text_input("Nome"), st.text_input("WhatsApp"), st.text_input("CPF")
        if st.form_submit_button("Salvar"):
            if n: supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": c}).execute(); st.success("Salvo!"); time.sleep(1); st.rerun()
    if not df_clientes.empty:
        st.download_button("📥 PDF Geral Clientes", gerar_pdf_geral_clientes(df_clientes), "clientes.pdf")
        st.dataframe(df_clientes[['nome', 'telefone', 'cpf']], use_container_width=True)

with tab_estoque:
    st.header("📦 Estoque")
    with st.form("c_est", clear_on_submit=True):
        e1, e2, e3, e4 = st.columns([1,2,1,1])
        c_p = e1.text_input("Cód", value=str(len(df_produtos)+1).zfill(3))
        n_p, p_p, q_p = e2.text_input("Peça"), e3.number_input("Preço"), e4.number_input("Qtd", min_value=0, step=1)
        if st.form_submit_button("Cadastrar"):
            supabase.table("produtos").insert({"codigo": c_p, "nome": n_p, "preco_venda": p_p, "quantidade_estoque": q_p}).execute(); st.rerun()
    st.dataframe(df_produtos[['codigo', 'nome', 'preco_venda', 'quantidade_estoque']], use_container_width=True)

with tab_dash:
    st.header("📊 Dashboard")
    if not df_vendas.empty:
        st.metric("Faturamento", f"R$ {df_vendas['valor'].sum():,.2f}")
        st.plotly_chart(px.pie(df_vendas, values='valor', names='metodo_pagamento', title="Métodos de Pagamento", hole=0.3), use_container_width=True)

st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
