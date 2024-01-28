import scrapy

from esaj.spiders.helper.innertext import innertext_quick
from esaj.spiders.helper.treatment import treatment

class CjsgSpider(scrapy.Spider):
    name = "cjsg"
    allowed_domains = ["esaj.tjsp.jus.br"]
    start_urls = ["https://esaj.tjsp.jus.br/cjsg/resultadoCompleta.do?conversationId=&dados.buscaInteiroTeor=vazamento&dados.pesquisarComSinonimos=S&dados.pesquisarComSinonimos=S&dados.buscaEmenta=&dados.nuProcOrigem=&dados.nuRegistro=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&codigoCr=&codigoTr=&nmAgente=&juizProlatorSelectedEntitiesList=&contadorjuizProlator=0&contadorMaiorjuizProlator=0&codigoJuizCr=&codigoJuizTr=&nmJuiz=&classesTreeSelection.values=&classesTreeSelection.text=&assuntosTreeSelection.values=&assuntosTreeSelection.text=&comarcaSelectedEntitiesList=&contadorcomarca=0&contadorMaiorcomarca=0&cdComarca=&nmComarca=&secoesTreeSelection.values=&secoesTreeSelection.text=&dados.dtJulgamentoInicio=&dados.dtJulgamentoFim=&dados.dtPublicacaoInicio=&dados.dtPublicacaoFim=&dados.origensSelecionadas=T&tipoDecisaoSelecionados=A&dados.ordenarPor=dtPublicacao"]

    def parse(self, response):
        for process in response.css('#tdResultados .fundocinza1'):
            yield {
                'numero_processo': process.css('[title="Visualizar Inteiro Teor"]::text').get(default="").strip(),
                'numero_ocorrencia_inteiro_teor': self.get_occurrence_number(process),
                'ementa': self.get_detail(process, 'Ementa:', '[style="display: none;"]'),
                'data_julgamento': self.get_detail(process, 'Data do julgamento:'),
                'data_publicacao': self.get_detail(process, 'Data de publicação:'),
            }

    def get_occurrence_number(self, process):
        text = process.css('.segredoJustica::text').get(default="").strip()
        pos = text.find(' ocorrência')

        occurrence_number = text[1:pos]

        if occurrence_number:
            return occurrence_number

        return ''

    def get_detail(self, process, search, css_selector=''):
        element = process.css(f'.ementaClass2 {css_selector}:contains("{search}")')
        text = innertext_quick(element)[0]

        pos = len(search)
        final_text = text[pos:]
        if final_text:
            return treatment(final_text)
        return ''


