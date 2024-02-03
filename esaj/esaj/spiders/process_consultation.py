import scrapy


class ProcessConsultationSpider(scrapy.Spider):
    name = "process_consultation"
    allowed_domains = ["esaj.tjsp.jus.br"]
    start_urls = ["https://esaj.tjsp.jus.br/cposg/search.do?conversationId=&paginaConsulta=0&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dePesquisaNuUnificado=&dePesquisaNuUnificado=UNIFICADO&dePesquisa=2317756-12.2023.8.26.0000&tipoNuProcesso=SAJ"]

    def parse(self, response):
        yield {
            'classe': response.css('#situacaoProcesso::text').get(default="").strip(),
            'status': response.css('#classeProcesso span::text').get(default="").strip(),
            'assunto': response.css('#assuntoProcesso span::text').get(default="").strip(),
            'secao': response.css('#secaoProcesso span::text').get(default="").strip(),
            'orgao_julgador': response.css('#orgaoJulgadorProcesso span::text').get(default="").strip(),
            'area': response.css('#areaProcesso span::text').get(default="").strip(),
            'relator': response.css('#relatorProcesso span::text').get(default="").strip(),
            'valor_acao': response.css('#valorAcaoProcesso span::text').get(default="").strip(),\
            # movimento (?)
        }

