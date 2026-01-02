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

# --- 3. CONEXÃO E DADOS ---
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

def load_data():
    try:
        v = supabase.table("vendas").select("*").order("data", desc=True).execute()
        c = supabase.table("clientes").select("*").order("nome").execute()
        p = supabase.table("produtos").select("*").order("codigo").execute()
        par = supabase.table("parcelas").select("*").execute()
        return pd.DataFrame(v.data), pd.DataFrame(c.data), pd.DataFrame(p.data), pd.DataFrame(par.data)
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 4. FUNÇÃO PDF COM DATAS BR ---
def gerar_pdf_financeiro(df_cli, df_parc, tipo="Consolidado"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.set_text_color(139, 94, 60)
    pdf.cell(0, 10, f"RELATÓRIO FINANCEIRO {tipo.upper()}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("helvetica", '', 10)
    # DATA ATUAL NO FORMATO BR
    pdf.cell(0, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    
    if tipo == "Consolidado":
        pdf.cell(80, 10, "Cliente", 1); pdf.cell(50, 10, "WhatsApp", 1); pdf.cell(60, 10, "Pendente", 1, 1)
        for _, cli in df_cli.iterrows():
            dev = df_parc[(df_parc['cliente_id'] == cli['id']) & (df_parc['pago'] == False)]['valor_parcela'].sum() if not df_parc.empty else 0
            if dev > 0:
                pdf.cell(80, 10, str(cli['nome']), 1); pdf.cell(50, 10, str(cli['telefone']), 1); pdf.cell(60, 10, f"{dev:,.2f}", 1, 1)
    return bytes(pdf.output())

# --- 5. CARREGAMENTO ---
df_v, df_c, df_p, df_par = load_data()

# --- 6. INTERFACE ---
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
            st.subheader("Carrinho Atual")
            st.table(pd.DataFrame(st.session_state.carrinho)[['nome', 'qtd', 'pr', 'tot']])
            
            with st.form("fechar"):
                cli_v = st.selectbox("Cliente", list(df_c['nome'].unique()) if not df_c.empty else ["Nenhum"])
                met = st.selectbox("Metodo", ["Crediário", "Pix", "Dinheiro", "Cartão"])
                par = st.number_input("Parcelas", min_value=1, value=1)
                # FORMATO BR NO INPUT
                dat = st.date_input("Data do 1º Vencimento", value=date.today())
                if st.form_submit_button("✅ FINALIZAR VENDA"):
                    total_v = sum(i['tot'] for i in st.session_state.carrinho)
                    txt_i = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho])
                    vid = supabase.table("vendas").insert({"item": txt_i, "valor": float(total_v), "metodo_pagamento": met}).execute().data[0]['id']
                    id_c = int(df_c[df_c['nome'] == cli_v]['id'].iloc[0])
                    for n in range(int(par)):
                        dv = pd.to_datetime(dat) + pd.DateOffset(months=n)
                        # SALVA NO BANCO (YYYY-MM-DD) MAS CALCULA CORRETAMENTE
                        supabase.table("parcelas").insert({"venda_id": vid, "cliente_id": id_c, "valor_parcela": float(total_v/par), "data_vencimento": dv.strftime('%Y-%m-%d'), "pago": (met in ["Pix", "Dinheiro"]), "numero_parcela": n + 1, "metodo_pagamento": met}).execute()
                    for i in st.session_state.carrinho:
                        q_at = int(df_p[df_p['codigo'] == i['cod']]['quantidade_estoque'].iloc[0])
                        supabase.table("produtos").update({"quantidade_estoque": q_at - i['qtd']}).eq("codigo", i['cod']).execute()
                    st.session_state.carrinho = []; st.success("Venda salva com sucesso!"); time.sleep(1); st.rerun()

# --- ABA FINANCEIRO (FOCO TOTAL EM DATA BR) ---
with tab_financeiro:
    st.header("📉 Gestão Financeira")
    cli_f = st.selectbox("Escolha o Cliente", ["--"] + list(df_c['nome'].unique()) if not df_c.empty else ["--"])
    if cli_f != "--":
        df_f = pd.merge(df_par, df_c[['id', 'nome']], left_on='cliente_id', right_on='id', suffixes=('_p', '_c'))
        df_cli = df_f[df_f['nome'] == cli_f].sort_values('data_vencimento')
        
        for _, r in df_cli.iterrows():
            # CONVERSÃO PARA EXIBIÇÃO BRASILEIRA
            data_exibicao = pd.to_datetime(r['data_vencimento']).strftime('%d/%m/%Y')
            
            with st.expander(f"Parc {r['numero_parcela']} | Venc: {data_exibicao} | R$ {r['valor_parcela']:.2f}"):
                nv_valor = st.number_input("Alterar Valor", value=float(r['valor_parcela']), key=f"val_{r['id_p']}")
                # INPUT DE DATA QUE JÁ APARECE FORMATADO
                nv_venc = st.date_input("Alterar Vencimento", value=pd.to_datetime(r['data_vencimento']).date(), key=f"venc_{r['id_p']}")
                
                c1, c2, c3 = st.columns(3)
                if c1.button("💾 Atualizar", key=f"up_p_{r['id_p']}"):
                    supabase.table("parcelas").update({"valor_parcela": float(nv_valor), "data_vencimento": nv_venc.strftime('%Y-%m-%d')}).eq("id", int(r['id_p'])).execute(); st.rerun()
                if not r['pago'] and c2.button("✅ Receber", key=f"bx_{r['id_p']}"):
                    supabase.table("parcelas").update({"pago": True}).eq("id", int(r['id_p'])).execute(); st.rerun()
                if c3.button("🗑️ Excluir", key=f"del_p_{r['id_p']}"):
                    supabase.table("parcelas").delete().eq("id", int(r['id_p'])).execute(); st.rerun()

# --- ABA CLIENTES ---
with tab_clientes:
    st.header("👤 Cadastro de Clientes")
    with st.form("c_cli", clear_on_submit=True):
        n, t, cp = st.text_input("Nome Completo"), st.text_input("WhatsApp"), st.text_input("CPF")
        if st.form_submit_button("Salvar"):
            if n: supabase.table("clientes").insert({"nome": n, "telefone": t, "cpf": cp}).execute(); st.rerun()
    
    if not df_c.empty:
        st.subheader("Clientes Cadastrados")
        st.dataframe(df_c[['nome', 'telefone', 'cpf']], use_container_width=True)

# --- ABA ESTOQUE ---
with tab_estoque:
    st.header("📦 Inventário")
    with st.form("cad_e", clear_on_submit=True):
        e1, e2, e3, e4 = st.columns(4)
        cp, np, pv, qi = e1.text_input("Cód"), e2.text_input("Peça"), e3.number_input("Preço"), e4.number_input("Qtd", min_value=0)
        if st.form_submit_button("Cadastrar"):
            if cp: supabase.table("produtos").insert({"codigo": str(cp), "nome": str(np), "preco_venda": float(pv), "quantidade_estoque": int(qi)}).execute(); st.rerun()
    
    if not df_p.empty:
        for _, pr in df_p.iterrows():
            with st.expander(f"{pr['codigo']} - {pr['nome']} ({int(pr['quantidade_estoque'])} unidades)"):
                en_p = st.text_input("Nome", pr['nome'], key=f"pn_{pr['id']}")
                ev_p = st.number_input("Preço", value=float(pr['preco_venda']), key=f"pv_{pr['id']}")
                eq_p = st.number_input("Estoque", value=int(pr['quantidade_estoque']), key=f"pq_{pr['id']}")
                if st.button("💾 Salvar Alterações", key=f"pu_{pr['id']}"):
                    supabase.table("produtos").update({"nome": en_p, "preco_venda": float(ev_p), "quantidade_estoque": int(eq_p)}).eq("id", int(pr['id'])).execute(); st.rerun()
                if st.button("🗑️ Deletar Produto", key=f"pd_{pr['id']}"):
                    supabase.table("produtos").delete().eq("id", int(pr['id'])).execute(); st.rerun()

# --- ABA DASHBOARD (DATAS NO GRÁFICO) ---
with tab_dash:
    st.header("📊 Resumo de Vendas")
    if not df_v.empty:
        df_v['data_br'] = pd.to_datetime(df_v['data']).dt.strftime('%d/%m/%Y')
        st.metric("Faturamento Bruto", f"R$ {df_v['valor'].sum():,.2f}")
        fig = px.bar(df_v, x='data_br', y='valor', title="Vendas por Dia", color_discrete_sequence=['#8b5e3c'], labels={'data_br': 'Data', 'valor': 'Valor (R$)'})
        st.plotly_chart(fig, use_container_width=True)

st.markdown('<div class="footer">Desenvolvido por tmanga</div>', unsafe_allow_html=True)
