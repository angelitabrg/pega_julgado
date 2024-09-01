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

class CposgSpider(scrapy.Spider):
    name = "cposg"
    allowed_domains = ["esaj.tjsp.jus.br"]

    # TODO: Adicionar buscar por URL
    def start_requests(self):
        process_number = getattr(self, "process_number", None)
        url_base = "https://esaj.tjsp.jus.br/cposg/search.do"

        if process_number:
            parameters = f'?conversationId=&paginaConsulta=0&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dePesquisaNuUnificado=&dePesquisaNuUnificado=UNIFICADO&dePesquisa={process_number}&tipoNuProcesso=SAJ'
            url = url_base + parameters

            yield scrapy.Request(url, callback=self.parse, meta={'process_number': process_number})
        else:
            with open('data/cjsg.csv', 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    process_number = row['numero_processo']
                    parameters = f'?conversationId=&paginaConsulta=0&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dePesquisaNuUnificado=&dePesquisaNuUnificado=UNIFICADO&dePesquisa={process_number}&tipoNuProcesso=SAJ'
                    url = url_base + parameters
                    yield scrapy.Request(url, callback=self.parse, meta={'process_number': process_number})


    def parse(self, response):
        process_number = response.meta.get('process_number')
        if response.css('.modal__lista-processos'):
            code_process = response.css('.modal__lista-processos__item__header #processoSelecionado::attr("value")').get('')
            url = f'https://esaj.tjsp.jus.br/cposg/show.do?processo.codigo={code_process}'
            yield scrapy.Request(url, callback=self.parse, meta={'process_number': process_number})
            return

        data = {
            'numero_processo': process_number,
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
        self.add_to_csv(data, 'cposg')
        self.first_instance(response)

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

            if self.process_and_document_exist_in_csv(process_number, document_origin, 'data/cposg/cposg_moviments.csv'):
                yield scrapy.Request(
                    url=url,
                    callback=self.open_pdf,
                    meta={
                        'process_number': process_number,
                        'cdprocesso': process,
                        'cddocumento': document_origin,
                        'title': title,
                        'description': description
                    },
                )

    def process_and_document_exist_in_csv(process_number, document_number, csv_file):
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            return df[(df['numero_processo'] == process_number) & (df['documento'] == document_number)].any().any()
        return False

    def open_pdf(self, response):
        yield scrapy.Request(url=response.body.decode('utf-8'), callback=self.pdf_viewer, meta=response.meta)


    def first_instance(self, response):
        table = response.css('table:contains("Nº de 1ª instância")').xpath('following-sibling::table[1]')
        process_number_and_type = innertext_quick(table.css('td:nth-child(1)'))

        if process_number_and_type and re.search(r'\((.*?)\)', process_number_and_type[0]):
            type = re.search(r'\((.*?)\)', process_number_and_type[0]).group(1)
            n_processo_1_instancia = process_number_and_type[0].split('(')[0]
        else:
            n_processo_1_instancia = process_number_and_type[0]
            type = ''

        try:
            data = {
                'numero_processo': response.css('#numeroProcesso::text').get('').strip(),
                'n_processo_1_instancia': n_processo_1_instancia,
                'tipo': type,
                'foro': table.css('td:nth-child(2)::text').get('').strip(),
                'vara': table.css('td:nth-child(3)::text').get('').strip(),
                'juiz': table.css('td:nth-child(4)::text').get('').strip(),
                'obs': table.css('td:nth-child(5)::text').get('').strip(),
            }
            self.add_to_csv(data, 'first_instance')
        except Exception as e:
            logging.error(f'Error saving first instance data: {e}')


    def pdf_viewer(self, response):
        html_script = response.css('script:contains("parametros")').get('')
        match = re.search(r'"parametros":"([^"]*)"', html_script)
        parameters = match.group(1) if match else None

        url = (f'https://esaj.tjsp.jus.br/pastadigital/getPDF.do?{parameters}')
        yield scrapy.Request(url=url, callback=self.save_pdf, meta=response.meta)


    def save_pdf(self, response):
        try:
            data_folder = 'data/cposg/pdf'
            if not os.path.exists(data_folder):
                os.makedirs(data_folder)

            if check_moviments_exists_in_csv(response.meta.get('process_number'), response.meta.get('cddocumento')):
                return

            file_name = str(uuid.uuid4())
            with open(f'{os.path.join(data_folder,file_name)}.pdf', 'wb') as pdf_file:
                pdf_file.write(response.body)

            pdf_data = {
                'pdf_name': file_name,
                'numero_processo': response.meta.get('process_number'),
                'documento': response.meta.get('cddocumento'),
                'titulo': response.meta.get('title'),
                'descricao': response.meta.get('description'),
                'processo': response.meta.get('cdprocesso'),
                'conteudo': self.pdf_to_text(response.body)
            }
            self.add_to_csv(pdf_data, 'cposg_moviments')

        except Exception as e:
            logging.error(f'Error saving PDF: {e}')

    def add_to_csv(self, data, file_name):
        data_folder = 'data/cposg'
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        csv_file = os.path.join(data_folder, f'{file_name}.csv')
        try:
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                if data['numero_processo'] in df['numero_processo'].values:
                    for key, value in data.items():
                        df.loc[df['numero_processo'] == data['numero_processo'], key] = value
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


    def check_process_and_document_and_content(self, row, process_number, document_number):
        return (row['numero_processo'] == process_number) and (row['documento'] == document_number) and (row['conteudo'] != '')


    def check_moviments_exists_in_csv(self, process_number, document_number):
        csv_file = 'data/cposg/cposg.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            return df.apply(self.check_process_and_document_and_content, axis=1,
                            args=(process_number, document_number)).any()
        return False
