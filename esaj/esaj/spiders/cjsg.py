import scrapy


class CjsgSpider(scrapy.Spider):
    name = "cjsg"
    allowed_domains = ["esaj.tjsp.jus.br"]
    start_urls = ["https://esaj.tjsp.jus.br/cjsg/resultadoCompleta.do?conversationId=&dados.buscaInteiroTeor=vazamento&dados.pesquisarComSinonimos=S&dados.pesquisarComSinonimos=S&dados.buscaEmenta=&dados.nuProcOrigem=&dados.nuRegistro=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&codigoCr=&codigoTr=&nmAgente=&juizProlatorSelectedEntitiesList=&contadorjuizProlator=0&contadorMaiorjuizProlator=0&codigoJuizCr=&codigoJuizTr=&nmJuiz=&classesTreeSelection.values=&classesTreeSelection.text=&assuntosTreeSelection.values=&assuntosTreeSelection.text=&comarcaSelectedEntitiesList=&contadorcomarca=0&contadorMaiorcomarca=0&cdComarca=&nmComarca=&secoesTreeSelection.values=&secoesTreeSelection.text=&dados.dtJulgamentoInicio=&dados.dtJulgamentoFim=&dados.dtPublicacaoInicio=&dados.dtPublicacaoFim=&dados.origensSelecionadas=T&tipoDecisaoSelecionados=A&dados.ordenarPor=dtPublicacao"]

    def parse(self, response):
        for process in response.css('#tdResultados .fundocinza1'):
            yield {
                'numero_processo': process.css('[title="Visualizar Inteiro Teor"]::text').get(default="").strip(),
                'numero_ocorrencia_inteiro_teor': self.get_occurrence_number(process),
            }

    def get_occurrence_number(self, process):
        text = process.css('.segredoJustica::text').get(default="").strip()
        pos = text.find(' ocorrência')

        occurrence_number = text[1:pos]

        if occurrence_number:
            return occurrence_number

        return ''


