import fitz  # PyMuPDF
import os

def extract_images_from_pdf(pdf_path, output_folder):
    # Verifica se a pasta de saída existe, se não, cria
    os.makedirs(output_folder, exist_ok=True)

    # Abre o arquivo PDF
    pdf_document = fitz.open(pdf_path)
    
    # Itera pelas páginas do PDF
    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)
        images = page.get_images(full=True)
        
        # Se houver imagens na página
        for img_index, img in enumerate(images):
            xref = img[0]  # Obtém a referência da imagem
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image_extension = base_image["ext"]
            
            # Define o caminho de saída para salvar a imagem
            image_filename = f"page_{page_number+1}_img_{img_index+1}.{image_extension}"
            output_path = os.path.join(output_folder, image_filename)
            
            # Salva a imagem
            with open(output_path, 'wb') as image_file:
                image_file.write(image_bytes)

    pdf_document.close()
    print(f'Imagens extraídas e salvas em "{output_folder}"')

# Percorre a pasta e processa cada PDF
for arq in os.listdir("./pds_bases_viagens"):
    caminho_arq = f"./pds_bases_viagens/{arq}"
    pasta_saida = f"./imagens_certa/{arq}".replace('.pdf', '')
    if caminho_arq.endswith('.pdf'):
        extract_images_from_pdf(caminho_arq, pasta_saida)
    else:
        print(f"{caminho_arq} não é um arquivo PDF.")
