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

class CposgSpider(scrapy.Spider):
    name = "cposg"
    allowed_domains = ["esaj.tjsp.jus.br"]

    def start_requests(self):
        process_number = getattr(self, "process_number", None)
        url = "https://esaj.tjsp.jus.br/cposg/search.do"

        if process_number:
            parameters = f'?conversationId=&paginaConsulta=0&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dePesquisaNuUnificado=&dePesquisaNuUnificado=UNIFICADO&dePesquisa={process_number}&tipoNuProcesso=SAJ'
            yield scrapy.Request(url + parameters, callback=self.parse)
        else:
            with open('data/cjsg.csv', 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    process_number = row['numero_processo']
                    parameters = f'?conversationId=&paginaConsulta=0&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dePesquisaNuUnificado=&dePesquisaNuUnificado=UNIFICADO&dePesquisa={process_number}&tipoNuProcesso=SAJ'
                    yield scrapy.Request(url + parameters, callback=self.parse)

    def parse(self, response):
        if response.css('.modal__lista-processos'):
            code_process = response.css('.modal__lista-processos__item__header #processoSelecionado::attr("value")').get()
            url = f'https://esaj.tjsp.jus.br/cposg/show.do?processo.codigo={code_process}'
            yield scrapy.Request(url, callback=self.parse)
            return

        data = {
            'numero_processo': response.css('#numeroProcesso::text').get().strip(),
            'situacao': response.css('#situacaoProcesso::text').get(default="").strip(),
            'classe': response.css('#classeProcesso span::text').get(default="").strip(),
            'assunto': response.css('#assuntoProcesso span::text').get(default="").strip(),
            'secao': response.css('#secaoProcesso span::text').get(default="").strip(),
            'orgao_julgador': response.css('#orgaoJulgadorProcesso span::text').get(default="").strip(),
            'area': response.css('#areaProcesso span::text').get(default="").strip(),
            'relator_a': response.css('#relatorProcesso span::text').get(default="").strip(),
            'valor_acao': response.css('#valorAcaoProcesso span::text').get(default="").strip(),
            'comarca': response.css('#maisDetalhes span:contains("Origem")').xpath('..').css('div div span::text').get()
        }
        self.add_to_excel(data, 'cposg')
        self.first_instances(response)

        link_movements = response.css('.descricaoMovimentacaoProcesso a.linkMovVincProc')
        for link_movement in link_movements:
            title = link_movement.css('::text').get(default="").strip()
            description = link_movement.xpath('..').css('span::text').get(default="").strip()
            document_origin = link_movement.attrib['cddocumento']
            resource_origin = link_movement.attrib['name']
            process = response.css('input[name="cdProcesso"]::attr(value)').get(default="")
            url = (
                f'https://esaj.tjsp.jus.br/cposg/verificarAcessoMovimentacao.do?cdDocumento={document_origin}'
                f'&origemRecurso={resource_origin}&cdProcesso={process}'
            )
            sleep(3)
            yield scrapy.Request(
                url=url,
                callback=self.open_pdf,
                meta={
                    'process_number': response.css('#numeroProcesso::text').get().strip(),
                    'cdprocesso': process,
                    'cddocumento': document_origin,
                    'title': title,
                    'description': description,
                    'timeout': 300
                },
            )

    def open_pdf(self, response):
        yield scrapy.Request(url=response.body.decode('utf-8'), callback=self.pdf_viewer, meta=response.meta)

    def first_instances(self, response):
        table = response.css('a[href*="esaj.tjsp.jus.br/cpopg/show.do?"]').xpath('ancestor::table')
        type = table.css('td:nth-child(1)').get('')

        try:
            data = {
                'numero_processo': response.css('#numeroProcesso::text').get().strip(),
                'n_1_instancia': table.css('td:nth-child(1) a::text').get().strip(),
                'tipo': re.search(r'\((.*?)\)', type).group(1) if re.search(r'\((.*?)\)', type) else None,
                'foro': table.css('td:nth-child(2)::text').get().strip(),
                'vara': table.css('td:nth-child(3)::text').get().strip(),
                'juiz': table.css('td:nth-child(4)::text').get().strip(),
                'obs': table.css('td:nth-child(5)::text').get().strip(),
            }
            self.add_to_excel(data, 'first_instances')
        except Exception as e:
            logging.warning(f'Error saving first instance data: {e}')


    def pdf_viewer(self, response):
        html_script = response.css('script:contains("parametros")').get()
        match = re.search(r'"parametros":"([^"]*)"', html_script)
        parameters = match.group(1) if match else None

        url = (f'https://esaj.tjsp.jus.br/pastadigital/getPDF.do?{parameters}')
        yield scrapy.Request(url=url, callback=self.save_pdf, meta=response.meta)

    def save_pdf(self, response):
        try:
            data_folder = 'data/pdf/cposg'
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
            self.add_to_excel(pdf_info, 'cposg_moviments')
        except Exception as e:
            logging.warning(f'Error saving PDF: {e}')

    def add_to_excel(self, pdf_info, file_name='file'):
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
