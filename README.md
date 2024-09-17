# Projeto de Consulta Jurídica no Portal de Serviços e-SAJ do Tribunal de Justiça do Estado de São Paulo

Este projeto realiza a raspagem de dados jurídicos do portal e-SAJ do Tribunal de Justiça do Estado de São Paulo. Ele utiliza o framework Scrapy para coletar informações de processos e julgados de 1º e 2º graus.

## Estrutura do Projeto

- `esaj/esaj/spiders/cjpg.py`: Spider para consulta de julgados de 1º grau (CJPG).
- `esaj/esaj/spiders/cjsg.py`: Spider para consulta de jurisprudência de 2º grau (CJSG).
- `esaj/esaj/spiders/cpopg.py`: Spider para consulta de processos do 1º grau (CPOPG).
- `esaj/esaj/spiders/cposg.py`: Spider para consulta de processos do 2º grau (CPOSG).
- `esaj/esaj/spiders/helpers/innertext.py`: Helper para extração de texto interno.
- `esaj/esaj/spiders/helpers/treatment.py`: Helper para tratamento de texto.

## Requisitos

- Python 3.x
- Scrapy
- pdfplumber
- pandas
- BeautifulSoup4

## Instalação

1. Clone o repositório:
    ```bash
    git clone <URL_DO_REPOSITORIO>
    cd <NOME_DO_REPOSITORIO>
    ```

2. Crie um ambiente virtual e ative-o:
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows use `venv\Scripts\activate`
    ```

3. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

## Como Executar

### Consulta de Julgados de 1º Grau (CJPG)

Para realizar a raspagem de dados de julgados de 1º grau, execute o seguinte comando:
```bash
scrapy crawl cjpg -a search='"LGPD" OU "Lei Geral de Proteção de Dados Pessoais" OU "13.709"'
```
Este comando inicia a spider `CjpgSpider`, que realiza uma busca no portal e-SAJ com os termos fornecidos. A spider coleta informações sobre os processos encontrados, como número do processo, classe, assunto, magistrado, foro, vara, data de disponibilização e ementa. Os dados são salvos no arquivo `data/cjpg.csv`.

#### Dados Coletados:
- `numero_processo`: Número do processo.
- `classe`: Classe do processo.
- `assunto`: Assunto do processo.
- `magistrado`: Nome do magistrado responsável.
- `foro`: Foro do processo.
- `vara`: Vara do processo.
- `data_disponibilizacao`: Data de disponibilização do processo.
- `ementa`: Ementa do processo.

#### Arquivos Criados:
- `data/cjpg.csv`: Contém os dados coletados sobre os processos.

### Consulta de Jurisprudência de 2º Grau (CJSG)

Para realizar a raspagem de dados de jurisprudência de 2º grau, execute o seguinte comando:
```bash
scrapy crawl cjsg -a search='"LGPD" OU "Lei Geral de Proteção de Dados Pessoais" OU "13.709"'
```
Este comando inicia a spider `CjsgSpider`, que realiza uma busca no portal e-SAJ com os termos fornecidos. A spider coleta informações sobre os processos encontrados, como número do processo, classe, assunto, relator(a), órgão julgador, comarca, data do julgamento, data de publicação e ementa. Os dados são salvos no arquivo `data/sp/cjsg.csv`.

#### Dados Coletados:
- `numero_processo`: Número do processo.
- `classe`: Classe do processo.
- `assunto`: Assunto do processo.
- `relator_a`: Nome do relator(a).
- `orgao_julgador`: Órgão julgador.
- `comarca`: Comarca do processo.
- `data_julgamento`: Data do julgamento.
- `data_publicacao`: Data de publicação.
- `ementa`: Ementa do processo.

#### Arquivos Criados:
- `data/sp/cjsg.csv`: Contém os dados coletados sobre os processos.

### Consulta de Processos do 1º Grau (CPOPG)

Para realizar a raspagem de dados de processos do 1º grau, execute um dos seguintes comandos:

#### Com número do processo específico:
```bash
scrapy crawl cpopg -a numero_processo=<NUMERO_DO_PROCESSO>
```

#### Sem número do processo específico:
```bash
scrapy crawl cpopg
```

Este comando inicia a spider `CpopgSpider`, que realiza uma busca no portal e-SAJ. Se um número de processo for fornecido, a busca será realizada com base nesse número. Caso contrário, a spider buscará processos a partir de um arquivo CSV existente (`data/cjpg.csv`). A spider coleta informações detalhadas sobre o processo, como situação, classe, assunto, área, juiz, valor da ação, foro, vara, distribuição, controle, partes do processo e advogados. Os dados são salvos no arquivo `data/cpopg.csv`. Movimentações do processo são salvas no arquivo `data/cpopg_movimentacoes_primeiro_grau.csv`.

#### Dados Coletados:
- `numero_processo`: Número do processo.
- `situacao`: Situação do processo.
- `classe`: Classe do processo.
- `assunto`: Assunto do processo.
- `area`: Área do processo.
- `juiz`: Nome do juiz responsável.
- `valor_acao`: Valor da ação.
- `foro`: Foro do processo.
- `vara`: Vara do processo.
- `distribuicao`: Data de distribuição do processo.
- `controle`: Número de controle do processo.
- `partes_processo_1_tipo_participacao`: Tipo de participação da primeira parte.
- `partes_processo_1_nome_parte`: Nome da primeira parte.
- `partes_processo_1_advogados`: Advogados da primeira parte.
- `partes_processo_2_tipo_participacao`: Tipo de participação da segunda parte.
- `partes_processo_2_nome_parte`: Nome da segunda parte.
- `partes_processo_2_advogados`: Advogados da segunda parte.
- `outros_assuntos`: Outros assuntos relacionados ao processo.
- `execucao_sentenca`: Informações sobre a execução da sentença.
- `processo_principal`: Número do processo principal.
- `link_processo_principal`: Link para o processo principal.
- `numero_processo_apensado`: Número do processo apensado.
- `link_processo_apensado`: Link para o processo apensado.
- `link_consulta_sg`: Link para consulta no sistema SG.

#### Movimentações Coletadas:
- `numero_processo`: Número do processo.
- `data`: Data da movimentação.
- `titulo`: Título da movimentação.
- `descricao`: Descrição da movimentação.

#### Arquivos Criados:
- `data/cpopg.csv`: Contém os dados coletados sobre os processos.
- `data/cpopg_movimentacoes_primeiro_grau.csv`: Contém as movimentações dos processos.

### Consulta de Processos do 2º Grau (CPOSG)

Para realizar a raspagem de dados de processos do 2º grau, execute um dos seguintes comandos:

#### Com número do processo específico:
```bash
scrapy crawl cposg -a process_number=<NUMERO_DO_PROCESSO>
```

#### Sem número do processo específico:
```bash
scrapy crawl cposg
```

Este comando inicia a spider `CposgSpider`, que realiza uma busca no portal e-SAJ. Se um número de processo for fornecido, a busca será realizada com base nesse número. Caso contrário, a spider buscará processos a partir de um arquivo CSV existente (`data/cjsg.csv`). A spider coleta informações detalhadas sobre o processo, como situação, classe, assunto, seção, órgão julgador, área, relator(a), valor da ação e comarca. Os dados são salvos no arquivo `data/cposg.csv`. Movimentações do processo são salvas no arquivo `data/cposg_moviments.csv`. PDFs dos documentos são salvos na pasta `data/cposg/pdf`.

#### Dados Coletados:
- `numero_processo`: Número do processo.
- `situacao`: Situação do processo.
- `classe`: Classe do processo.
- `assunto`: Assunto do processo.
- `secao`: Seção do processo.
- `orgao_julgador`: Órgão julgador.
- `area`: Área do processo.
- `relator_a`: Nome do relator(a).
- `valor_acao`: Valor da ação.
- `comarca`: Comarca do processo.

#### Movimentações Coletadas:
- `numero_processo`: Número do processo.
- `documento`: Documento da movimentação.
- `titulo`: Título da movimentação.
- `descricao`: Descrição da movimentação.
- `processo`: Processo relacionado.
- `conteudo`: Conteúdo extraído do PDF.

#### Arquivos Criados:
- `data/cposg.csv`: Contém os dados coletados sobre os processos.
- `data/cposg_moviments.csv`: Contém as movimentações dos processos.
- `data/cposg/pdf`: Pasta contendo os PDFs dos documentos.

## Troubleshooting

### Problemas Comuns

1. **Erro de Conexão**: Verifique sua conexão com a internet e tente novamente.
2. **Erro de Permissão**: Verifique as permissões de escrita na pasta de destino.
3. **Dependências Faltando**: Certifique-se de que todas as dependências estão instaladas corretamente.

### Soluções

- **Erro de Conexão**: Reinicie sua conexão de internet e tente novamente.
- **Erro de Permissão**: Execute o comando com permissões elevadas (por exemplo, `sudo` no Linux).
- **Dependências Faltando**: Reinstale as dependências usando `pip install -r requirements.txt`.
