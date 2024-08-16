import os
from io import BytesIO

import pdfplumber
import scrapy
import urllib.parse
import logging
import uuid
import re
import pandas as pd
import csv

from esaj.spiders.helpers.innertext import innertext_quick
from esaj.spiders.helpers.treatment import treatment


class CjpgSpider(scrapy.Spider):
    name = "cjpg"
    allowed_domains = ["esaj.tjsp.jus.br"]

    def __init__(self, search, page=None, *args, **kwargs):
        super(CjpgSpider, self).__init__(*args, **kwargs)
        self.search = search
        self.page = page

    def start_requests(self):
        if self.search is not None:
            url = f'https://esaj.tjsp.jus.br/cjpg/pesquisar.do?conversationId=&dadosConsulta.pesquisaLivre={urllib.parse.quote(self.search)}&tipoNumero=UNIFICADO&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dadosConsulta.nuProcesso=&dadosConsulta.nuProcessoAntigo=&classeTreeSelection.values=&classeTreeSelection.text=&assuntoTreeSelection.values=&assuntoTreeSelection.text=&agenteSelectedEntitiesList=&contadoragente=0&contadorMaioragente=0&cdAgente=&nmAgente=&dadosConsulta.dtInicio=&dadosConsulta.dtFim=09%2F02%2F2024&varasTreeSelection.values=&varasTreeSelection.text=&dadosConsulta.ordenacao=DESC'
            yield scrapy.Request(url, self.parse)
        else:
            logging.warning(f'The search does not found. method: start_requests')
            return

    def parse(self, response):
        if self.page and 'https://esaj.tjsp.jus.br/cjpg/pesquisar.do?conversationId=&dadosConsulta.pesquisaLivre' in response.url:
            yield scrapy.Request(
                url=f'https://esaj.tjsp.jus.br/cjpg/trocarDePagina.do?pagina={self.page}',
                headers={'Accept': 'text/html; charset=latin1;'},
                cookies=self.set_cookies(response),
                callback=self.parse
            )
            return

        for process in response.css('#tdResultados table table'):
            try:
                process_number = self.process_number(process)
                data = {
                    'numero_processo': process_number,
                    'classe': self.get_detail(process, 'tr', 'Classe:').strip(),
                    'assunto': self.get_detail(process, 'tr', 'Assunto:').strip(),
                    'magistrado': self.get_detail(process, 'tr', 'Magistrado:'),
                    'foro': self.get_detail(process, 'tr', 'Foro:'),
                    'vara': self.get_detail(process, 'tr', 'Vara:'),
                    'data_disponibilizacao': self.get_detail(process, 'tr', 'Data de Disponibilização:'),
                    'ementa': treatment(innertext_quick(process.css('tr:last-child div:last-child'))[0]).strip(),
                }
                self.add_to_excel(data, 'cjpg')

                if not self.process_and_content_exists_in_csv(process_number):
                    attributes = process.css('a[title="Visualizar Inteiro Teor"]::attr("name")').get().split('-')
                    cdprocesso = attributes[0]
                    cdforo = attributes[1]
                    mnalias = attributes[2]
                    cddocumento = attributes[3]
                    url = f'https://esaj.tjsp.jus.br/cjpg/obterArquivo.do?cdProcesso={cdprocesso}&cdForo={cdforo}&nmAlias={mnalias}&cdDocumento={cddocumento}'
                    yield scrapy.Request(
                        url=url,
                        meta={
                            'process_number': process_number,
                            'cdprocesso': cdprocesso,
                            'cddocumento': cddocumento
                        },
                        callback=self.pdf_viewer
                    )
            except Exception as e:
                logging.warning(f'Error saving process data: message={e}')

        logging.info(f"\nURL: {response.url}, Current page: {self.get_current_page(response)}, Has next page: {self.has_next_page(response)}")

        if self.has_next_page(response):
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

    def process_and_content_exists_in_csv(self, process_number):
        data_folder = 'data'
        csv_file = os.path.join(data_folder, 'cjpg_pdf_info.csv')
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            if process_number in df['process_number'].values:
                row = df.loc[df['process_number'] == process_number]
                if pd.notnull(row['conteudo']).all():
                    logging.info(f"[Pass]Process number {process_number} already has content in CSV.")
                    return True
                else:
                    logging.info(f"[Not pass]Process number {process_number} does not have content in CSV.")
            else:
                logging.info(f"[Not pass]Process number {process_number} not found in CSV.")
        return False

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
        html_script = response.css('script:contains("parametros")').get('')
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
            data_folder = 'data/pdf/cjpg'
            if not os.path.exists(data_folder):
                os.makedirs(data_folder)

            file_name = str(uuid.uuid4())
            with open(f'{os.path.join(data_folder,file_name)}.pdf', 'wb') as pdf_file:
                pdf_file.write(response.body)

            content = ''

            try:
                content = self.pdf_to_text(response.body)
            except Exception as e:
                logging.error(f"The error when get content. {e}")

            pdf_info = {
                'pdf_name': file_name,
                'process_number': response.meta.get('process_number'),
                'cddocumento': response.meta.get('cddocumento'),
                'cdprocesso': response.meta.get('cdprocesso'),
                'conteudo': content
            }
            self.add_to_excel(pdf_info, 'cjpg_pdf_info')
        except Exception as e:
            logging.warning(f'Error saving PDF: {e}')

    def add_to_excel(self, data, file_name):
        data_folder = 'data'
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        csv_file = os.path.join(data_folder, f'{file_name}.csv')
        try:
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                if data['process_number'] in df['process_number'].values:
                    row_index = df[df['process_number'] == data['process_number']].index[0]
                    if pd.isnull(df.at[row_index, 'conteudo']):
                        df.at[row_index, 'conteudo'] = data['conteudo']
                        df.at[row_index, 'pdf_name'] = data['pdf_name']
                else:
                    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            else:
                df = pd.DataFrame([data])

            df.to_csv(csv_file, index=False, quoting=csv.QUOTE_NONNUMERIC, encoding='utf-8')
        except Exception as e:
            logging.error(f"The error occurred while adding information from the PDF to the CSV. {e}")

    def pdf_to_text(self, pdf_content):
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            extracted_text = ""
            for page in pdf.pages:
                extracted_text += page.extract_text()

        extracted_text = ' '.join(extracted_text.split())
        extracted_text = extracted_text.replace('\n', ' ')
        extracted_text = extracted_text.replace('\t', '')

        extracted_text = re.sub(r'[;,\'\"\r]', '', extracted_text)
        extracted_text = re.sub(r'\s+', ' ', extracted_text)

        return treatment(extracted_text)

