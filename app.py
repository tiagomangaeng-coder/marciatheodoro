import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Marcia Theodoro - Livro Caixa",
    page_icon="👗",
    layout="wide"
)

# --- 2. CONEXÃO SEGURA COM SUPABASE ---
def init_connection():
    try:
        # Verifica se os campos existem nos Secrets
        if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
            st.error("❌ Erro: Chaves SUPABASE_URL ou SUPABASE_KEY não encontradas nos Secrets do Streamlit.")
            st.info("💡 Vá em Settings > Secrets e adicione suas credenciais.")
            st.stop()
        
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        # Validação de URL para evitar o erro "Invalid URL"
        if not url.startswith("https://"):
            st.error("❌ Erro: A URL do Supabase deve começar com 'https://'. Verifique seus Secrets.")
            st.stop()

        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Erro crítico de conexão: {e}")
        st.stop()

supabase = init_connection()

# --- 3. ESTILO VISUAL (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #fcfaf8; }
    [data-testid="stMetricValue"] { color: #8b5e3c; font-weight: bold; }
    .stButton>button { 
        background-color: #8b5e3c; 
        color: white; 
        border-radius: 8px;
        width: 100%;
    }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. FUNÇÕES DE BANCO DE DADOS ---
def get_vendas():
    # Busca todas as vendas ordenadas pela data mais recente
    res = supabase.table("vendas").select("*").order("data", desc=True).execute()
    return pd.DataFrame(res.data)

def add_venda(item, valor, metodo, obs):
    nova_venda = {
        "item": item,
        "valor": valor,
        "metodo_pagamento": metodo,
        "observacao": obs,
        "data": datetime.now().isoformat()
    }
    supabase.table("vendas").insert(nova_venda).execute()

# --- 5. INTERFACE - BARRA LATERAL (CADASTRO) ---
with st.sidebar:
    st.title("👗 Marcia Theodoro")
    st.markdown("---")
    st.header("Registrar Nova Venda")
    
    with st.form("form_venda", clear_on_submit=True):
        item = st.text_input("Descrição da Peça", placeholder="Ex: Blusa Seda Branca")
        valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
        metodo = st.selectbox("Forma de Pagamento", ["Pix", "Crédito", "Débito", "Dinheiro"])
        obs = st.text_area("Observações adicionais")
        
        submit = st.form_submit_button("Confirmar Venda")
    
    if submit:
        if item and valor > 0:
            with st.spinner("Salvando..."):
                add_venda(item, valor, metodo, obs)
                st.success("Venda registrada!")
                st.rerun()
        else:
            st.warning("Por favor, preencha o item e o valor.")

# --- 6. PAINEL PRINCIPAL (DASHBOARD) ---
st.title("📊 Livro Caixa Digital")
st.markdown("Controle de fluxo de caixa da loja em tempo real.")

df = get_vendas()

if not df.empty:
    # Tratamento das datas
    df['data'] = pd.to_datetime(df['data'])
    df['data_display'] = df['data'].dt.strftime('%d/%m/%Y %H:%M')
    
    # --- MÉTRICAS ---
    total_receita = df['valor'].sum()
    total_itens = len(df)
    ticket_medio = total_receita / total_itens if total_itens > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Faturamento Total", f"R$ {total_receita:,.2f}")
    col2.metric("Vendas Realizadas", total_itens)
    col3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
    
    st.markdown("---")
    
    # --- GRÁFICOS ---
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        st.subheader("Vendas por Categoria")
        fig_pizza = px.pie(df, values='valor', names='metodo_pagamento', 
                           hole=0.4, color_discrete_sequence=px.colors.qualitative.Antique)
        st.plotly_chart(fig_pizza, use_container_width=True)
        
    with g_col2:
        st.subheader("Evolução das Vendas")
        # Agrupa por dia para o gráfico de linha
        df_evolucao = df.groupby(df['data'].dt.date)['valor'].sum().reset_index()
        fig_linha = px.line(df_evolucao, x='data', y='valor', markers=True,
                            line_shape='spline', labels={'data': 'Data', 'valor': 'Total (R$)'})
        fig_linha.update_traces(line_color='#8b5e3c')
        st.plotly_chart(fig_linha, use_container_width=True)

    # --- TABELA DE LANÇAMENTOS ---
    st.subheader("📝 Histórico de Lançamentos")
    st.dataframe(
        df[['data_display', 'item', 'valor', 'metodo_pagamento', 'observacao']],
        column_config={
            "data_display": "Data e Hora",
            "item": "Produto",
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "metodo_pagamento": "Pagamento",
            "observacao": "Notas"
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Botão para baixar em Excel/CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Relatório (CSV)", data=csv, file_name="vendas_marcia_theodoro.csv", mime='text/csv')

else:
    st.info("Nenhuma venda encontrada no sistema. Comece registrando uma venda na barra lateral.")

# --- RODAPÉ ---
st.markdown("---")
st.caption(f"© {datetime.now().year} Marcia Theodoro Boutique | Sistema de Gestão Interna")
