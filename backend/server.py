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

# PDF Generation
from weasyprint import HTML, CSS
from fastapi.responses import FileResponse
import tempfile
import shutil
from pathlib import Path as PathlibPath

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# PDF Storage Configuration
PDF_STORAGE_DIR = PathlibPath("/app/shared_pdfs")
PDF_STORAGE_DIR.mkdir(exist_ok=True)

# Create subdirectories for organization
(PDF_STORAGE_DIR / "documents").mkdir(exist_ok=True)
(PDF_STORAGE_DIR / "controls").mkdir(exist_ok=True)
(PDF_STORAGE_DIR / "templates").mkdir(exist_ok=True)
(PDF_STORAGE_DIR / "backups").mkdir(exist_ok=True)

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
    MOA = "moa"  # Management Operations Administrator

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

class ControlStatus(str, Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLIANCE_CHECK = "compliance_check"
    NON_COMPLIANT = "non_compliant"
    CERTIFICATE_GENERATED = "certificate_generated"
    DECLARANT_VALIDATION = "declarant_validation"
    COMPLETED = "completed"
    FINE_ISSUED = "fine_issued"

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"

class NonComplianceType(str, Enum):
    SPECIES = "species"
    ORIGIN = "origin"
    VALUE = "value"
    CLASSIFICATION = "classification"
    DOCUMENTATION = "documentation"

class FineStatus(str, Enum):
    PENDING = "pending"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"

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

class Declaration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    declaration_id: str
    importer_name: str
    importer_address: str
    goods_description: str
    origin_country: str
    value_cfr: float
    customs_regime: str
    declaration_date: str
    customs_office: str
    tariff_code: Optional[str] = None
    weight: Optional[float] = None
    quantity: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sydonia_data: Optional[Dict[str, Any]] = None

class Regulation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    title: str
    description: str
    category: str
    fine_rate: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ComplianceCheckItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item: str
    status: ComplianceStatus = ComplianceStatus.PENDING
    notes: Optional[str] = None
    checked_by: Optional[str] = None
    checked_at: Optional[datetime] = None

class Control(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    declaration_id: str
    control_officer_id: str
    control_officer_name: str
    status: ControlStatus = ControlStatus.INITIATED
    compliance_checks: List[ComplianceCheckItem] = []
    non_compliance_type: Optional[NonComplianceType] = None
    non_compliance_details: Optional[str] = None
    fiscal_impact: Optional[float] = None
    applicable_regulation: Optional[str] = None
    declarant_acknowledged: bool = False
    certificate_path: Optional[str] = None
    pv_generated: bool = False
    fine_decision: Optional[str] = None  # "pass_over" or "customs_fine"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    history: List[ActionHistory] = []

class ControlCreate(BaseModel):
    declaration_id: str

class ComplianceCheckUpdate(BaseModel):
    compliance_checks: List[ComplianceCheckItem]

class NonComplianceUpdate(BaseModel):
    non_compliance_type: NonComplianceType
    non_compliance_details: str
    fiscal_impact: float
    applicable_regulation: str

class DeclarantValidation(BaseModel):
    acknowledged: bool
    fine_decision: str  # "pass_over" or "customs_fine"

class CustomsFine(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    control_id: str
    declaration_id: str
    amount: float
    regulation_code: str
    status: FineStatus = FineStatus.PENDING
    sydonia_lo_number: Optional[str] = None
    payment_notice_path: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

def save_pdf_to_shared_folder(pdf_path: str, filename: str, subfolder: str = "documents") -> str:
    """Save PDF to shared folder and return the permanent path"""
    try:
        # Create date-based subfolder
        date_folder = datetime.now(timezone.utc).strftime("%Y/%m")
        target_dir = PDF_STORAGE_DIR / subfolder / date_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique filename to avoid conflicts
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        target_path = target_dir / safe_filename
        
        # Copy the temporary PDF to permanent location
        shutil.copy2(pdf_path, target_path)
        
        logger.info(f"PDF saved to shared folder: {target_path}")
        return str(target_path)
    except Exception as e:
        logger.error(f"Error saving PDF to shared folder: {str(e)}")
        return pdf_path  # Return original path if saving fails

def generate_document_pdf(document: Document, template: DocumentTemplate, save_to_shared: bool = False) -> str:
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
        
        # Save to shared folder if requested
        if save_to_shared:
            filename = f"{document.title.replace(' ', '_')}_{document.id[:8]}.pdf"
            return save_pdf_to_shared_folder(temp_file.name, filename, "documents")
        
        return temp_file.name
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

def generate_certificate_of_visit_pdf(control: Control, declaration: Declaration, save_to_shared: bool = False) -> str:
    """Generate Certificate of Visit PDF"""
    
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
                border-bottom: 3px solid #dc2626;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .title {{
                font-size: 26px;
                font-weight: bold;
                color: #dc2626;
                margin-bottom: 10px;
            }}
            .subtitle {{
                font-size: 16px;
                color: #374151;
                font-weight: 600;
            }}
            .warning-box {{
                background-color: #fef2f2;
                border-left: 4px solid #dc2626;
                padding: 15px;
                margin: 20px 0;
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
            .fiscal-impact {{
                background-color: #fef3c7;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #f59e0b;
                margin: 20px 0;
            }}
            .signature-section {{
                margin-top: 50px;
                border-top: 2px solid #e5e7eb;
                padding-top: 30px;
            }}
            .signature-box {{
                border: 2px solid #374151;
                padding: 20px;
                margin: 20px 0;
                min-height: 80px;
            }}
            .footer {{
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 12px;
                color: #6b7280;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">CERTIFICAT DE VISITE</div>
            <div class="subtitle">Administration Douanière de Nouvelle-Calédonie</div>
        </div>
        
        <div class="warning-box">
            <strong>AVIS DE NON-CONFORMITÉ</strong><br>
            La déclaration en douane ci-dessous présente des non-conformités qui nécessitent une régularisation.
        </div>
        
        <div class="section">
            <div class="section-title">Informations de la Déclaration</div>
            <div class="field">
                <div class="field-label">N° Déclaration:</div>
                <div class="field-value">{declaration.declaration_id}</div>
            </div>
            <div class="field">
                <div class="field-label">Importateur:</div>
                <div class="field-value">{declaration.importer_name}</div>
            </div>
            <div class="field">
                <div class="field-label">Adresse:</div>
                <div class="field-value">{declaration.importer_address}</div>
            </div>
            <div class="field">
                <div class="field-label">Description marchandises:</div>
                <div class="field-value">{declaration.goods_description}</div>
            </div>
            <div class="field">
                <div class="field-label">Pays d'origine:</div>
                <div class="field-value">{declaration.origin_country}</div>
            </div>
            <div class="field">
                <div class="field-label">Valeur CFR:</div>
                <div class="field-value">{declaration.value_cfr:,.0f} XPF</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Non-Conformité Constatée</div>
            <div class="field">
                <div class="field-label">Type de non-conformité:</div>
                <div class="field-value">{control.non_compliance_type}</div>
            </div>
            <div class="field">
                <div class="field-label">Détails:</div>
                <div class="field-value">{control.non_compliance_details}</div>
            </div>
            <div class="field">
                <div class="field-label">Réglementation applicable:</div>
                <div class="field-value">{control.applicable_regulation}</div>
            </div>
        </div>
        
        <div class="fiscal-impact">
            <div class="section-title">Impact Fiscal</div>
            <div style="font-size: 20px; font-weight: bold; color: #d97706;">
                Montant des droits et taxes: {control.fiscal_impact:,.0f} XPF
            </div>
        </div>
        
        <div class="signature-section">
            <div class="section-title">Validation du Déclarant</div>
            <p>Je soussigné(e), représentant de <strong>{declaration.importer_name}</strong>, 
            reconnais avoir pris connaissance des non-conformités constatées et accepte 
            les mesures correctives proposées.</p>
            
            <div class="signature-box">
                <strong>Signature du déclarant:</strong><br><br>
                Date: _______________<br><br>
                Nom et qualité: ___________________________________<br><br>
                Signature:
            </div>
        </div>
        
        <div class="footer">
            <p>Certificat généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} UTC</p>
            <p>Administration Douanière de Nouvelle-Calédonie - Bureau de {declaration.customs_office}</p>
            <p>Contrôle effectué par: {control.control_officer_name}</p>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    try:
        HTML(string=html_content).write_pdf(temp_file.name)
        
        # Save to shared folder if requested
        if save_to_shared:
            filename = f"Certificat_Visite_{declaration.declaration_id}_{control.id[:8]}.pdf"
            return save_pdf_to_shared_folder(temp_file.name, filename, "controls")
        
        return temp_file.name
    except Exception as e:
        logger.error(f"Certificate PDF generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Certificate PDF generation failed")

def generate_payment_notice_pdf(fine: CustomsFine, declaration: Declaration) -> str:
    """Generate Payment Notice PDF"""
    
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
                border-bottom: 3px solid #dc2626;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .title {{
                font-size: 26px;
                font-weight: bold;
                color: #dc2626;
                margin-bottom: 10px;
            }}
            .amount-box {{
                background-color: #fee2e2;
                border: 2px solid #dc2626;
                padding: 20px;
                text-align: center;
                margin: 20px 0;
                border-radius: 8px;
            }}
            .amount {{
                font-size: 28px;
                font-weight: bold;
                color: #dc2626;
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
            .payment-info {{
                background-color: #f0f9ff;
                border-left: 4px solid #0ea5e9;
                padding: 15px;
                margin: 20px 0;
            }}
            .footer {{
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 12px;
                color: #6b7280;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">AVIS DE PAIEMENT</div>
            <div class="subtitle">Administration Douanière de Nouvelle-Calédonie</div>
        </div>
        
        <div class="amount-box">
            <div>MONTANT À RÉGLER</div>
            <div class="amount">{fine.amount:,.0f} XPF</div>
        </div>
        
        <div class="section">
            <div class="section-title">Informations de l'Amende</div>
            <div class="field">
                <div class="field-label">N° Amende LO:</div>
                <div class="field-value">{fine.sydonia_lo_number or 'En attente'}</div>
            </div>
            <div class="field">
                <div class="field-label">N° Déclaration:</div>
                <div class="field-value">{declaration.declaration_id}</div>
            </div>
            <div class="field">
                <div class="field-label">Code réglementation:</div>
                <div class="field-value">{fine.regulation_code}</div>
            </div>
            <div class="field">
                <div class="field-label">Date d'émission:</div>
                <div class="field-value">{fine.created_at.strftime('%d/%m/%Y')}</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Informations du Redevable</div>
            <div class="field">
                <div class="field-label">Importateur:</div>
                <div class="field-value">{declaration.importer_name}</div>
            </div>
            <div class="field">
                <div class="field-label">Adresse:</div>
                <div class="field-value">{declaration.importer_address}</div>
            </div>
        </div>
        
        <div class="payment-info">
            <div class="section-title">Modalités de Paiement</div>
            <p><strong>Délai de paiement:</strong> 30 jours à compter de la date d'émission</p>
            <p><strong>Modes de paiement acceptés:</strong></p>
            <ul>
                <li>Chèque à l'ordre de "Administration Douanière NC"</li>
                <li>Virement bancaire (coordonnées en fin de document)</li>
                <li>Paiement en espèces au bureau des douanes</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>Avis généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} UTC</p>
            <p>Administration Douanière de Nouvelle-Calédonie</p>
            <p>Contact: douanes@gouv.nc | Tél: +687 XX XX XX</p>
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
        logger.error(f"Payment notice PDF generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Payment notice PDF generation failed")

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

# Control Workflow endpoints
@api_router.post("/controls", response_model=Control)
async def create_control(
    control_data: ControlCreate,
    current_user: User = Depends(require_role([UserRole.CONTROL_OFFICER, UserRole.VALIDATION_OFFICER]))
):
    # Get declaration from Sydonia API
    sydonia_response = await get_sydonia_declaration(control_data.declaration_id, current_user)
    declaration_data = sydonia_response["data"]
    
    # Create Declaration record
    declaration = Declaration(**declaration_data)
    await db.declarations.insert_one(declaration.dict())
    
    # Create Control record
    default_compliance_checks = [
        ComplianceCheckItem(item="Vérification identité importateur"),
        ComplianceCheckItem(item="Contrôle cohérence déclaration/marchandises"),
        ComplianceCheckItem(item="Vérification origine marchandises"),
        ComplianceCheckItem(item="Contrôle valeur déclarée"),
        ComplianceCheckItem(item="Vérification classement tarifaire"),
        ComplianceCheckItem(item="Contrôle des documents d'accompagnement"),
        ComplianceCheckItem(item="Vérification du régime douanier"),
    ]
    
    control = Control(
        declaration_id=control_data.declaration_id,
        control_officer_id=current_user.id,
        control_officer_name=current_user.full_name,
        compliance_checks=default_compliance_checks,
        status=ControlStatus.IN_PROGRESS
    )
    
    # Add creation to history
    action = ActionHistory(
        action="control_initiated",
        user_id=current_user.id,
        user_name=current_user.full_name,
        details={"declaration_id": control_data.declaration_id}
    )
    control.history.append(action)
    
    await db.controls.insert_one(control.dict())
    return control

@api_router.get("/controls", response_model=List[Control])
async def get_controls(current_user: User = Depends(get_current_user)):
    query = {}
    
    # Role-based filtering
    if current_user.role == UserRole.CONTROL_OFFICER:
        query["control_officer_id"] = current_user.id
    # Validation officers can see all controls
    
    controls = await db.controls.find(query).to_list(1000)
    return [Control(**control) for control in controls]

@api_router.get("/controls/{control_id}", response_model=Control)
async def get_control(control_id: str, current_user: User = Depends(get_current_user)):
    control = await db.controls.find_one({"id": control_id})
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    
    # Check permissions
    control_obj = Control(**control)
    if (current_user.role == UserRole.CONTROL_OFFICER and 
        control_obj.control_officer_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this control")
    
    return control_obj

@api_router.put("/controls/{control_id}/compliance", response_model=Control)
async def update_compliance_checks(
    control_id: str,
    update_data: ComplianceCheckUpdate,
    current_user: User = Depends(require_role([UserRole.CONTROL_OFFICER, UserRole.VALIDATION_OFFICER]))
):
    control = await db.controls.find_one({"id": control_id})
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    
    # Update compliance checks
    updated_checks = []
    for check in update_data.compliance_checks:
        if check.status != ComplianceStatus.PENDING:
            check.checked_by = current_user.full_name
            check.checked_at = datetime.now(timezone.utc)
        updated_checks.append(check)
    
    # Check if any non-compliant items
    non_compliant_items = [check for check in updated_checks if check.status == ComplianceStatus.NON_COMPLIANT]
    new_status = ControlStatus.NON_COMPLIANT if non_compliant_items else ControlStatus.COMPLIANCE_CHECK
    
    # Add history entry
    action = ActionHistory(
        action="compliance_check_updated",
        user_id=current_user.id,
        user_name=current_user.full_name,
        details={"non_compliant_count": len(non_compliant_items)}
    )
    
    await db.controls.update_one(
        {"id": control_id},
        {
            "$set": {
                "compliance_checks": [check.dict() for check in updated_checks],
                "status": new_status,
                "updated_at": datetime.now(timezone.utc)
            },
            "$push": {"history": action.dict()}
        }
    )
    
    # Get updated control
    updated_control = await db.controls.find_one({"id": control_id})
    return Control(**updated_control)

@api_router.put("/controls/{control_id}/non-compliance", response_model=Control)
async def update_non_compliance(
    control_id: str,
    update_data: NonComplianceUpdate,
    current_user: User = Depends(require_role([UserRole.CONTROL_OFFICER, UserRole.VALIDATION_OFFICER]))
):
    control = await db.controls.find_one({"id": control_id})
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    
    # Get declaration
    declaration = await db.declarations.find_one({"declaration_id": control["declaration_id"]})
    if not declaration:
        raise HTTPException(status_code=404, detail="Declaration not found")
    
    # Update control with non-compliance details
    update_dict = {
        "non_compliance_type": update_data.non_compliance_type,
        "non_compliance_details": update_data.non_compliance_details,
        "fiscal_impact": update_data.fiscal_impact,
        "applicable_regulation": update_data.applicable_regulation,
        "status": ControlStatus.CERTIFICATE_GENERATED,
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Generate Certificate of Visit PDF
    control_obj = Control(**control)
    control_obj.non_compliance_type = update_data.non_compliance_type
    control_obj.non_compliance_details = update_data.non_compliance_details
    control_obj.fiscal_impact = update_data.fiscal_impact
    control_obj.applicable_regulation = update_data.applicable_regulation
    
    declaration_obj = Declaration(**declaration)
    certificate_path = generate_certificate_of_visit_pdf(control_obj, declaration_obj)
    update_dict["certificate_path"] = certificate_path
    
    # Add history entry
    action = ActionHistory(
        action="certificate_generated",
        user_id=current_user.id,
        user_name=current_user.full_name,
        details={"non_compliance_type": update_data.non_compliance_type}
    )
    
    await db.controls.update_one(
        {"id": control_id},
        {
            "$set": update_dict,
            "$push": {"history": action.dict()}
        }
    )
    
    # Get updated control
    updated_control = await db.controls.find_one({"id": control_id})
    return Control(**updated_control)

@api_router.post("/controls/{control_id}/declarant-validation")
async def declarant_validation(
    control_id: str,
    validation_data: DeclarantValidation,
    current_user: User = Depends(require_role([UserRole.CONTROL_OFFICER, UserRole.VALIDATION_OFFICER]))
):
    control = await db.controls.find_one({"id": control_id})
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    
    if not validation_data.acknowledged:
        raise HTTPException(status_code=400, detail="Declarant must acknowledge the certificate")
    
    # Update control
    update_dict = {
        "declarant_acknowledged": True,
        "fine_decision": validation_data.fine_decision,
        "pv_generated": True,
        "updated_at": datetime.now(timezone.utc)
    }
    
    # Add history entry
    action = ActionHistory(
        action="declarant_validated",
        user_id=current_user.id,
        user_name=current_user.full_name,
        details={"decision": validation_data.fine_decision}
    )
    
    if validation_data.fine_decision == "pass_over":
        update_dict["status"] = ControlStatus.COMPLETED
        action.action = "control_completed_pass_over"
    else:
        update_dict["status"] = ControlStatus.FINE_ISSUED
        action.action = "customs_fine_initiated"
        
        # Create customs fine
        fine = CustomsFine(
            control_id=control_id,
            declaration_id=control["declaration_id"],
            amount=control["fiscal_impact"],
            regulation_code=control["applicable_regulation"]
        )
        
        # Generate LO number (mock)
        fine.sydonia_lo_number = f"LO{datetime.now().strftime('%Y%m%d')}{control_id[:6].upper()}"
        
        # Generate payment notice
        declaration = await db.declarations.find_one({"declaration_id": control["declaration_id"]})
        declaration_obj = Declaration(**declaration)
        payment_notice_path = generate_payment_notice_pdf(fine, declaration_obj)
        fine.payment_notice_path = payment_notice_path
        
        await db.fines.insert_one(fine.dict())
    
    await db.controls.update_one(
        {"id": control_id},
        {
            "$set": update_dict,
            "$push": {"history": action.dict()}
        }
    )
    
    return {"message": f"Control completed with decision: {validation_data.fine_decision}"}

@api_router.get("/controls/{control_id}/certificate")
async def download_certificate(
    control_id: str,
    current_user: User = Depends(get_current_user)
):
    control = await db.controls.find_one({"id": control_id})
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    
    if not control.get("certificate_path"):
        raise HTTPException(status_code=404, detail="Certificate not generated yet")
    
    filename = f"Certificat_Visite_{control['declaration_id']}.pdf"
    return FileResponse(
        path=control["certificate_path"],
        filename=filename,
        media_type='application/pdf'
    )

@api_router.get("/fines/{fine_id}/payment-notice")
async def download_payment_notice(
    fine_id: str,
    current_user: User = Depends(get_current_user)
):
    fine = await db.fines.find_one({"id": fine_id})
    if not fine:
        raise HTTPException(status_code=404, detail="Fine not found")
    
    if not fine.get("payment_notice_path"):
        raise HTTPException(status_code=404, detail="Payment notice not generated yet")
    
    filename = f"Avis_Paiement_{fine['sydonia_lo_number']}.pdf"
    return FileResponse(
        path=fine["payment_notice_path"],
        filename=filename,
        media_type='application/pdf'
    )

# Document Templates endpoints
@api_router.get("/templates", response_model=List[DocumentTemplate])
async def get_templates(current_user: User = Depends(get_current_user)):
    templates = await db.templates.find().to_list(1000)
    return [DocumentTemplate(**template) for template in templates]

@api_router.post("/templates", response_model=DocumentTemplate)
async def create_template(
    template_data: DocumentTemplate, 
    current_user: User = Depends(require_role([UserRole.VALIDATION_OFFICER, UserRole.MOA]))
):
    template_dict = template_data.dict()
    await db.templates.insert_one(template_dict)
    return template_data

@api_router.put("/templates/{template_id}", response_model=DocumentTemplate)
async def update_template(
    template_id: str,
    template_data: DocumentTemplate,
    current_user: User = Depends(require_role([UserRole.MOA]))
):
    template_dict = template_data.dict()
    await db.templates.update_one(
        {"id": template_id},
        {"$set": template_dict}
    )
    updated_template = await db.templates.find_one({"id": template_id})
    if not updated_template:
        raise HTTPException(status_code=404, detail="Template not found")
    return DocumentTemplate(**updated_template)

@api_router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(require_role([UserRole.MOA, UserRole.VALIDATION_OFFICER]))
):
    # Check if template is being used by existing documents
    documents_using_template = await db.documents.count_documents({"template_id": template_id})
    if documents_using_template > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete template: {documents_using_template} document(s) are using this template"
        )
    
    result = await db.templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully"}

# Document Type Management for MOA
class DocumentTypeCreate(BaseModel):
    name: str
    description: str
    code: str

class DocumentTypeModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    code: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str

@api_router.get("/document-types", response_model=List[DocumentTypeModel])
async def get_document_types(current_user: User = Depends(get_current_user)):
    doc_types = await db.document_types.find().to_list(1000)
    return [DocumentTypeModel(**doc_type) for doc_type in doc_types]

@api_router.post("/document-types", response_model=DocumentTypeModel)
async def create_document_type(
    doc_type_data: DocumentTypeCreate,
    current_user: User = Depends(require_role([UserRole.MOA]))
):
    # Check if code already exists
    existing = await db.document_types.find_one({"code": doc_type_data.code})
    if existing:
        raise HTTPException(status_code=400, detail="Document type code already exists")
    
    doc_type = DocumentTypeModel(
        **doc_type_data.dict(),
        created_by=current_user.id
    )
    
    await db.document_types.insert_one(doc_type.dict())
    return doc_type

@api_router.put("/document-types/{doc_type_id}", response_model=DocumentTypeModel)
async def update_document_type(
    doc_type_id: str,
    doc_type_data: DocumentTypeCreate,
    current_user: User = Depends(require_role([UserRole.MOA]))
):
    doc_type_dict = doc_type_data.dict()
    await db.document_types.update_one(
        {"id": doc_type_id},
        {"$set": doc_type_dict}
    )
    
    updated_doc_type = await db.document_types.find_one({"id": doc_type_id})
    if not updated_doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")
    return DocumentTypeModel(**updated_doc_type)

@api_router.delete("/document-types/{doc_type_id}")
async def delete_document_type(
    doc_type_id: str,
    current_user: User = Depends(require_role([UserRole.MOA]))
):
    # Get the document type first to check its code
    doc_type = await db.document_types.find_one({"id": doc_type_id})
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    # Check if document type is being used by existing documents or templates
    # We need to check both the custom code and any enum values that might match
    code_variations = [
        doc_type["code"],
        doc_type["code"].lower(),
        doc_type["name"].lower().replace(" ", "_").replace("'", "")
    ]
    
    total_documents = 0
    total_templates = 0
    
    for code_var in code_variations:
        documents_count = await db.documents.count_documents({"document_type": code_var})
        templates_count = await db.templates.count_documents({"document_type": code_var})
        total_documents += documents_count
        total_templates += templates_count
    
    if total_documents > 0 or total_templates > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete document type: {total_documents} document(s) and {total_templates} template(s) are using this type"
        )
    
    result = await db.document_types.delete_one({"id": doc_type_id})
    return {"message": "Document type deleted successfully"}

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
        "customs_office": "Nouméa-Port",
        "tariff_code": "8471.30.00",
        "weight": 250.5,
        "quantity": 10
    }
    
    return {"data": mock_data, "status": "success"}

# Initialize default templates and regulations
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

@api_router.post("/init/regulations")
async def initialize_regulations():
    existing_regulations = await db.regulations.count_documents({})
    if existing_regulations > 0:
        return {"message": "Regulations already initialized"}
    
    default_regulations = [
        Regulation(
            code="CD-215",
            title="Fausse déclaration d'origine",
            description="Déclaration erronée du pays d'origine des marchandises",
            category="Origin",
            fine_rate=0.15
        ),
        Regulation(
            code="CD-230",
            title="Sous-évaluation",
            description="Déclaration d'une valeur inférieure à la valeur réelle",
            category="Value",  
            fine_rate=0.25
        ),
        Regulation(
            code="CD-182",
            title="Fausse déclaration d'espèce",
            description="Classification tarifaire incorrecte des marchandises",
            category="Classification",
            fine_rate=0.20
        )
    ]
    
    for regulation in default_regulations:
        await db.regulations.insert_one(regulation.dict())
    
    return {"message": f"Initialized {len(default_regulations)} default regulations"}

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