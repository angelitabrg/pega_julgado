import pandas as pd
import subprocess
import logging
import traceback

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def execute_scrapy(numero_processo):
    comando = f"scrapy crawl cpopg -a numero_processo={numero_processo}"
    subprocess.Popen(comando, shell=True).wait()

def main(arquivo_csv):
    try:
        df = pd.read_csv(arquivo_csv, encoding='utf-8')
        numeros_processos_vistos = set()
        for _, linha in df.iterrows():
            numero_processo = linha['numero_processo']
            if numero_processo not in numeros_processos_vistos:
                numeros_processos_vistos.add(numero_processo)
                execute_scrapy(numero_processo)
    except Exception as e:
        logging.error(f"Erro ao processar o arquivo CSV: {e}. Rastreamento de pilha:\n{traceback.format_exc()}")

if __name__ == "__main__":
    arquivo_csv = 'data/cjpg.csv'
    main(arquivo_csv)