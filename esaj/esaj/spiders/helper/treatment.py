import re
def treatment(value):
    return re.sub(r'([\n\r]+)', r'', value)
