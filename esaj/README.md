# Legal Consultation
## How to make a legal consultation?
### To CJPG
    scrapy crawl cjpg -o cjpg.csv -a instance=cjpg -a search='your search'
### To CJSG
    scrapy crawl cjsg -o cjsg.csv -a instance=cjsg -a search='your search'
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
