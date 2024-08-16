# Legal Consultation
## How to make a legal consultation?
### To CJPG
    scrapy crawl cjpg -a search='"LGPD" OU "Lei Geral de Proteção de Dados Pessoais" OU "13.709"'
### To CJSG
```bash
    scrapy crawl cjsg -a search='"LGPD" OU "Lei Geral de Proteção de Dados Pessoais" OU "13.709"'
```
# testing
```bash
    scrapy crawl cjsg -a search='"ovni"'
```


## TODO:
- [ ] Add _inteiro teor_ download (Because they don't have reecaptcha).


# Process Consultation
## How to make a process consultation?
### To CJSG
    scrapy crawl cposg -o cposg.csv -a process_number='process_number'

## TODO:
- [ ] Add erros logs.
- [ ] Add for CJPG.
- [ ] Add when you have legal recourse.
- [ ] Add on table id on pdf for identify pdf.
