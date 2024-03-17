import re
def treatment(text):
    return re.sub(r'[\n\r\t\s]+', ' ', text).strip()
