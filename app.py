import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

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
        st.error("Erro: Verifique as chaves nos Secrets do Streamlit.")
        st.stop()

supabase = init_connection()

# --- 5. FUNÇÕES DE DADOS ---
def get_data(tabela):
    try:
        res = supabase.table(tabela).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# Carregamento de dados
df_clientes = get_data("clientes")
df_produtos = get_data("produtos")
df_vendas = get_data("vendas")
df_parcelas = get_data("parcelas")

# --- 6. INTERFACE POR ABAS ---
st.title("👗 Marcia Theodoro - Sistema de Gestão Pro")

tab_dash, tab_venda, tab_financeiro, tab_clientes, tab_estoque = st.tabs([
    "📊 Dashboard", "💰 Realizar Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque"
])

# --- ABA 1: DASHBOARD ---
with tab_dash:
    st.header("📊 Resumo Financeiro")
    if not df_parcelas.empty:
        df_parcelas['data_vencimento'] = pd.to_datetime(df_parcelas['data_vencimento']).dt.date
        hoje = datetime.now().date()
        
        recebido = df_parcelas[df_parcelas['pago'] == True]['valor_parcela'].sum()
        a_receber = df_parcelas[df_parcelas['pago'] == False]['valor_parcela'].sum()
        atrasado = df_parcelas[(df_parcelas['pago'] == False) & (df_parcelas['data_vencimento'] < hoje)]['valor_parcela'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Total", f"R$ {df_vendas['valor'].sum():,.2f}" if not df_vendas.empty else "0,00")
        c2.metric("Recebido", f"R$ {recebido:,.2f}")
        c3.metric("A Receber", f"R$ {a_receber:,.2f}")
        c4.metric("Atrasado", f"R$ {atrasado:,.2f}", delta_color="inverse")
    else:
        st.info("Aguardando dados para o dashboard.")

# --- ABA 2: REALIZAR VENDA (COM PARCELAMENTO INTELIGENTE) ---
with tab_venda:
    st.header("💰 Nova Venda")
    
    if df_produtos.empty or df_clientes.empty:
        st.warning("⚠️ Cadastre Clientes e Produtos antes de vender.")
    else:
        # Seleção do Produto (Fora do form para atualizar preço automático)
        lista_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
        prod_sel_txt = st.selectbox("1. Produto", lista_p)
        
        cod_p = prod_sel_txt.split(" - ")[0]
        prod_data = df_produtos[df_produtos['codigo'] == cod_p].iloc[0]
        
        with st.form("confirmar_venda_final", clear_on_submit=True):
            col_v1, col_v2 = st.columns(2)
            
            # Seleção do Cliente
            lista_c = {r['nome']: r['id'] for _, r in df_clientes.iterrows()}
            cliente_nome = col_v1.selectbox("2. Cliente", list(lista_c.keys()))
            
            # Preço Automático
            valor_venda = col_v2.number_input("3. Valor Final (R$)", value=float(prod_data['preco_venda']), format="%.2f")
            
            col_v3, col_v4 = st.columns(2)
            metodo_v = col_v3.selectbox("4. Pagamento", ["Crediário", "Pix", "Dinheiro", "Cartão"])
            parc_v = col_v4.number_input("5. Parcelas", min_value=1, value=1)
            
            # NOVA FUNCIONALIDADE: DATA DO PRIMEIRO PAGAMENTO
            data_primeira = st.date_input("6. Data do 1º Pagamento/Vencimento", value=datetime.now())
            
            if st.form_submit_button("🛒 FINALIZAR"):
                # 1. Registrar Venda
                v_res = supabase.table("vendas").insert({"item": prod_sel_txt, "valor": valor_venda, "metodo_pagamento": metodo_v}).execute()
                v_id = v_res.data[0]['id']
                
                # 2. Gerar Parcelas Automáticas
                valor_cada = valor_venda / parc_v
                for i in range(parc_v):
                    # Calcula o mês seguinte mantendo o dia usando pandas DateOffset
                    venc_p = pd.to_datetime(data_primeira) + pd.DateOffset(months=i)
                    pago_p = True if metodo_v in ["Pix", "Dinheiro"] else False
                    
                    supabase.table("parcelas").insert({
                        "venda_id": v_id, 
                        "cliente_id": lista_c[cliente_nome], 
                        "valor_parcela": valor_cada,
                        "data_vencimento": venc_p.strftime('%Y-%m-%d'), 
                        "pago": pago_p, 
                        "numero_parcela": i+1, 
                        "metodo_pagamento": metodo_v
                    }).execute()
                
                # 3. Baixa Estoque
                supabase.table("produtos").update({"quantidade_estoque": int(prod_data['quantidade_estoque']) - 1}).eq("codigo", cod_p).execute()
                
                st.success(f"Venda concluída! {parc_v} parcelas geradas.")
                st.rerun()

# --- ABA 3: FINANCEIRO ---
with tab_financeiro:
    st.header("📉 Contas e Baixas")
    if not df_parcelas.empty:
        df_fin = pd.merge(df_parcelas, df_clientes[['id', 'nome']], left_on='cliente_id', right_on='id', how='left')
        
        cli_filtro = st.selectbox("Filtrar Cliente", ["--"] + list(df_clientes['nome'].unique()))
        
        if cli_filtro != "--":
            df_cli = df_fin[(df_fin['nome'] == cli_filtro) & (df_fin['pago'] == False)].sort_values('data_vencimento')
            if not df_cli.empty:
                for idx, row in df_cli.iterrows():
                    c_b1, c_b2 = st.columns([3, 1])
                    c_b1.write(f"Parc {row['numero_parcela']} | Venc: {pd.to_datetime(row['data_vencimento']).strftime('%d/%m/%Y')} | **R$ {row['valor_parcela']:.2f}**")
                    if c_b2.button("Dar Baixa", key=f"f_{row['id']}"):
                        supabase.table("parcelas").update({"pago": True}).eq("id", row['id']).execute()
                        st.rerun()
            else:
                st.info("Nenhuma conta pendente para este cliente.")

# --- ABA 4: CLIENTES ---
with tab_clientes:
    st.header("👤 Clientes")
    with st.form("cad_cli_v4", clear_on_submit=True):
        c_c1, c_c2, c_c3 = st.columns(3)
        n_c = c_c1.text_input("Nome")
        t_c = c_c2.text_input("Telefone")
        cpf_c = c_c3.text_input("CPF")
        if st.form_submit_button("Salvar Cliente"):
            supabase.table("clientes").insert({"nome": n_c, "telefone": t_c, "cpf": cpf_c}).execute()
            st.rerun()
    st.dataframe(df_clientes[['nome', 'telefone', 'cpf']], use_container_width=True, hide_index=True)

# --- ABA 5: ESTOQUE ---
with tab_estoque:
    st.header("📦 Mercadorias")
    with st.form("cad_prod_v4", clear_on_submit=True):
        ce1, ce2, ce3, ce4 = st.columns([1, 2, 1, 1])
        c_p = ce1.text_input("Cód", value=str(len(df_produtos)+1).zfill(3))
        n_p = ce2.text_input("Peça")
        p_p = ce3.number_input("Preço", min_value=0.0)
        q_p = ce4.number_input("Qtd", min_value=0, step=1)
        if st.form_submit_button("Salvar Mercadoria"):
            supabase.table("produtos").insert({"codigo": c_p, "nome": n_p, "preco_venda": p_p, "quantidade_estoque": q_p}).execute()
            st.rerun()
    st.dataframe(df_produtos[['codigo', 'nome', 'preco_venda', 'quantidade_estoque']], use_container_width=True, hide_index=True)

# --- 7. RODAPÉ ---
st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
