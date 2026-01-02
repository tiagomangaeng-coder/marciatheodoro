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
    /* Ajuste para inputs ficarem mais limpos */
    .stNumberInput, .stTextInput, .stSelectbox { margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE ABERTURA (INTRO) ---
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
        st.error("Erro: Configure as chaves SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit Cloud.")
        st.stop()

supabase = init_connection()

# --- 5. FUNÇÕES DE BUSCA DE DADOS ---
def get_data(tabela):
    try:
        res = supabase.table(tabela).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# Carregamento de dados globais
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
        c4.metric("Atrasado (Inadimplência)", f"R$ {atrasado:,.2f}", delta_color="inverse")
        
        col_ga, col_gb = st.columns(2)
        with col_ga:
            if not df_vendas.empty:
                fig_p = px.pie(df_vendas, values='valor', names='metodo_pagamento', hole=0.4, title="Meios de Pagamento")
                st.plotly_chart(fig_p, use_container_width=True)
        with col_gb:
            df_mes = df_parcelas[df_parcelas['pago'] == False].copy()
            if not df_mes.empty:
                df_mes['m'] = pd.to_datetime(df_mes['data_vencimento']).dt.strftime('%m/%y')
                fig_b = px.bar(df_mes.groupby('m')['valor_parcela'].sum().reset_index(), x='m', y='valor_parcela', title="Previsão de Recebimento Mensal", color_discrete_sequence=['#8b5e3c'])
                st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("Nenhum dado financeiro para exibir no momento.")

# --- ABA 2: REALIZAR VENDA (REVISADA) ---
with tab_venda:
    st.header("💰 Nova Venda")
    
    if df_produtos.empty:
        st.warning("⚠️ Você precisa cadastrar produtos na aba 'Estoque' primeiro.")
    elif df_clientes.empty:
        st.warning("⚠️ Você precisa cadastrar clientes na aba 'Clientes' primeiro.")
    else:
        # 1. Seleção do Produto (Fora do form para atualizar o preço na hora)
        lista_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_produtos.iterrows()]
        prod_sel_txt = st.selectbox("1. Escolha o Produto", lista_p)
        
        # Busca automática do preço e estoque
        cod_p = prod_sel_txt.split(" - ")[0]
        prod_data = df_produtos[df_produtos['codigo'] == cod_p].iloc[0]
        preco_sugerido = float(prod_data['preco_venda'])
        estoque_atual = int(prod_data['quantidade_estoque'])

        st.markdown(f"**Estoque disponível:** {estoque_atual} unidades")

        # 2. Formulário para o restante da venda
        with st.form("confirmar_venda", clear_on_submit=True):
            col_v1, col_v2 = st.columns(2)
            
            # Seleção do Cliente (Sempre aparece)
            lista_c = {r['nome']: r['id'] for _, r in df_clientes.iterrows()}
            cliente_nome = col_v1.selectbox("2. Escolha o Cliente", list(lista_c.keys()))
            
            # Preço (Já vem preenchido com o valor do cadastro)
            valor_venda = col_v2.number_input("3. Valor Final (R$)", value=preco_sugerido, format="%.2f")
            
            col_v3, col_v4 = st.columns(2)
            metodo_v = col_v3.selectbox("4. Método de Pagamento", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito", "Crediário"])
            parc_v = col_v4.number_input("5. Quantas Parcelas?", min_value=1, value=1)
            
            obs_v = st.text_area("Observações da Venda")
            
            btn_finalizar = st.form_submit_button("🛒 FINALIZAR VENDA")
            
            if btn_finalizar:
                if estoque_atual <= 0:
                    st.error("❌ Erro: Produto sem estoque disponível!")
                else:
                    try:
                        # Grava a Venda
                        v_res = supabase.table("vendas").insert({
                            "item": prod_sel_txt, 
                            "valor": valor_venda, 
                            "metodo_pagamento": metodo_v,
                            "observacao": obs_v
                        }).execute()
                        v_id = v_res.data[0]['id']
                        
                        # Gera as Parcelas
                        valor_p = valor_venda / parc_v
                        for i in range(parc_v):
                            venc_p = (datetime.now() + timedelta(days=30 * i)).date()
                            pago_p = True if metodo_v in ["Pix", "Dinheiro"] else False
                            supabase.table("parcelas").insert({
                                "venda_id": v_id, 
                                "cliente_id": lista_c[cliente_nome], 
                                "valor_parcela": valor_p,
                                "data_vencimento": str(venc_p), 
                                "pago": pago_p, 
                                "numero_parcela": i+1, 
                                "metodo_pagamento": metodo_v
                            }).execute()
                        
                        # Baixa no Estoque
                        supabase.table("produtos").update({"quantidade_estoque": estoque_atual - 1}).eq("codigo", cod_p).execute()
                        
                        st.success(f"✅ Venda de '{prod_sel_txt}' para '{cliente_nome}' realizada com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao processar venda: {e}")

# --- ABA 3: FINANCEIRO (CONTAS PAGAS E A PAGAR) ---
with tab_financeiro:
    st.header("📉 Financeiro")
    if not df_parcelas.empty and not df_clientes.empty:
        # Mescla tabelas para mostrar nomes
        df_fin = pd.merge(df_parcelas, df_clientes[['id', 'nome', 'cpf']], left_on='cliente_id', right_on='id', how='left')
        
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            st.subheader("⏳ A Receber")
            df_pend = df_fin[df_fin['pago'] == False]
            st.dataframe(df_pend[['nome', 'data_vencimento', 'valor_parcela', 'numero_parcela']], use_container_width=True, hide_index=True)
            
        with c_f2:
            st.subheader("✅ Recebidos")
            df_pago = df_fin[df_fin['pago'] == True]
            st.dataframe(df_pago[['nome', 'data_vencimento', 'valor_parcela']], use_container_width=True, hide_index=True)
            
        st.divider()
        st.subheader("Dar Baixa em Pagamento")
        cli_baixa = st.selectbox("Selecione o Cliente que está pagando", ["--"] + list(df_clientes['nome'].unique()))
        
        if cli_baixa != "--":
            df_filtrado = df_fin[(df_fin['nome'] == cli_baixa) & (df_fin['pago'] == False)]
            if not df_filtrado.empty:
                for idx, row in df_filtrado.iterrows():
                    col_b1, col_b2 = st.columns([3, 1])
                    col_b1.write(f"Parcela {row['numero_parcela']} - Vence em {row['data_vencimento']} - **R$ {row['valor_parcela']:.2f}**")
                    if col_b2.button("Confirmar Recebimento", key=f"pay_{row['id']}"):
                        supabase.table("parcelas").update({"pago": True}).eq("id", row['id']).execute()
                        st.success("Pagamento registrado!")
                        st.rerun()
            else:
                st.info("Este cliente não possui contas pendentes.")
    else:
        st.info("Aguardando lançamentos financeiros.")

# --- ABA 4: CLIENTES ---
with tab_clientes:
    st.header("👤 Cadastro de Clientes")
    with st.form("form_novo_cliente", clear_on_submit=True):
        c_c1, c_c2, c_c3 = st.columns(3)
        n_c = c_c1.text_input("Nome Completo")
        t_c = c_c2.text_input("Telefone (WhatsApp)")
        cpf_c = c_c3.text_input("CPF")
        if st.form_submit_button("💾 Salvar Cliente"):
            if n_c:
                supabase.table("clientes").insert({"nome": n_c, "telefone": t_c, "cpf": cpf_c}).execute()
                st.success("Cliente cadastrado com sucesso!")
                st.rerun()
            else:
                st.error("O nome é obrigatório.")
    
    st.subheader("Clientes Cadastrados")
    st.dataframe(df_clientes[['nome', 'telefone', 'cpf']], use_container_width=True, hide_index=True)

# --- ABA 5: ESTOQUE ---
with tab_estoque:
    st.header("📦 Cadastro de Mercadorias")
    with st.form("form_novo_produto", clear_on_submit=True):
        ce1, ce2, ce3, ce4 = st.columns([1, 2, 1, 1])
        prox_cod = str(len(df_produtos) + 1).zfill(3)
        cod_p = ce1.text_input("Código", value=prox_cod)
        nome_p = ce2.text_input("Nome da Peça")
        prec_p = ce3.number_input("Preço de Venda (R$)", min_value=0.0)
        qtd_p = ce4.number_input("Qtd Inicial", min_value=0, step=1)
        if st.form_submit_button("💾 Salvar Produto"):
            if nome_p:
                supabase.table("produtos").insert({
                    "codigo": cod_p, "nome": nome_p, "preco_venda": prec_p, "quantidade_estoque": qtd_p
                }).execute()
                st.success("Produto adicionado ao estoque!")
                st.rerun()
    
    st.subheader("Inventário Atual")
    st.dataframe(df_produtos[['codigo', 'nome', 'preco_venda', 'quantidade_estoque']], use_container_width=True, hide_index=True)

# --- 7. RODAPÉ ---
st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
