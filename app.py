import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Marcia Theodoro - Gestão Pro",
    page_icon="👗",
    layout="wide"
)

# --- 2. ESTILO CSS (ABERTURA, RODAPÉ E INTERFACE) ---
st.markdown("""
    <style>
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    .intro-container { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 80vh; text-align: center; }
    .intro-title { font-size: 5rem; font-family: 'serif'; color: #8b5e3c; animation: blink 1.5s infinite; letter-spacing: 5px; text-transform: uppercase; }
    .intro-subtitle { font-size: 2rem; color: #a68a64; letter-spacing: 10px; text-transform: uppercase; animation: blink 1.5s infinite; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #fcfaf8; color: #8b5e3c; text-align: center; padding: 10px; font-weight: bold; z-index: 100; }
    .main { background-color: #fcfaf8; }
    div[data-testid="stMetricValue"] { color: #8b5e3c; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #8b5e3c !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE ABERTURA (5 SEGUNDOS) ---
if 'intro_visto' not in st.session_state:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div class="intro-container"><div class="intro-title">Márcia Theodoro</div><div class="intro-subtitle">Boutique</div></div>', unsafe_allow_html=True)
    time.sleep(5)
    st.session_state['intro_visto'] = True
    placeholder.empty()
    st.rerun()

# --- 4. CONEXÃO SUPABASE ---
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Erro: Configure as chaves nos Secrets do Streamlit.")
        st.stop()

supabase = init_connection()

# --- 5. FUNÇÕES DE DADOS E PDF ---
def get_data(tabela):
    try:
        res = supabase.table(tabela).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def gerar_pdf_cliente(nome, df_parc):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 20)
    pdf.set_text_color(139, 94, 60) 
    pdf.cell(0, 15, "MÁRCIA THEODORO BOUTIQUE", ln=True, align='C')
    pdf.set_font("helvetica", '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Extrato de Conta - Cliente: {nome}", ln=True, align='C')
    pdf.cell(0, 5, f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_fill_color(241, 237, 233)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(35, 10, "Vencimento", border=1, fill=True, align='C')
    pdf.cell(75, 10, "Descrição / Parcela", border=1, fill=True, align='C')
    pdf.cell(35, 10, "Valor", border=1, fill=True, align='C')
    pdf.cell(45, 10, "Situação", border=1, fill=True, align='C', ln=True)
    pdf.set_font("helvetica", '', 10)
    total_pendente = 0
    for _, row in df_parc.iterrows():
        status = "RECEBIDO" if row['pago'] else "PENDENTE"
        venc = pd.to_datetime(row['data_vencimento']).strftime('%d/%m/%Y')
        valor = f"R$ {row['valor_parcela']:,.2f}"
        pdf.cell(35, 10, venc, border=1, align='C')
        pdf.cell(75, 10, f"Parcela {row['numero_parcela']}", border=1)
        pdf.cell(35, 10, valor, border=1, align='R')
        pdf.cell(45, 10, status, border=1, align='C', ln=True)
        if not row['pago']: total_pendente += row['valor_parcela']
    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_text_color(139, 94, 60)
    pdf.cell(0, 10, f"SALDO TOTAL DEVEDOR: R$ {total_pendente:,.2f}", ln=True, align='R')
    return bytes(pdf.output())

# --- 6. CARREGAMENTO DE DADOS ---
df_clientes = get_data("clientes")
df_produtos = get_data("produtos")
df_vendas = get_data("vendas")
df_parcelas = get_data("parcelas")

# --- 7. INTERFACE PRINCIPAL ---
st.title("👗 Marcia Theodoro - Sistema de Gestão Pro")

tab_dash, tab_venda, tab_financeiro, tab_clientes, tab_estoque = st.tabs([
    "📊 Dashboard", "💰 Realizar Venda", "📉 Financeiro & PDF", "👤 Clientes", "📦 Estoque"
])

# --- ABA: DASHBOARD ---
with tab_dash:
    st.header("Resumo Estratégico")
    if not df_parcelas.empty:
        df_parcelas['data_vencimento'] = pd.to_datetime(df_parcelas['data_vencimento']).dt.date
        hoje = datetime.now().date()
        recebido = df_parcelas[df_parcelas['pago'] == True]['valor_parcela'].sum()
        a_receber = df_parcelas[df_parcelas['pago'] == False]['valor_parcela'].sum()
        atrasado = df_parcelas[(df_parcelas['pago'] == False) & (df_parcelas['data_vencimento'] < hoje)]['valor_parcela'].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Bruto", f"R$ {df_vendas['valor'].sum():,.2f}" if not df_vendas.empty else "0,00")
        c2.metric("Total Recebido", f"R$ {recebido:,.2f}")
        c3.metric("Contas a Receber", f"R$ {a_receber:,.2f}")
        c4.metric("Inadimplência", f"R$ {atrasado:,.2f}", delta_color="inverse")

# --- ABA: VENDAS (PREÇO AUTOMÁTICO E PARCELAMENTO) ---
with tab_venda:
    st.header("💰 Nova Venda")
    if not df_produtos.empty and not df_clientes.empty:
        lista_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
        prod_sel_txt = st.selectbox("1. Selecione a Mercadoria", lista_p)
        cod_p = prod_sel_txt.split(" - ")[0]
        prod_data = df_produtos[df_produtos['codigo'] == cod_p].iloc[0]
        preco_sugerido = float(prod_data['preco_venda'])
        estoque_atual = int(prod_data['quantidade_estoque'])

        with st.form("form_venda_final"):
            c_v1, c_v2 = st.columns(2)
            lista_c = {r['nome']: r['id'] for _, r in df_clientes.iterrows()}
            cliente_venda = c_v1.selectbox("2. Selecione o Cliente", list(lista_c.keys()))
            valor_final = c_v2.number_input("3. Valor da Venda (R$)", value=preco_sugerido)
            c_v3, c_v4 = st.columns(2)
            metodo = c_v3.selectbox("4. Pagamento", ["Crediário", "Pix", "Dinheiro", "Cartão"])
            qtd_parc = c_v4.number_input("5. Parcelas", min_value=1, value=1)
            data_inicial = st.date_input("6. Data do 1º Vencimento", value=datetime.now())
            if st.form_submit_button("🛒 FINALIZAR"):
                if estoque_atual > 0:
                    v_res = supabase.table("vendas").insert({"item": prod_sel_txt, "valor": valor_final, "metodo_pagamento": metodo}).execute()
                    v_id = v_res.data[0]['id']
                    valor_p = valor_final / qtd_parc
                    for i in range(qtd_parc):
                        venc = pd.to_datetime(data_inicial) + pd.DateOffset(months=i)
                        pago_status = True if metodo in ["Pix", "Dinheiro"] else False
                        supabase.table("parcelas").insert({
                            "venda_id": v_id, "cliente_id": lista_c[cliente_venda], "valor_parcela": valor_p,
                            "data_vencimento": venc.strftime('%Y-%m-%d'), "pago": pago_status, "numero_parcela": i+1, "metodo_pagamento": metodo
                        }).execute()
                    supabase.table("produtos").update({"quantidade_estoque": estoque_atual - 1}).eq("codigo", cod_p).execute()
                    st.success("Venda registrada!")
                    st.rerun()
                else: st.error("Produto sem estoque!")

# --- ABA: FINANCEIRO & PDF (CORREÇÃO DO KEYERROR AQUI) ---
with tab_financeiro:
    st.header("📉 Extratos e Baixas")
    if not df_parcelas.empty and not df_clientes.empty:
        # Merge explícito definindo sufixos para evitar ambiguidade na coluna 'id'
        df_fin = pd.merge(
            df_parcelas, 
            df_clientes[['id', 'nome']], 
            left_on='cliente_id', 
            right_on='id', 
            how='left',
            suffixes=('_parcela', '_cliente')
        )
        
        cli_sel = st.selectbox("Selecione o Cliente para Gerar PDF ou Dar Baixa", ["--"] + list(df_clientes['nome'].unique()))
        
        if cli_sel != "--":
            df_cli_parc = df_fin[df_fin['nome'] == cli_sel].sort_values('data_vencimento')
            try:
                pdf_bytes = gerar_pdf_cliente(cli_sel, df_cli_parc)
                st.download_button(label="📥 Baixar Extrato em PDF", data=pdf_bytes, file_name=f"extrato_{cli_sel.replace(' ', '_')}.pdf", mime="application/pdf")
            except Exception as e: st.error(f"Erro ao gerar PDF: {e}")
            
            st.divider()
            for _, r in df_cli_parc.iterrows():
                col_x1, col_x2 = st.columns([3, 1])
                status_icon = "✅" if r['pago'] else "⏳"
                col_x1.write(f"{status_icon} Parc {r['numero_parcela']} - Venc: {pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')} - **R$ {r['valor_parcela']:.2f}**")
                if not r['pago']:
                    # Corrigido: r['id'] virou r['id_parcela'] devido ao merge com sufixo
                    if col_x2.button("Receber", key=f"btn_{r['id_parcela']}"):
                        supabase.table("parcelas").update({"pago": True}).eq("id", r['id_parcela']).execute()
                        st.rerun()

# --- ABA: CLIENTES ---
with tab_clientes:
    with st.form("cad_cli_v5"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Nome")
        t = c2.text_input("Telefone")
        cp = c3.text_input("CPF")
        if st.form_submit_button("Salvar Cliente"):
            supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": cp}).execute(); st.rerun()
    st.dataframe(df_clientes[['nome', 'telefone', 'cpf']], use_container_width=True, hide_index=True)

# --- ABA: ESTOQUE ---
with tab_estoque:
    with st.form("cad_prod_v5"):
        e1, e2, e3, e4 = st.columns([1, 2, 1, 1])
        c_p = e1.text_input("Cód", value=str(len(df_produtos)+1).zfill(3))
        n_p = e2.text_input("Peça"); p_p = e3.number_input("Preço"); q_p = e4.number_input("Qtd", min_value=0, step=1)
        if st.form_submit_button("Cadastrar"):
            supabase.table("produtos").insert({"codigo": c_p, "nome": n_p, "preco_venda": p_p, "quantidade_estoque": q_p}).execute(); st.rerun()
    st.dataframe(df_produtos[['codigo', 'nome', 'preco_venda', 'quantidade_estoque']], use_container_width=True, hide_index=True)

# --- RODAPÉ ---
st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
