--Tabela de chats (conversas)
CREATE TABLE CHATS(
	ID_CHAT SERIAL PRIMARY KEY,
	DT_CHAT TIMESTAMP,
	NR_PERGUNTAS INT,
	NR_RESPOSTAS INT
);

--Tabela de procedimentos e leis
CREATE TABLE PROCEDIMENTOS(
	ID_PROCEDIMENTO SERIAL PRIMARY KEY,
	NM_PROCEIMENTO VARCHAR(50)
);

--Tabela intermediária de procedimentos de um chat
CREATE TABLE PROCEDIMENTOS_CHAT(
	ID_PROCEDIMENTOS_CHAT SERIAL PRIMARY KEY,
	CD_CHAT INT,
	CD_PROCEDIMENTO INT,
	
	FOREIGN KEY (CD_CHAT) REFERENCES CHATS(ID_CHAT),
    FOREIGN KEY (CD_PROCEDIMENTO) REFERENCES PROCEDIMENTOS(ID_PROCEDIMENTO)
);

--Tabela de controle de tokens
CREATE TABLE CONTROLE(
	ID_CONTROLE SERIAL PRIMARY KEY,
	CD_CHAT INT,
	NR_TOKENS INT,
	VL_TOKENS DECIMAL,

	FOREIGN KEY (CD_CHAT) REFERENCES CHATS(ID_CHAT)
);

	
-- Function para atualizar controle
CREATE OR REPLACE FUNCTION fnc_atualizar_controle(p_nr_tokens_perg INT, p_nr_tokens_resp INT , p_vl_dolar DECIMAL, p_cd_chat INT)
RETURNS VOID AS
$$
BEGIN
	
	UPDATE controle SET 
    nr_tokens_perg = nr_tokens_perg + p_nr_tokens_perg,  
    nr_tokens_resp = nr_tokens_resp + p_nr_tokens_resp,
    vl_dolar = vl_dolar + p_vl_dolar
    WHERE cd_chat = p_cd_chat;
END;$$
LANGUAGE 'plpgsql';


-- Function para atualizar chat
CREATE OR REPLACE FUNCTION fnc_atualizar_chat(p_id_chat INT)
RETURNS VOID AS
$$
BEGIN
	
	UPDATE CHATS SET 
    nr_perguntas = nr_perguntas + 1,  
    nr_respostas = nr_respostas + 1 
    WHERE id_chat = p_id_chat;
END;$$
LANGUAGE 'plpgsql';

-- Procedure para inserir chat e controle
CREATE OR REPLACE PROCEDURE prc_inserir_chat(OUT v_id_chat INT)
LANGUAGE plpgsql
AS $$
BEGIN 

	INSERT INTO chats(dt_chat, nr_perguntas, nr_respostas) 
    VALUES (NOW(), 0, 0)
    RETURNING id_chat INTO v_id_chat;
    
    INSERT INTO controle(cd_chat, nr_tokens_perg, nr_tokens_resp, vl_dolar)
    VALUES(v_id_chat, 0, 0, 0.0);
END;
$$;


-- Procedure para inserir procedimentos por chat
CREATE OR REPLACE PROCEDURE prc_procedimento_chat(p_nm_procedimento VARCHAR, p_id_chat INT)
LANGUAGE 'plpgsql'
AS $$
DECLARE
	v_id_procedimento INT;
BEGIN 
	
	SELECT id_procedimento FROM procedimentos 
    WHERE nm_procedimento = p_nm_procedimento
	INTO v_id_procedimento;
	
	INSERT INTO procedimentos_chat(cd_chat, cd_procedimento)
    VALUES(p_id_chat, v_id_procedimento);
END;$$;