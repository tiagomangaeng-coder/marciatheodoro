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

# --- 2. ESTILO CSS (ABERTURA E INTERFACE) ---
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

# --- 3. LÓGICA DE ABERTURA ---
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
        st.error("Erro: Configure as chaves nos Secrets.")
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
    
    # Cabeçalho
    pdf.set_font("helvetica", 'B', 20)
    pdf.set_text_color(139, 94, 60) # Cor Marrom Boutique
    pdf.cell(0, 15, "MÁRCIA THEODORO BOUTIQUE", ln=True, align='C')
    
    pdf.set_font("helvetica", '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Extrato de Conta - Cliente: {nome}", ln=True, align='C')
    pdf.cell(0, 5, f"Data do Relatório: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)

    # Tabela
    pdf.set_fill_color(241, 237, 233)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(30, 10, "Vencimento", border=1, fill=True)
    pdf.cell(80, 10, "Item/Venda", border=1, fill=True)
    pdf.cell(30, 10, "Valor", border=1, fill=True)
    pdf.cell(50, 10, "Status", border=1, fill=True, ln=True)

    pdf.set_font("helvetica", '', 10)
    total_pendente = 0
    
    for _, row in df_parc.iterrows():
        status = "PAGO" if row['pago'] else "PENDENTE"
        venc = pd.to_datetime(row['data_vencimento']).strftime('%d/%m/%Y')
        valor = f"R$ {row['valor_parcela']:,.2f}"
        
        pdf.cell(30, 10, venc, border=1)
        pdf.cell(80, 10, f"Parc {row['numero_parcela']}", border=1)
        pdf.cell(30, 10, valor, border=1)
        pdf.cell(50, 10, status, border=1, ln=True)
        
        if not row['pago']:
            total_pendente += row['valor_parcela']

    pdf.ln(5)
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, f"VALOR TOTAL EM ABERTO: R$ {total_pendente:,.2f}", ln=True, align='R')
    
    return pdf.output()

# --- 6. CARREGAMENTO DE DADOS ---
df_clientes = get_data("clientes")
df_produtos = get_data("produtos")
df_vendas = get_data("vendas")
df_parcelas = get_data("parcelas")

# --- 7. INTERFACE POR ABAS ---
st.title("👗 Marcia Theodoro - Gestão Pro")

tab_dash, tab_venda, tab_financeiro, tab_clientes, tab_estoque = st.tabs([
    "📊 Dashboard", "💰 Vendas", "📉 Financeiro & PDF", "👤 Clientes", "📦 Estoque"
])

# --- ABA: DASHBOARD ---
with tab_dash:
    if not df_parcelas.empty:
        recebido = df_parcelas[df_parcelas['pago'] == True]['valor_parcela'].sum()
        a_receber = df_parcelas[df_parcelas['pago'] == False]['valor_parcela'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento", f"R$ {df_vendas['valor'].sum():,.2f}" if not df_vendas.empty else "0,00")
        c2.metric("Recebido", f"R$ {recebido:,.2f}")
        c3.metric("A Receber", f"R$ {a_receber:,.2f}")

# --- ABA: VENDAS (PARCELAMENTO INTELIGENTE) ---
with tab_venda:
    st.header("💰 Nova Venda")
    if not df_produtos.empty and not df_clientes.empty:
        lista_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
        prod_sel = st.selectbox("1. Escolha o Produto", lista_p)
        cod_p = prod_sel.split(" - ")[0]
        prod_data = df_produtos[df_produtos['codigo'] == cod_p].iloc[0]

        with st.form("form_venda_pdf"):
            c_v1, c_v2 = st.columns(2)
            cli_dic = {r['nome']: r['id'] for _, r in df_clientes.iterrows()}
            nome_cli = c_v1.selectbox("2. Cliente", list(cli_dic.keys()))
            valor_v = c_v2.number_input("3. Valor Final", value=float(prod_data['preco_venda']))
            
            c_v3, c_v4 = st.columns(2)
            metodo = c_v3.selectbox("4. Pagamento", ["Crediário", "Pix", "Dinheiro", "Cartão"])
            parc = c_v4.number_input("5. Parcelas", min_value=1, value=1)
            
            data_1 = st.date_input("6. Data do 1º Vencimento", value=datetime.now())
            
            if st.form_submit_button("🛒 FINALIZAR VENDA"):
                v_res = supabase.table("vendas").insert({"item": prod_sel, "valor": valor_v, "metodo_pagamento": metodo}).execute()
                v_id = v_res.data[0]['id']
                
                for i in range(parc):
                    venc = pd.to_datetime(data_1) + pd.DateOffset(months=i)
                    pago = True if metodo in ["Pix", "Dinheiro"] else False
                    supabase.table("parcelas").insert({
                        "venda_id": v_id, "cliente_id": cli_dic[nome_cli], "valor_parcela": valor_v/parc,
                        "data_vencimento": venc.strftime('%Y-%m-%d'), "pago": pago, "numero_parcela": i+1, "metodo_pagamento": metodo
                    }).execute()
                
                supabase.table("produtos").update({"quantidade_estoque": int(prod_data['quantidade_estoque']) - 1}).eq("codigo", cod_p).execute()
                st.success("Venda registrada com sucesso!")
                st.rerun()

# --- ABA: FINANCEIRO & PDF (NOVIDADE) ---
with tab_financeiro:
    st.header("📉 Financeiro e Comprovantes")
    if not df_parcelas.empty:
        df_fin = pd.merge(df_parcelas, df_clientes[['id', 'nome']], left_on='cliente_id', right_on='id', how='left')
        
        col_f1, col_f2 = st.columns([2, 1])
        
        with col_f1:
            cli_sel = st.selectbox("Selecione o Cliente para Ver Detalhes", ["--"] + list(df_clientes['nome'].unique()))
        
        if cli_sel != "--":
            df_cli_parc = df_fin[df_fin['nome'] == cli_sel].sort_values('data_vencimento')
            
            # BOTÃO DE PDF
            pdf_data = gerar_pdf_cliente(cli_sel, df_cli_parc)
            st.download_button(
                label="📥 Baixar Extrato em PDF",
                data=pdf_data,
                file_name=f"extrato_{cli_sel.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
            
            st.write(f"### Histórico de {cli_sel}")
            for _, row in df_cli_parc.iterrows():
                st.write(f"Venc: {pd.to_datetime(row['data_vencimento']).strftime('%d/%m/%Y')} | Parc {row['numero_parcela']} | **R$ {row['valor_parcela']:.2f}** | {'✅ Pago' if row['pago'] else '⏳ Pendente'}")
                if not row['pago']:
                    if st.button(f"Dar Baixa na Parcela {row['numero_parcela']}", key=f"p_{row['id']}"):
                        supabase.table("parcelas").update({"pago": True}).eq("id", row['id']).execute()
                        st.rerun()
                st.divider()

# --- ABA: CLIENTES ---
with tab_clientes:
    with st.form("cad_cli"):
        n_c = st.text_input("Nome")
        t_c = st.text_input("Telefone")
        c_c = st.text_input("CPF")
        if st.form_submit_button("Salvar Cliente"):
            supabase.table("clientes").insert({"nome": n_c, "telefone": t_c, "cpf": c_c}).execute()
            st.rerun()
    st.dataframe(df_clientes[['nome', 'telefone', 'cpf']], use_container_width=True, hide_index=True)

# --- ABA: ESTOQUE ---
with tab_estoque:
    with st.form("cad_p"):
        c1, c2, c3, c4 = st.columns([1,2,1,1])
        cd_p = c1.text_input("Cód", value=str(len(df_produtos)+1).zfill(3))
        nm_p = c2.text_input("Peça")
        pr_p = c3.number_input("Preço")
        qt_p = c4.number_input("Qtd", min_value=0, step=1)
        if st.form_submit_button("Salvar"):
            supabase.table("produtos").insert({"codigo": cd_p, "nome": nm_p, "preco_venda": pr_p, "quantidade_estoque": qt_p}).execute()
            st.rerun()
    st.dataframe(df_produtos, use_container_width=True, hide_index=True)

# --- RODAPÉ ---
st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
