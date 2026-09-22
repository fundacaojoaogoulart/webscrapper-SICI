"""Gera os três HTMLs estáticos. Execute com Python 3, sem dependências externas."""
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent
PAPER = '#f5f5f5'
INK = '#2d3142'
MUTED = '#4f5d75'
ACCENT = '#eb6c36'
LINK = '#2e5aa8'


def text(x, y, value, cls='name', anchor='middle'):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(value)}</text>'


def box(x, y, title, sub, tag='MÓDULO', focal=False, lines=(), w=240, h=80, optional=False):
    color = ACCENT if focal else INK
    fill = '#fce9e0' if focal else '#ffffff'
    dash = ' stroke-dasharray="4,3"' if optional else ''
    return (f'<g class="node"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" '
            f'fill="{fill}" stroke="{color}"{dash}/>'
            + text(x+12, y+16, tag, 'tag', 'start')
            + text(x+w/2, y+36, title)
            + text(x+w/2, y+54, sub, 'mono')
            + ''.join(text(x+w/2, y+70+i*16, line, 'note') for i, line in enumerate(lines)) + '</g>')


def arrow(path, color=MUTED, dashed=False, marker=None):
    marker = marker or ('arrow-accent' if color == ACCENT else 'arrow-link' if color == LINK else 'arrow')
    dash = ' stroke-dasharray="5,4"' if dashed else ''
    return f'<path class="connector" d="{path}" fill="none" stroke="{color}" stroke-width="1.2"{dash} marker-end="url(#{marker})"/>'


def label(x, y, value):
    # y is the connector ordinate; mask ends 8 px above it.
    w = max(48, len(value)*5.5+16)
    return f'<rect class="label-mask" x="{x-w/2}" y="{y-24}" width="{w}" height="16" fill="{PAPER}"/>' + text(x, y-13, value, 'arrow-label')


def legend(value):
    return f'<path d="M40 660 H1240" stroke="#bfc0c0"/>' + text(40, 684, value, 'note', 'start')


def page(slug, title, subtitle, body, notes):
    markers = ''.join(f'<marker id="{name}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{color}"/></marker>' for name, color in [('arrow', MUTED), ('arrow-accent', ACCENT), ('arrow-link', LINK)])
    markers += f'<marker id="arrow-open" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polyline points="0 0, 8 3, 0 6" fill="none" stroke="{MUTED}"/></marker>'
    nav = ' · '.join(f'<a href="{s}.html"'+(' aria-current="page"' if s == slug else '')+f'>{n}</a>' for s,n in [('arquitetura','01 Arquitetura'),('fluxo-dados','02 Fluxo de dados'),('sequencia','03 Sequência')])
    html = f'''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — SICI</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&amp;family=Geist:wght@400;500;600&amp;family=Geist+Mono:wght@400;500&amp;display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}} body{{margin:0;background:{PAPER};color:{INK};font-family:'Geist',system-ui,sans-serif}}
main{{max-width:1360px;margin:auto;padding:40px}} nav,footer{{font-size:12px;color:{MUTED}}} a{{color:{LINK};text-underline-offset:4px}} [aria-current]{{font-weight:600}}
.eyebrow{{font-family:'Geist Mono',monospace;font-size:10px;letter-spacing:.15em;margin-top:32px;color:{MUTED}}} h1{{font-family:'Instrument Serif',Georgia,serif;font-weight:400;font-size:36px;margin:8px 0 12px}} .subtitle{{color:{MUTED};line-height:1.6;max-width:900px}}
.canvas{{overflow-x:auto}} svg{{display:block;width:100%;min-width:960px}} svg text{{fill:{INK}}} .name{{font:600 12px 'Geist',sans-serif}} .mono{{font:9px 'Geist Mono',monospace;fill:{MUTED}}} .tag{{font:8px 'Geist Mono',monospace;fill:{MUTED};letter-spacing:.08em}} .arrow-label{{font:8px 'Geist Mono',monospace;fill:{MUTED}}} .note{{font:11px 'Geist',sans-serif;fill:{MUTED}}}
.notes{{display:grid;grid-template-columns:1.3fr 1fr;gap:24px}} section{{border-top:1px solid #bfc0c0;padding-top:16px}} h2{{font-size:16px}} li,p{{line-height:1.65}} section li{{margin-bottom:8px;font-size:14px}} code{{font-family:'Geist Mono',monospace;font-size:.85em}} footer{{border-top:1px solid #bfc0c0;margin-top:32px;padding-top:16px}}
@media(max-width:700px){{main{{padding:20px}}.notes{{grid-template-columns:1fr}}}} @media print{{main{{padding:0}}svg{{min-width:0}}nav{{display:none}}.canvas{{overflow:visible}}}}
</style></head><body><main><nav aria-label="Diagramas">{nav}</nav>
<p class="eyebrow">SICI / DOCUMENTAÇÃO PARA DESENVOLVEDORES</p><h1>{escape(title)}</h1><p class="subtitle">{escape(subtitle)}</p>
<div class="canvas"><svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">
<title id="{slug}-title">{escape(title)}</title><desc id="{slug}-desc">{escape(subtitle)}</desc><defs>{markers}</defs><rect width="1280" height="720" fill="{PAPER}"/>
{body}</svg></div><div class="notes">{notes}</div>
<footer>Fonte: código Python do repositório, conferido em 22/09/2026. Graphify usado como índice de navegação. Tema padrão Diagram Design · doc-wide 1280 × 720.<br>HTML estático; sem execução do robô. Fontes Google opcionais, com fallbacks locais. <a href="../arquitetura.md">Guia e referências</a>.</footer>
</main></body></html>'''
    (OUT / f'{slug}.html').write_text(html, encoding='utf-8')


def architecture():
    edges = [
        arrow('M280 120 H380'),
        arrow('M620 100 H960', LINK),
        arrow('M620 140 H792 Q800 140 800 148 V300', dashed=True),
        arrow('M420 160 V232 Q420 240 412 240 H168 Q160 240 160 248 V300', dashed=True),
        arrow('M500 160 V300'),
        arrow('M680 340 H620'),
        arrow('M760 380 V520'),
        arrow('M840 380 V432 Q840 440 848 440 H1072 Q1080 440 1080 448 V520', dashed=True),
    ]
    body = ''.join(edges) + label(332,120,'THREAD') + label(788,100,'SELENIUM')
    body += ''.join([
        box(40,80,'Painel principal','painel_principal.py', 'ENTRADA', True),
        box(380,80,'Raspagem e encaminhamento','scraper_sici_nome.py'),
        box(960,80,'Portal SICI','sici.rio.rj.gov.br', 'EXTERNO'),
        box(40,300,'Cruzamento de lideranças','match_lideres.py'),
        box(380,300,'Regras de configuração','config_manager.py'),
        box(680,300,'Atualização do MFE','atualizador_MFE.py','PROCESSAMENTO',True),
        box(680,520,'Classificação de áreas','area_negocio_ml.py'),
        box(960,520,'Cálculo de tercis','calculadora_tercis.py'),
        box(40,520,'Conferências CGGI','gestores_equipes.py','ENTRADA INDEPENDENTE'),
    ])
    body += text(40, 440, 'Acesso offline no painel: MFE, PLC e PRLF.', 'note','start')
    body += text(40, 464, 'CGGI possui janela própria; não é acionado pelo painel principal.', 'note','start')
    body += legend('Seta: chamada / uso · Tracejado: chamada condicional · Azul: navegador / portal externo · Laranja: pontos de entrada e integração')
    page('arquitetura','Arquitetura dos módulos','Visão das responsabilidades e das chamadas principais: painel → raspagem → processamento, com configuração compartilhada e uma entrada CGGI independente.',body,
         '''<section><h2>Como navegar pelo código</h2><ul><li><code>painel_principal.py</code> cria a interface e inicia a raspagem em uma thread. Os botões offline chamam MFE e lideranças diretamente.</li><li><code>scraper_sici_nome.py</code> também coordena os próximos passos: pergunta se o usuário quer atualizar o MFE e cruzar lideranças.</li><li>As setas mostram as relações principais. A inicialização de <code>config.txt</code> pelo painel e seus atalhos offline estão descritos aqui para manter a visão legível.</li></ul></section>
<section><h2>Serviços e entrada independente</h2><ul><li>MFE lê regras de configuração, classifica áreas via ML e, se solicitado, calcula tercis a partir de empenhos.</li><li><code>gestores_equipes.py</code> abre seu próprio painel para conferências de gestores e ordenadores; não há importação dele no painel principal.</li><li>Referências: painel L6–26, L28–82; scraper L54, L140, L346–354; MFE L123–205; gestores L146–189.</li></ul></section>''')


def data_flow():
    # Fluxo técnico: gramática de arquitetura, sem atribuir papéis organizacionais fictícios.
    body = ''.join([
        arrow('M280 120 H360', LINK),
        arrow('M600 120 H680'),
        arrow('M920 120 H1000'),
        arrow('M800 160 V320'),
        arrow('M920 360 H1000'),
        arrow('M720 160 V232 Q720 240 712 240 H488 Q480 240 480 248 V520'),
        arrow('M600 560 H680'),
        arrow('M280 372 H680'),
    ])
    # Hop over the branch at x480: only one point crossing, never a shared segment.
    body = body.replace('M280 372 H680','M280 372 H472 a8,8 0 0,1 16,0 H680')
    body += label(640,120,'DATAFRAME') + label(960,120,'EXPORTA')
    body += text(820,272,'DADOS SICI','mono','start')
    body += ''.join([
        box(40,80,'Portal SICI','HTML / árvore organizacional','FONTE'),
        box(360,80,'Filtrar e capturar','scraper_sici_nome.py','TRANSFORMAÇÃO'),
        box(680,80,'Registros do SICI','DataFrame em memória','DADOS',True),
        box(1000,80,'Extração datada','sici_extracao_*.xlsx','ARQUIVO'),
        box(40,300,'Insumos para MFE','MFE_Base.xlsx + config.txt','ENTRADAS',lines=['model_fjg.pkl + vectorizer_fjg.pkl','Ordenadores / empenhos: opcionais'],h=112),
        box(680,320,'Enriquecer e preencher MFE','atualizador_MFE.py','TRANSFORMAÇÃO'),
        box(1000,320,'MFE atualizado','MFE_Atualizada.xlsx','ARQUIVO'),
        box(360,520,'Cruzar por nome normalizado','match_lideres.py','TRANSFORMAÇÃO'),
        box(680,520,'Lideranças encontradas','planilha_cruzamento_{PLC|PRLF}.xlsx','ARQUIVO',w=320),
    ])
    body += text(1000,196,'* = YYYYMMDD_HHMM','mono','start')
    body += text(40,472,'Outra entrada do cruzamento:', 'note','start')
    body += text(40,496,'planilha de lideranças com NOME.', 'note','start')
    body += text(40,600,'Offline: o Excel SICI é lido como DataFrame e alimenta as mesmas rotinas.', 'note','start')
    body += legend('Setas representam dados, não a ordem de execução · MFE e lideranças dependem de escolhas do usuário · Azul: origem web')
    page('fluxo-dados','Fluxo de dados e arquivos','Do portal SICI ao DataFrame compartilhado, à extração Excel e aos resultados de MFE e lideranças; arquivos existentes permitem reutilizar o processamento offline.',body,
         '''<section><h2>Contratos de dados</h2><ul><li>A extração contém <code>órgão</code>, <code>escalão</code>, <code>área</code>, <code>cargo</code>, <code>titular</code> e <code>data_extracao</code>. O nome real do arquivo é <code>sici_extracao_YYYYMMDD_HHMM.xlsx</code>.</li><li>MFE combina regras, predição de áreas e entradas opcionais; copia <code>MFE_Base.xlsx</code>, remove as linhas de dados e preenche a saída por posição de coluna.</li><li>Empenhos são agrupados por nome normalizado; os totais positivos determinam os quantis 0,333333 e 0,666666. Na integração MFE, o resultado fica em memória.</li></ul></section>
<section><h2>Leitura correta das saídas</h2><ul><li>PLC/PRLF normalizam <code>NOME</code> e <code>titular</code>, fazem um left join e mantêm apenas lideranças encontradas. Os nomes de saída mostrados correspondem aos modos offline com tarefa explícita.</li><li>A chamada pós-raspagem omite a tarefa e pode falhar; veja a sequência. Não há garantia de saída de lideranças nesse caminho.</li><li><code>Relatorio_Intermediario_Tercis.xlsx</code> pertence ao helper separado <code>cruzar_sici_com_tercis()</code>, não ao fluxo integrado MFE.</li><li>Referências: scraper L320–354; MFE L110–205, L281–332; tercis L57–149; match L54–165.</li></ul></section>''')


def sequence():
    xs = [120,360,600,840,1120]
    body = ''
    for x in xs:
        body += f'<path d="M{x} 120 V628" stroke="#bfc0c0" stroke-dasharray="3,3"/>'
    # Two single-region opt fragments. Lifelines group UI/worker and post-processing explicitly.
    for y,h,guard in [(376,100,'[usuário aceita atualizar MFE]'),(488,100,'[usuário aceita cruzar líderes]')]:
        body += f'<rect x="560" y="{y}" width="600" height="{h}" rx="4" fill="none" stroke="#bfc0c0"/>'
        body += f'<rect x="560" y="{y}" width="40" height="16" fill="{PAPER}" stroke="#bfc0c0"/>'
        body += text(580,y+12,'OPT','tag') + text(612,y+16,guard,'mono','start')
    messages = [
        (120,360,152,'Iniciar raspagem',False,None),
        (360,600,204,'Thread: iniciar_raspagem()',True,'arrow-open'),
        (600,840,252,'Navegar e capturar',False,None),
        (840,600,296,'Dados coletados',True,None),
        (600,1120,428,'atualizar_planilha_mfe(df)',False,None),
        (1120,600,464,'Retorno da rotina',True,None),
        (600,1120,540,'cruzar_planilhas(df)',False,None),
        (1120,600,576,'Retorno ou exceção¹',True,None),
        (600,360,620,'Retorno ou exceção',True,None),
    ]
    for a,b,y,caption,dashed,marker in messages:
        body += arrow(f'M{a} {y} H{b}',dashed=dashed,marker=marker)
        # Keep labels within a lifeline interval, even for long messages.
        cx = (a+b)/2 if abs(a-b)<=240 else 976
        body += label(cx,y,caption)
    # Local save and final UI update are annotations, not fictional participants/messages.
    body += f'<rect x="616" y="320" width="228" height="40" rx="4" fill="{PAPER}" stroke="#bfc0c0"/>'
    body += text(628,336,'Encerra Chrome; exporta Excel.', 'note','start')
    body += text(628,352,'Continua se há registros.', 'note','start')
    for x,y,h in [(356,144,476),(596,204,416),(836,244,60),(1116,420,44),(1116,532,44)]:
        body += f'<rect x="{x}" y="{y}" width="8" height="{h}" fill="#ececec" stroke="#4f5d75" stroke-width="0.8"/>'
    for x,title,sub in [(40,'Usuário','confirma os próximos passos'),(280,'Painel / tarefa','painel_principal.py'),(520,'Scraper','scraper_sici_nome.py'),(760,'Chrome / SICI','Selenium'),(1040,'Pós-processamento','MFE / match_lideres')]:
        body += box(x,40,title,sub,'PARTICIPANTE',w=160)
    body += legend('Tempo: de cima para baixo · Sólida: chamada · Tracejada preenchida: retorno · Tracejada aberta: início assíncrono · OPT: etapa opcional')
    page('sequencia','Sequência da raspagem completa','Execução iniciada no painel: uma thread executa o scraper, coleta dados via Chrome, salva a extração e oferece MFE e lideranças em duas etapas opcionais sucessivas.',body,
         '''<section><h2>Escopo e execução</h2><ul><li>O cenário mostra coleta com registros. Painel e sua tarefa aparecem em uma coluna; MFE e match em outra, como rotinas alternativas de pós-processamento. As confirmações são diálogos do scraper com o usuário.</li><li>A tarefa desabilita botões, chama o scraper e atualiza o status; no <code>finally</code>, reabilita botões. As rotinas opcionais executam sequencialmente na mesma thread da raspagem.</li><li>No <code>finally</code> do scraper, o navegador é encerrado e os registros existentes são exportados, inclusive após erros na coleta. Sem registros, ele exibe um aviso e não oferece as etapas seguintes.</li></ul></section>
<section><h2>¹ Comportamento atual a observar</h2><ul><li>O scraper chama <code>cruzar_planilhas(df)</code> com <code>tarefa=""</code>. A rotina só define a saída local e cria <code>status</code> para <code>PLC</code> ou <code>PRLF</code>; entradas válidas usuais chegam à seleção de uma coluna <code>status</code> inexistente.</li><li>Os botões offline passam a tarefa explicitamente. A sequência não trata a chamada pós-raspagem como sucesso garantido.</li><li>Retorno de MFE não é confirmação de gravação: alguns erros são tratados internamente com retorno sem valor. O status do painel indica retorno ou exceção propagada.</li><li>Referências: painel L14–26; scraper L303–358; match L54–90, L128–163.</li></ul></section>''')


if __name__ == '__main__':
    architecture()
    data_flow()
    sequence()
    print('Gerados: arquitetura.html, fluxo-dados.html, sequencia.html')
