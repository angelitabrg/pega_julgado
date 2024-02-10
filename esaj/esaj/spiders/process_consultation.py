import scrapy
import re
import uuid
import logging

class ProcessConsultationSpider(scrapy.Spider):
    name = "process_consultation"
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
        yield {
            'classe': response.css('#situacaoProcesso::text').get(default="").strip(),
            'status': response.css('#classeProcesso span::text').get(default="").strip(),
            'assunto': response.css('#assuntoProcesso span::text').get(default="").strip(),
            'secao': response.css('#secaoProcesso span::text').get(default="").strip(),
            'orgao_julgador': response.css('#orgaoJulgadorProcesso span::text').get(default="").strip(),
            'area': response.css('#areaProcesso span::text').get(default="").strip(),
            'relator': response.css('#relatorProcesso span::text').get(default="").strip(),
            'valor_acao': response.css('#valorAcaoProcesso span::text').get(default="").strip(),
        }

        process = response.css('input[name="cdProcesso"]::attr(value)').get()
        link_movements = response.css('a.linkMovVincProc')

        for link_movement in link_movements:
            document_origin = link_movement.attrib['cddocumento']
            resource_origin = link_movement.attrib['name']
            url = (
                f'https://esaj.tjsp.jus.br/cposg/verificarAcessoMovimentacao.do?cdDocumento={document_origin}'
                f'&origemRecurso={resource_origin}&cdProcesso={process}'
            )

            if document_origin == '12':
                yield scrapy.Request(url=url, callback=self.open_pdf)

    def open_pdf(self, response):
        yield scrapy.Request(url=response.body.decode('utf-8'), callback=self.pdf_viewer)

    def pdf_viewer(self, response):
        html_script = response.css('script:contains("parametros")').get()
        match = re.search(r'"parametros":"([^"]*)"', html_script)
        parameters = match.group(1) if match else None

        url = (f'https://esaj.tjsp.jus.br/pastadigital/getPDF.do?{parameters}')
        yield scrapy.Request(url=url, callback=self.download_pdf)

    def download_pdf(self, response):
        process_number = str(uuid.uuid4())
        pdf_filename = f'{process_number}.pdf'
        try:
            with open(pdf_filename, 'wb') as pdf_file:
                pdf_file.write(response.body)
            self.log(f'PDF saved successfully: {pdf_filename}')
        except Exception as e:
            self.log(f'Error saving PDF: {e}')
