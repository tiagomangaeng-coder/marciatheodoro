import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Marcia Theodoro - Gestão Pro",
    page_icon="👗",
    layout="wide"
)

# --- 2. ESTILO CSS (INCLUINDO ABERTURA E RODAPÉ) ---
st.markdown("""
    <style>
    /* Estilo da Abertura */
    @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
    .intro-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 80vh;
        text-align: center;
    }
    .intro-title {
        font-size: 5rem;
        font-family: 'Playfair Display', serif;
        color: #8b5e3c;
        margin-bottom: 0;
        animation: blink 1.5s infinite;
        letter-spacing: 5px;
        text-transform: uppercase;
    }
    .intro-subtitle {
        font-size: 2rem;
        color: #a68a64;
        letter-spacing: 10px;
        text-transform: uppercase;
        animation: blink 1.5s infinite;
    }

    /* Estilo do Rodapé Fixo */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: transparent;
        color: #8b5e3c;
        text-align: center;
        padding: 10px;
        font-size: 0.9rem;
        font-weight: bold;
        letter-spacing: 1px;
    }

    /* Estilos Gerais do App */
    .main { background-color: #fcfaf8; }
    div[data-testid="stMetricValue"] { color: #8b5e3c; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #8b5e3c !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DA ABERTURA (5 SEGUNDOS) ---
if 'intro_visto' not in st.session_state:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
            <div class="intro-container">
                <div class="intro-title">Márcia Theodoro</div>
                <div class="intro-subtitle">Boutique</div>
            </div>
        """, unsafe_allow_html=True)
    time.sleep(5)
    st.session_state['intro_visto'] = True
    placeholder.empty()
    st.rerun()

# --- 4. CONEXÃO COM SUPABASE ---
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro de conexão. Verifique os Secrets.")
        st.stop()

supabase = init_connection()

# --- 5. FUNÇÕES DE DADOS E EXPORTAÇÃO ---
def get_data(tabela):
    res = supabase.table(tabela).select("*").execute()
    return pd.DataFrame(res.data)

def converter_para_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# --- 6. INTERFACE PRINCIPAL ---
st.title("👗 Marcia Theodoro - Sistema de Gestão Pro")

aba_dash, aba_vendas, aba_financeiro, aba_clientes, aba_estoque = st.tabs([
    "📊 Dashboard", "💰 Vendas", "📉 Financeiro (Exportar)", "👤 Clientes", "📦 Estoque"
])

# Carregamento de dados
df_clientes = get_data("clientes")
df_produtos = get_data("produtos")
df_vendas = get_data("vendas")
df_parcelas = get_data("parcelas")

# --- ABA: DASHBOARD ---
with aba_dash:
    st.header("Resumo Geral do Negócio")
    if not df_parcelas.empty:
        hoje = datetime.now().date()
        df_parcelas['data_vencimento'] = pd.to_datetime(df_parcelas['data_vencimento']).dt.date
        recebido = df_parcelas[df_parcelas['pago'] == True]['valor_parcela'].sum()
        a_receber = df_parcelas[df_parcelas['pago'] == False]['valor_parcela'].sum()
        atrasado = df_parcelas[(df_parcelas['pago'] == False) & (df_parcelas['data_vencimento'] < hoje)]['valor_parcela'].sum()
        faturamento = df_vendas['valor'].sum() if not df_vendas.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento (Vendas)", f"R$ {faturamento:,.2f}")
        c2.metric("Total Recebido", f"R$ {recebido:,.2f}")
        c3.metric("Contas a Receber", f"R$ {a_receber:,.2f}")
        c4.metric("Inadimplência", f"R$ {atrasado:,.2f}", delta_color="inverse")

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_p = px.pie(df_vendas, values='valor', names='metodo_pagamento', hole=0.4, title="Meios de Pagamento")
            st.plotly_chart(fig_p, use_container_width=True)
        with col_g2:
            df_parcelas['mes'] = pd.to_datetime(df_parcelas['data_vencimento']).dt.strftime('%m/%y')
            df_mes = df_parcelas[df_parcelas['pago'] == False].groupby('mes')['valor_parcela'].sum().reset_index()
            fig_b = px.bar(df_mes, x='mes', y='valor_parcela', title="Previsão de Recebimento", color_discrete_sequence=['#8b5e3c'])
            st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("Inicie as vendas para visualizar os gráficos.")

# --- ABA: VENDAS ---
with aba_vendas:
    st.header("Nova Venda")
    if not df_produtos.empty:
        with st.form("form_venda", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            prod_info = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
            item_sel = col1.selectbox("Produto", prod_info)
            metodo = col2.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão", "Crediário"])
            parc = col3.number_input("Parcelas", min_value=1, value=1)
            cod_p = item_sel.split(" - ")[0]
            dados_p = df_produtos[df_produtos['codigo'] == cod_p].iloc[0]
            valor_v = st.number_input("Valor Final", value=float(dados_p['preco_venda']))
            cli_id = None
            if metodo == "Crediário":
                cli_dic = {r['nome']: r['id'] for _, r in df_clientes.iterrows()}
                cli_id = cli_dic.get(st.selectbox("Cliente", list(cli_dic.keys())))
            if st.form_submit_button("Confirmar Venda"):
                v_res = supabase.table("vendas").insert({"item": item_sel, "valor": valor_v, "metodo_pagamento": metodo}).execute()
                v_id = v_res.data[0]['id']
                v_parc = valor_v / parc
                for i in range(parc):
                    venc = (datetime.now() + timedelta(days=30 * i)).date()
                    pago = True if metodo in ["Pix", "Dinheiro"] else False
                    supabase.table("parcelas").insert({"venda_id": v_id, "cliente_id": cli_id, "valor_parcela": v_parc, "data_vencimento": str(venc), "pago": pago, "numero_parcela": i+1, "metodo_pagamento": metodo}).execute()
                supabase.table("produtos").update({"quantidade_estoque": int(dados_p['quantidade_estoque'])-1}).eq("codigo", cod_p).execute()
                st.success("Venda registrada!")
                st.rerun()

# --- ABA: FINANCEIRO ---
with aba_financeiro:
    st.header("Gestão Financeira e Exportação")
    if not df_parcelas.empty:
        df_full = pd.merge(df_parcelas, df_clientes[['id', 'nome']], left_on='cliente_id', right_on='id', how='left')
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            st.subheader("⏳ A Receber")
            df_p = df_full[df_full['pago'] == False]
            st.dataframe(df_p[['nome', 'data_vencimento', 'valor_parcela']], use_container_width=True)
            st.download_button("📥 Exportar Pendentes", data=converter_para_csv(df_p), file_name="a_receber.csv")
        with c_f2:
            st.subheader("✅ Recebidos")
            df_pg = df_full[df_full['pago'] == True]
            st.dataframe(df_pg[['nome', 'data_vencimento', 'valor_parcela']], use_container_width=True)
            st.download_button("📥 Exportar Recebidos", data=converter_para_csv(df_pg), file_name="contas_pagas.csv")

# --- ABA: CLIENTES E ESTOQUE (RESUMIDOS) ---
with aba_clientes:
    st.subheader("Cadastro de Clientes")
    with st.form("c_cli"):
        n_c = st.text_input("Nome")
        if st.form_submit_button("Salvar"):
            supabase.table("clientes").insert({"nome": n_c}).execute()
            st.rerun()
    st.dataframe(df_clientes, use_container_width=True)

with aba_estoque:
    st.subheader("Estoque")
    st.dataframe(df_produtos, use_container_width=True)

# --- 7. RODAPÉ PERSONALIZADO ---
st.markdown("""
    <div class="footer">
        Desenvolvido por tmanga
    </div>
    """, unsafe_allow_html=True)
