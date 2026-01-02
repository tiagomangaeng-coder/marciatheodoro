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
    [data-testid="stMetricValue"] { color: #8b5e3c !important; font-size: 1.8rem; }
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

# --- 3. CONEXÃO E CARREGAMENTO ---
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

def load_data():
    v = supabase.table("vendas").select("*").order("data", desc=True).execute()
    c = supabase.table("clientes").select("*").order("nome").execute()
    p = supabase.table("produtos").select("*").order("codigo").execute()
    par = supabase.table("parcelas").select("*").execute()
    return pd.DataFrame(v.data), pd.DataFrame(c.data), pd.DataFrame(p.data), pd.DataFrame(par.data)

# --- 4. FUNÇÕES DE PDF ---
def gerar_pdf_financeiro(df_cli, df_parc, tipo="Consolidado"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    titulo = f"RELATÓRIO FINANCEIRO {tipo.upper()}"
    pdf.cell(0, 10, titulo, ln=True, align='C')
    pdf.set_font("helvetica", '', 10)
    pdf.cell(0, 10, f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(5)

    if tipo == "Consolidado":
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(80, 10, "Cliente", 1, 0, 'C', True)
        pdf.cell(50, 10, "WhatsApp", 1, 0, 'C', True)
        pdf.cell(60, 10, "Saldo Devedor (R$)", 1, 1, 'C', True)
        if not df_cli.empty:
            for _, cli in df_cli.iterrows():
                dev = df_parc[(df_parc['cliente_id'] == cli['id']) & (df_parc['pago'] == False)]['valor_parcela'].sum() if not df_parc.empty else 0
                if dev > 0:
                    pdf.cell(80, 10, str(cli['nome']), 1)
                    pdf.cell(50, 10, str(cli['telefone']), 1)
                    pdf.cell(60, 10, f"{dev:,.2f}", 1, 1, 'R')
    else:
        if not df_cli.empty:
            for _, cli in df_cli.iterrows():
                pdf.set_font("helvetica", 'B', 12); pdf.cell(0, 10, f"Cliente: {cli['nome']}", ln=True)
                pdf.set_font("helvetica", '', 10)
                parc_cli = df_parc[df_parc['cliente_id'] == cli['id']].sort_values('data_vencimento') if not df_parc.empty else pd.DataFrame()
                for _, p in parc_cli.iterrows():
                    dt = pd.to_datetime(p['data_vencimento']).strftime('%d/%m/%Y')
                    pdf.cell(40, 8, dt, 1); pdf.cell(80, 8, f"Parc {p['numero_parcela']}", 1); pdf.cell(40, 8, f"{p['valor_parcela']:.2f}", 1, 1)
                pdf.ln(5)
    return bytes(pdf.output())

# --- 5. CARREGAMENTO ---
df_v, df_c, df_p, df_par = load_data()

# --- 6. INTERFACE POR ABAS ---
tab_venda, tab_financeiro, tab_clientes, tab_estoque, tab_dash = st.tabs([
    "🛒 Venda", "📉 Financeiro", "👤 Clientes", "📦 Estoque", "📊 Dashboard"
])

# --- ABA VENDAS ---
with tab_venda:
    st.header("🛍️ Carrinho de Compras")
    col_add, col_resumo = st.columns([1, 1.5])
    
    with col_add:
        st.subheader("Adicionar Peça")
        if not df_p.empty and 'nome' in df_p.columns:
            it_l = [f"{r['codigo']} - {r['nome']}" for _, r in df_p.iterrows()]
            it_sel = st.selectbox("Escolha o Produto", it_l)
            cod_ref = it_sel.split(" - ")[0]
            peca = df_p[df_p['codigo'] == cod_ref].iloc[0]
            
            pr_un = st.number_input("Preço Unitário (R$)", value=float(peca['preco_venda']))
            qt_v = st.number_input("Quantidade", min_value=1, step=1)
            
            if st.button("➕ Adicionar ao Carrinho"):
                if qt_v <= peca['quantidade_estoque']:
                    st.session_state.carrinho.append({
                        "cod": peca['codigo'], "nome": peca['nome'], 
                        "qtd": int(qt_v), "pr": pr_un, "tot": pr_un * qt_v
                    })
                    st.rerun()
                else: st.error("Estoque insuficiente!")
        else: st.warning("Cadastre produtos no estoque primeiro.")
    
    with col_resumo:
        st.subheader("Itens no Carrinho")
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            st.table(df_cart[['nome', 'qtd', 'pr', 'tot']])
            total_venda = df_cart['tot'].sum()
            st.markdown(f"### Total: R$ {total_venda:,.2f}")

            with st.expander("🔧 Editar Item do Carrinho"):
                idx = st.selectbox("Selecione o Item", range(len(st.session_state.carrinho)), 
                                   format_func=lambda x: f"{st.session_state.carrinho[x]['nome']}")
                c_e1, c_e2 = st.columns(2)
                nova_q = c_e1.number_input("Nova Qtd", value=st.session_state.carrinho[idx]['qtd'], key=f"q_{idx}")
                novo_p = c_e2.number_input("Novo Preço", value=st.session_state.carrinho[idx]['pr'], key=f"p_{idx}")
                
                b1, b2 = st.columns(2)
                if b1.button("🔄 Atualizar"):
                    st.session_state.carrinho[idx]['qtd'] = nova_q
                    st.session_state.carrinho[idx]['pr'] = novo_p
                    st.session_state.carrinho[idx]['tot'] = nova_q * novo_p
                    st.rerun()
                if b2.button("❌ Remover"):
                    st.session_state.carrinho.pop(idx)
                    st.rerun()

            st.divider()
            with st.form("fechar_caixa"):
                # CORREÇÃO KEYERROR: VERIFICAÇÃO DE CLIENTES
                if not df_c.empty and 'nome' in df_c.columns:
                    lista_nomes_clientes = list(df_c['nome'].unique())
                else:
                    lista_nomes_clientes = []

                cli_v = st.selectbox("Cliente", lista_nomes_clientes if lista_nomes_clientes else ["Nenhum cliente cadastrado"])
                
                met = st.selectbox("Forma de Pagamento", ["Crediário", "Pix", "Dinheiro", "Cartão"])
                parc_n = st.number_input("Parcelas", min_value=1, value=1)
                venc1 = st.date_input("1º Vencimento", value=date.today())
                
                if st.form_submit_button("✅ FINALIZAR VENDA"):
                    if not lista_nomes_clientes:
                        st.error("Cadastre um cliente antes de finalizar.")
                    else:
                        txt_itens = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho])
                        vid = supabase.table("vendas").insert({"item": txt_itens, "valor": total_venda, "metodo_pagamento": met}).execute().data[0]['id']
                        
                        for i in range(parc_n):
                            dt_v = pd.to_datetime(venc1) + pd.DateOffset(months=i)
                            supabase.table("parcelas").insert({
                                "venda_id": vid, "cliente_id": df_c[df_c['nome']==cli_v]['id'].values[0],
                                "valor_parcela": total_venda/parc_n, "data_vencimento": dt_v.strftime('%Y-%m-%d'),
                                "pago": (met in ["Pix", "Dinheiro"]), "numero_parcela": i+1, "metodo_pagamento": met
                            }).execute()
                        
                        for item in st.session_state.carrinho:
                            q_at = df_p[df_p['codigo']==item['cod']]['quantidade_estoque'].values[0]
                            supabase.table("produtos").update({"quantidade_estoque": int(q_at - item['qtd'])}).eq("codigo", item['cod']).execute()
                        
                        st.session_state.carrinho = []; st.success("Venda Concluída!"); time.sleep(1); st.rerun()
        else: st.info("Carrinho vazio.")

# --- ABA FINANCEIRO ---
with tab_financeiro:
    st.header("📉 Financeiro")
    t_rel = st.radio("Relatório Geral", ["Consolidado", "Completo"], horizontal=True)
    st.download_button(f"📥 Baixar Relatório {t_rel}", gerar_pdf_financeiro(df_c, df_par, t_rel), f"fin_{t_rel.lower()}.pdf")
    
    st.divider()
    
    # CORREÇÃO KEYERROR: VERIFICAÇÃO DE CLIENTES NO FINANCEIRO
    if not df_c.empty and 'nome' in df_c.columns:
        opcoes_clientes = ["--"] + list(df_c['nome'].unique())
    else:
        opcoes_clientes = ["--"]

    cli_f = st.selectbox("Ver Extrato/Dar Baixa", opcoes_clientes)
    
    if cli_f != "--":
        df_f = pd.merge(df_par, df_c[['id', 'nome']], left_on='cliente_id', right_on='id', suffixes=('_p', '_c'))
        df_cli = df_f[df_f['nome'] == cli_f].sort_values('data_vencimento')
        for _, r in df_cli.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            dt_br = pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')
            c1.write(f"Parc {r['numero_parcela']} - {dt_br} - R$ {r['valor_parcela']:.2f}")
            if not r['pago'] and c2.button("Receber", key=f"rec_{r['id_p']}"):
                supabase.table("parcelas").update({"pago": True}).eq("id", r['id_p']).execute(); st.rerun()
            if c3.button("🗑️", key=f"del_p_{r['id_p']}"):
                supabase.table("parcelas").delete().eq("id", r['id_p']).execute(); st.rerun()

# --- ABA CLIENTES ---
with tab_clientes:
    st.header("👤 Clientes")
    with st.form("cad_c", clear_on_submit=True):
        n, t, cp = st.text_input("Nome"), st.text_input("Whats"), st.text_input("CPF")
        if st.form_submit_button("Salvar"):
            supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": cp}).execute(); st.rerun()
    if not df_c.empty:
        for _, cli in df_c.iterrows():
            with st.expander(f"Editar: {cli['nome']}"):
                en = st.text_input("Nome", cli['nome'], key=f"cn_{cli['id']}")
                et = st.text_input("Whats", cli['telefone'], key=f"ct_{cli['id']}")
                if st.button("💾 Atualizar", key=f"cu_{cli['id']}"):
                    supabase.table("clientes").update({"nome": en, "telefone": et}).eq("id", cli['id']).execute(); st.rerun()
                if st.button("🗑️ Excluir Cliente", key=f"cd_{cli['id']}"):
                    supabase.table("clientes").delete().eq("id", cli['id']).execute(); st.rerun()

# --- ABA ESTOQUE ---
with tab_estoque:
    st.header("📦 Estoque")
    with st.form("cad_e", clear_on_submit=True):
        e1, e2, e3, e4 = st.columns(4)
        c_p = e1.text_input("Cód"); n_p = e2.text_input("Peça"); p_p = e3.number_input("Preço"); q_p = e4.number_input("Qtd", min_value=0, step=1)
        if st.form_submit_button("Cadastrar"):
            supabase.table("produtos").insert({"codigo": c_p, "nome": n_p, "preco_venda": p_p, "quantidade_estoque": q_p}).execute(); st.rerun()
    if not df_p.empty:
        for _, pr in df_p.iterrows():
            with st.expander(f"{pr['codigo']} - {pr['nome']}"):
                eq = st.number_input("Estoque", value=int(pr['quantidade_estoque']), key=f"pq_{pr['id']}")
                if st.button("💾 Atualizar", key=f"pu_{pr['id']}"):
                    supabase.table("produtos").update({"quantidade_estoque": eq}).eq("id", pr['id']).execute(); st.rerun()
                if st.button("🗑️ Excluir Peça", key=f"pd_{pr['id']}"):
                    supabase.table("produtos").delete().eq("id", pr['id']).execute(); st.rerun()

# --- ABA DASHBOARD ---
with tab_dash:
    st.header("📊 Dash")
    if not df_v.empty:
        st.metric("Faturamento", f"R$ {df_v['valor'].sum():,.2f}")
        st.plotly_chart(px.bar(df_v.groupby('metodo_pagamento')['valor'].sum().reset_index(), x='valor', y='metodo_pagamento', orientation='h', color_discrete_sequence=['#8b5e3c']), use_container_width=True)
    else:
        st.info("Sem dados para o dashboard.")

st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
