from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import uuid
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="Customs Administration API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class UserRole(str, Enum):
    DRAFTING_AGENT = "drafting_agent"
    CONTROL_OFFICER = "control_officer" 
    VALIDATION_OFFICER = "validation_officer"

class DocumentStatus(str, Enum):
    DRAFT = "draft"
    UNDER_CONTROL = "under_control"
    UNDER_VALIDATION = "under_validation"
    VALIDATED = "validated"
    REJECTED = "rejected"

class DocumentType(str, Enum):
    CUSTOMS_REPORT = "customs_report"
    ADMINISTRATIVE_ACT = "administrative_act"
    VIOLATION_REPORT = "violation_report"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: UserRole

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class ActionHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    user_id: str
    user_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[Dict[str, Any]] = None

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    document_type: DocumentType
    status: DocumentStatus = DocumentStatus.DRAFT
    template_id: str
    content: Dict[str, Any] = {}
    sydonia_data: Optional[Dict[str, Any]] = None
    created_by: str
    created_by_name: str
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    history: List[ActionHistory] = []

class DocumentCreate(BaseModel):
    title: str
    document_type: DocumentType
    template_id: str
    content: Dict[str, Any] = {}

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    status: Optional[DocumentStatus] = None
    assigned_to: Optional[str] = None

class DocumentTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    document_type: DocumentType
    fields: List[Dict[str, Any]] = []
    checklist: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"username": username})
    if user is None:
        raise credentials_exception
    return User(**user)

def require_role(required_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker

# Authentication endpoints
@api_router.post("/auth/register", response_model=User)
async def register_user(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user_dict = user_data.dict()
    del user_dict["password"]
    user = User(**user_dict)
    
    user_doc = user.dict()
    user_doc["password"] = hashed_password
    
    await db.users.insert_one(user_doc)
    return user

@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user = await db.users.find_one({"username": user_credentials.username})
    if not user or not verify_password(user_credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    user_obj = User(**user)
    return Token(access_token=access_token, token_type="bearer", user=user_obj)

@api_router.get("/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Document Templates endpoints
@api_router.get("/templates", response_model=List[DocumentTemplate])
async def get_templates(current_user: User = Depends(get_current_user)):
    templates = await db.templates.find().to_list(1000)
    return [DocumentTemplate(**template) for template in templates]

@api_router.post("/templates", response_model=DocumentTemplate)
async def create_template(
    template_data: DocumentTemplate, 
    current_user: User = Depends(require_role([UserRole.VALIDATION_OFFICER]))
):
    template_dict = template_data.dict()
    await db.templates.insert_one(template_dict)
    return template_data

# Documents endpoints
@api_router.get("/documents", response_model=List[Document])
async def get_documents(current_user: User = Depends(get_current_user)):
    query = {}
    
    # Role-based filtering
    if current_user.role == UserRole.DRAFTING_AGENT:
        query["created_by"] = current_user.id
    elif current_user.role == UserRole.CONTROL_OFFICER:
        query["$or"] = [
            {"status": DocumentStatus.UNDER_CONTROL},
            {"assigned_to": current_user.id}
        ]
    # Validation officers can see all documents
    
    documents = await db.documents.find(query).to_list(1000)
    return [Document(**doc) for doc in documents]

@api_router.post("/documents", response_model=Document)
async def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(require_role([UserRole.DRAFTING_AGENT]))
):
    # Get template
    template = await db.templates.find_one({"id": document_data.template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    document = Document(
        **document_data.dict(),
        created_by=current_user.id,
        created_by_name=current_user.full_name
    )
    
    # Add creation to history
    action = ActionHistory(
        action="created",
        user_id=current_user.id,
        user_name=current_user.full_name,
        details={"document_type": document_data.document_type}
    )
    document.history.append(action)
    
    document_dict = document.dict()
    await db.documents.insert_one(document_dict)
    return document

@api_router.get("/documents/{document_id}", response_model=Document)
async def get_document(document_id: str, current_user: User = Depends(get_current_user)):
    document = await db.documents.find_one({"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    doc_obj = Document(**document)
    if (current_user.role == UserRole.DRAFTING_AGENT and 
        doc_obj.created_by != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this document")
    
    return doc_obj

@api_router.put("/documents/{document_id}", response_model=Document)
async def update_document(
    document_id: str, 
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_user)
):
    document = await db.documents.find_one({"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_obj = Document(**document)
    
    # Check permissions
    if (current_user.role == UserRole.DRAFTING_AGENT and 
        doc_obj.created_by != current_user.id and 
        doc_obj.status != DocumentStatus.DRAFT):
        raise HTTPException(status_code=403, detail="Not authorized to update this document")
    
    # Update document
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    # Add history entry
    action = ActionHistory(
        action="updated",
        user_id=current_user.id,
        user_name=current_user.full_name,
        details=update_dict
    )
    
    # Update history in document
    await db.documents.update_one(
        {"id": document_id},
        {
            "$set": update_dict,
            "$push": {"history": action.dict()}
        }
    )
    
    # Get updated document
    updated_doc = await db.documents.find_one({"id": document_id})
    return Document(**updated_doc)

@api_router.post("/documents/{document_id}/submit")
async def submit_document(
    document_id: str,
    current_user: User = Depends(require_role([UserRole.DRAFTING_AGENT]))
):
    document = await db.documents.find_one({"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_obj = Document(**document)
    if doc_obj.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if doc_obj.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Document is not in draft status")
    
    # Update status and add history
    action = ActionHistory(
        action="submitted_for_control",
        user_id=current_user.id,
        user_name=current_user.full_name
    )
    
    await db.documents.update_one(
        {"id": document_id},
        {
            "$set": {
                "status": DocumentStatus.UNDER_CONTROL,
                "updated_at": datetime.now(timezone.utc)
            },
            "$push": {"history": action.dict()}
        }
    )
    
    return {"message": "Document submitted for control"}

# PDF Generation
from weasyprint import HTML, CSS
from fastapi.responses import FileResponse
import tempfile

def generate_document_pdf(document: Document, template: DocumentTemplate) -> str:
    """Generate PDF for a document"""
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                margin: 40px;
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #2563eb;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .title {{
                font-size: 24px;
                font-weight: bold;
                color: #1e40af;
                margin-bottom: 10px;
            }}
            .subtitle {{
                font-size: 14px;
                color: #6b7280;
            }}
            .section {{
                margin-bottom: 25px;
            }}
            .section-title {{
                font-size: 18px;
                font-weight: bold;
                color: #374151;
                border-bottom: 1px solid #e5e7eb;
                padding-bottom: 5px;
                margin-bottom: 15px;
            }}
            .field {{
                margin-bottom: 12px;
                display: flex;
                justify-content: space-between;
            }}
            .field-label {{
                font-weight: 600;
                color: #4b5563;
                width: 40%;
            }}
            .field-value {{
                width: 55%;
                color: #111827;
            }}
            .footer {{
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 12px;
                color: #6b7280;
            }}
            .history {{
                background-color: #f9fafb;
                padding: 15px;
                border-radius: 6px;
                margin-top: 20px;
            }}
            .history-item {{
                margin-bottom: 8px;
                font-size: 13px;
            }}
            .status {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                background-color: #dbeafe;
                color: #1d4ed8;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">Administration Douanière de Nouvelle-Calédonie</div>
            <div class="subtitle">Système de Gestion des Actes Administratifs</div>
        </div>
        
        <div class="section">
            <div class="section-title">Informations du Document</div>
            <div class="field">
                <div class="field-label">Titre:</div>
                <div class="field-value">{document.title}</div>
            </div>
            <div class="field">
                <div class="field-label">Type:</div>
                <div class="field-value">{document.document_type}</div>
            </div>
            <div class="field">
                <div class="field-label">Statut:</div>
                <div class="field-value"><span class="status">{document.status}</span></div>
            </div>
            <div class="field">
                <div class="field-label">Créé par:</div>
                <div class="field-value">{document.created_by_name}</div>
            </div>
            <div class="field">
                <div class="field-label">Date de création:</div>
                <div class="field-value">{document.created_at.strftime('%d/%m/%Y à %H:%M')}</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Contenu du Document</div>
    """
    
    # Add template fields with content
    for field in template.fields:
        field_name = field.get('name', '')
        field_label = field.get('label', field_name)
        field_value = document.content.get(field_name, 'Non renseigné')
        
        html_content += f"""
            <div class="field">
                <div class="field-label">{field_label}:</div>
                <div class="field-value">{field_value}</div>
            </div>
        """
    
    # Add Sydonia data if available
    if document.sydonia_data:
        html_content += f"""
        <div class="section">
            <div class="section-title">Données Sydonia</div>
            <div class="field">
                <div class="field-label">N° Déclaration:</div>
                <div class="field-value">{document.sydonia_data.get('declaration_id', 'N/A')}</div>
            </div>
            <div class="field">
                <div class="field-label">Importateur:</div>
                <div class="field-value">{document.sydonia_data.get('importer_name', 'N/A')}</div>
            </div>
            <div class="field">
                <div class="field-label">Description marchandises:</div>
                <div class="field-value">{document.sydonia_data.get('goods_description', 'N/A')}</div>
            </div>
        </div>
        """
    
    # Add history
    html_content += """
        <div class="section">
            <div class="section-title">Historique des Actions</div>
            <div class="history">
    """
    
    for action in document.history:
        action_time = action.timestamp.strftime('%d/%m/%Y à %H:%M')
        html_content += f"""
            <div class="history-item">
                <strong>{action.action}</strong> par {action.user_name} le {action_time}
            </div>
        """
    
    html_content += f"""
            </div>
        </div>
        
        <div class="footer">
            <p>Document généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} UTC</p>
            <p>Administration Douanière de Nouvelle-Calédonie - Système de Gestion des Actes Administratifs</p>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    try:
        HTML(string=html_content).write_pdf(temp_file.name)
        return temp_file.name
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

@api_router.get("/documents/{document_id}/pdf")
async def download_document_pdf(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    # Get document
    document = await db.documents.find_one({"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_obj = Document(**document)
    
    # Check permissions
    if (current_user.role == UserRole.DRAFTING_AGENT and 
        doc_obj.created_by != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to download this document")
    
    # Get template
    template = await db.templates.find_one({"id": doc_obj.template_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template_obj = DocumentTemplate(**template)
    
    # Generate PDF
    pdf_path = generate_document_pdf(doc_obj, template_obj)
    
    # Return file
    filename = f"{doc_obj.title.replace(' ', '_')}_{doc_obj.id[:8]}.pdf"
    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type='application/pdf'
    )

# Mock Sydonia API endpoint
@api_router.get("/sydonia/declaration/{declaration_id}")
async def get_sydonia_declaration(
    declaration_id: str,
    current_user: User = Depends(get_current_user)
):
    # Mock Sydonia data
    mock_data = {
        "declaration_id": declaration_id,
        "importer_name": "SARL Import Export NC",
        "importer_address": "123 Rue de la Paix, Nouméa",
        "goods_description": "Matériel informatique",
        "origin_country": "France",
        "value_cfr": 45000,
        "customs_regime": "Importation définitive",
        "declaration_date": "2024-01-15",
        "customs_office": "Nouméa-Port"
    }
    
    return {"data": mock_data, "status": "success"}

# Initialize default templates
@api_router.post("/init/templates")
async def initialize_templates():
    existing_templates = await db.templates.count_documents({})
    if existing_templates > 0:
        return {"message": "Templates already initialized"}
    
    default_templates = [
        DocumentTemplate(
            name="Rapport de contrôle douanier",
            document_type=DocumentType.CUSTOMS_REPORT,
            fields=[
                {"name": "declaration_id", "type": "text", "required": True, "label": "N° Déclaration"},
                {"name": "importer_name", "type": "text", "required": True, "label": "Nom importateur"},
                {"name": "control_date", "type": "date", "required": True, "label": "Date contrôle"},
                {"name": "findings", "type": "textarea", "required": True, "label": "Constatations"},
                {"name": "decision", "type": "select", "required": True, "label": "Décision", 
                 "options": ["Conforme", "Non-conforme", "Complément d'enquête"]}
            ],
            checklist=[
                "Vérification identité importateur",
                "Contrôle cohérence déclaration/marchandises",
                "Vérification origine marchandises",
                "Contrôle valeur déclarée",
                "Vérification classement tarifaire"
            ]
        ),
        DocumentTemplate(
            name="Acte administratif de saisie",
            document_type=DocumentType.ADMINISTRATIVE_ACT,
            fields=[
                {"name": "seizure_date", "type": "date", "required": True, "label": "Date saisie"},
                {"name": "location", "type": "text", "required": True, "label": "Lieu"},
                {"name": "goods_description", "type": "textarea", "required": True, "label": "Description marchandises"},
                {"name": "legal_basis", "type": "text", "required": True, "label": "Base légale"},
                {"name": "estimated_value", "type": "number", "required": True, "label": "Valeur estimée"}
            ],
            checklist=[
                "Présence témoin",
                "Inventaire détaillé marchandises",
                "Photos prises",
                "Notification intéressé",
                "Mise sous séquestre"
            ]
        )
    ]
    
    for template in default_templates:
        await db.templates.insert_one(template.dict())
    
    return {"message": f"Initialized {len(default_templates)} default templates"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()