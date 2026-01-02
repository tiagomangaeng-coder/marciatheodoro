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
    [data-testid="stMetricValue"] { color: #8b5e3c !important; }
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

# --- 3. CONEXÃO E DADOS ---
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

def load_data():
    try:
        v_res = supabase.table("vendas").select("*").order("data", desc=True).execute()
        c_res = supabase.table("clientes").select("*").order("nome").execute()
        p_res = supabase.table("produtos").select("*").order("codigo").execute()
        par_res = supabase.table("parcelas").select("*").execute()

        df_v = pd.DataFrame(v_res.data) if v_res.data else pd.DataFrame(columns=['id', 'data', 'item', 'valor', 'metodo_pagamento'])
        df_c = pd.DataFrame(c_res.data) if c_res.data else pd.DataFrame(columns=['id', 'nome', 'telefone', 'cpf'])
        df_p = pd.DataFrame(p_res.data) if p_res.data else pd.DataFrame(columns=['id', 'codigo', 'nome', 'preco_venda', 'quantidade_estoque'])
        df_par = pd.DataFrame(par_res.data) if par_res.data else pd.DataFrame(columns=['id', 'venda_id', 'cliente_id', 'valor_parcela', 'data_vencimento', 'pago', 'numero_parcela', 'metodo_pagamento'])
        
        return df_v, df_c, df_p, df_par
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 4. FUNÇÃO PDF ATUALIZADA (AGRUPADA POR VENDA) ---
def gerar_pdf_financeiro(df_cli, df_parc, df_vendas, tipo="Consolidado"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    pdf.cell(0, 10, f"RELATÓRIO FINANCEIRO {tipo.upper()}", ln=True, align='C')
    pdf.set_font("helvetica", '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)

    if tipo == "Consolidado":
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(80, 10, "Cliente", 1, 0, 'C', True)
        pdf.cell(50, 10, "WhatsApp", 1, 0, 'C', True)
        pdf.cell(60, 10, "Pendente Total (R$)", 1, 1, 'C', True)
        pdf.set_font("helvetica", '', 10)
        for _, cli in df_cli.iterrows():
            dev = df_parc[(df_parc['cliente_id'] == cli['id']) & (df_parc['pago'] == False)]['valor_parcela'].sum() if not df_parc.empty else 0
            if dev > 0:
                pdf.cell(80, 10, str(cli['nome']), 1); pdf.cell(50, 10, str(cli['telefone']), 1); pdf.cell(60, 10, f"{dev:,.2f}", 1, 1, 'R')
    else:
        # EXTRATO INDIVIDUAL AGRUPADO POR VENDA
        for _, cli in df_cli.iterrows():
            pdf.set_font("helvetica", 'B', 14); pdf.set_text_color(139, 94, 60)
            pdf.cell(0, 10, f"CLIENTE: {cli['nome']}", ln=True)
            pdf.ln(2)
            
            parc_cli = df_parc[df_parc['cliente_id'] == cli['id']] if not df_parc.empty else pd.DataFrame()
            if not parc_cli.empty:
                vendas_ids = parc_cli['venda_id'].unique()
                for v_id in vendas_ids:
                    # Dados da Venda
                    venda_info = df_vendas[df_vendas['id'] == v_id]
                    if not venda_info.empty:
                        v = venda_info.iloc[0]
                        data_v = pd.to_datetime(v['data']).strftime('%d/%m/%Y')
                        pdf.set_font("helvetica", 'B', 11); pdf.set_text_color(0, 0, 0)
                        pdf.cell(0, 8, f"Compra em {data_v} - Itens: {v['item']} - Total: R$ {v['valor']:.2f}", ln=True)
                        
                        # Tabela de Parcelas desta Venda
                        pdf.set_font("helvetica", 'B', 9); pdf.set_fill_color(245, 245, 245)
                        pdf.cell(40, 7, "Vencimento", 1, 0, 'C', True)
                        pdf.cell(60, 7, "Parcela", 1, 0, 'C', True)
                        pdf.cell(40, 7, "Valor (R$)", 1, 0, 'C', True)
                        pdf.cell(45, 7, "Status", 1, 1, 'C', True)
                        
                        pdf.set_font("helvetica", '', 9)
                        parc_venda = parc_cli[parc_cli['venda_id'] == v_id].sort_values('numero_parcela')
                        for _, p in parc_venda.iterrows():
                            pdf.cell(40, 7, pd.to_datetime(p['data_vencimento']).strftime('%d/%m/%Y'), 1, 0, 'C')
                            pdf.cell(60, 7, f"Parcela {p['numero_parcela']}", 1)
                            pdf.cell(40, 7, f"{p['valor_parcela']:.2f}", 1, 0, 'R')
                            pdf.cell(45, 7, "PAGO" if p['pago'] else "PENDENTE", 1, 1, 'C')
                        pdf.ln(5)
    return bytes(pdf.output())

# --- 5. CARREGAMENTO ---
df_v, df_c, df_p, df_par = load_data()

# --- 6. INTERFACE ---
tab_dash, tab_venda, tab_financeiro, tab_clientes, tab_estoque = st.tabs(["📊 Dashboard", "🛒 Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque"])

# --- ABA DASHBOARD ---
with tab_dash:
    st.header("📊 Inteligência de Negócio")
    col_f1, col_f2 = st.columns(2)
    data_inicio = col_f1.date_input("Início do Período", value=date.today() - timedelta(days=30))
    data_fim = col_f2.date_input("Fim do Período", value=date.today() + timedelta(days=90))
    if not df_v.empty:
        df_v['data_dt'] = pd.to_datetime(df_v['data']).dt.date
        df_v_filtrado = df_v[(df_v['data_dt'] >= data_inicio) & (df_v['data_dt'] <= data_fim)]
        df_par['venc_dt'] = pd.to_datetime(df_par['data_vencimento']).dt.date
        df_par_filtrado = df_par[(df_par['venc_dt'] >= data_inicio) & (df_par['venc_dt'] <= data_fim)]
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", f"R$ {df_v_filtrado['valor'].sum():,.2f}")
        m2.metric("Já Recebido", f"R$ {df_par_filtrado[df_par_filtrado['pago'] == True]['valor_parcela'].sum():,.2f}")
        m3.metric("A Receber", f"R$ {df_par_filtrado[df_par_filtrado['pago'] == False]['valor_parcela'].sum():,.2f}")

# --- ABA VENDAS ---
with tab_venda:
    st.header("🛍️ Realizar Venda")
    c1, col_carrinho = st.columns([1, 1.5])
    with c1:
        if not df_p.empty:
            list_p = [f"{r['codigo']} - {r['nome']}" for _, r in df_p.iterrows()]
            sel_p = st.selectbox("Produto", list_p)
            peca = df_p[df_p['codigo'] == sel_p.split(" - ")[0]].iloc[0]
            pr_u = st.number_input("Preço Unitário", value=float(peca['preco_venda']))
            qt_v = st.number_input("Quantidade", min_value=1, step=1)
            if st.button("➕ Adicionar"):
                if qt_v <= peca['quantidade_estoque']:
                    st.session_state.carrinho.append({"cod": peca['codigo'], "nome": peca['nome'], "qtd": int(qt_v), "pr": float(pr_u), "tot": float(pr_u * qt_v)})
                    st.rerun()
                else: st.error("Estoque baixo!")
    with col_carrinho:
        if st.session_state.carrinho:
            st.table(pd.DataFrame(st.session_state.carrinho)[['nome', 'qtd', 'pr', 'tot']])
            with st.expander("🔧 Editar ou Remover Item"):
                idx_edit = st.selectbox("Item", range(len(st.session_state.carrinho)), format_func=lambda x: st.session_state.carrinho[x]['nome'])
                col_e1, col_e2 = st.columns(2)
                nq = col_e1.number_input("Nova Qtd", value=st.session_state.carrinho[idx_edit]['qtd'])
                np_pr = col_e2.number_input("Novo Preço", value=st.session_state.carrinho[idx_edit]['pr'])
                if st.button("🔄 Atualizar"):
                    st.session_state.carrinho[idx_edit]['qtd'], st.session_state.carrinho[idx_edit]['pr'], st.session_state.carrinho[idx_edit]['tot'] = int(nq), float(np_pr), float(nq * np_pr)
                    st.rerun()
                if st.button("❌ Remover"): st.session_state.carrinho.pop(idx_edit); st.rerun()
            st.divider()
            with st.form("fechar"):
                cli_v = st.selectbox("Cliente", list(df_c['nome'].unique()) if not df_c.empty else ["Nenhum"])
                met = st.selectbox("Método", ["Crediário", "Pix", "Dinheiro", "Cartão"])
                par = st.number_input("Parcelas", min_value=1, value=1)
                dat = st.date_input("1º Vencimento", value=date.today())
                if st.form_submit_button("✅ FINALIZAR VENDA"):
                    total_v = sum(i['tot'] for i in st.session_state.carrinho)
                    v_res = supabase.table("vendas").insert({"item": ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho]), "valor": total_v, "metodo_pagamento": met}).execute()
                    vid = v_res.data[0]['id']
                    id_c = int(df_c[df_c['nome'] == cli_v]['id'].iloc[0])
                    for n in range(int(par)):
                        dv = pd.to_datetime(dat) + pd.DateOffset(months=n)
                        supabase.table("parcelas").insert({"venda_id": vid, "cliente_id": id_c, "valor_parcela": float(total_v/par), "data_vencimento": dv.strftime('%Y-%m-%d'), "pago": (met in ["Pix", "Dinheiro"]), "numero_parcela": n + 1, "metodo_pagamento": met}).execute()
                    for item in st.session_state.carrinho:
                        st_at = int(supabase.table("produtos").select("quantidade_estoque").eq("codigo", item['cod']).execute().data[0]['quantidade_estoque'])
                        supabase.table("produtos").update({"quantidade_estoque": st_at - item['qtd']}).eq("codigo", item['cod']).execute()
                    st.session_state.carrinho = []; st.success("Venda salva!"); time.sleep(1); st.rerun()

# --- ABA FINANCEIRO (CORREÇÕES SOLICITADAS) ---
with tab_financeiro:
    st.header("📉 Gestão Financeira")
    st.subheader("📋 Relatório Consolidado (Geral)")
    if not df_c.empty:
        # Removido rádio de escolha: agora apenas Consolidado como padrão geral
        pdf_consolidado = gerar_pdf_financeiro(df_c, df_par, df_v, "Consolidado")
        st.download_button("📥 Baixar Relatório Consolidado Geral", data=pdf_consolidado, file_name="financeiro_consolidado.pdf")
    
    st.divider()
    st.subheader("👤 Extrato Organizado por Venda")
    ops_cli = ["--"] + list(df_c['nome'].unique()) if not df_c.empty else ["--"]
    cli_f = st.selectbox("Selecione o Cliente", ops_cli)
    
    if cli_f != "--":
        # Botão PDF Individual (Agora Agrupado por Venda)
        pdf_ind = gerar_pdf_financeiro(df_c[df_c['nome'] == cli_f], df_par, df_v, "Individual")
        st.download_button(f"📥 Baixar Extrato de {cli_f}", data=pdf_ind, file_name=f"extrato_{cli_f}.pdf")
        
        # Visualização na Tela Organizada por Venda
        id_cliente = int(df_c[df_c['nome'] == cli_f]['id'].iloc[0])
        parc_cli = df_par[df_par['cliente_id'] == id_cliente]
        vendas_ids = parc_cli['venda_id'].unique()
        
        for v_id in vendas_ids:
            v_info = df_v[df_v['id'] == v_id]
            if not v_info.empty:
                v = v_info.iloc[0]
                dt_v = pd.to_datetime(v['data']).strftime('%d/%m/%Y')
                with st.container():
                    st.markdown(f"#### 🛒 Compra em {dt_v} - Total: R$ {v['valor']:.2f}")
                    st.caption(f"Itens: {v['item']}")
                    
                    parc_venda = parc_cli[parc_cli['venda_id'] == v_id].sort_values('numero_parcela')
                    for _, r in parc_venda.iterrows():
                        c1, c2, c3 = st.columns([3, 1, 1])
                        dt_p = pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')
                        c1.write(f"{'✅' if r['pago'] else '⏳'} Parcela {r['numero_parcela']} - {dt_p} - R$ {r['valor_parcela']:.2f}")
                        if not r['pago'] and c2.button("Baixa", key=f"bx_{r['id']}"):
                            supabase.table("parcelas").update({"pago": True}).eq("id", int(r['id'])).execute(); st.rerun()
                        if c3.button("🗑️", key=f"del_{r['id']}"):
                            supabase.table("parcelas").delete().eq("id", int(r['id'])).execute(); st.rerun()
                    st.divider()

# --- ABA CLIENTES ---
with tab_clientes:
    st.header("👤 Clientes")
    with st.form("c_cli"):
        n, t, cp = st.text_input("Nome"), st.text_input("Whats"), st.text_input("CPF")
        if st.form_submit_button("Salvar"):
            if n: supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": cp}).execute(); st.rerun()
    for _, cli in df_c.iterrows():
        with st.expander(f"Editar: {cli['nome']}"):
            en, et, ec = st.text_input("Nome", cli['nome'], key=f"cn_{cli['id']}"), st.text_input("Whats", cli['telefone'], key=f"ct_{cli['id']}"), st.text_input("CPF", cli.get('cpf',''), key=f"cc_{cli['id']}")
            if st.button("💾 Atualizar", key=f"cu_{cli['id']}"):
                supabase.table("clientes").update({"nome": en, "telefone": et, "cpf": ec}).eq("id", int(cli['id'])).execute(); st.rerun()
            if st.button("🗑️ Excluir", key=f"cd_{cli['id']}"):
                supabase.table("clientes").delete().eq("id", int(cli['id'])).execute(); st.rerun()

# --- ABA ESTOQUE ---
with tab_estoque:
    st.header("📦 Estoque")
    with st.form("cad_est"):
        e1, e2, e3, e4 = st.columns(4)
        c_p, n_p, pr_p, q_p = e1.text_input("Cód"), e2.text_input("Peça"), e3.number_input("Preço"), e4.number_input("Qtd")
        if st.form_submit_button("Cadastrar"):
            if c_p: supabase.table("produtos").insert({"codigo": str(c_p), "nome": str(n_p), "preco_venda": float(pr_p), "quantidade_estoque": int(q_p)}).execute(); st.rerun()
    for _, pr in df_p.iterrows():
        with st.expander(f"{pr['codigo']} - {pr['nome']} ({int(pr['quantidade_estoque'])} un)"):
            nn, nq = st.text_input("Nome", pr['nome'], key=f"p_n_{pr['id']}"), st.number_input("Estoque", value=int(pr['quantidade_estoque']), key=f"p_q_{pr['id']}")
            if st.button("💾 Salvar", key=f"p_u_{pr['id']}"):
                supabase.table("produtos").update({"nome": nn, "quantidade_estoque": int(nq)}).eq("id", int(pr['id'])).execute(); st.rerun()
            if st.button("🗑️ Deletar", key=f"p_d_{pr['id']}"):
                supabase.table("produtos").delete().eq("id", int(pr['id'])).execute(); st.rerun()

st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
