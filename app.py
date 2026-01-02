import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Marcia Theodoro - Gestão Pro", page_icon="👗", layout="wide")

# --- ESTILO CSS (ABERTURA, RODAPÉ E INTERFACE) ---
st.markdown("""
    <style>
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    .intro-container { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 80vh; text-align: center; }
    .intro-title { font-size: 5rem; font-family: 'serif'; color: #8b5e3c; animation: blink 1.5s infinite; letter-spacing: 5px; text-transform: uppercase; }
    .intro-subtitle { font-size: 2rem; color: #a68a64; letter-spacing: 10px; text-transform: uppercase; animation: blink 1.5s infinite; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #fcfaf8; color: #8b5e3c; text-align: center; padding: 10px; font-weight: bold; }
    .main { background-color: #fcfaf8; }
    div[data-testid="stMetricValue"] { color: #8b5e3c; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #8b5e3c !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE ABERTURA ---
if 'intro_visto' not in st.session_state:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div class="intro-container"><div class="intro-title">Márcia Theodoro</div><div class="intro-subtitle">Boutique</div></div>', unsafe_allow_html=True)
    time.sleep(5)
    st.session_state['intro_visto'] = True
    placeholder.empty()
    st.rerun()

# --- CONEXÃO SUPABASE ---
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Configure as chaves no Streamlit Cloud (Settings > Secrets).")
        st.stop()

supabase = init_connection()

# --- FUNÇÕES AUXILIARES ---
def get_data(tabela):
    res = supabase.table(tabela).select("*").execute()
    return pd.DataFrame(res.data)

def converter_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# --- CARREGAMENTO INICIAL DE DADOS ---
df_clientes = get_data("clientes")
df_produtos = get_data("produtos")
df_vendas = get_data("vendas")
df_parcelas = get_data("parcelas")

# --- NAVEGAÇÃO POR ABAS ---
tab_dash, tab_venda, tab_financeiro, tab_clientes, tab_estoque = st.tabs([
    "📊 Dashboard", "💰 Realizar Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque"
])

# --- ABA 1: DASHBOARD ---
with tab_dash:
    st.header("📊 Resumo do Negócio")
    if not df_parcelas.empty:
        hoje = datetime.now().date()
        df_parcelas['data_vencimento'] = pd.to_datetime(df_parcelas['data_vencimento']).dt.date
        recebido = df_parcelas[df_parcelas['pago'] == True]['valor_parcela'].sum()
        a_receber = df_parcelas[df_parcelas['pago'] == False]['valor_parcela'].sum()
        atrasado = df_parcelas[(df_parcelas['pago'] == False) & (df_parcelas['data_vencimento'] < hoje)]['valor_parcela'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Total", f"R$ {df_vendas['valor'].sum():,.2f}" if not df_vendas.empty else "0,00")
        c2.metric("Total Recebido", f"R$ {recebido:,.2f}")
        c3.metric("A Receber", f"R$ {a_receber:,.2f}")
        c4.metric("Inadimplência", f"R$ {atrasado:,.2f}", delta_color="inverse")
        
        col_ga, col_gb = st.columns(2)
        with col_ga:
            fig_p = px.pie(df_vendas, values='valor', names='metodo_pagamento', hole=0.4, title="Meios de Pagamento")
            st.plotly_chart(fig_p, use_container_width=True)
        with col_gb:
            df_mes = df_parcelas[df_parcelas['pago'] == False].copy()
            df_mes['m'] = pd.to_datetime(df_mes['data_vencimento']).dt.strftime('%m/%y')
            fig_b = px.bar(df_mes.groupby('m')['valor_parcela'].sum().reset_index(), x='m', y='valor_parcela', title="Previsão Mensal")
            st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("Nenhum dado financeiro disponível ainda.")

# --- ABA 2: VENDAS ---
with tab_venda:
    st.header("💰 Registrar Venda")
    if df_produtos.empty:
        st.warning("Cadastre produtos no Estoque primeiro.")
    else:
        with st.form("form_venda_v3", clear_on_submit=True):
            col_v1, col_v2 = st.columns(2)
            lista_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
            prod_sel = col_v1.selectbox("Selecione o Produto", lista_p)
            metodo = col_v2.selectbox("Método de Pagamento", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito", "Crediário"])
            
            col_v3, col_v4 = st.columns(2)
            parc = col_v3.number_input("Número de Parcelas", min_value=1, value=1)
            
            # Busca preço e estoque do produto
            cod_p = prod_sel.split(" - ")[0]
            item_data = df_produtos[df_produtos['codigo'] == cod_p].iloc[0]
            valor_v = col_v4.number_input("Valor Final (R$)", value=float(item_data['preco_venda']))
            
            # SELEÇÃO DE CLIENTE (Obrigatória para Crediário)
            cli_id = None
            if metodo == "Crediário":
                if not df_clientes.empty:
                    cli_opcoes = {r['nome']: r['id'] for _, r in df_clientes.iterrows()}
                    nome_cli_sel = st.selectbox("Selecione o Cliente (Crediário)", list(cli_opcoes.keys()))
                    cli_id = cli_opcoes[nome_cli_sel]
                else:
                    st.error("❌ Erro: Cadastre um cliente antes de vender no Crediário.")

            if st.form_submit_button("Finalizar Venda"):
                if metodo == "Crediário" and cli_id is None:
                    st.error("Selecione um cliente para prosseguir.")
                elif item_data['quantidade_estoque'] <= 0:
                    st.error("Produto sem estoque!")
                else:
                    # 1. Salvar Venda
                    v_res = supabase.table("vendas").insert({"item": prod_sel, "valor": valor_v, "metodo_pagamento": metodo}).execute()
                    v_id = v_res.data[0]['id']
                    
                    # 2. Gerar Parcelas
                    v_parc = valor_v / parc
                    for i in range(parc):
                        venc = (datetime.now() + timedelta(days=30 * i)).date()
                        pago_status = True if metodo in ["Pix", "Dinheiro"] else False
                        supabase.table("parcelas").insert({
                            "venda_id": v_id, "cliente_id": cli_id, "valor_parcela": v_parc,
                            "data_vencimento": str(venc), "pago": pago_status, "numero_parcela": i+1, "metodo_pagamento": metodo
                        }).execute()
                    
                    # 3. Baixa Estoque
                    supabase.table("produtos").update({"quantidade_estoque": int(item_data['quantidade_estoque']) - 1}).eq("codigo", cod_p).execute()
                    st.success("✅ Venda realizada com sucesso!")
                    st.rerun()

# --- ABA 3: FINANCEIRO ---
with tab_financeiro:
    st.header("📉 Fluxo de Caixa e Exportação")
    if not df_parcelas.empty:
        df_f = pd.merge(df_parcelas, df_clientes[['id', 'nome', 'cpf']], left_on='cliente_id', right_on='id', how='left')
        
        c_exp1, c_exp2 = st.columns(2)
        with c_exp1:
            df_pen = df_f[df_f['pago'] == False]
            st.subheader("⏳ A Receber")
            st.dataframe(df_pen[['nome', 'data_vencimento', 'valor_parcela']], use_container_width=True)
            st.download_button("Baixar CSV Pendentes", converter_csv(df_pen), "pendentes.csv")
        with c_exp2:
            df_pag = df_f[df_f['pago'] == True]
            st.subheader("✅ Recebidos")
            st.dataframe(df_pag[['nome', 'data_vencimento', 'valor_parcela']], use_container_width=True)
            st.download_button("Baixar CSV Pagos", converter_csv(df_pag), "pagos.csv")

# --- ABA 4: CLIENTES ---
with tab_clientes:
    st.header("👤 Gestão de Clientes")
    with st.form("form_cliente", clear_on_submit=True):
        col_c1, col_c2, col_c3 = st.columns(3)
        n_cli = col_c1.text_input("Nome Completo")
        t_cli = col_c2.text_input("Telefone (WhatsApp)")
        cpf_cli = col_c3.text_input("CPF")
        if st.form_submit_button("Cadastrar Cliente"):
            if n_cli:
                supabase.table("clientes").insert({"nome": n_cli, "telefone": t_cli, "cpf": cpf_cli}).execute()
                st.success("Cliente cadastrado!")
                st.rerun()
    st.subheader("Lista de Clientes")
    st.dataframe(df_clientes[['nome', 'telefone', 'cpf']], use_container_width=True, hide_index=True)

# --- ABA 5: ESTOQUE ---
with tab_estoque:
    st.header("📦 Controle de Estoque")
    with st.form("form_estoque", clear_on_submit=True):
        col_e1, col_e2, col_e3, col_e4 = st.columns([1, 2, 1, 1])
        sugestao_cod = str(len(df_produtos) + 1).zfill(3)
        c_prod = col_e1.text_input("Código", value=sugestao_cod)
        n_prod = col_e2.text_input("Nome da Peça")
        p_prod = col_e3.number_input("Preço Venda", min_value=0.0)
        q_prod = col_e4.number_input("Qtd Inicial", min_value=0, step=1)
        if st.form_submit_button("Salvar Produto"):
            if n_prod and c_prod:
                supabase.table("produtos").insert({"codigo": c_prod, "nome": n_prod, "preco_venda": p_prod, "quantidade_estoque": q_prod}).execute()
                st.success("Produto adicionado!")
                st.rerun()
    st.dataframe(df_produtos[['codigo', 'nome', 'preco_venda', 'quantidade_estoque']], use_container_width=True, hide_index=True)

# --- RODAPÉ ---
st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
