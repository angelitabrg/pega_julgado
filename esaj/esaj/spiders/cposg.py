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
            yield scrapy.Request(url + parameters, self.parse)
        else:
            logging.warning('Process number is missing')

    def parse(self, response):
        data = {
            'classe': response.css('#situacaoProcesso::text').get(default="").strip(),
            'status': response.css('#classeProcesso span::text').get(default="").strip(),
            'assunto': response.css('#assuntoProcesso span::text').get(default="").strip(),
            'secao': response.css('#secaoProcesso span::text').get(default="").strip(),
            'orgao_julgador': response.css('#orgaoJulgadorProcesso span::text').get(default="").strip(),
            'area': response.css('#areaProcesso span::text').get(default="").strip(),
            'relator': response.css('#relatorProcesso span::text').get(default="").strip(),
            'valor_acao': response.css('#valorAcaoProcesso span::text').get(default="").strip(),
        }
        self.add_to_excel(data, 'cposg')

        link_movements = response.css('a.linkMovVincProc')
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
            sleep(5)
            yield scrapy.Request(
                url=url,
                callback=self.open_pdf,
                meta={
                    'cdprocesso': process,
                    'cddocumento': document_origin,
                    'title': title,
                    'description': description
                },
            )

    def open_pdf(self, response):
        yield scrapy.Request(url=response.body.decode('utf-8'), callback=self.pdf_viewer, meta=response.meta)

    def pdf_viewer(self, response):
        html_script = response.css('script:contains("parametros")').get()
        match = re.search(r'"parametros":"([^"]*)"', html_script)
        parameters = match.group(1) if match else None

        url = (f'https://esaj.tjsp.jus.br/pastadigital/getPDF.do?{parameters}')
        yield scrapy.Request(url=url, callback=self.save_pdf, meta=response.meta)

    def download_pdf(self, response):
        process_number = str(uuid.uuid4())
        pdf_filename = f'{process_number}.pdf'
        try:
            with open(pdf_filename, 'wb') as pdf_file:
                pdf_file.write(response.body)
            self.log(f'PDF saved successfully: {pdf_filename}')
        except Exception as e:
            self.log(f'Error saving PDF: {e}')

    def save_pdf(self, response):
        try:
            file_name = str(uuid.uuid4())
            with open(f'{file_name}.pdf', 'wb') as pdf_file:
                pdf_file.write(response.body)

            pdf_info = {
                'pdf_name': file_name,
                'process_number': getattr(self, "process_number", None),
                'cddocumento': response.meta.get('cddocumento'),
                'title': response.meta.get('title'),
                'description': response.meta.get('description'),
                'cdprocesso': response.meta.get('cdprocesso')
            }
            self.add_to_excel(pdf_info, 'moviments')
        except Exception as e:
            logging.warning(f'Error saving PDF: {e}')


    def add_to_excel(self, pdf_info, file_name='file'):
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