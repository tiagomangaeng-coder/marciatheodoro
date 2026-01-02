import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Marcia Theodoro - Gestão Pro",
    page_icon="👗",
    layout="wide"
)

# --- 2. CONEXÃO COM SUPABASE ---
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro de conexão. Verifique os Secrets.")
        st.stop()

supabase = init_connection()

# --- 3. ESTILO CSS ---
st.markdown("""
    <style>
    .main { background-color: #fcfaf8; }
    div[data-testid="stMetricValue"] { color: #8b5e3c; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f1ede9; 
        border-radius: 5px 5px 0 0; 
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #8b5e3c !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE DADOS E EXPORTAÇÃO ---
def get_data(tabela):
    res = supabase.table(tabela).select("*").execute()
    return pd.DataFrame(res.data)

def converter_para_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# --- 5. INTERFACE PRINCIPAL ---
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
        
        # Métricas Calculadas
        recebido = df_parcelas[df_parcelas['pago'] == True]['valor_parcela'].sum()
        a_receber = df_parcelas[df_parcelas['pago'] == False]['valor_parcela'].sum()
        atrasado = df_parcelas[(df_parcelas['pago'] == False) & (df_parcelas['data_vencimento'] < hoje)]['valor_parcela'].sum()
        faturamento = df_vendas['valor'].sum() if not df_vendas.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento (Vendas)", f"R$ {faturamento:,.2f}")
        c2.metric("Total Recebido", f"R$ {recebido:,.2f}")
        c3.metric("Contas a Receber", f"R$ {a_receber:,.2f}")
        c4.metric("Inadimplência (Atrasados)", f"R$ {atrasado:,.2f}", delta_color="inverse")

        st.divider()
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Meios de Pagamento")
            fig_p = px.pie(df_vendas, values='valor', names='metodo_pagamento', hole=0.4, color_discrete_sequence=px.colors.qualitative.Antique)
            st.plotly_chart(fig_p, use_container_width=True)
            
        with col_g2:
            st.subheader("Recebimentos Futuros")
            df_parcelas['mes'] = pd.to_datetime(df_parcelas['data_vencimento']).dt.strftime('%m/%y')
            df_mes = df_parcelas[df_parcelas['pago'] == False].groupby('mes')['valor_parcela'].sum().reset_index()
            fig_b = px.bar(df_mes, x='mes', y='valor_parcela', color_discrete_sequence=['#8b5e3c'])
            st.plotly_chart(fig_b, use_container_width=True)

        # Exportação Rápida no Dashboard
        st.download_button("📥 Baixar Todas as Vendas (CSV)", data=converter_para_csv(df_vendas), file_name="vendas_marcia_theodoro.csv")
    else:
        st.info("Inicie as vendas para visualizar os gráficos.")

# --- ABA: VENDAS ---
with aba_vendas:
    st.header("Nova Venda")
    if df_produtos.empty:
        st.warning("Cadastre produtos no estoque.")
    else:
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

            if st.form_submit_button("Confirmar"):
                # Salva Venda
                v_res = supabase.table("vendas").insert({"item": item_sel, "valor": valor_v, "metodo_pagamento": metodo}).execute()
                v_id = v_res.data[0]['id']
                
                # Gera Parcelas
                v_parc = valor_v / parc
                for i in range(parc):
                    venc = (datetime.now() + timedelta(days=30 * i)).date()
                    pago = True if metodo in ["Pix", "Dinheiro"] else False
                    supabase.table("parcelas").insert({
                        "venda_id": v_id, "cliente_id": cli_id, "valor_parcela": v_parc,
                        "data_vencimento": str(venc), "pago": pago, "numero_parcela": i+1, "metodo_pagamento": metodo
                    }).execute()
                
                # Baixa Estoque
                supabase.table("produtos").update({"quantidade_estoque": int(dados_p['quantidade_estoque'])-1}).eq("codigo", cod_p).execute()
                st.success("Venda registrada!")
                st.rerun()

# --- ABA: FINANCEIRO (CONTAS PAGAS E A PAGAR) ---
with aba_financeiro:
    st.header("Gestão Financeira e Exportação")
    
    if not df_parcelas.empty:
        df_full = pd.merge(df_parcelas, df_clientes[['id', 'nome']], left_on='cliente_id', right_on='id', how='left')
        
        col_f1, col_f2 = st.columns(2)
        
        # --- SEÇÃO: CONTAS A PAGAR (PENDENTES) ---
        with col_f1:
            st.subheader("⏳ Contas a Receber (Pendentes)")
            df_pendente = df_full[df_full['pago'] == False]
            st.dataframe(df_pendente[['nome', 'data_vencimento', 'valor_parcela']], use_container_width=True)
            st.download_button("📥 Exportar Contas a Receber", data=converter_para_csv(df_pendente), file_name="contas_a_receber.csv")
            
        # --- SEÇÃO: CONTAS PAGAS ---
        with col_f2:
            st.subheader("✅ Contas Recebidas")
            df_paga = df_full[df_full['pago'] == True]
            st.dataframe(df_paga[['nome', 'data_vencimento', 'valor_parcela']], use_container_width=True)
            st.download_button("📥 Exportar Contas Recebidas", data=converter_para_csv(df_paga), file_name="contas_pagas.csv")

        st.divider()
        st.subheader("Baixar Pagamento")
        cliente_filtro = st.selectbox("Selecione o Cliente para dar Baixa", ["Selecione"] + list(df_clientes['nome'].unique()))
        
        if cliente_filtro != "Selecione":
            df_baixa = df_full[(df_full['nome'] == cliente_filtro) & (df_full['pago'] == False)]
            if not df_baixa.empty:
                for idx, row in df_baixa.iterrows():
                    c_b1, c_b2 = st.columns([3, 1])
                    c_b1.write(f"Parc {row['numero_parcela']} - Venc: {row['data_vencimento']} - R$ {row['valor_parcela']:.2f}")
                    if c_b2.button("Dar Baixa", key=f"baixa_{row['id']}"):
                        supabase.table("parcelas").update({"pago": True}).eq("id", row['id']).execute()
                        st.rerun()
            else:
                st.info("Este cliente não possui parcelas pendentes.")
    else:
        st.info("Nenhuma movimentação financeira.")

# --- ABA: CLIENTES ---
with aba_clientes:
    st.subheader("Cadastro de Clientes")
    with st.form("c_cli", clear_on_submit=True):
        n_c = st.text_input("Nome")
        t_c = st.text_input("Telefone")
        if st.form_submit_button("Salvar Cliente"):
            supabase.table("clientes").insert({"nome": n_c, "telefone": t_c}).execute()
            st.rerun()
    st.dataframe(df_clientes[['nome', 'telefone']], use_container_width=True)

# --- ABA: ESTOQUE ---
with aba_estoque:
    st.subheader("Controle de Estoque")
    with st.form("c_prod", clear_on_submit=True):
        c1, c2, c3 = st.columns([1,3,1])
        proximo_cod = str(len(df_produtos)+1).zfill(3)
        cod_p = c1.text_input("Código", value=proximo_cod)
        nome_p = c2.text_input("Produto")
        preco_p = c3.number_input("Preço Venda", min_value=0.0)
        qtd_p = st.number_input("Quantidade Inicial", min_value=0)
        if st.form_submit_button("Salvar Mercadoria"):
            supabase.table("produtos").insert({"codigo": cod_p, "nome": nome_p, "preco_venda": preco_p, "quantidade_estoque": qtd_p}).execute()
            st.rerun()
    
    st.dataframe(df_produtos[['codigo', 'nome', 'preco_venda', 'quantidade_estoque']], use_container_width=True)
    st.download_button("📥 Exportar Inventário", data=converter_para_csv(df_produtos), file_name="estoque_atual.csv")
