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
import traceback

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
                numero_processo = self.numero_processo(process)
                data = {
                    'numero_processo': numero_processo,
                    'classe': self.get_detail(process, 'tr', 'Classe:').strip(),
                    'assunto': self.get_detail(process, 'tr', 'Assunto:').strip(),
                    'magistrado': self.get_detail(process, 'tr', 'Magistrado:'),
                    'foro': self.get_detail(process, 'tr', 'Foro:'),
                    'vara': self.get_detail(process, 'tr', 'Vara:'),
                    'data_disponibilizacao': self.get_detail(process, 'tr', 'Data de Disponibilização:'),
                    'ementa': treatment(innertext_quick(process.css('tr:last-child div:last-child'))[0]).strip(),
                }
                self.add_to_excel(data, 'cjpg')

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

    def has_next_page(self, response):
        if response.css('[title="Próxima página"]'):
            return True

    def get_current_page(self, response):
        return int(response.css('.trocaDePagina [style="font-weight:bold;"]::text').get().strip())

    def next_page(self, response):
        return self.get_current_page(response) + 1

    def numero_processo(self, process):
        element = process.css(f'a[title="Visualizar Inteiro Teor"]')
        text = innertext_quick(element)[0]
        if text is not None:
            return text.strip()
        else:
            logging.warning('O numero do processo nao foi encontrado.')

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

    def add_to_excel(self, data, file_name):
        data_folder = 'data'
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        csv_file = os.path.join(data_folder, f'{file_name}.csv')
        try:
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            else:
                df = pd.DataFrame([data])

            df.to_csv(csv_file, index=False, quoting=csv.QUOTE_NONNUMERIC, encoding='utf-8')
        except Exception as e:
            logging.error(
                f"Ocorreu um erro ao adicionar informações do PDF ao CSV. mensagem_erro: {e}\n{traceback.format_exc()}")