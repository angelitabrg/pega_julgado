from time import sleep
import os
import scrapy
import urllib.parse
import logging
import pandas as pd
import csv

from esaj.spiders.helpers.innertext import innertext_quick
from esaj.spiders.helpers.treatment import treatment


class CjsgSpider(scrapy.Spider):
    name = "cjsg"
    allowed_domains = ["esaj.tjsp.jus.br"]

    def start_requests(self):
        search = getattr(self, "search", None)
        if search is not None:
            url = f'https://esaj.tjsp.jus.br/cjsg/resultadoCompleta.do?conversationId=&dados.buscaInteiroTeor={urllib.parse.quote(search)}&dados.pesquisarComSinonimos=S&dados.pesquisarComSinonimos=S&dados.buscaEmenta=&dados.nuProcOrigem=&dados.nuRegistro=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&codigoCr=&codigoTr=&nmAgente=&juizProlatorSelectedEntitiesList=&contadorjuizProlator=0&contadorMaiorjuizProlator=0&codigoJuizCr=&codigoJuizTr=&nmJuiz=&classesTreeSelection.values=&classesTreeSelection.text=&assuntosTreeSelection.values=&assuntosTreeSelection.text=&comarcaSelectedEntitiesList=&contadorcomarca=0&contadorMaiorcomarca=0&cdComarca=&nmComarca=&secoesTreeSelection.values=&secoesTreeSelection.text=&dados.dtJulgamentoInicio=&dados.dtJulgamentoFim=&dados.dtPublicacaoInicio=&dados.dtPublicacaoFim=&dados.origensSelecionadas=T&tipoDecisaoSelecionados=A&dados.ordenarPor=dtPublicacao'
            yield scrapy.Request(url, self.parse, meta={'selector': '#tdResultados table table'})
        else:
            logging.warning(f'The search does not found. method: start_requests')
            return

    def parse(self, response):
        selector = response.meta.get('selector')

        try:
            for process in response.css(selector):
                data = {
                    'numero_processo': process.css('a[title="Visualizar Inteiro Teor"]::text').get(default='').strip(),
                    'classe': self.get_classe(process),
                    'assunto': self.get_assunto(process),
                    'relator_a': self.get_detail(process, 'tr', 'Relator(a):'),
                    'orgao_julgador': self.get_detail(process, 'tr', 'Órgão julgador:'),
                    'comarca': self.get_detail(process, 'tr', 'Comarca:'),
                    'data_julgamento': self.get_detail(process, 'tr', 'Data do julgamento:'),
                    'data_publicacao': self.get_detail(process, 'tr', 'Data de publicação:'),
                    'ementa': treatment(innertext_quick(process.css('tr:last-child div:last-child'))[0]).strip(),
                }
                self.add_to_csv(data, 'cjsg')

            logging.info(
                f"\nURL: {response.url}, Current page: {self.get_current_page(response)}, Has next page: {self.has_next_page(response)}")
        except Exception as e:
            logging.error(f"The error occurred while extracting information. message={e}")


        if self.has_next_page(response):
            yield scrapy.Request(
                url=f'https://esaj.tjsp.jus.br/cjsg/trocaDePagina.do?tipoDeDecisao=A&pagina={self.next_page(response)}',
                headers={'Accept': 'text/html; charset=latin1;'},
                cookies=self.set_cookies(response),
                meta={'selector': 'table:first-of-type table'},
                callback=self.parse
            )

    def get_assunto(self, process):
        subject = self.get_detail(process, 'tr', 'Assunto:').split('/')
        if len(subject) > 1:
            return '|'.join(subject[1:]).strip()
        else:
            return subject[0]

    def get_classe(self, process):
        process_class = self.get_detail(process, 'tr', 'Classe/Assunto:').split('/')
        if len(process_class) > 1:
            return process_class[0].strip()
        else:
            return self.get_detail(process, 'tr', 'Classe:').strip()

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
        return int(response.css('.trocaDePagina .paginaAtual::text').get("").strip())

    def next_page(self, response):
        return self.get_current_page(response) + 1


    def get_detail(self, process, css_selector, search=''):
        element = process.css(f'{css_selector} :contains("{search}")')
        text = innertext_quick(element)[0]
        text_pos = text.find(search)
        if text_pos > -1:
            init_pos = len(search)
        else:
            init_pos = 0
        final_text = text[init_pos:]
        if final_text:
            return treatment(final_text).strip()
        return ''

    def add_to_csv(self, data, file_name):
        data_folder = 'data/sp'
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        csv_file = os.path.join(data_folder, f'{file_name}.csv')
        try:
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                if not data['numero_processo'] in df['numero_processo'].values:
                    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)

            else:
                df = pd.DataFrame([data])

            df.to_csv(csv_file, index=False, quoting=csv.QUOTE_NONNUMERIC, encoding='utf-8')
        except Exception as e:
            logging.error(f"The error occurred while adding information from the PDF to the CSV. message={e}")