

import os

import pdfplumber

def para_txt(pdf_file):
    text = ''
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text




for arq in os.listdir(r"./ENC_Manual_de_Viagens"):
    caminho_completo = os.path.join(r"./ENC_Manual_de_Viagens", arq)
    texto = para_txt(caminho_completo)
    with open(f"{caminho_completo.replace('.pdf', '')}.txt", "w", encoding="utf8") as txt_file:
        txt_file.write(texto)



    

