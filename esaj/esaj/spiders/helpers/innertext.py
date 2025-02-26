from bs4 import BeautifulSoup


def innertext_quick(elements, delimiter=""):
    if elements == []: return ['']
    return list(delimiter.join(el.strip() for el in element.css('*::text').getall()) for element in elements)

def innertext(selector):
    html = selector.get(default='')
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text().strip()