import streamlit as st
from supabase import create_client, Client
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Marcia Theodoro - Livro Caixa", layout="wide")

# Conexão com Supabase (Substitua pelos seus dados ou use Secrets)
URL = "SUA_URL_DO_SUPABASE"
KEY = "SUA_ANON_KEY_DO_SUPABASE"
supabase: Client = create_client(URL, KEY)

# --- ESTILO ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.title("👗 Marcia Theodoro - Controle de Vendas")
st.subheader("Livro Caixa Digital")

# --- BARRA LATERAL (CADASTRO) ---
with st.sidebar:
    st.header("Nova Venda")
    with st.form("form_venda", clear_on_submit=True):
        item = st.text_input("Nome da Peça/Descrição")
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        metodo = st.selectbox("Método de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro"])
        obs = st.text_area("Observações")
        submit = st.form_submit_button("Registrar Venda")

    if submit:
        if item and valor > 0:
            data = {"item": item, "valor": valor, "metodo_pagamento": metodo, "observacao": obs}
            supabase.table("vendas").insert(data).execute()
            st.success("Venda registrada com sucesso!")
            st.rerun()
        else:
            st.error("Preencha o nome do item e o valor.")

# --- DASHBOARD PRINCIPAL ---
# Buscar dados
response = supabase.table("vendas").select("*").order("data", desc=True).execute()
df = pd.DataFrame(response.data)

if not df.empty:
    # Métricas
    total_vendas = df["valor"].sum()
    qtd_vendas = len(df)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Faturamento Total", f"R$ {total_vendas:,.2f}")
    col2.metric("Quantidade de Vendas", qtd_vendas)
    col3.metric("Ticket Médio", f"R$ {(total_vendas/qtd_vendas):,.2f}")

    st.divider()

    # Tabela de Lançamentos
    st.write("### Últimos Lançamentos")
    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y %H:%M')
    st.dataframe(df[["data", "item", "valor", "metodo_pagamento", "observacao"]], use_container_width=True)
else:
    st.info("Nenhuma venda registrada ainda.")