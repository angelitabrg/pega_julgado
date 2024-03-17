from io import BytesIO

import pdfplumber
import scrapy
import re
import uuid
import logging
import pandas as pd
import csv
import os
from time import sleep
from esaj.spiders.helpers.innertext import innertext_quick
from esaj.spiders.helpers.treatment import treatment

class CpopgSpider(scrapy.Spider):
    name = "cpopg"
    allowed_domains = ["esaj.tjsp.jus.br"]

    def start_requests(self):
        process_number = getattr(self, "process_number", None)
        url = "https://esaj.tjsp.jus.br/cpopg/search.do"

        if process_number:
            parameters = f'?conversationId=&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dadosConsulta.valorConsultaNuUnificado=&dadosConsulta.valorConsultaNuUnificado=UNIFICADO&dadosConsulta.valorConsulta={process_number}&dadosConsulta.tipoNuProcesso=SAJ'
            yield scrapy.Request(url + parameters, callback=self.parse, meta={'process_number': process_number})
        else:
            with open('data/cjpg_process_number.csv', 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    process_number = row['numero_processo']
                    parameters = f'?conversationId=&paginaConsulta=0&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dePesquisaNuUnificado=&dePesquisaNuUnificado=UNIFICADO&dePesquisa={process_number}&tipoNuProcesso=SAJ'
                    yield scrapy.Request(url + parameters, callback=self.parse, meta={'process_number': process_number})

    def parse(self, response):
        process_number = response.meta.get('process_number')
        if response.css('.modal__lista-processos'):
            code_process = response.css('.modal__lista-processos__item__header #processoSelecionado::attr("value")').get('')
            url = f'https://esaj.tjsp.jus.br/cpopg/show.do?processo.codigo={code_process}'
            yield scrapy.Request(url, callback=self.parse, meta={'process_number': process_number})
            return

        data = {
            'numero_processo': process_number,
            'situacao': response.css('#situacaoProcesso::text,.unj-tag::text').get(default="").strip(),
            'classe': response.css('#classeProcesso span::text,#classeProcesso::text').get(default="").strip(),
            'assunto': response.css('#assuntoProcesso span::text,#assuntoProcesso::text').get(default="").strip(),
            'area': innertext_quick(response.css('#areaProcesso'))[0],
            'juiz': response.css('#juizProcesso::text').get(default="").strip(),
            'valor_acao': treatment(response.css('#valorAcaoProcesso span::text,#valorAcaoProcesso::text').get(default="").strip()),
            'foro': response.css('#foroProcesso::text').get(default="").strip(),
            'vara': response.css('#varaProcesso::text').get(default="").strip(),
        }
        self.add_to_csv(data, 'cpopg')

    def open_pdf(self, response):
        yield scrapy.Request(url=response.body.decode('utf-8'), callback=self.pdf_viewer, meta=response.meta)

    def pdf_viewer(self, response):
        html_script = response.css('script:contains("parametros")').get('')
        match = re.search(r'"parametros":"([^"]*)"', html_script)
        parameters = match.group(1) if match else None

        url = (f'https://esaj.tjsp.jus.br/pastadigital/getPDF.do?{parameters}')
        yield scrapy.Request(url=url, callback=self.save_pdf, meta=response.meta)

    def save_pdf(self, response):
        try:
            data_folder = 'data/pdf/cpopg'
            if not os.path.exists(data_folder):
                os.makedirs(data_folder)

            file_name = str(uuid.uuid4())
            with open(f'{os.path.join(data_folder,file_name)}.pdf', 'wb') as pdf_file:
                pdf_file.write(response.body)

            pdf_info = {
                'pdf_name': file_name,
                'numero_processo': response.meta.get('process_number'),
                'documento': response.meta.get('cddocumento'),
                'titulo': response.meta.get('title'),
                'descricao': response.meta.get('description'),
                'processo': response.meta.get('cdprocesso'),
                'conteudo': self.pdf_to_text(response.body)
            }
            self.add_to_csv(pdf_info, 'cpopg_moviments')
        except Exception as e:
            logging.warning(f'Error saving PDF: {e}')

    def add_to_csv(self, pdf_info, file_name='file'):
        data_folder = 'data'
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        csv_file = os.path.join(data_folder, f'{file_name}.csv')
        try:
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                df = pd.concat([df, pd.DataFrame([pdf_info])], ignore_index=True)
            else:
                df = pd.DataFrame([pdf_info])

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

        return extracted_text
