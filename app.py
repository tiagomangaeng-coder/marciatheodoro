import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Marcia Theodoro - Gestão de Vendas",
    page_icon="👗",
    layout="wide"
)

# --- CONEXÃO COM SUPABASE ---
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro de conexão. Verifique os Secrets no Streamlit Cloud.")
        st.stop()

supabase = init_connection()

# --- ESTILO CSS ---
st.markdown("""
    <style>
    .main { background-color: #fcfaf8; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f1f1f1; border-radius: 5px; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #8b5e3c !important; color: white !important; }
    div[data-testid="stMetricValue"] { color: #8b5e3c; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def listar_produtos():
    res = supabase.table("produtos").select("*").order("codigo").execute()
    return pd.DataFrame(res.data)

def listar_vendas():
    res = supabase.table("vendas").select("*").order("data", desc=True).execute()
    return pd.DataFrame(res.data)

# --- INTERFACE PRINCIPAL ---
st.title("👗 Marcia Theodoro - Sistema de Gestão")

aba_vendas, aba_estoque, aba_relatorios = st.tabs([
    "💰 Registrar Venda", 
    "📦 Cadastro de Mercadoria", 
    "📊 Relatórios e Gráficos"
])

# --- ABA 2: CADASTRO DE MERCADORIA ---
with aba_estoque:
    st.header("Gerenciamento de Estoque")
    df_produtos = listar_produtos()
    
    col_cad, col_list = st.columns([1, 2])
    
    with col_cad:
        st.subheader("Novo Item")
        # Lógica para o próximo código 001, 002...
        proximo_cod = str(len(df_produtos) + 1).zfill(3)
        
        with st.form("form_prod", clear_on_submit=True):
            st.info(f"Código do Produto: **{proximo_cod}**")
            nome_p = st.text_input("Nome da Peça")
            preco_p = st.number_input("Preço de Venda (R$)", min_value=0.0, format="%.2f")
            qtd_p = st.number_input("Quantidade em Estoque", min_value=0, step=1)
            
            if st.form_submit_button("Salvar Produto"):
                if nome_p and preco_p > 0:
                    supabase.table("produtos").insert({
                        "codigo": proximo_cod,
                        "nome": nome_p,
                        "preco_venda": preco_p,
                        "quantidade_estoque": qtd_p
                    }).execute()
                    st.success(f"Item {proximo_cod} cadastrado!")
                    st.rerun()
                else:
                    st.error("Preencha o nome e o preço corretamente.")

    with col_list:
        st.subheader("Itens Cadastrados")
        if not df_produtos.empty:
            st.dataframe(
                df_produtos[['codigo', 'nome', 'preco_venda', 'quantidade_estoque']],
                column_config={
                    "codigo": "Cód",
                    "nome": "Descrição",
                    "preco_venda": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
                    "quantidade_estoque": "Estoque"
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Nenhum produto cadastrado.")

# --- ABA 1: REGISTRAR VENDA ---
with aba_vendas:
    st.header("Nova Venda")
    
    if df_produtos.empty:
        st.warning("⚠️ Você precisa cadastrar produtos na aba de estoque antes de vender.")
    else:
        with st.form("form_venda", clear_on_submit=True):
            col_v1, col_v2 = st.columns(2)
            
            # Criar lista para o seletor: "001 - Camisa Seda"
            lista_opcoes = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
            item_selecionado = col_v1.selectbox("Selecione o Produto", options=lista_opcoes)
            
            # Pegar dados do produto selecionado para sugerir preço e validar estoque
            cod_sel = item_selecionado.split(" - ")[0]
            prod_info = df_produtos[df_produtos['codigo'] == cod_sel].iloc[0]
            
            metodo = col_v2.selectbox("Forma de Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"])
            
            valor_venda = st.number_input("Preço Final (R$)", value=float(prod_info['preco_venda']), format="%.2f")
            obs_venda = st.text_area("Observações (Tamanho, Cor, Cliente, etc.)")
            
            if st.form_submit_button("Finalizar Venda"):
                if prod_info['quantidade_estoque'] > 0:
                    # 1. Registra a Venda
                    supabase.table("vendas").insert({
                        "item": item_selecionado,
                        "valor": valor_venda,
                        "metodo_pagamento": metodo,
                        "observacao": obs_venda
                    }).execute()
                    
                    # 2. Baixa no Estoque
                    nova_qtd = int(prod_info['quantidade_estoque']) - 1
                    supabase.table("produtos").update({"quantidade_estoque": nova_qtd}).eq("codigo", cod_sel).execute()
                    
                    st.success(f"Venda confirmada! Estoque atual de {prod_info['nome']}: {nova_qtd}")
                    st.rerun()
                else:
                    st.error(f"Estoque insuficiente de {prod_info['nome']}!")

    st.markdown("---")
    st.subheader("Últimos Lançamentos")
    df_vendas = listar_vendas()
    if not df_vendas.empty:
        df_vendas['data_f'] = pd.to_datetime(df_vendas['data']).dt.strftime('%d/%m/%Y %H:%M')
        st.dataframe(df_vendas[['data_f', 'item', 'valor', 'metodo_pagamento']], use_container_width=True, hide_index=True)

# --- ABA 3: RELATÓRIOS E GRÁFICOS ---
with aba_relatorios:
    st.header("Análise de Resultados")
    
    if not df_vendas.empty:
        total_venda = df_vendas['valor'].sum()
        num_vendas = len(df_vendas)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Acumulado", f"R$ {total_venda:,.2f}")
        c2.metric("Total de Peças Vendidas", num_vendas)
        c3.metric("Ticket Médio", f"R$ {(total_venda/num_vendas):,.2f}")
        
        st.markdown("---")
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Gráfico de Meios de Pagamento
            fig_metodo = px.pie(df_vendas, values='valor', names='metodo_pagamento', 
                                title="Vendas por Tipo de Pagamento", hole=0.3,
                                color_discrete_sequence=px.colors.qualitative.Antique)
            st.plotly_chart(fig_metodo, use_container_width=True)
            
        with col_g2:
            # Gráfico de evolução diária
            df_vendas['data_dia'] = pd.to_datetime(df_vendas['data']).dt.date
            faturamento_diario = df_vendas.groupby('data_dia')['valor'].sum().reset_index()
            fig_linha = px.line(faturamento_diario, x='data_dia', y='valor', title="Evolução das Vendas",
                                markers=True, labels={'data_dia': 'Data', 'valor': 'Total (R$)'})
            fig_linha.update_traces(line_color='#8b5e3c')
            st.plotly_chart(fig_linha, use_container_width=True)
    else:
        st.info("Aguardando vendas para gerar relatórios.")

# RODAPÉ
st.caption(f"© {datetime.now().year} Marcia Theodoro - Sistema Desenvolvido para Gestão Interna")
