import PyPDF2




arquivoInput = "./pdfs_bases/procedimentos/manual_adiantamento_jbs.pdf"
pdf = open(arquivoInput, "rb")
pdf_reader = PyPDF2.PdfReader(pdf)
total_paginas=len(pdf_reader.pages)
for i in range (total_paginas):
    pagina = pdf_reader.pages[i]
    print(pagina.extract_text())
