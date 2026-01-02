import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Marcia Theodoro - Gestão Pro", page_icon="👗", layout="wide")

# --- 2. ESTILO CSS ---
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

# --- 3. LÓGICA DE ABERTURA ---
if 'intro_visto' not in st.session_state:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div class="intro-container"><div class="intro-title">Márcia Theodoro</div><div class="intro-subtitle">Boutique</div></div>', unsafe_allow_html=True)
    time.sleep(5)
    st.session_state['intro_visto'] = True
    placeholder.empty()
    st.rerun()

# Inicializa o Carrinho de Compras
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- 4. CONEXÃO E DADOS ---
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

def get_data(tabela):
    res = supabase.table(tabela).select("*").execute()
    return pd.DataFrame(res.data)

# --- 5. FUNÇÕES DE PDF ---
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
    
    # Tabela de parcelas
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 10, "Vencimento", 1, 0, 'C', True)
    pdf.cell(80, 10, "Parcela", 1, 0, 'C', True)
    pdf.cell(30, 10, "Valor", 1, 0, 'C', True)
    pdf.cell(40, 10, "Status", 1, 1, 'C', True)
    
    total_devedor = 0
    for _, r in df_parc.iterrows():
        v = f"R$ {r['valor_parcela']:.2f}"
        s = "PAGO" if r['pago'] else "PENDENTE"
        pdf.cell(40, 10, str(r['data_vencimento']), 1, 0, 'C')
        pdf.cell(80, 10, f"Parc {r['numero_parcela']}", 1, 0, 'C')
        pdf.cell(30, 10, v, 1, 0, 'C')
        pdf.cell(40, 10, s, 1, 1, 'C')
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
    pdf.cell(0, 10, "MÁRCIA THEODORO BOUTIQUE - RELATÓRIO GERAL DE CLIENTES", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(80, 10, "Nome", 1, 0, 'C')
    pdf.cell(50, 10, "Telefone", 1, 0, 'C')
    pdf.cell(60, 10, "CPF", 1, 1, 'C')
    
    pdf.set_font("helvetica", '', 10)
    for _, r in df_clientes.iterrows():
        pdf.cell(80, 10, str(r['nome']), 1)
        pdf.cell(50, 10, str(r['telefone']), 1)
        pdf.cell(60, 10, str(r['cpf']), 1, 1)
        
    return bytes(pdf.output())

# --- 6. CARREGAMENTO ---
df_clientes = get_data("clientes")
df_produtos = get_data("produtos")
df_parcelas = get_data("parcelas")
df_vendas = get_data("vendas")

# --- 7. INTERFACE ---
st.title("👗 Marcia Theodoro - PDV Avançado")

tab_venda, tab_financeiro, tab_clientes, tab_estoque, tab_dash = st.tabs([
    "🛒 Carrinho/Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque", "📊 Dash"
])

# --- ABA: VENDAS (MULTI-PRODUTOS) ---
with tab_venda:
    st.header("🛍️ PDV - Carrinho de Compras")
    
    col_v1, col_v2 = st.columns([1, 2])
    
    with col_v1:
        st.subheader("Adicionar Item")
        lista_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
        prod_sel = st.selectbox("Selecione o Produto", lista_p)
        
        cod_p = prod_sel.split(" - ")[0]
        p_data = df_produtos[df_produtos['codigo'] == cod_p].iloc[0]
        
        qtd_item = st.number_input("Quantidade", min_value=1, value=1)
        valor_un = st.number_input("Preço Unitário (R$)", value=float(p_data['preco_venda']))
        
        if st.button("➕ Adicionar ao Carrinho"):
            if qtd_item > p_data['quantidade_estoque']:
                st.error("Estoque insuficiente!")
            else:
                st.session_state.carrinho.append({
                    "codigo": cod_p,
                    "nome": p_data['nome'],
                    "qtd": qtd_item,
                    "valor_total": valor_un * qtd_item
                })
                st.toast(f"{p_data['nome']} adicionado!")

    with col_v2:
        st.subheader("Carrinho Atual")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            st.table(df_cart)
            total_venda = df_cart['valor_total'].sum()
            st.markdown(f"### Total: R$ {total_venda:.2f}")
            
            if st.button("🗑️ Limpar Carrinho"):
                st.session_state.carrinho = []
                st.rerun()
                
            st.divider()
            st.subheader("Finalizar Venda")
            with st.form("finalizar_venda"):
                lista_c_dic = {r['nome']: r['id'] for _, r in df_clientes.iterrows()}
                cli_venda = st.selectbox("Escolha o Cliente", list(lista_c_dic.keys()))
                metodo = st.selectbox("Pagamento", ["Crediário", "Pix", "Dinheiro", "Cartão"])
                parc = st.number_input("Parcelas", min_value=1, value=1)
                data_v = st.date_input("1º Vencimento", value=datetime.now())
                
                if st.form_submit_button("✅ CONFIRMAR VENDA"):
                    itens_str = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho])
                    v_res = supabase.table("vendas").insert({"item": itens_str, "valor": total_venda, "metodo_pagamento": metodo}).execute()
                    v_id = v_res.data[0]['id']
                    
                    # Parcelas e Estoque
                    valor_p = total_venda / parc
                    for i in range(parc):
                        venc = pd.to_datetime(data_v) + pd.DateOffset(months=i)
                        pago = True if metodo in ["Pix", "Dinheiro"] else False
                        supabase.table("parcelas").insert({
                            "venda_id": v_id, "cliente_id": lista_c_dic[cli_venda], "valor_parcela": valor_p,
                            "data_vencimento": venc.strftime('%Y-%m-%d'), "pago": pago, "numero_parcela": i+1, "metodo_pagamento": metodo
                        }).execute()
                    
                    for item in st.session_state.carrinho:
                        est_atual = df_produtos[df_produtos['codigo'] == item['codigo']]['quantidade_estoque'].values[0]
                        supabase.table("produtos").update({"quantidade_estoque": int(est_atual - item['qtd'])}).eq("codigo", item['codigo']).execute()
                    
                    st.session_state.carrinho = []
                    st.success("Venda finalizada com sucesso!")
                    st.rerun()
        else:
            st.info("Carrinho vazio.")

# --- ABA: FINANCEIRO ---
with tab_financeiro:
    st.header("📉 Financeiro")
    if not df_parcelas.empty:
        df_fin = pd.merge(df_parcelas, df_clientes[['id', 'nome']], left_on='cliente_id', right_on='id', how='left', suffixes=('_p', '_c'))
        
        cli_sel = st.selectbox("Verificar Cliente", ["--"] + list(df_clientes['nome'].unique()))
        if cli_sel != "--":
            df_cli = df_fin[df_fin['nome'] == cli_sel].sort_values('data_vencimento')
            st.download_button("📥 Baixar PDF Individual", gerar_pdf_cliente(cli_sel, df_cli), f"extrato_{cli_sel}.pdf")
            
            for _, r in df_cli.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"Parc {r['numero_parcela']} - Venc: {r['data_vencimento']} - R$ {r['valor_parcela']:.2f}")
                if not r['pago'] and col2.button("Receber", key=f"rec_{r['id_p']}"):
                    supabase.table("parcelas").update({"pago": True}).eq("id", r['id_p']).execute()
                    st.rerun()

# --- ABA: CLIENTES (RELATÓRIO GERAL) ---
with tab_clientes:
    st.header("👤 Gestão de Clientes")
    
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        with st.form("cad_cli"):
            n = st.text_input("Nome")
            t = st.text_input("WhatsApp")
            c = st.text_input("CPF")
            if st.form_submit_button("Salvar Cliente"):
                supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": c}).execute()
                st.rerun()
                
    with col_c2:
        st.subheader("Relatórios")
        if not df_clientes.empty:
            pdf_geral = gerar_pdf_geral_clientes(df_clientes)
            st.download_button("📥 Baixar Relatório Geral de Clientes (PDF)", pdf_geral, "relatorio_geral_clientes.pdf")

    st.dataframe(df_clientes[['nome', 'telefone', 'cpf']], use_container_width=True)

# --- ABA: ESTOQUE ---
with tab_estoque:
    st.header("📦 Estoque")
    with st.form("cad_prod"):
        e1, e2, e3, e4 = st.columns([1,2,1,1])
        c_p = e1.text_input("Cód", value=str(len(df_produtos)+1).zfill(3))
        n_p = e2.text_input("Peça")
        p_p = e3.number_input("Preço")
        q_p = e4.number_input("Qtd", min_value=0, step=1)
        if st.form_submit_button("Cadastrar"):
            supabase.table("produtos").insert({"codigo": c_p, "nome": n_p, "preco_venda": p_p, "quantidade_estoque": q_p}).execute()
            st.rerun()
    st.dataframe(df_produtos, use_container_width=True)

# --- ABA: DASHBOARD ---
with tab_dash:
    if not df_vendas.empty:
        st.metric("Faturamento Total", f"R$ {df_vendas['valor'].sum():,.2f}")
        fig = px.bar(df_vendas, x='metodo_pagamento', y='valor', title="Vendas por Método")
        st.plotly_chart(fig, use_container_width=True)

# RODAPÉ
st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
