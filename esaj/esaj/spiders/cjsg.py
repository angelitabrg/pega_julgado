import scrapy
import pdb

from esaj.spiders.helper.innertext import innertext_quick
from esaj.spiders.helper.treatment import treatment
from scrapy_splash import SplashRequest



next_page_script = """
function main(splash, args)
    splash:go(args.url)

    local a_element = splash:select('[title="Próxima página"]')
    a_element:mouse_click()

    splash:wait(splash.args.wait)  
    return splash:html()
end
"""

class CjsgSpider(scrapy.Spider):
    name = "cjsg"
    allowed_domains = ["esaj.tjsp.jus.br"]

    def start_requests(self):
        url = "https://esaj.tjsp.jus.br/cjsg/resultadoCompleta.do?conversationId=&dados.buscaInteiroTeor=vazamento&dados.pesquisarComSinonimos=S&dados.pesquisarComSinonimos=S&dados.buscaEmenta=&dados.nuProcOrigem=&dados.nuRegistro=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&codigoCr=&codigoTr=&nmAgente=&juizProlatorSelectedEntitiesList=&contadorjuizProlator=0&contadorMaiorjuizProlator=0&codigoJuizCr=&codigoJuizTr=&nmJuiz=&classesTreeSelection.values=&classesTreeSelection.text=&assuntosTreeSelection.values=&assuntosTreeSelection.text=&comarcaSelectedEntitiesList=&contadorcomarca=0&contadorMaiorcomarca=0&cdComarca=&nmComarca=&secoesTreeSelection.values=&secoesTreeSelection.text=&dados.dtJulgamentoInicio=&dados.dtJulgamentoFim=&dados.dtPublicacaoInicio=&dados.dtPublicacaoFim=&dados.origensSelecionadas=T&tipoDecisaoSelecionados=A&dados.ordenarPor=dtPublicacao"
        yield SplashRequest(url, self.parse, args={'wait': 1})

    def parse(self, response):
        for process in response.css('#tdResultados tbody tbody'):
            yield {
                'numero_processo': process.css('[title="Visualizar Inteiro Teor"]::text').get(default="").strip(),
                'numero_ocorrencia_inteiro_teor': self.get_occurrence_number(process),
                'data_julgamento': self.get_detail(process, 'tr', 'Data do julgamento:'),
                'data_publicacao': self.get_detail(process, 'tr', 'Data de publicação:'),
                'ementa': self.get_detail(process, 'tr:last-child', 'Ementa:'),
            }
        if self.has_next_page(response) is not None:
            yield SplashRequest(
                response.url,
                callback=self.parse,
                endpoint='execute',
                dont_filter=True,
                args={'wait': 2, 'lua_source': next_page_script, 'url': response.url}
            )

    def has_next_page(self, response):
        if response.css('[title="Próxima página"]'):
            return True

    def get_current_page(self, response):
        return int(response.css('.paginaAtual::text').get().strip())

    def get_occurrence_number(self, process):
        text = process.css('.segredoJustica::text').get(default="").strip()
        pos = text.find(' ocorrência')
        occurrence_number = text[1:pos]
        if occurrence_number:
            return occurrence_number.strip()
        return ''

    def get_detail(self, process, css_selector, search=''):
        element = process.css(f'{css_selector} :contains("{search}")')
        text = innertext_quick(element)[0]
        if text.find(search) > -1:
            pos = len(search)
        else:
            pos = 0
        final_text = text[pos:]
        if final_text:
            return treatment(final_text).strip()
        return ''


