import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import time
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Marcia Theodoro - Gestão Pro", page_icon="👗", layout="wide")

st.markdown("""
    <style>
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    .intro-container { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 80vh; text-align: center; }
    .intro-title { font-size: 5rem; font-family: 'serif'; color: #8b5e3c; animation: blink 1.5s infinite; letter-spacing: 5px; text-transform: uppercase; }
    .intro-subtitle { font-size: 2rem; color: #a68a64; letter-spacing: 10px; text-transform: uppercase; animation: blink 1.5s infinite; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #fcfaf8; color: #8b5e3c; text-align: center; padding: 10px; font-weight: bold; z-index: 100; }
    .stTabs [aria-selected="true"] { background-color: #8b5e3c !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LÓGICA DE ABERTURA ---
if 'intro_visto' not in st.session_state:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown('<div class="intro-container"><div class="intro-title">Márcia Theodoro</div><div class="intro-subtitle">Boutique</div></div>', unsafe_allow_html=True)
    time.sleep(5)
    st.session_state['intro_visto'] = True
    placeholder.empty()
    st.rerun()

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# --- 3. CONEXÃO E CARREGAMENTO BLINDADO ---
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

def load_data():
    """Carrega dados garantindo que as colunas existam mesmo se o banco estiver vazio"""
    try:
        v_data = supabase.table("vendas").select("*").order("data", desc=True).execute().data
        c_data = supabase.table("clientes").select("*").order("nome").execute().data
        p_data = supabase.table("produtos").select("*").order("codigo").execute().data
        par_data = supabase.table("parcelas").select("*").execute().data

        df_v = pd.DataFrame(v_data) if v_data else pd.DataFrame(columns=['id', 'data', 'item', 'valor', 'metodo_pagamento'])
        df_c = pd.DataFrame(c_data) if c_data else pd.DataFrame(columns=['id', 'nome', 'telefone', 'cpf'])
        df_p = pd.DataFrame(p_data) if p_data else pd.DataFrame(columns=['id', 'codigo', 'nome', 'preco_venda', 'quantidade_estoque'])
        df_par = pd.DataFrame(par_data) if par_data else pd.DataFrame(columns=['id', 'venda_id', 'cliente_id', 'valor_parcela', 'data_vencimento', 'pago', 'numero_parcela', 'metodo_pagamento'])
        
        return df_v, df_c, df_p, df_par
    except Exception as e:
        st.error(f"Erro ao conectar com o banco: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 4. FUNÇÃO PDF ---
def gerar_pdf_financeiro(df_cli, df_parc, tipo="Consolidado"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    pdf.cell(0, 10, f"RELATÓRIO FINANCEIRO {tipo.upper()}", ln=True, align='C')
    pdf.set_font("helvetica", '', 10)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    
    if tipo == "Consolidado" and not df_cli.empty:
        pdf.cell(80, 10, "Cliente", 1); pdf.cell(50, 10, "WhatsApp", 1); pdf.cell(60, 10, "Pendente", 1, 1)
        for _, cli in df_cli.iterrows():
            dev = df_parc[(df_parc['cliente_id'] == cli['id']) & (df_parc['pago'] == False)]['valor_parcela'].sum() if not df_parc.empty else 0
            if dev > 0:
                pdf.cell(80, 10, str(cli['nome']), 1); pdf.cell(50, 10, str(cli['telefone']), 1); pdf.cell(60, 10, f"{dev:,.2f}", 1, 1)
    return bytes(pdf.output())

# --- 5. CARREGAMENTO DOS DADOS ---
df_v, df_c, df_p, df_par = load_data()

# --- 6. INTERFACE POR ABAS ---
tab_venda, tab_financeiro, tab_clientes, tab_estoque, tab_dash = st.tabs(["🛒 Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque", "📊 Dashboard"])

# --- ABA VENDAS ---
with tab_venda:
    st.header("🛍️ Realizar Venda")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        if not df_p.empty:
            list_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_p.iterrows()]
            sel_p = st.selectbox("Produto", list_p)
            peca = df_p[df_p['codigo'] == sel_p.split(" - ")[0]].iloc[0]
            pr_u = st.number_input("Preço Unitário", value=float(peca['preco_venda']))
            qt_v = st.number_input("Quantidade", min_value=1, step=1)
            if st.button("➕ Adicionar"):
                st.session_state.carrinho.append({"cod": peca['codigo'], "nome": peca['nome'], "qtd": int(qt_v), "pr": float(pr_u), "tot": float(pr_u * qt_v)})
                st.rerun()
    with c2:
        if st.session_state.carrinho:
            st.table(pd.DataFrame(st.session_state.carrinho)[['nome', 'qtd', 'pr', 'tot']])
            total_v = sum(i['tot'] for i in st.session_state.carrinho)
            
            with st.form("fechar"):
                cli_v = st.selectbox("Cliente", list(df_c['nome'].unique()) if not df_c.empty else ["Nenhum"])
                met = st.selectbox("Metodo", ["Crediário", "Pix", "Dinheiro", "Cartão"])
                par = st.number_input("Parcelas", min_value=1, value=1)
                dat = st.date_input("1º Vencimento", value=date.today())
                if st.form_submit_button("✅ FINALIZAR VENDA"):
                    if df_c.empty: 
                        st.error("Cadastre um cliente primeiro!")
                    else:
                        txt_i = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho])
                        vid = supabase.table("vendas").insert({"item": txt_i, "valor": float(total_v), "metodo_pagamento": met}).execute().data[0]['id']
                        id_c = int(df_c[df_c['nome'] == cli_v]['id'].iloc[0])
                        for n in range(int(par)):
                            dv = pd.to_datetime(dat) + pd.DateOffset(months=n)
                            supabase.table("parcelas").insert({"venda_id": vid, "cliente_id": id_c, "valor_parcela": float(total_v/par), "data_vencimento": dv.strftime('%Y-%m-%d'), "pago": (met in ["Pix", "Dinheiro"]), "numero_parcela": n + 1, "metodo_pagamento": met}).execute()
                        for i in st.session_state.carrinho:
                            q_at = int(df_p[df_p['codigo'] == i['cod']]['quantidade_estoque'].iloc[0])
                            supabase.table("produtos").update({"quantidade_estoque": q_at - i['qtd']}).eq("codigo", i['cod']).execute()
                        st.session_state.carrinho = []; st.success("Venda salva!"); time.sleep(1); st.rerun()

# --- ABA FINANCEIRO (COM PROTEÇÃO DE MERGE) ---
with tab_financeiro:
    st.header("📉 Financeiro")
    if df_par.empty or df_c.empty:
        st.info("O banco de dados financeiro está vazio. Realize vendas para ver os extratos.")
    else:
        cli_f = st.selectbox("Escolha o Cliente", ["--"] + list(df_c['nome'].unique()))
        if cli_f != "--":
            # Merge seguro: as colunas agora existem garantidamente pela função load_data()
            df_f = pd.merge(df_par, df_c[['id', 'nome']], left_on='cliente_id', right_on='id', suffixes=('_p', '_c'))
            df_cli = df_f[df_f['nome'] == cli_f].sort_values('data_vencimento')
            for _, r in df_cli.iterrows():
                with st.expander(f"Parc {r['numero_parcela']} - {pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')} - R$ {r['valor_parcela']:.2f}"):
                    c1, c2 = st.columns(2)
                    if not r['pago'] and c1.button("✅ Receber", key=f"bx_{r['id_p']}"):
                        supabase.table("parcelas").update({"pago": True}).eq("id", int(r['id_p'])).execute(); st.rerun()
                    if c2.button("🗑️ Excluir", key=f"del_p_{r['id_p']}"):
                        supabase.table("parcelas").delete().eq("id", int(r['id_p'])).execute(); st.rerun()

# --- ABA CLIENTES ---
with tab_clientes:
    st.header("👤 Cadastro de Clientes")
    with st.form("c_cli", clear_on_submit=True):
        n, t, cp = st.text_input("Nome Completo"), st.text_input("WhatsApp"), st.text_input("CPF")
        if st.form_submit_button("Salvar"):
            if n: supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": cp}).execute(); st.rerun()
    if not df_c.empty:
        for _, cli in df_c.iterrows():
            with st.expander(f"Editar: {cli['nome']}"):
                en = st.text_input("Nome", cli['nome'], key=f"cn_{cli['id']}")
                et = st.text_input("Whats", cli['telefone'], key=f"ct_{cli['id']}")
                ec = st.text_input("CPF", cli.get('cpf', ''), key=f"cc_{cli['id']}")
                if st.button("💾 Atualizar", key=f"cu_{cli['id']}"):
                    supabase.table("clientes").update({"nome": en, "telefone": et, "cpf": ec}).eq("id", int(cli['id'])).execute(); st.rerun()
                if st.button("🗑️ Excluir", key=f"cd_{cli['id']}"):
                    supabase.table("clientes").delete().eq("id", int(cli['id'])).execute(); st.rerun()

# --- ABA ESTOQUE ---
with tab_estoque:
    st.header("📦 Estoque")
    with st.form("cad_e", clear_on_submit=True):
        e1, e2, e3, e4 = st.columns(4)
        cp, np, pv, qi = e1.text_input("Cód"), e2.text_input("Peça"), e3.number_input("Preço"), e4.number_input("Qtd", min_value=0)
        if st.form_submit_button("Cadastrar"):
            if cp: supabase.table("produtos").insert({"codigo": str(cp), "nome": str(np), "preco_venda": float(pv), "quantidade_estoque": int(qi)}).execute(); st.rerun()
    if not df_p.empty:
        for _, pr in df_p.iterrows():
            with st.expander(f"{pr['codigo']} - {pr['nome']}"):
                eq = st.number_input("Estoque", value=int(pr['quantidade_estoque']), key=f"pq_{pr['id']}")
                if st.button("💾 Atualizar", key=f"pu_{pr['id']}"):
                    supabase.table("produtos").update({"quantidade_estoque": int(eq)}).eq("id", int(pr['id'])).execute(); st.rerun()
                if st.button("🗑️ Excluir", key=f"pd_{pr['id']}"):
                    supabase.table("produtos").delete().eq("id", int(pr['id'])).execute(); st.rerun()

# --- ABA DASHBOARD ---
with tab_dash:
    if not df_v.empty:
        st.metric("Faturamento", f"R$ {df_v['valor'].sum():,.2f}")
        df_v['data_br'] = pd.to_datetime(df_v['data']).dt.strftime('%d/%m/%Y')
        st.plotly_chart(px.bar(df_v, x='data_br', y='valor', title="Vendas por Dia", color_discrete_sequence=['#8b5e3c']), use_container_width=True)

st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
