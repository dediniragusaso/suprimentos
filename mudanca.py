from flask import abort
from pymongo import MongoClient
import os
import psycopg2
from decimal import Decimal

def conexao_banco():
    try:
        db_link = os.getenv("DB_LINK", "postgres://avnadmin:AVNS_F0MZTuXcV6F6xwUYDwi@gedai-postgres-gedaijef.h.aivencloud.com:12518/dbchatsuprimentos?sslmode=require")
        if not db_link:
            raise ValueError("Variável de ambiente DB_LINK não definida.")

        # Adicionar parâmetros de SSL
        conn = psycopg2.connect(
            db_link,
            sslmode='require',
            sslrootcert='/etc/secrets/ca.pem'
        )
        print("Conexão feita com sucesso!")
        return conn
    except Exception as e:
        raise RuntimeError(f"Erro ao conectar no banco de dados: {e}")

def convert_decimal(obj):
    """Converte valores Decimal para float."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, list):  # Caso seja um array
        return [convert_decimal(i) for i in obj]
    if isinstance(obj, dict):  # Caso seja um dicionário
        return {k: convert_decimal(v) for k, v in obj.items()}
    return obj

try:
    # Conectar ao banco PostgreSQL
    with conexao_banco() as conn:
        with conn.cursor() as cursor:
            # Executar consulta
            cursor.execute("""
                SELECT c.id_chat, c.dt_chat, array_agg(pc.ds_pergunta), 
                       array_agg(p.nm_procedimento), c.nr_perguntas, 
                       c.nr_respostas, con.vl_dolar 
                FROM controle con 
                JOIN chats c ON con.cd_chat = c.id_chat 
                JOIN procedimentos_chat pc ON c.id_chat = pc.cd_chat 
                JOIN procedimentos p ON p.id_procedimento = pc.cd_procedimento 
                GROUP BY c.id_chat, c.dt_chat, c.nr_perguntas, c.nr_respostas, con.vl_dolar
            """)

            # Conectar ao MongoDB
            conexao_mongo = MongoClient(os.getenv("DB_LINK_MONGO"))
            chat_suprimentos = conexao_mongo["chat_suprimentos"]
            collectionChats = chat_suprimentos["chats"]

            # Processar linhas e corrigir valores Decimal
            documentos = []
            for linha in cursor.fetchall():
                print(f"Linha encontrada: {linha}")
                documentos.append(convert_decimal({
                    "id_chat": linha[0],
                    "dt_chat": linha[1],
                    "ds_pergunta": linha[2],
                    "nm_procedimento": linha[3],
                    "nr_perguntas": linha[4],
                    "nr_respostas": linha[5],
                    "vl_dolar": linha[6]
                }))

            # Inserir documentos no MongoDB
            if documentos:
                collectionChats.insert_many(documentos)
                print(f"{len(documentos)} linhas inseridas no MongoDB com sucesso!")

except Exception as e:
    print(f"Erro: {e}")
