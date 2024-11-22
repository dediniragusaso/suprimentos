from pymongo import MongoClient
from datetime import datetime
from abc import ABCMeta, abstractmethod 
from dotenv import load_dotenv
import os

load_dotenv()

class Connection(metaclass = ABCMeta):
    
    @abstractmethod 
    def connection(self):
        pass
        
class Client(Connection):
    
    def connection(self):
        conn = os.getenv("DB_LINK")
        self.client = MongoClient(host=conn)["dbChatSuprimentos"]["Client"]
        
    def __init__(self, id, nome, empresa, cargo):
        self.id = id
        self.nome = nome
        self.empresa = empresa
        self.cargo = cargo
        
        try:
            self.client["clientes"].insert_one(
                {"_id": self.id, 
                 "data_criacao": datetime.now(),
                 "nome": self.nome, 
                 "empresa": self.empresa, 
                 "cargo": self.cargo})
        except Exception as e:
            print(e)  
            
        
class Chat(Connection):
    
    def connection(self):
        conn = os.getenv("DB_LINK")
        self.client = MongoClient(host=conn)["dbChatSuprimentos"]["Chat"]
    
 
    def __init__(self, cd_client):  
        self.id = None      
        self.cd_client = cd_client
        
        try:
            self.client.insert_one(
                { "dt_criacao": datetime.now(),
                  "cd_client": self.cd_client})
        except Exception as e:
            print(e)  
    
    @property
    def getChat(self):        
        
        return self.client.aggregate([
            {"$match":{"cd_client": self.cd_client}},
            {"$sort":{"dt_criacao": -1}},
            {"$project":{"_id":1}},
            {"$limit": 1}
        ])
        
    def isErro(self):
        
        try:
            exists = self.client.count_documents({
                "cd_client": self.cd_client,
                "$expr": {
                    "$allElementsTrue": [
                        { "$map": {
                            "input": { "$slice": ["$ar_procedimentos", -3, 3] },
                            "as": "item",
                            "in": { "$eq": ["$$item", "erro"] }
                        }}
                    ]
                }
            }) > 0
            
            return exists
        except Exception as e:
            print(e)
            return False

        
    def setPerguntaResposta(self, pergunta, procedimento, resposta, custo):
        
        try:
            
            self.client.update_one(
                {"_id": self.id},
                {
                    "$inc": {"nr_pergunta": 1, "nr_resposta": 1, "vl_custo": custo},
                    "$push": {
                        "ar_perguntas": pergunta,
                        "ar_respostas": resposta,
                        "ar_procedimentos": procedimento
                    }
                }
            )   
            
            return True

        except Exception as e:
            print(e)
            return False 