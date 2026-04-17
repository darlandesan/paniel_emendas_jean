import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, dash_table, Input, Output, State, ctx
import requests
import unicodedata
import re
import os
import webbrowser
from threading import Timer
from fpdf import FPDF
import plotly.io as pio

# 1. FUNÇÕES DE APOIO
def normalizar_nome(nome):
    if not isinstance(nome, str) or nome.lower() in ['vazio', 'nan', '']: return "NÃO REGIONALIZADO"
    nome = nome.strip().upper()
    nome = "".join(c for c in unicodedata.normalize('NFKD', nome) if not unicodedata.combining(c))
    return nome.replace('-', ' ')

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:8050")

# 2. CARREGAMENTO E LIMPEZA
print("📖 Sistema de Gestão Parlamentar - Senador Jean Paul Prates - Painel")
df = pd.read_csv('base_jean_paul_finalizada.csv', sep=';')

def limpar_valor(valor):
    try:
        s = str(valor).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
        return float(s)
    except: return 0.0

df['Valor_Num'] = df['Valor (R$)'].apply(limpar_valor)
df['Município'] = df['Município'].fillna('NÃO REGIONALIZADO').astype(str)
df['Muni_Norm'] = df['Município'].apply(normalizar_nome)
df['Objeto'] = df['Objeto'].fillna('Vazio')
df['Ano'] = df['Ano'].astype(str)
df['Área'] = df['Área'].fillna('Outros')

# 3. GEOJSON
url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-24-mun.json"
geojson_rn = requests.get(url).json()
for feature in geojson_rn['features']:
    feature['id'] = normalizar_nome(feature['properties']['name'])

# 4. APP E LAYOUT
app = dash.Dash(__name__)

app.layout = html.Div(style={'fontFamily': 'Segoe UI, sans-serif', 'padding': '20px', 'backgroundColor': '#f4f7f9'}, children=[
    
    # Cabeçalho
    html.Div(style={
        'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
        'backgroundColor': '#002147', 'color': 'white', 'padding': '10px 25px', 'borderRadius': '10px', 'marginBottom': '20px'
    }, children=[
        html.Div(style={'display': 'flex', 'alignItems': 'center'}, children=[
            html.Img(src='/assets/foto_senador.jpg', style={'height': '90px', 'width': '90px', 'objectFit': 'cover', 'borderRadius': '5px', 'marginRight': '25px', 'border': '2px solid #FFFFFF'}),
            html.Div([
                html.H1("Painel de Emendas RN - Senador Jean Paul Prates", style={'margin': '0', 'fontSize': '22px'}),
                html.P("Consolidado Técnico de Obras e Investimentos - 2020 a 2023", style={'margin': '0', 'opacity': '0.8', 'fontSize': '14px'})
            ])
        ]),
        html.Div(style={'textAlign': 'right'}, children=[
            html.Small("SISTEMA DE GESTÃO PARLAMENTAR", style={'letterSpacing': '1px'}),
            html.Div("v13.0 Final", style={'fontSize': '12px', 'opacity': '0.7'})
        ])
    ]),

    # GRID SUPERIOR: [FILTROS] [MAPA] [GRÁFICO ÁREA]
    html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1.5fr 1fr', 'gap': '15px'}, children=[
        
        # Coluna 1: Central de Filtros
        html.Div([
            html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
                html.H3("🎯 Filtros", style={'marginTop': '0', 'color': '#002147', 'fontSize': '16px', 'borderBottom': '1px solid #eee', 'paddingBottom': '5px'}),
                
                html.Label("📍 Município", style={'fontWeight': 'bold', 'fontSize': '12px'}),
                dcc.Dropdown(id='dropdown-muni', options=[{'label': m, 'value': normalizar_nome(m)} for m in sorted([x for x in df['Município'].unique() if x != 'nan'])], placeholder="Todos", style={'marginBottom': '10px'}),
                
                html.Label("📂 Área", style={'fontWeight': 'bold', 'fontSize': '12px'}),
                dcc.Dropdown(id='dropdown-area', placeholder="Todas", style={'marginBottom': '10px'}),

                html.Label("🏗️ Objeto", style={'fontWeight': 'bold', 'fontSize': '12px'}),
                dcc.Dropdown(id='dropdown-objeto', placeholder="Todos", style={'marginBottom': '10px'}),

                html.Label("📅 Ano", style={'fontWeight': 'bold', 'fontSize': '12px'}),
                dcc.Dropdown(id='dropdown-ano', options=[{'label': a, 'value': a} for a in sorted(df['Ano'].unique())], placeholder="Todos", style={'marginBottom': '15px'}),

                html.Div(id='sidebar-info', style={'padding': '12px', 'backgroundColor': '#eef2f7', 'borderRadius': '8px', 'borderLeft': '4px solid #002147'})
            ]),
            
            html.Div(style={'marginTop': '15px', 'display': 'flex', 'flexDirection': 'column', 'gap': '8px'}, children=[
                html.Button("🔄 LIMPAR", id='btn-reset', n_clicks=0, style={'backgroundColor': '#666', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'padding': '8px'}),
                html.Button("📥 PDF", id='btn-pdf', n_clicks=0, style={'backgroundColor': '#002147', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'padding': '8px', 'fontWeight': 'bold'}),
                html.Button("📊 CSV", id='btn-csv', n_clicks=0, style={'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 'borderRadius': '5px', 'padding': '8px', 'fontWeight': 'bold'}),
                dcc.Download(id="download-pdf"), dcc.Download(id="download-csv")
            ])
        ]),

        # Coluna 2: Mapa
        html.Div(style={'backgroundColor': 'white', 'borderRadius': '10px', 'padding': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(id='mapa-principal', style={'height': '540px'})
        ]),

        # Coluna 3: Gráfico de ÁREA (RESTURADO)
        html.Div(style={'backgroundColor': 'white', 'borderRadius': '10px', 'padding': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(id='grafico-area', style={'height': '540px'})
        ])
    ]),

    # GRID INFERIOR: [OBJETO] [ANO]
    html.Div(style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '20px', 'marginTop': '20px'}, children=[
        html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(id='grafico-objeto', style={'height': '350px'})
        ]),
        html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(id='grafico-ano', style={'height': '350px'})
        ])
    ]),

    # TABELA
    html.Div(style={'marginTop': '20px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px'}, children=[
        dash_table.DataTable(
            id='tabela-final', 
            columns=[{"name": i, "id": i} for i in ['Emenda', 'Município', 'Área', 'Objeto', 'Valor (R$)']], 
            page_size=8, 
            style_header={'backgroundColor': '#002147', 'color': 'white', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'left', 'fontSize': '12px'}
        )
    ])
])

# 5. FUNÇÃO PDF
def criar_pdf(muni_nome, total_txt, fig_mapa, fig_area, fig_obj, fig_ano, dados_tabela, contato_n, contato_t):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatorio Consolidado - Senador Jean Paul Prates", ln=True, align='C')
    pdf.set_font("Arial", "", 11); pdf.cell(190, 8, f"Localidade: {muni_nome}", ln=True, align='C')
    
    if contato_n != "-":
        pdf.set_font("Arial", "I", 9); pdf.cell(190, 5, f"Responsavel: {contato_n} | Tel: {contato_t}", ln=True, align='C')
    
    pdf.ln(5); pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 12, f"VALOR TOTAL: {total_txt}", ln=True, align='C', fill=True); pdf.ln(5)

    pio.write_image(fig_mapa, "temp_mapa.png", width=800, height=450)
    pio.write_image(fig_area, "temp_area.png", width=800, height=450)
    
    pdf.image("temp_mapa.png", x=10, y=55, w=90)
    pdf.image("temp_area.png", x=105, y=55, w=90)

    pdf.set_y(195); pdf.set_font("Arial", "B", 8); pdf.set_fill_color(0, 33, 71); pdf.set_text_color(255, 255, 255)
    pdf.cell(30, 7, "Emenda", 1, 0, 'C', True); pdf.cell(40, 7, "Municipio", 1, 0, 'C', True)
    pdf.cell(80, 7, "Objeto", 1, 0, 'C', True); pdf.cell(40, 7, "Valor", 1, 1, 'C', True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", "", 6)
    for row in dados_tabela[:20]:
        pdf.cell(30, 6, str(row['Emenda']), 1)
        pdf.cell(40, 6, str(row['Município'])[:25], 1)
        pdf.cell(80, 6, str(row['Objeto'])[:60], 1)
        pdf.cell(40, 6, str(row['Valor (R$)']), 1, 1)

    nome_pdf = f"Relatorio_{muni_nome}.pdf"
    pdf.output(nome_pdf)
    return nome_pdf

# 6. CALLBACK
@app.callback(
    [Output('dropdown-muni', 'value'), Output('dropdown-area', 'options'), Output('dropdown-area', 'value'),
     Output('dropdown-objeto', 'options'), Output('dropdown-objeto', 'value'), Output('dropdown-ano', 'value'),
     Output('sidebar-info', 'children'), Output('mapa-principal', 'figure'), Output('grafico-area', 'figure'),
     Output('grafico-objeto', 'figure'), Output('grafico-ano', 'figure'),
     Output('tabela-final', 'data'), Output('download-pdf', 'data'), Output('download-csv', 'data')],
    [Input('dropdown-muni', 'value'), Input('dropdown-area', 'value'), Input('dropdown-objeto', 'value'), 
     Input('dropdown-ano', 'value'), Input('mapa-principal', 'clickData'),
     Input('btn-reset', 'n_clicks'), Input('btn-pdf', 'n_clicks'), Input('btn-csv', 'n_clicks')],
    [State('tabela-final', 'data')]
)
def update_dashboard(muni_sel, area_sel, obj_sel, ano_sel, map_click, reset_clicks, pdf_clicks, csv_clicks, current_table):
    t_id = ctx.triggered_id
    if t_id == 'btn-reset': muni_sel, area_sel, obj_sel, ano_sel = None, None, None, None
    elif t_id == 'mapa-principal' and map_click: muni_sel = map_click['points'][0]['location']

    df_f = df.copy()
    
    contato_nome, contato_tel = "-", "-"
    label_local = "Rio Grande do Norte (Total)"
    if muni_sel:
        df_f = df_f[df_f['Muni_Norm'] == muni_sel]
        label_local = df_f['Município'].iloc[0]
        c_n = df_f[df_f['Contato (Nome)'].str.upper() != 'VAZIO']['Contato (Nome)']
        c_t = df_f[df_f['Contato (Tel)'].str.upper() != 'VAZIO']['Contato (Tel)']
        contato_nome = c_n.iloc[0] if not c_n.empty else "Não Informado"
        contato_tel = c_t.iloc[0] if not c_t.empty else "Não Informado"

    opcoes_area = [{'label': a, 'value': a} for a in sorted(df_f['Área'].unique())]
    if area_sel and area_sel not in [o['value'] for o in opcoes_area]: area_sel = None
    if area_sel: df_f = df_f[df_f['Área'] == area_sel]

    opcoes_obj = [{'label': o[:60] + "...", 'value': o} for o in sorted(df_f['Objeto'].unique()) if o != "Vazio"]
    if obj_sel and obj_sel not in [o['value'] for o in opcoes_obj]: obj_sel = None
    if obj_sel: df_f = df_f[df_f['Objeto'] == obj_sel]

    if ano_sel: df_f = df_f[df_f['Ano'] == ano_sel]

    total_val = df_f['Valor_Num'].sum()
    total_txt = f"R$ {total_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    sidebar_content = [
        html.Div([html.B("👤 Responsavel: "), html.Span(contato_nome if muni_sel else "-")]),
        html.Div([html.B("📞 Telefone: "), html.Span(contato_tel if muni_sel else "-")], style={'marginBottom': '10px'}),
        html.Div([html.Small("TOTAL FILTRADO"), html.Div(total_txt, style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#002147'})])
    ]

    # GRÁFICOS
    df_map = df.groupby(['Município', 'Muni_Norm'])['Valor_Num'].sum().reset_index()
    df_map['Ranking'] = df_map['Valor_Num'].rank(pct=True)
    fig_map = px.choropleth(df_map, geojson=geojson_rn, locations='Muni_Norm', color='Ranking', color_continuous_scale="Blues", title="Ranking Geográfico")
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})

    resumo_area = df_f.groupby('Área')['Valor_Num'].sum().reset_index().sort_values('Valor_Num', ascending=True)
    fig_area = px.bar(resumo_area, y='Área', x='Valor_Num', orientation='h', title="Recursos por Área", color_discrete_sequence=['#002147'])
    
    resumo_obj = df_f.groupby('Objeto')['Valor_Num'].sum().reset_index().sort_values('Valor_Num', ascending=True).tail(8)
    fig_obj = px.bar(resumo_obj, y='Objeto', x='Valor_Num', orientation='h', title="Detalhamento de Objetos", color_discrete_sequence=['#0056b3'])
    
    resumo_ano = df_f.groupby('Ano')['Valor_Num'].sum().reset_index()
    fig_ano = px.bar(resumo_ano, x='Ano', y='Valor_Num', title="Evolução por Ano", color_discrete_sequence=['#28a745'])

    # EXPORTAÇÕES
    pdf_out, csv_out = None, None
    if t_id == 'btn-pdf':
        pdf_path = criar_pdf(label_local, total_txt, fig_map, fig_area, fig_obj, fig_ano, df_f.to_dict('records'), contato_nome, contato_tel)
        pdf_out = dcc.send_file(pdf_path)
    elif t_id == 'btn-csv':
        csv_out = dcc.send_data_frame(df_f[['Emenda', 'Município', 'Área', 'Objeto', 'Valor (R$)']].to_csv, f"Emendas_{label_local}.csv", index=False, sep=';', encoding='utf-8-sig')

    return muni_sel, opcoes_area, area_sel, opcoes_obj, obj_sel, ano_sel, sidebar_content, fig_map, fig_area, fig_obj, fig_ano, df_f.to_dict('records'), pdf_out, csv_out

if __name__ == '__main__':
    Timer(1.5, abrir_navegador).start()
    app.run(debug=False, port=8050)