from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Configuração do FastAPI
app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração do banco de dados
SQLALCHEMY_DATABASE_URL = "sqlite:///./orcamentos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo do banco de dados
class OrcamentoDB(Base):
    __tablename__ = "orcamentos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100))
    email = Column(String(120))
    telefone = Column(String(20))
    empresa = Column(String(100))
    servicos = Column(String(200))
    mensagem = Column(Text)
    data_criacao = Column(DateTime, default=datetime.utcnow)

# Criar tabelas
Base.metadata.create_all(bind=engine)

# Modelo Pydantic para validação de dados
class Orcamento(BaseModel):
    nome: str
    email: str
    telefone: str
    empresa: Optional[str] = None
    servicos: List[str]
    mensagem: str

def enviar_email(dados: Orcamento):
    try:
        remetente = os.getenv('EMAIL_REMETENTE')
        senha = os.getenv('EMAIL_SENHA')
        destinatario = os.getenv('EMAIL_DESTINATARIO')
        
        if not all([remetente, senha, destinatario]):
            print("Configurações de e-mail não encontradas")
            return
        
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = f'Novo Orçamento - {dados.nome}'
        
        corpo = f"""
        Novo pedido de orçamento recebido:
        
        Nome: {dados.nome}
        Email: {dados.email}
        Telefone: {dados.telefone}
        Empresa: {dados.empresa or 'Não informada'}
        Serviços: {', '.join(dados.servicos)}
        Mensagem: {dados.mensagem}
        """
        
        msg.attach(MIMEText(corpo, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()
        
        print("E-mail enviado com sucesso")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")

@app.post("/api/orcamento")
async def criar_orcamento(orcamento: Orcamento):
    try:
        db = SessionLocal()
        
        # Criar novo orçamento no banco de dados
        db_orcamento = OrcamentoDB(
            nome=orcamento.nome,
            email=orcamento.email,
            telefone=orcamento.telefone,
            empresa=orcamento.empresa,
            servicos=', '.join(orcamento.servicos),
            mensagem=orcamento.mensagem
        )
        
        db.add(db_orcamento)
        db.commit()
        
        # Tentar enviar e-mail
        enviar_email(orcamento)
        
        return {"mensagem": "Orçamento criado com sucesso!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

# Configurar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Rota para servir o arquivo index.html
@app.get("/")
async def read_root():
    try:
        return FileResponse('index.html')
    except Exception as e:
        print(f"Erro ao servir index.html: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao carregar a página")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 