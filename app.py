import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Marcia Theodoro - Sistema Pro", page_icon="👗", layout="wide")

def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- FUNÇÕES DE DADOS ---
def get_data(tabela):
    res = supabase.table(tabela).select("*").execute()
    return pd.DataFrame(res.data)

# --- INTERFACE ---
st.title("👗 Marcia Theodoro - Gestão & Crediário")

aba_vendas, aba_financeiro, aba_clientes, aba_estoque = st.tabs([
    "💰 Vendas", "📉 Contas a Receber", "👤 Clientes", "📦 Estoque"
])

# --- ABA: CLIENTES ---
with aba_clientes:
    st.header("Cadastro de Clientes")
    with st.form("cad_cliente", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        nome_cli = col_c1.text_input("Nome Completo")
        tel_cli = col_c2.text_input("Telefone")
        if st.form_submit_button("Cadastrar Cliente"):
            if nome_cli:
                supabase.table("clientes").insert({"nome": nome_cli, "telefone": tel_cli}).execute()
                st.success("Cliente cadastrado!")
                st.rerun()
    
    df_clientes = get_data("clientes")
    if not df_clientes.empty:
        st.dataframe(df_clientes[['nome', 'telefone']], use_container_width=True)

# --- ABA: ESTOQUE (Simplified for the example) ---
with aba_estoque:
    df_prod = get_data("produtos")
    st.write("### Produtos em Estoque")
    st.dataframe(df_prod, use_container_width=True)

# --- ABA: VENDAS (COM PARCELAMENTO) ---
with aba_vendas:
    st.header("Nova Venda")
    if df_prod.empty:
        st.warning("Cadastre produtos primeiro.")
    else:
        with st.form("venda_pro"):
            col_v1, col_v2, col_v3 = st.columns(3)
            
            # Seleção de Produto
            prod_list = [f"{r['codigo']} - {r['nome']}" for _, r in df_prod.iterrows()]
            item_sel = col_v1.selectbox("Produto", prod_list)
            
            # Forma de Pagamento
            metodo = col_v2.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Cartão", "Crediário"])
            
            # Parcelas
            num_parcelas = col_v3.number_input("Número de Parcelas", min_value=1, value=1)
            
            # Cliente (Só aparece se for Crediário)
            cliente_id = None
            if metodo == "Crediário":
                if not df_clientes.empty:
                    cli_list = {r['nome']: r['id'] for _, r in df_clientes.iterrows()}
                    nome_cli_sel = st.selectbox("Selecionar Cliente para Crediário", list(cli_list.keys()))
                    cliente_id = cli_list[nome_cli_sel]
                else:
                    st.error("Cadastre um cliente antes de usar o Crediário!")

            cod_sel = item_sel.split(" - ")[0]
            prod_info = df_prod[df_prod['codigo'] == cod_sel].iloc[0]
            valor_total = st.number_input("Valor Total da Venda", value=float(prod_info['preco_venda']))
            
            if st.form_submit_button("Finalizar Venda"):
                # 1. Salvar a Venda
                venda_res = supabase.table("vendas").insert({
                    "item": item_sel, "valor": valor_total, "metodo_pagamento": metodo
                }).execute()
                venda_id = venda_res.data[0]['id']
                
                # 2. Criar Parcelas
                valor_p = valor_total / num_parcelas
                for i in range(num_parcelas):
                    vencimento = (datetime.now() + timedelta(days=30 * i)).strftime('%Y-%m-%d')
                    # Se for Pix/Dinheiro, já nasce pago
                    esta_pago = True if metodo in ["Pix", "Dinheiro"] else False
                    
                    supabase.table("parcelas").insert({
                        "venda_id": venda_id, "cliente_id": cliente_id,
                        "valor_parcela": valor_p, "data_vencimento": vencimento,
                        "pago": esta_pago, "numero_parcela": i+1, "metodo_pagamento": metodo
                    }).execute()
                
                # 3. Baixa Estoque
                supabase.table("produtos").update({"quantidade_estoque": int(prod_info['quantidade_estoque']) - 1}).eq("codigo", cod_sel).execute()
                
                st.success("Venda e parcelas registradas com sucesso!")
                st.rerun()

# --- ABA: FINANCEIRO (CONTAS A PAGAR/PAGAS) ---
with aba_financeiro:
    st.header("Gestão de Parcelas e Cobrança")
    df_parc = get_data("parcelas")
    
    if not df_parc.empty:
        # Cruzar dados para ver o nome do cliente
        df_full = pd.merge(df_parc, df_clientes, left_on="cliente_id", right_on="id", how="left", suffixes=('_parc', '_cli'))
        
        filtro_cliente = st.selectbox("Filtrar por Cliente", ["Todos"] + list(df_clientes['nome'].unique()))
        status_pag = st.radio("Status", ["Todas", "Pagas", "A Vencer"], horizontal=True)
        
        df_filtered = df_full.copy()
        if filtro_cliente != "Todos":
            df_filtered = df_filtered[df_filtered['nome'] == filtro_cliente]
        
        if status_pag == "Pagas":
            df_filtered = df_filtered[df_filtered['pago'] == True]
        elif status_pag == "A Vencer":
            df_filtered = df_filtered[df_filtered['pago'] == False]
        
        # Tabela de Parcelas
        st.write(f"### Parcelas - {filtro_cliente}")
        
        # Exibição para marcar como pago
        for index, row in df_filtered.iterrows():
            with st.container():
                c_parc1, c_parc2, c_parc3, c_parc4 = st.columns([2, 1, 1, 1])
                status_txt = "✅ Pago" if row['pago'] else "⏳ Pendente"
                c_parc1.write(f"**{row['nome'] if pd.notna(row['nome']) else 'Venda Direta'}** - Parc {row['numero_parcela']}")
                c_parc2.write(f"R$ {row['valor_parcela']:,.2f}")
                c_parc3.write(f"Venc: {row['data_vencimento']}")
                
                if not row['pago']:
                    if c_parc4.button("Dar Baixa", key=f"pay_{row['id_parc']}"):
                        supabase.table("parcelas").update({"pago": True}).eq("id", row['id_parc']).execute()
                        st.rerun()
                else:
                    c_parc4.write(status_txt)
                st.divider()
    else:
        st.info("Nenhuma parcela encontrada.")
