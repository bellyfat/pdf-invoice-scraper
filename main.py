# ONLY SUPPORTS KRUEGER INVOICES

# John Carlee
# JCarlee@gmail.com
# http://www.daffodilparker.com

import PyPDF2
import sqlite3
from time import strptime
import os
from tkinter import filedialog
from tkinter import *

root = Tk()
root.withdraw()
dir_path = os.getcwd()                                                     # Where main.py lives
conn = sqlite3.connect(dir_path + "\\" + "invoice.db")                     # Connect to DB in main directory
c = conn.cursor()
short_list = []
freight_invoice = ''
rep = {" ST": "", " BU": "", " PC": "", "'": ""}
rep = dict((re.escape(k), v) for k, v in rep.items())
pattern = re.compile("|".join(rep.keys()))
rep2 = {"$": "", ",": ""}
rep2 = dict((re.escape(g), h) for g, h in rep2.items())
pattern2 = re.compile("|".join(rep2.keys()))
total_items = 0


# Check if string is actually an int
def represents_int(s):
    """Check if string should be integer"""
    try:
        int(s)
        return True
    except ValueError:
        return False


def create_file_list():
    """Create list of file paths if ending in .pdf"""
    files_output = []
    local_path = filedialog.askdirectory()
    for file in os.listdir(local_path):
            filename = os.fsdecode(file)
            if filename.endswith(".pdf"):
                files_output.append(local_path + '\\' + filename)
            else:
                pass
    return files_output, local_path


def kreuger_invoice_info(lng_lst):
    """Extract Invoice number and date from PDF"""
    invoice_number = ''
    invoice_myd = ''
    for z in lng_lst:
        if 'Invoice #' in z:
            invoice_number = z.replace('Invoice # ', '')
        elif 'Invoice Date' in z:
            invoice_myd = z.replace('Invoice Date ', '')
        elif 'Credit #' in z:
            invoice_number = z.replace('Credit # ', '')
    invoice_year = invoice_myd[-4:]
    invoice_mnth = invoice_myd[:3]
    invoice_month = strptime(invoice_mnth, '%b').tm_mon
    invoice_day = invoice_myd[4:6]
    return invoice_number, invoice_myd, invoice_year, invoice_month, int(invoice_day)


def negative_val(val1):
    """Change a value to negative"""
    price1 = -float(val1)
    return price1


def define_bunch(current_list):
    """Define multiple variables for insert statement"""
    qty_fn = current_list[0]
    itm_fn = current_list[1]
    prc_fn = current_list[2].split()
    price_fn = prc_fn[0].replace('$', '')
    item_type_fn = prc_fn[1]
    price_total_raw_fn = current_list[3]
    return qty_fn, itm_fn, prc_fn, price_fn, item_type_fn, price_total_raw_fn


def no_desc_sql():
    """SQL statement execution if no description"""
    sql_five = '''INSERT INTO item_test(invoice, date, year, month, day, source, qty, itm, item, type, price, 
    price_total, taxable, file)
    VALUES('{0}', '{1}', {2}, {3}, {4}, '{5}', {6}, '{7}', '{8}', '{9}', {10}, {11}, {12}, '{13}');''' \
        .format(invoice_no, invoice_date, year, month, day, 'Krueger', qty, itm, item, item_type, price,
                price_total, taxable, file_name)
    c.execute(sql_five)


def desc_sql(c_list):
    """SQL statement execution if description"""
    desc = c_list[5]
    sql_desc = '''INSERT INTO item_test(invoice, date, year, month, day, source, qty, itm, item, type, price, 
    price_total, taxable, desc, file)
          VALUES('{0}', '{1}', {2}, {3}, {4}, '{5}', {6}, '{7}', '{8}', '{9}', {10}, {11}, {12}, '{13}', '{14}');''' \
        .format(invoice_no, invoice_date, year, month, day, 'Krueger', qty, itm, item, item_type, price,
                price_total, taxable, desc, file_name)
    c.execute(sql_desc)


def freight_sql(lng_lst):
    """SQL statement for freight table"""
    freight_price = lng_lst[frt_index].replace('$', '').strip()
    sql_freight = '''INSERT INTO freight_test(invoice_no, invoice_date, year, month, day, price, source, file)
                VALUES('{0}', '{1}', {2}, {3}, {4}, {5}, '{6}', '{7}');''' \
        .format(invoice_no, invoice_date, year, month, day, freight_price, 'Krueger', file_name)
    c.execute(sql_freight)


files, pdf_path = create_file_list()


for pdf in files:
    pdfFileObj = open(pdf, 'rb')
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    no_of_pages = pdfReader.getNumPages()
    pdf_text = ''
    for page in range(no_of_pages):
        pageObj = pdfReader.getPage(page)
        pdf_text += pageObj.extractText()
    long_list = pdf_text.splitlines()
    for index, line in enumerate(long_list):
        if 'Freight' in line:
            frt_index = index + 1
    if 'Invoice #' in long_list[4]:
        short_list = long_list[16:-15]
    elif 'Credit #' in long_list:
        short_list = long_list[16:-9]
    invoice_no, invoice_date, year, month, day = kreuger_invoice_info(long_list)
    name_check = [1]
    markers = []
    for index, line in enumerate(short_list):
        if represents_int(line) and (index - name_check[-1] != 1):
            markers.append(index)
            name_check.append(index)
    mark_first = markers[:-1]
    mark_last = markers[1:]
    file_name = pdf[len(pdf_path) + 1:-len('.pdf')]
    for x, y in zip(mark_first, mark_last):
        cur_list = short_list[x:y]
        qty, itm, prc, price, item_type, price_total_raw = define_bunch(cur_list)
        price_total = pattern2.sub(lambda m: rep2[re.escape(m.group(0))], price_total_raw)
        taxable = 0
        if 'T' in cur_list[3]:
            taxable = 1
            price_total = price_total.replace('T', '')
        if "Credit Invoice" in long_list[3]:
            price, price_total = negative_val(price), negative_val(price_total)
        name_list = list(filter(None, cur_list[4].split('  ')))
        item_long = name_list[0]
        item = pattern.sub(lambda m: rep[re.escape(m.group(0))], item_long)
        # print(invoice_no, ' | ', invoice_date, ' | ', 'Krueger', ' | ', qty, ' | ', itm, ' | ', item, ' | ',
        #       item_type, ' | ', price, ' | ', price_total, ' | ', file_name)
        if y - x == 5:
            total_items += 1
            no_desc_sql()
        elif y-x == 6:
            total_items += 1
            desc_sql(cur_list)
        if "Freight" in long_list and file_name != freight_invoice:
            freight_invoice = file_name
            freight_sql(long_list)
    pdfFileObj.close()
conn.commit()
conn.close()
print('{0} records added to database'.format(total_items))
