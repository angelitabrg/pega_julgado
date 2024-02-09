from time import sleep

import scrapy
import urllib.parse
import logging

from esaj.spiders.helper.innertext import innertext_quick
from esaj.spiders.helper.treatment import treatment


class CjsgSpider(scrapy.Spider):
    name = "cjsg"
    allowed_domains = ["esaj.tjsp.jus.br"]

    def __init__(self, search, instance, *args, **kwargs):
        super(CjsgSpider, self).__init__(*args, **kwargs)
        self.search = search
        self.instance = instance

    def start_requests(self):
        if self.search is not None and self.instance is not None:
            url = f'https://esaj.tjsp.jus.br/cjsg/resultadoCompleta.do?conversationId=&dados.buscaInteiroTeor={urllib.parse.quote(self.search)}&dados.pesquisarComSinonimos=S&dados.pesquisarComSinonimos=S&dados.buscaEmenta=&dados.nuProcOrigem=&dados.nuRegistro=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&codigoCr=&codigoTr=&nmAgente=&juizProlatorSelectedEntitiesList=&contadorjuizProlator=0&contadorMaiorjuizProlator=0&codigoJuizCr=&codigoJuizTr=&nmJuiz=&classesTreeSelection.values=&classesTreeSelection.text=&assuntosTreeSelection.values=&assuntosTreeSelection.text=&comarcaSelectedEntitiesList=&contadorcomarca=0&contadorMaiorcomarca=0&cdComarca=&nmComarca=&secoesTreeSelection.values=&secoesTreeSelection.text=&dados.dtJulgamentoInicio=&dados.dtJulgamentoFim=&dados.dtPublicacaoInicio=&dados.dtPublicacaoFim=&dados.origensSelecionadas=T&tipoDecisaoSelecionados=A&dados.ordenarPor=dtPublicacao'
            yield scrapy.Request(url, self.parse, meta={'selector': '#tdResultados table table'})

    def parse(self, response):
        selector = response.meta.get('selector')

        for process in response.css(selector):
            yield {
                'numero_processo': process.css('a[title="Visualizar Inteiro Teor"]::text').get().strip(),
                'classe': self.get_detail(process, 'tr', 'Classe/Assunto:').split('/')[0].strip(),
                'assunto': self.get_detail(process, 'tr', 'Classe/Assunto:').split('/')[1].strip(),
                'relator_a': self.get_detail(process, 'tr', 'Relator(a):'),
                'orgao_julgador': self.get_detail(process, 'tr', 'Órgão julgador:'),
                'comarca': self.get_detail(process, 'tr', 'Comarca:'),
                'data_julgamento': self.get_detail(process, 'tr', 'Data do julgamento:'),
                'data_publicacao': self.get_detail(process, 'tr', 'Data de publicação:'),
                'ementa': treatment(innertext_quick(process.css('tr:last-child div:last-child'))[0]).strip(),
            }

        logging.info(f"\nURL: {response.url}, Current page: {self.get_current_page(response)}, Has next page: {self.has_next_page(response)}")

        if self.has_next_page(response):
            sleep(3)
            next_page = self.next_page(response)
            next_url = f'https://esaj.tjsp.jus.br/cjsg/trocaDePagina.do?tipoDeDecisao=A&pagina={next_page}'
            yield scrapy.Request(
                url=next_url,
                headers={'Accept': 'text/html; charset=latin1;'},
                cookies=self.set_cookies(response),
                meta={'selector': 'table:first-of-type table'},
                callback=self.parse
            )

    def set_cookies(self, response):
        cookies = {}
        for cookie in response.headers.getlist(b'Set-Cookie'):
            cookie_str = cookie.decode('utf-8')
            key, value = cookie_str.split('=', 1)
            cookies[key] = value.split(';', 1)[0]
        return cookies

    def has_next_page(self, response):
        if response.css('[title="Próxima página"]'):
            return True

    def get_current_page(self, response):
        return int(response.css('.paginaAtual::text').get().strip())

    def next_page(self, response):
        return self.get_current_page(response) + 1

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
