from io import BytesIO

import pdfplumber
import scrapy
import re
import logging
import pandas as pd
import csv
import os
import traceback

from bs4 import BeautifulSoup
from esaj.spiders.helpers.innertext import innertext_quick
from esaj.spiders.helpers.treatment import treatment

class CpopgSpider(scrapy.Spider):
    name = "cpopg"
    allowed_domains = ["esaj.tjsp.jus.br"]
    url_base = "https://esaj.tjsp.jus.br/cpopg"

    def start_requests(self):
        numero_processo = getattr(self, "numero_processo", None)
        url = "https://esaj.tjsp.jus.br/cpopg/search.do"

        if numero_processo:
            parametros = f'?conversationId=&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dadosConsulta.valorConsultaNuUnificado=&dadosConsulta.valorConsultaNuUnificado=UNIFICADO&dadosConsulta.valorConsulta={numero_processo}&dadosConsulta.tipoNuProcesso=SAJ'
            yield scrapy.Request(url + parametros, callback=self.parse, meta={'numero_processo': numero_processo})
        else:
            caminho_csv_cpopg = 'data/cpopg.csv'
            if os.path.exists(caminho_csv_cpopg) and os.path.getsize(caminho_csv_cpopg) > 0:
                df_cpopg = pd.read_csv(caminho_csv_cpopg, encoding='utf-8')
                ultimo_numero_processo = df_cpopg['numero_processo'].iloc[-1]
            else:
                ultimo_numero_processo = None

            df_cjpg = pd.read_csv('data/cjpg.csv', encoding='utf-8')

            if ultimo_numero_processo in df_cjpg['numero_processo'].values:
                indice_inicial = df_cjpg[df_cjpg['numero_processo'] == ultimo_numero_processo].index[0] + 1
            else:
                indice_inicial = 0

            # Fazer requisições para processos do cjpg
            for _, linha in df_cjpg.iloc[indice_inicial:].iterrows():
                numero_processo = linha['numero_processo']
                if not df_cpopg['numero_processo'].str.contains(numero_processo).any():
                    parametros = f'?conversationId=&paginaConsulta=0&cbPesquisa=NUMPROC&numeroDigitoAnoUnificado=&foroNumeroUnificado=&dePesquisaNuUnificado=&dePesquisaNuUnificado=UNIFICADO&dePesquisa={numero_processo}&tipoNuProcesso=SAJ'
                    yield scrapy.Request(url + parametros, callback=self.parse,
                                         meta={'numero_processo': numero_processo})
                    

    def parse(self, response):
        numero_processo = response.meta.get('numero_processo')
        if response.css('.modal__lista-processos'):
            code_process = response.css('.modal__lista-processos__item__header #processoSelecionado::attr("value")').get('')
            url = f'https://esaj.tjsp.jus.br/cpopg/show.do?processo.codigo={code_process}'
            yield scrapy.Request(url, callback=self.parse, meta={'numero_processo': numero_processo})
            return

        data = {
            'numero_processo': numero_processo,
            'situacao': '|'.join(response.css('.unj-tag::text').getall()).strip(),
            'classe': response.css('#classeProcesso span::text,#classeProcesso::text').get(default="").strip(),
            'assunto': response.css('#assuntoProcesso span::text,#assuntoProcesso::text').get(default="").strip(),
            'area': innertext_quick(response.css('#areaProcesso'))[0],
            'juiz': response.css('#juizProcesso::text').get(default="").strip(),
            'valor_acao': treatment(response.css('#valorAcaoProcesso span::text,#valorAcaoProcesso::text').get(default="").strip()),
            'foro': response.css('#foroProcesso::text').get(default="").strip(),
            'vara': response.css('#varaProcesso::text').get(default="").strip(),
            'distribuicao': response.css('#dataHoraDistribuicaoProcesso::text').get(default="").strip(),
            'controle': response.css('#numeroControleProcesso::text').get(default="").strip(),
            'partes_processo_1_tipo_participacao': response.css('.mensagemExibindo.tipoDeParticipacao::text').getall()[0].strip()  if len(self.extrair_partes_advogados(response)) > 0 else '',
            'partes_processo_1_nome_parte': '|'.join(self.extrair_partes_advogados(response)[0]['nomes_parte']) if len(self.extrair_partes_advogados(response)) > 0 else '',
            'partes_processo_1_advogados': '|'.join(self.extrair_partes_advogados(response)[0]['advogados_parte']) if len(self.extrair_partes_advogados(response)) > 0 else '',
            'partes_processo_2_tipo_participacao': response.css('.mensagemExibindo.tipoDeParticipacao::text').getall()[1].strip() if len(self.extrair_partes_advogados(response)) > 1 else '',
            'partes_processo_2_nome_parte': '|'.join(self.extrair_partes_advogados(response)[1]['nomes_parte']) if len(self.extrair_partes_advogados(response)) > 1 else '',
            'partes_processo_2_advogados': '|'.join(self.extrair_partes_advogados(response)[1]['advogados_parte']) if len(self.extrair_partes_advogados(response)) > 1 else '',
            'outros_assuntos': response.xpath('//div[contains(@class, "col-lg-2 mb-2")][.//span[contains(@class, "unj-label") and contains(text(), "Outros assuntos")]]//div[@class="line-clamp__2"]/span/text()').get(),
            'execucao_sentenca': re.sub(r'\s*\(.*?\)\s*', '', response.xpath('//div[contains(@class, "col-lg-12 col-xl-13")][.//span[contains(@class, "unj-label") and contains(text(), "Execução de Sentença")]]//div/span[contains(@class, "unj-larger")]/text()').get(default="").strip()),
            'processo_principal': response.xpath('//div[contains(@class, "col-lg-4 col-xl-3 mb-2")][.//span[contains(@class, "unj-label") and contains(text(), "Processo principal")]]//div/a/text()').get(),
            'link_processo_principal': self.link_processo_principal(response),
            'numero_processo_apensado': self.numero_processo_apensado(response),
            'link_processo_apensado': self.link_processo_apensado(response),
            'link_consulta_sg': self.link_consulta_sg(response),
        }
        self.adicionar_csv(data, 'cpopg')

        movements = self.extrair_movimentos(response, numero_processo)
        for movement in movements:
            self.adicionar_csv(movement, 'cpopg_movimentacoes_primeiro_grau')

    def link_processo_principal(self, response):
        link_relativo = response.xpath('//div[contains(@class, "col-lg-4 col-xl-3 mb-2")][.//span[contains(@class, "unj-label") and contains(text(), "Processo principal")]]//div/a/@href').get()
        if link_relativo:
            return f"{self.url_base}{link_relativo}"
        return None

    def link_processo_apensado(self, response):
        link_relativo = response.xpath(
            '//div[contains(@class, "col-lg-4 col-xl-3 mb-2")][.//span[contains(@class, "unj-label") and contains(text(), "Apensado ao")]]//div/a/@href').get()
        if link_relativo:
            return f"{self.url_base}{link_relativo}"
        return None

    def numero_processo_apensado(self, response):
        return response.xpath(
            '//div[contains(@class, "col-lg-4 col-xl-3 mb-2")][.//span[contains(@class, "unj-label") and contains(text(), "Apensado ao")]]//div/a/text()').get()

    def extrair_movimentos(self, response, numero_processo):
        movimentos = []
        for linha in response.css('#tabelaTodasMovimentacoes tr'):
            data = linha.css('.dataMovimentacao::text').get(default="").strip()

            titulo = linha.css('.descricaoMovimentacao a::text').get(default="").strip()
            if not titulo:
                titulo = linha.css('.descricaoMovimentacao::text').get(default="").strip()

            descricao = linha.css('.descricaoMovimentacao span::text').get(default="").strip()

            movimento = {
                'numero_processo': numero_processo,
                'data': data,
                'titulo': titulo,
                'descricao': descricao
            }
            movimentos.append(movimento)
        return movimentos

    def link_consulta_sg(self, response):
        caminho = response.css('.linkConsultaSG::attr("href")').get()
        if not caminho:
            return ""

        params = caminho.split('?')[1] if '?' in caminho else ''
        param_dict = dict(param.split('=') for param in params.split('&') if '=' in param)

        nu_processo = param_dict.get('nuProcesso', '')
        cd_processo_sg = param_dict.get('cdProcessoSg', '')
        cd_foro_sg = param_dict.get('cdForoSg', '')
        is_processo_origem_cr = param_dict.get('isProcessoOrigemCr', '')

        if not nu_processo or not cd_processo_sg or not cd_foro_sg or not is_processo_origem_cr:
            return ""

        return f"{self.url_base}/abrirConsultaProcessoSG.do?nuProcesso={nu_processo}&cdProcessoSg={cd_processo_sg}&cdForoSg={cd_foro_sg}&isProcessoOrigemCr={is_processo_origem_cr}"

    def extrair_partes_advogados(self, response):
        partes_advogados = []
        for elemento in response.css('.nomeParteEAdvogado'):
            partes_texto = elemento.get().split('<br>')
            partes_limpas = [
                re.sub(r'[\n\t\xa0]', '', BeautifulSoup(part, 'html.parser').get_text().strip())
                for part in partes_texto if part.strip()
            ]
            nomes_parte = [partes_limpas[0]] if partes_limpas else []
            advogados_parte = [re.sub(r'^Advogado:|^Advogada:', '', part).strip() for part in partes_limpas[1:]]
            partes_advogados.append({
                'nomes_parte': nomes_parte,
                'advogados_parte': advogados_parte
            })
        return partes_advogados

    def adicionar_csv(self, dados, file_name='file'):
        data_folder = 'data'
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)

        csv_file = os.path.join(data_folder, f'{file_name}.csv')
        try:
            if os.path.exists(csv_file) and os.path.getsize(csv_file) > 0:
                df = pd.read_csv(csv_file)
            else:
                df = pd.DataFrame(columns=dados.keys())

            df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
            df.to_csv(csv_file, index=False, quoting=csv.QUOTE_NONNUMERIC, encoding='utf-8')
        except Exception as e:
            logging.error(
                f"Ocorreu um erro ao adicionar informações do PDF ao CSV. Tipo de dado: PDF info. Erro: {e}. Arquivo CSV: {csv_file}, Informações do csv: {dados}\nRastreamento de pilha:\n{traceback.format_exc()}")
