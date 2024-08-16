import subprocess
import pandas as pd
import csv
import os

def execute_scrapy(process_number):
    command = f"scrapy crawl cposg -a process_number={process_number}"
    subprocess.Popen(command, shell=True).wait()

def main(csv_file):
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            process_number = row['numero_processo']
            execute_scrapy(process_number)

if __name__ == "__main__":
    csv_file = "data/sp/cjsg.csv"
    main(csv_file)
