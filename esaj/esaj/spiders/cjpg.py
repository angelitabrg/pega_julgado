import os
from time import sleep

import scrapy
import urllib.parse
import logging
import uuid
import re
import pandas as pd
import csv

from esaj.spiders.helpers.innertext import innertext_quick
from esaj.spiders.helpers.treatment import treatment


class LegalConsultationSpider(scrapy.Spider):
    name = "cjpg"
    allowed_domains = ["esaj.tjsp.jus.br"]

    def start_requests(self):
        search = getattr(self, "search", None)
        if search is not None:
            url = f'https://esaj.tjsp.jus.br/cjpg/pesquisar.do?conversationId=&dadosConsulta.pesquisaLivre={urllib.parse.quote(search)}&tipoNumero=UNIFICADO&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dadosConsulta.nuProcesso=&dadosConsulta.nuProcessoAntigo=&classeTreeSelection.values=&classeTreeSelection.text=&assuntoTreeSelection.values=&assuntoTreeSelection.text=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&cdAgente=&nmAgente=&dadosConsulta.dtInicio=&dadosConsulta.dtFim=09%2F02%2F2024&varasTreeSelection.values=&varasTreeSelection.text=&dadosConsulta.ordenacao=DESC'
            yield scrapy.Request(url, self.parse)
        else:
            logging.warning(f'The search does not found. method: start_requests')
            return

    def parse(self, response):
        for process in response.css('#tdResultados table table'):
            data = {
                'numero_processo': self.process_number(process),
                'classe': self.get_detail(process, 'tr', 'Classe:').strip(),
                'assunto': self.get_detail(process, 'tr', 'Assunto:').strip(),
                'magistrado': self.get_detail(process, 'tr', 'Magistrado:'),
                'foro': self.get_detail(process, 'tr', 'Foro:'),
                'vara': self.get_detail(process, 'tr', 'Vara:'),
                'data_disponibilizacao': self.get_detail(process, 'tr', 'Data de Disponibilização:'),
                'ementa': treatment(innertext_quick(process.css('tr:last-child div:last-child'))[0]).strip(),
            }
            self.add_to_excel(data, 'cjpg')

            sleep(5)
            attributes = process.css('a[title="Visualizar Inteiro Teor"]::attr("name")').get().split('-')
            cdprocesso = attributes[0]
            cdforo = attributes[1]
            mnalias = attributes[2]
            cddocumento = attributes[3]
            url = f'https://esaj.tjsp.jus.br/cjpg/obterArquivo.do?cdProcesso={cdprocesso}&cdForo={cdforo}&nmAlias={mnalias}&cdDocumento={cddocumento}'
            yield scrapy.Request(
                url=url,
                meta={
                    'process_number': self.process_number(process),
                    'cdprocesso': cdprocesso,
                    'cddocumento': cddocumento
                },
                callback=self.pdf_viewer
            )

        logging.info(f"\nURL: {response.url}, Current page: {self.get_current_page(response)}, Has next page: {self.has_next_page(response)}")

        if self.has_next_page(response):
            sleep(3)
            yield scrapy.Request(
                url=f'https://esaj.tjsp.jus.br/cjpg/trocarDePagina.do?pagina={self.next_page(response)}',
                headers={'Accept': 'text/html; charset=latin1;'},
                cookies=self.set_cookies(response),
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
        return int(response.css('.trocaDePagina [style="font-weight:bold;"]::text').get().strip())

    def next_page(self, response):
        return self.get_current_page(response) + 1

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
            with open(f'{file_name}.pdf', 'wb') as pdf_file:
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

    def add_to_excel(self, pdf_info, file_name='pdf_info'):
        csv_file = f'{file_name}.csv'
        try:
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                df = pd.concat([df, pd.DataFrame([pdf_info])], ignore_index=True)
            else:
                df = pd.DataFrame([pdf_info])

            df.to_csv(csv_file, index=False, quoting=csv.QUOTE_NONNUMERIC, encoding='utf-8')
        except Exception as e:
            logging.error(f"The error occurred while adding information from the PDF to the CSV. {e}")

