import os
from time import sleep

import scrapy
import urllib.parse
import logging
import uuid
import re
import pandas as pd
from openpyxl import Workbook

from esaj.spiders.helpers.innertext import innertext_quick
from esaj.spiders.helpers.treatment import treatment


class LegalConsultationSpider(scrapy.Spider):
    name = "legal_consultation"
    allowed_domains = ["esaj.tjsp.jus.br"]

    def __init__(self, search, instance, *args, **kwargs):
        super(LegalConsultationSpider, self).__init__(*args, **kwargs)
        self.search = search
        self.instance = instance

    def start_requests(self):
        if self.search is not None and self.instance is not None:
            if self.instance == "cjsg":
                url = f'https://esaj.tjsp.jus.br/cjsg/resultadoCompleta.do?conversationId=&dados.buscaInteiroTeor={urllib.parse.quote(self.search)}&dados.pesquisarComSinonimos=S&dados.pesquisarComSinonimos=S&dados.buscaEmenta=&dados.nuProcOrigem=&dados.nuRegistro=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&codigoCr=&codigoTr=&nmAgente=&juizProlatorSelectedEntitiesList=&contadorjuizProlator=0&contadorMaiorjuizProlator=0&codigoJuizCr=&codigoJuizTr=&nmJuiz=&classesTreeSelection.values=&classesTreeSelection.text=&assuntosTreeSelection.values=&assuntosTreeSelection.text=&comarcaSelectedEntitiesList=&contadorcomarca=0&contadorMaiorcomarca=0&cdComarca=&nmComarca=&secoesTreeSelection.values=&secoesTreeSelection.text=&dados.dtJulgamentoInicio=&dados.dtJulgamentoFim=&dados.dtPublicacaoInicio=&dados.dtPublicacaoFim=&dados.origensSelecionadas=T&tipoDecisaoSelecionados=A&dados.ordenarPor=dtPublicacao'
            elif self.instance == 'cjpg':
                url = f'https://esaj.tjsp.jus.br/cjpg/pesquisar.do?conversationId=&dadosConsulta.pesquisaLivre={urllib.parse.quote(self.search)}&tipoNumero=UNIFICADO&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dadosConsulta.nuProcesso=&dadosConsulta.nuProcessoAntigo=&classeTreeSelection.values=&classeTreeSelection.text=&assuntoTreeSelection.values=&assuntoTreeSelection.text=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&cdAgente=&nmAgente=&dadosConsulta.dtInicio=&dadosConsulta.dtFim=09%2F02%2F2024&varasTreeSelection.values=&varasTreeSelection.text=&dadosConsulta.ordenacao=DESC'
            else:
                logging.warning(f'The instance "{self.instance}" does not exist.')
                return

            yield scrapy.Request(url, self.parse, meta={'selector': '#tdResultados table table'})

    def parse(self, response):
        selector = response.meta.get('selector')

        if self.instance == "cjsg":
            for process in response.css(selector):
                yield self.set_cjsg_values(process)
        elif self.instance == 'cjpg':
            for process in response.css(selector):
                yield self.set_cjpg_values(process)
                yield self.open_pdf(process)

        logging.info(f"\nURL: {response.url}, Current page: {self.get_current_page(response)}, Has next page: {self.has_next_page(response)}")

        if self.has_next_page(response):
            sleep(3)
            next_page = self.next_page(response)
            url = self.next_page_url()
            next_url = f'{url}{next_page}'

            yield scrapy.Request(
                url=next_url,
                headers={'Accept': 'text/html; charset=latin1;'},
                cookies=self.set_cookies(response),
                meta={'selector': self.next_selector() },
                callback=self.parse
            )

    def next_page_url(self):
        if self.instance == 'cjpg':
            return 'https://esaj.tjsp.jus.br/cjpg/trocarDePagina.do?pagina='
        return 'https://esaj.tjsp.jus.br/cjsg/trocaDePagina.do?tipoDeDecisao=A&pagina='

    def next_selector(self):
        if self.instance == 'cjsg':
            return 'table:first-of-type table'
        return '#tdResultados table table'

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
        return int(response.css('.trocaDePagina [style="font-weight:bold;"]::text, .trocaDePagina .paginaAtual::text').get().strip())

    def next_page(self, response):
        return self.get_current_page(response) + 1

    def set_cjsg_values(self, process):
        try:
            return {
                'numero_processo': process.css('a[title="Visualizar Inteiro Teor"]::text').get(default='').strip(),
                'classe': self.get_detail(process, 'tr', 'Classe/Assunto:').split('/')[0].strip(),
                'assunto': self.get_detail(process, 'tr', 'Classe/Assunto:').split('/')[1].strip(),
                'relator_a': self.get_detail(process, 'tr', 'Relator(a):'),
                'orgao_julgador': self.get_detail(process, 'tr', 'Órgão julgador:'),
                'comarca': self.get_detail(process, 'tr', 'Comarca:'),
                'data_julgamento': self.get_detail(process, 'tr', 'Data do julgamento:'),
                'data_publicacao': self.get_detail(process, 'tr', 'Data de publicação:'),
                'ementa': treatment(innertext_quick(process.css('tr:last-child div:last-child'))[0]).strip(),
            }
        except Exception as e:
            logging.warning(f'Could not retrieve message: {e}, method: set_cjsg_values')


    def set_cjpg_values(self, process):
        try:
            return {
                'numero_processo': self.process_number(process),
                'classe': self.get_detail(process, 'tr', 'Classe:').strip(),
                'assunto': self.get_detail(process, 'tr', 'Assunto:').strip(),
                'magistrado': self.get_detail(process, 'tr', 'Magistrado:'),
                'foro': self.get_detail(process, 'tr', 'Foro:'),
                'vara': self.get_detail(process, 'tr', 'Vara:'),
                'data_disponibilizacao': self.get_detail(process, 'tr', 'Data de Disponibilização:'),
                'ementa': treatment(innertext_quick(process.css('tr:last-child div:last-child'))[0]).strip(),
            }
        except Exception as e:
            logging.warning(f'Could not retrieve message: {e}. method: set_cjpg_values')

    def process_number(self, process):
        element = process.css(f'a[title="Visualizar Inteiro Teor"]')
        text = innertext_quick(element)[0]
        if text is not None:
            return text.strip()
        else:
            logging.warning('Process number was not found.')

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


    def open_pdf(self, process):
        sleep(5)
        element = process.css('a[title="Visualizar Inteiro Teor"]::attr("name")')
        if element is not None:
            try:
                attributes = element.get()
                cdprocesso = attributes[0]
                cdforo = attributes[1]
                mnalias = attributes[2]
                cddocumento = attributes[3]
                url = (f'https://esaj.tjsp.jus.br/cjpg/obterArquivo.do?cdProcesso={cdprocesso}&cdForo={cdforo}&nmAlias={mnalias}&cdDocumento={cddocumento}')
                yield scrapy.Request(
                    url=url,
                    callback=self.pdf_viewer,
                    meta={
                        'process_number': self.process_number(process),
                        'cdprocesso': attributes[0],
                        'cddocumento': attributes[3]
                    })
            except Exception as e:
                logging.warning(f'Could not retrieve message: {e}. method: open_pdf')
        else:
            logging.warning(f'The inteiro teor was not found. method: open_pdf')

    def pdf_viewer(self, response):
        html_script = response.css('script:contains("parametros")').get()
        match = re.search(r'"parametros":"([^"]*)"', html_script)
        parameters = match.group(1) if match else None

        url = (f'https://esaj.tjsp.jus.br/pastadigital/getPDF.do?{parameters}')
        yield scrapy.Request(
            url=url,
            callback=self.save_pdf,
            meta=response.meta
        )

    def save_pdf(self, response):
        try:
            file_name = str(uuid.uuid4())
            with open(os.path.join('pdfs', f'{file_name}.pdf'), 'wb') as pdf_file:
                pdf_file.write(response.body)

            pdf_info = {
                'pdf_name': file_name,
                'process_number': response.meta.get('process_number'),
                'cddocumento': response.meta.get('cddocumento'),
                'cdprocesso': response.meta.get('cdprocesso')
            }
            self.add_to_excel(pdf_info)
        except Exception as e:
            logging.warning(f'Error saving PDF: {e}')

    def add_to_excel(self, pdf_info):
        excel_file = 'pdf_info.xlsx'
        try:
            if os.path.exists(excel_file):
                df = pd.read_excel(excel_file)
                df = df.append(pdf_info, ignore_index=True)
            else:
                df = pd.DataFrame([pdf_info])

            with pd.ExcelWriter(excel_file, engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, index=False)
        except Exception as e:
            logging.error(f"Error occurred while adding PDF info to Excel: {e}")
