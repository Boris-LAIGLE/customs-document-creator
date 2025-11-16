import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Textarea } from './components/ui/textarea';
import { Label } from './components/ui/label';
import { Separator } from './components/ui/separator';
import { Alert, AlertDescription } from './components/ui/alert';
import { Checkbox } from './components/ui/checkbox';
import { FileText, Users, CheckCircle, Clock, AlertTriangle, Plus, LogOut, Search, Filter, 
         Settings, Download, Eye, PlayCircle, StopCircle, XCircle } from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, {
        username,
        password
      });
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  const register = async (userData) => {
    try {
      await axios.post(`${API}/auth/register`, userData);
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, register, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Login Component
const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const { login, register } = useAuth();

  const [registerData, setRegisterData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    role: 'drafting_agent'
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    const result = await login(username, password);
    if (!result.success) {
      setError(result.error);
    }
    setLoading(false);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    const result = await register(registerData);
    if (result.success) {
      setShowRegister(false);
      setError('');
      alert('Registration successful! Please login.');
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-xl border-0 bg-white/80 backdrop-blur-sm">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
            <FileText className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-slate-800">
            Administration Douanière
          </CardTitle>
          <CardDescription className="text-slate-600">
            Système de gestion des actes administratifs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!showRegister ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Nom d'utilisateur</Label>
                <Input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="transition-all duration-200 focus:scale-[1.02]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Mot de passe</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="transition-all duration-200 focus:scale-[1.02]"
                />
              </div>
              {error && (
                <Alert className="border-red-200 bg-red-50">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <AlertDescription className="text-red-700">{error}</AlertDescription>
                </Alert>
              )}
              <Button 
                type="submit" 
                className="w-full bg-blue-600 hover:bg-blue-700 transition-all duration-200 hover:scale-[1.02]" 
                disabled={loading}
              >
                {loading ? 'Connexion...' : 'Se connecter'}
              </Button>
              <Button 
                type="button" 
                variant="outline" 
                className="w-full" 
                onClick={() => setShowRegister(true)}
              >
                Créer un compte
              </Button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="reg-username">Nom d'utilisateur</Label>
                <Input
                  id="reg-username"
                  type="text"
                  value={registerData.username}
                  onChange={(e) => setRegisterData({...registerData, username: e.target.value})}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={registerData.email}
                  onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="full_name">Nom complet</Label>
                <Input
                  id="full_name"
                  type="text"
                  value={registerData.full_name}
                  onChange={(e) => setRegisterData({...registerData, full_name: e.target.value})}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Rôle</Label>
                <Select value={registerData.role} onValueChange={(value) => setRegisterData({...registerData, role: value})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="drafting_agent">Agent de rédaction</SelectItem>
                    <SelectItem value="control_officer">Agent de contrôle</SelectItem>
                    <SelectItem value="validation_officer">Agent de validation</SelectItem>
                    <SelectItem value="moa">Administrateur MOA</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="reg-password">Mot de passe</Label>
                <Input
                  id="reg-password"
                  type="password"
                  value={registerData.password}
                  onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                  required
                />
              </div>
              {error && (
                <Alert className="border-red-200 bg-red-50">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <AlertDescription className="text-red-700">{error}</AlertDescription>
                </Alert>
              )}
              <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-700" disabled={loading}>
                {loading ? 'Création...' : 'Créer le compte'}
              </Button>
              <Button 
                type="button" 
                variant="outline" 
                className="w-full" 
                onClick={() => setShowRegister(false)}
              >
                Retour à la connexion
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const { user, logout } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [controls, setControls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState('documents');

  useEffect(() => {
    fetchData();
    initializeTemplates();
    initializeRegulations();
  }, []);

  const fetchData = async () => {
    try {
      const requests = [
        axios.get(`${API}/documents`),
        axios.get(`${API}/templates`)
      ];
      
      // Only fetch controls for control officers and validation officers
      if (user.role === 'control_officer' || user.role === 'validation_officer') {
        requests.push(axios.get(`${API}/controls`));
      }
      
      const responses = await Promise.all(requests);
      setDocuments(responses[0].data);
      setTemplates(responses[1].data);
      
      if (responses[2]) {
        setControls(responses[2].data);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const initializeTemplates = async () => {
    try {
      await axios.post(`${API}/init/templates`);
    } catch (error) {
      console.error('Error initializing templates:', error);
    }
  };

  const initializeRegulations = async () => {
    try {
      await axios.post(`${API}/init/regulations`);
    } catch (error) {
      console.error('Error initializing regulations:', error);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      draft: { color: 'bg-slate-100 text-slate-700', label: 'Brouillon' },
      under_control: { color: 'bg-orange-100 text-orange-700', label: 'En contrôle' },
      under_validation: { color: 'bg-blue-100 text-blue-700', label: 'En validation' },
      validated: { color: 'bg-green-100 text-green-700', label: 'Validé' },
      rejected: { color: 'bg-red-100 text-red-700', label: 'Rejeté' }
    };
    
    const config = statusConfig[status] || statusConfig.draft;
    return (
      <Badge className={`${config.color} border-0`}>
        {config.label}
      </Badge>
    );
  };

  const getRoleLabel = (role) => {
    const roles = {
      drafting_agent: 'Agent de rédaction',
      control_officer: 'Agent de contrôle',
      validation_officer: 'Agent de validation',
      moa: 'Administrateur MOA'
    };
    return roles[role] || role;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Chargement...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <FileText className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-xl font-semibold text-slate-800">Administration Douanière</h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-slate-800">{user.full_name}</p>
                <p className="text-xs text-slate-500">{getRoleLabel(user.role)}</p>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={logout}
                className="flex items-center space-x-2"
              >
                <LogOut className="h-4 w-4" />
                <span>Déconnexion</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={selectedTab} onValueChange={setSelectedTab} className="space-y-6">
          <TabsList className={`grid w-full ${
            user.role === 'moa' ? 'grid-cols-5 lg:w-[600px]' :
            (user.role === 'control_officer' || user.role === 'validation_officer') ? 'grid-cols-4 lg:w-[500px]' : 
            'grid-cols-3 lg:w-96'
          }`}>
            <TabsTrigger value="documents" className="flex items-center space-x-2">
              <FileText className="h-4 w-4" />
              <span>Documents</span>
            </TabsTrigger>
            {(user.role === 'control_officer' || user.role === 'validation_officer') && (
              <TabsTrigger value="controls" className="flex items-center space-x-2">
                <Settings className="h-4 w-4" />
                <span>Contrôles</span>
              </TabsTrigger>
            )}
            <TabsTrigger value="templates" className="flex items-center space-x-2">
              <Users className="h-4 w-4" />
              <span>Modèles</span>
            </TabsTrigger>
            {user.role === 'moa' && (
              <TabsTrigger value="admin" className="flex items-center space-x-2">
                <Settings className="h-4 w-4" />
                <span>Administration</span>
              </TabsTrigger>
            )}
            <TabsTrigger value="stats" className="flex items-center space-x-2">
              <CheckCircle className="h-4 w-4" />
              <span>Statistiques</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="documents" className="space-y-6">
            <DocumentsView documents={documents} templates={templates} onRefresh={fetchData} />
          </TabsContent>

          {(user.role === 'control_officer' || user.role === 'validation_officer') && (
            <TabsContent value="controls" className="space-y-6">
              <ControlsView controls={controls} onRefresh={fetchData} />
            </TabsContent>
          )}

          <TabsContent value="templates" className="space-y-6">
            <TemplatesView templates={templates} onRefresh={fetchData} />
          </TabsContent>

          {user.role === 'moa' && (
            <TabsContent value="admin" className="space-y-6">
              <AdminView templates={templates} onRefresh={fetchData} />
            </TabsContent>
          )}

          <TabsContent value="stats" className="space-y-6">
            <StatsView documents={documents} controls={controls} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

// Documents View Component
const DocumentsView = ({ documents, templates, onRefresh }) => {
  const { user } = useAuth();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [newDocument, setNewDocument] = useState({
    title: '',
    document_type: 'customs_report',
    template_id: '',
    content: {}
  });

  const canCreateDocument = user.role === 'drafting_agent';

  const getStatusBadge = (status) => {
    const statusConfig = {
      draft: { color: 'bg-slate-100 text-slate-700', label: 'Brouillon' },
      under_control: { color: 'bg-orange-100 text-orange-700', label: 'En contrôle' },
      under_validation: { color: 'bg-blue-100 text-blue-700', label: 'En validation' },
      validated: { color: 'bg-green-100 text-green-700', label: 'Validé' },
      rejected: { color: 'bg-red-100 text-red-700', label: 'Rejeté' }
    };
    
    const config = statusConfig[status] || statusConfig.draft;
    return (
      <Badge className={`${config.color} border-0`}>
        {config.label}
      </Badge>
    );
  };

  const handleCreateDocument = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/documents`, newDocument);
      setShowCreateDialog(false);
      setNewDocument({
        title: '',
        document_type: 'customs_report',
        template_id: '',
        content: {}
      });
      onRefresh();
    } catch (error) {
      console.error('Error creating document:', error);
      alert('Erreur lors de la création du document');
    }
  };

  const handleSubmitDocument = async (documentId) => {
    try {
      await axios.post(`${API}/documents/${documentId}/submit`);
      onRefresh();
      alert('Document soumis pour contrôle');
    } catch (error) {
      console.error('Error submitting document:', error);
      alert('Erreur lors de la soumission');
    }
  };

  const handleDownloadPDF = async (documentId) => {
    try {
      const response = await axios.get(`${API}/documents/${documentId}/pdf`, {
        responseType: 'blob'
      });
      
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from response headers or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'document.pdf';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?(.+)"?/);
        if (match) {
          filename = match[1];
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Erreur lors du téléchargement du PDF');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-800">Mes Documents</h2>
        {canCreateDocument && (
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700">
                <Plus className="h-4 w-4 mr-2" />
                Nouveau Document
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Créer un nouveau document</DialogTitle>
                <DialogDescription>
                  Sélectionnez un modèle pour commencer
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateDocument} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Titre</Label>
                  <Input
                    id="title"
                    value={newDocument.title}
                    onChange={(e) => setNewDocument({...newDocument, title: e.target.value})}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="document_type">Type de document</Label>
                  <Select value={newDocument.document_type} onValueChange={(value) => setNewDocument({...newDocument, document_type: value})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="customs_report">Rapport douanier</SelectItem>
                      <SelectItem value="administrative_act">Acte administratif</SelectItem>
                      <SelectItem value="violation_report">Rapport d'infraction</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="template">Modèle</Label>
                  <Select value={newDocument.template_id} onValueChange={(value) => setNewDocument({...newDocument, template_id: value})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner un modèle" />
                    </SelectTrigger>
                    <SelectContent>
                      {templates.filter(t => t.document_type === newDocument.document_type).map(template => (
                        <SelectItem key={template.id} value={template.id}>
                          {template.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button type="submit" className="w-full">
                  Créer le document
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="grid gap-4">
        {documents.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FileText className="h-12 w-12 text-slate-400 mb-4" />
              <h3 className="text-lg font-medium text-slate-600 mb-2">Aucun document</h3>
              <p className="text-slate-500 text-center">
                {canCreateDocument ? 'Créez votre premier document pour commencer' : 'Aucun document à afficher'}
              </p>
            </CardContent>
          </Card>
        ) : (
          documents.map(document => (
            <Card key={document.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 mb-1">{document.title}</h3>
                    <p className="text-sm text-slate-500">
                      Créé par {document.created_by_name} • {new Date(document.created_at).toLocaleDateString('fr-FR')}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getStatusBadge(document.status)}
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4 text-sm text-slate-600">
                    <span>Type: {document.document_type}</span>
                    <span>•</span>
                    <span>Modifié: {new Date(document.updated_at).toLocaleDateString('fr-FR')}</span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {document.status === 'draft' && document.created_by === user.id && (
                      <Button 
                        size="sm" 
                        onClick={() => handleSubmitDocument(document.id)}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        Soumettre
                      </Button>
                    )}
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleDownloadPDF(document.id)}
                      className="flex items-center space-x-1"
                    >
                      <FileText className="h-3 w-3" />
                      <span>PDF</span>
                    </Button>
                    <Button variant="outline" size="sm">
                      Voir détails
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

// Templates View Component
const TemplatesView = ({ templates }) => {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Modèles de Documents</h2>
      
      <div className="grid gap-4 md:grid-cols-2">
        {templates.map(template => (
          <Card key={template.id}>
            <CardHeader>
              <CardTitle className="text-lg">{template.name}</CardTitle>
              <CardDescription>
                Type: {template.document_type} • {template.fields.length} champs
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <h4 className="font-medium text-sm text-slate-700 mb-2">Champs requis:</h4>
                  <div className="flex flex-wrap gap-1">
                    {template.fields.slice(0, 3).map(field => (
                      <Badge key={field.name} variant="outline" className="text-xs">
                        {field.label}
                      </Badge>
                    ))}
                    {template.fields.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{template.fields.length - 3} autres
                      </Badge>
                    )}
                  </div>
                </div>
                
                {template.checklist.length > 0 && (
                  <div>
                    <h4 className="font-medium text-sm text-slate-700 mb-2">Points de contrôle:</h4>
                    <p className="text-xs text-slate-600">
                      {template.checklist.length} éléments de vérification
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// Document Type Card Component
const DocumentTypeCard = ({ docType, onDelete, onEdit }) => {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const handleDelete = () => {
    onDelete(docType.id, docType.name);
    setShowDeleteDialog(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{docType.name}</CardTitle>
        <CardDescription className="text-sm">
          Code: {docType.code}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-slate-600 mb-4">{docType.description}</p>
        <div className="flex justify-end space-x-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => onEdit(docType)}
            className="hover:bg-blue-50"
          >
            <Settings className="h-3 w-3 mr-1" />
            Modifier
          </Button>
          
          <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
            <DialogTrigger asChild>
              <Button 
                variant="outline" 
                size="sm" 
                className="text-red-600 hover:bg-red-50 hover:border-red-200"
              >
                <XCircle className="h-3 w-3 mr-1" />
                Supprimer
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle className="flex items-center text-red-600">
                  <AlertTriangle className="h-5 w-5 mr-2" />
                  Confirmer la suppression
                </DialogTitle>
                <DialogDescription>
                  Êtes-vous sûr de vouloir supprimer le type de document <strong>"{docType.name}"</strong> ?
                </DialogDescription>
              </DialogHeader>
              
              <Alert className="border-red-200 bg-red-50">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                <AlertDescription className="text-red-700">
                  <strong>Attention :</strong> Cette action est irréversible et pourrait affecter 
                  les documents et modèles existants utilisant ce type.
                </AlertDescription>
              </Alert>

              <div className="flex justify-end space-x-2 mt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setShowDeleteDialog(false)}
                >
                  Annuler
                </Button>
                <Button 
                  variant="destructive" 
                  onClick={handleDelete}
                  className="bg-red-600 hover:bg-red-700"
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Supprimer définitivement
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </CardContent>
    </Card>
  );
};

// Admin View Component for MOA
const AdminView = ({ templates, onRefresh }) => {
  const [documentTypes, setDocumentTypes] = useState([]);
  const [showCreateTemplate, setShowCreateTemplate] = useState(false);
  const [showCreateDocType, setShowCreateDocType] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    document_type: 'customs_report',
    fields: [],
    checklist: []
  });
  const [newDocType, setNewDocType] = useState({
    name: '',
    description: '',
    code: ''
  });
  const [newField, setNewField] = useState({
    name: '',
    label: '',
    type: 'text',
    required: false
  });
  const [newCheckItem, setNewCheckItem] = useState('');

  useEffect(() => {
    fetchDocumentTypes();
  }, []);

  const fetchDocumentTypes = async () => {
    try {
      const response = await axios.get(`${API}/document-types`);
      setDocumentTypes(response.data);
    } catch (error) {
      console.error('Error fetching document types:', error);
    }
  };

  const handleCreateTemplate = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/templates`, newTemplate);
      setShowCreateTemplate(false);
      setNewTemplate({
        name: '',
        document_type: 'customs_report',
        fields: [],
        checklist: []
      });
      onRefresh();
      alert('Modèle créé avec succès');
    } catch (error) {
      console.error('Error creating template:', error);
      alert('Erreur lors de la création du modèle');
    }
  };

  const handleCreateDocType = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/document-types`, newDocType);
      setShowCreateDocType(false);
      setNewDocType({
        name: '',
        description: '',
        code: ''
      });
      fetchDocumentTypes();
      alert('Type de document créé avec succès');
    } catch (error) {
      console.error('Error creating document type:', error);
      alert('Erreur lors de la création du type de document');
    }
  };

  const handleDeleteDocType = async (docTypeId, docTypeName) => {
    const confirmed = window.confirm(
      `Êtes-vous sûr de vouloir supprimer le type de document "${docTypeName}" ?\n\n` +
      'Cette action est irréversible et pourrait affecter les documents existants.'
    );
    
    if (!confirmed) return;

    try {
      await axios.delete(`${API}/document-types/${docTypeId}`);
      fetchDocumentTypes();
      alert('Type de document supprimé avec succès');
    } catch (error) {
      console.error('Error deleting document type:', error);
      const errorMsg = error.response?.data?.detail || 'Erreur lors de la suppression';
      alert(`Erreur: ${errorMsg}`);
    }
  };

  const handleEditDocType = (docType) => {
    setNewDocType({
      name: docType.name,
      description: docType.description,
      code: docType.code
    });
    setShowCreateDocType(true);
  };

  const handleDeleteTemplate = async (templateId, templateName) => {
    const confirmed = window.confirm(
      `Êtes-vous sûr de vouloir supprimer le modèle "${templateName}" ?\n\n` +
      'Cette action est irréversible et pourrait affecter les documents existants.'
    );
    
    if (!confirmed) return;

    try {
      await axios.delete(`${API}/templates/${templateId}`);
      onRefresh();
      alert('Modèle supprimé avec succès');
    } catch (error) {
      console.error('Error deleting template:', error);
      const errorMsg = error.response?.data?.detail || 'Erreur lors de la suppression';
      alert(`Erreur: ${errorMsg}`);
    }
  };

  const handleEditTemplate = (template) => {
    setNewTemplate({
      name: template.name,
      document_type: template.document_type,
      fields: [...template.fields],
      checklist: [...template.checklist]
    });
    setShowCreateTemplate(true);
  };

  const addField = () => {
    if (newField.name && newField.label) {
      setNewTemplate({
        ...newTemplate,
        fields: [...newTemplate.fields, { ...newField }]
      });
      setNewField({
        name: '',
        label: '',
        type: 'text',
        required: false
      });
    }
  };

  const removeField = (index) => {
    const updatedFields = newTemplate.fields.filter((_, i) => i !== index);
    setNewTemplate({
      ...newTemplate,
      fields: updatedFields
    });
  };

  const addCheckItem = () => {
    if (newCheckItem.trim()) {
      setNewTemplate({
        ...newTemplate,
        checklist: [...newTemplate.checklist, newCheckItem.trim()]
      });
      setNewCheckItem('');
    }
  };

  const removeCheckItem = (index) => {
    const updatedChecklist = newTemplate.checklist.filter((_, i) => i !== index);
    setNewTemplate({
      ...newTemplate,
      checklist: updatedChecklist
    });
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Administration MOA</h2>
      
      <Tabs defaultValue="templates" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="templates">Gestion des Modèles</TabsTrigger>
          <TabsTrigger value="doc-types">Types de Documents</TabsTrigger>
          <TabsTrigger value="backups">Sauvegardes PDF</TabsTrigger>
        </TabsList>

        <TabsContent value="templates" className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Modèles de Documents</h3>
            <Dialog open={showCreateTemplate} onOpenChange={setShowCreateTemplate}>
              <DialogTrigger asChild>
                <Button className="bg-green-600 hover:bg-green-700">
                  <Plus className="h-4 w-4 mr-2" />
                  Nouveau Modèle
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Créer un nouveau modèle</DialogTitle>
                  <DialogDescription>
                    Définissez les champs et contrôles pour ce modèle
                  </DialogDescription>
                </DialogHeader>
                
                <form onSubmit={handleCreateTemplate} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Nom du modèle</Label>
                      <Input
                        value={newTemplate.name}
                        onChange={(e) => setNewTemplate({...newTemplate, name: e.target.value})}
                        required
                      />
                    </div>
                    <div>
                      <Label>Type de document</Label>
                      <Select value={newTemplate.document_type} onValueChange={(value) => 
                        setNewTemplate({...newTemplate, document_type: value})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="customs_report">Rapport douanier</SelectItem>
                          <SelectItem value="administrative_act">Acte administratif</SelectItem>
                          <SelectItem value="violation_report">Rapport d'infraction</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <Separator />

                  <div>
                    <h4 className="font-medium mb-3">Champs du modèle</h4>
                    <div className="grid grid-cols-4 gap-2 mb-3">
                      <Input
                        placeholder="Nom du champ"
                        value={newField.name}
                        onChange={(e) => setNewField({...newField, name: e.target.value})}
                      />
                      <Input
                        placeholder="Libellé"
                        value={newField.label}
                        onChange={(e) => setNewField({...newField, label: e.target.value})}
                      />
                      <Select value={newField.type} onValueChange={(value) => setNewField({...newField, type: value})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="text">Texte</SelectItem>
                          <SelectItem value="textarea">Zone de texte</SelectItem>
                          <SelectItem value="number">Nombre</SelectItem>
                          <SelectItem value="date">Date</SelectItem>
                          <SelectItem value="select">Liste déroulante</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button type="button" onClick={addField} size="sm">Ajouter</Button>
                    </div>

                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {newTemplate.fields.map((field, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                          <span className="text-sm">
                            <strong>{field.label}</strong> ({field.type})
                          </span>
                          <Button 
                            type="button" 
                            variant="outline" 
                            size="sm"
                            onClick={() => removeField(index)}
                          >
                            <XCircle className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <Separator />

                  <div>
                    <h4 className="font-medium mb-3">Liste de contrôle</h4>
                    <div className="flex gap-2 mb-3">
                      <Input
                        placeholder="Élément de contrôle"
                        value={newCheckItem}
                        onChange={(e) => setNewCheckItem(e.target.value)}
                      />
                      <Button type="button" onClick={addCheckItem} size="sm">Ajouter</Button>
                    </div>

                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {newTemplate.checklist.map((item, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                          <span className="text-sm">{item}</span>
                          <Button 
                            type="button" 
                            variant="outline" 
                            size="sm"
                            onClick={() => removeCheckItem(index)}
                          >
                            <XCircle className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <Button type="submit" className="w-full">
                    Créer le modèle
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {templates.map(template => (
              <Card key={template.id} className="card-hover">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-lg">{template.name}</CardTitle>
                      <CardDescription>
                        Type: {template.document_type} • {template.fields.length} champs
                      </CardDescription>
                    </div>
                    <div className="flex space-x-1">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleEditTemplate(template)}
                        className="hover:bg-blue-50"
                      >
                        <Settings className="h-3 w-3" />
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleDeleteTemplate(template.id, template.name)}
                        className="text-red-600 hover:bg-red-50"
                      >
                        <XCircle className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="doc-types" className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Types de Documents</h3>
            <Dialog open={showCreateDocType} onOpenChange={setShowCreateDocType}>
              <DialogTrigger asChild>
                <Button className="bg-purple-600 hover:bg-purple-700">
                  <Plus className="h-4 w-4 mr-2" />
                  Nouveau Type
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Créer un type de document</DialogTitle>
                </DialogHeader>
                
                <form onSubmit={handleCreateDocType} className="space-y-4">
                  <div>
                    <Label>Nom</Label>
                    <Input
                      value={newDocType.name}
                      onChange={(e) => setNewDocType({...newDocType, name: e.target.value})}
                      placeholder="Ex: Certificat d'origine"
                      required
                    />
                  </div>
                  <div>
                    <Label>Code</Label>
                    <Input
                      value={newDocType.code}
                      onChange={(e) => setNewDocType({...newDocType, code: e.target.value.toUpperCase()})}
                      placeholder="Ex: CERT_ORIGIN"
                      required
                    />
                  </div>
                  <div>
                    <Label>Description</Label>
                    <Textarea
                      value={newDocType.description}
                      onChange={(e) => setNewDocType({...newDocType, description: e.target.value})}
                      placeholder="Description du type de document"
                    />
                  </div>
                  <Button type="submit" className="w-full">
                    Créer le type
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {documentTypes.map(docType => (
              <DocumentTypeCard 
                key={docType.id} 
                docType={docType} 
                onDelete={handleDeleteDocType}
                onEdit={handleEditDocType}
              />
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Controls View Component
const ControlsView = ({ controls, onRefresh }) => {
  const { user } = useAuth();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedControl, setSelectedControl] = useState(null);
  const [newControl, setNewControl] = useState({
    declaration_id: ''
  });

  const canCreateControl = user.role === 'control_officer' || user.role === 'validation_officer';

  const handleCreateControl = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/controls`, newControl);
      setShowCreateDialog(false);
      setNewControl({ declaration_id: '' });
      onRefresh();
      alert('Contrôle créé avec succès');
    } catch (error) {
      console.error('Error creating control:', error);
      alert('Erreur lors de la création du contrôle');
    }
  };

  const getControlStatusBadge = (status) => {
    const statusConfig = {
      initiated: { color: 'bg-slate-100 text-slate-700', label: 'Initié' },
      in_progress: { color: 'bg-blue-100 text-blue-700', label: 'En cours' },
      compliance_check: { color: 'bg-yellow-100 text-yellow-700', label: 'Vérification' },
      non_compliant: { color: 'bg-red-100 text-red-700', label: 'Non-conforme' },
      certificate_generated: { color: 'bg-purple-100 text-purple-700', label: 'Certificat généré' },
      declarant_validation: { color: 'bg-indigo-100 text-indigo-700', label: 'En validation' },
      completed: { color: 'bg-green-100 text-green-700', label: 'Terminé' },
      fine_issued: { color: 'bg-red-100 text-red-700', label: 'Amende émise' }
    };
    
    const config = statusConfig[status] || statusConfig.initiated;
    return (
      <Badge className={`${config.color} border-0`}>
        {config.label}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-800">Contrôles Douaniers</h2>
        {canCreateControl && (
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700">
                <Plus className="h-4 w-4 mr-2" />
                Nouveau Contrôle
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Initier un nouveau contrôle</DialogTitle>
                <DialogDescription>
                  Saisissez le numéro de déclaration Sydonia
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateControl} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="declaration_id">N° Déclaration Sydonia</Label>
                  <Input
                    id="declaration_id"
                    value={newControl.declaration_id}
                    onChange={(e) => setNewControl({...newControl, declaration_id: e.target.value})}
                    placeholder="Ex: D2024/15847"
                    required
                  />
                </div>
                <Button type="submit" className="w-full">
                  Créer le contrôle
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="grid gap-4">
        {controls.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Settings className="h-12 w-12 text-slate-400 mb-4" />
              <h3 className="text-lg font-medium text-slate-600 mb-2">Aucun contrôle</h3>
              <p className="text-slate-500 text-center">
                {canCreateControl ? 'Initiez votre premier contrôle pour commencer' : 'Aucun contrôle à afficher'}
              </p>
            </CardContent>
          </Card>
        ) : (
          controls.map(control => (
            <Card key={control.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 mb-1">
                      Déclaration {control.declaration_id}
                    </h3>
                    <p className="text-sm text-slate-500">
                      Agent: {control.control_officer_name} • {new Date(control.created_at).toLocaleDateString('fr-FR')}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getControlStatusBadge(control.status)}
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4 text-sm text-slate-600">
                    <span>Mis à jour: {new Date(control.updated_at).toLocaleDateString('fr-FR')}</span>
                    {control.fiscal_impact && (
                      <>
                        <span>•</span>
                        <span className="font-medium text-red-600">
                          Impact: {control.fiscal_impact.toLocaleString()} XPF
                        </span>
                      </>
                    )}
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setSelectedControl(control)}
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      Détails
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Control Details Dialog */}
      {selectedControl && (
        <ControlDetailsDialog 
          control={selectedControl} 
          onClose={() => setSelectedControl(null)}
          onRefresh={onRefresh}
        />
      )}
    </div>
  );
};

// Control Details Dialog Component
const ControlDetailsDialog = ({ control, onClose, onRefresh }) => {
  const { user } = useAuth();
  const [complianceChecks, setComplianceChecks] = useState(control.compliance_checks || []);
  const [nonComplianceData, setNonComplianceData] = useState({
    non_compliance_type: '',
    non_compliance_details: '',
    fiscal_impact: '',
    applicable_regulation: ''
  });
  const [declarantValidation, setDeclarantValidation] = useState({
    acknowledged: false,
    fine_decision: ''
  });

  const canEdit = user.role === 'control_officer' || user.role === 'validation_officer';

  const handleComplianceUpdate = async () => {
    try {
      await axios.put(`${API}/controls/${control.id}/compliance`, {
        compliance_checks: complianceChecks
      });
      onRefresh();
      alert('Vérifications de conformité mises à jour');
    } catch (error) {
      console.error('Error updating compliance:', error);
      alert('Erreur lors de la mise à jour');
    }
  };

  const handleNonComplianceSubmit = async () => {
    try {
      await axios.put(`${API}/controls/${control.id}/non-compliance`, {
        ...nonComplianceData,
        fiscal_impact: parseFloat(nonComplianceData.fiscal_impact)
      });
      onRefresh();
      alert('Certificat de visite généré');
    } catch (error) {
      console.error('Error updating non-compliance:', error);
      alert('Erreur lors de la génération du certificat');
    }
  };

  const handleDeclarantValidation = async () => {
    try {
      await axios.post(`${API}/controls/${control.id}/declarant-validation`, declarantValidation);
      onRefresh();
      alert('Validation du déclarant enregistrée');
    } catch (error) {
      console.error('Error validating:', error);
      alert('Erreur lors de la validation');
    }
  };

  const downloadCertificate = async () => {
    try {
      const response = await axios.get(`${API}/controls/${control.id}/certificate`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Certificat_Visite_${control.declaration_id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading certificate:', error);
      alert('Erreur lors du téléchargement');
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Contrôle - Déclaration {control.declaration_id}</DialogTitle>
          <DialogDescription>
            Agent: {control.control_officer_name} • Statut: {control.status}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="compliance" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="compliance">Conformité</TabsTrigger>
            <TabsTrigger value="non-compliance">Non-conformité</TabsTrigger>
            <TabsTrigger value="validation">Validation</TabsTrigger>
            <TabsTrigger value="history">Historique</TabsTrigger>
          </TabsList>

          <TabsContent value="compliance" className="space-y-4">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Vérifications de conformité</h3>
              {complianceChecks.map((check, index) => (
                <div key={check.id} className="flex items-center space-x-4 p-4 border rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium">{check.item}</p>
                    {check.notes && (
                      <p className="text-sm text-slate-600 mt-1">{check.notes}</p>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <Select 
                      value={check.status} 
                      onValueChange={(value) => {
                        const updated = [...complianceChecks];
                        updated[index] = {...check, status: value};
                        setComplianceChecks(updated);
                      }}
                      disabled={!canEdit}
                    >
                      <SelectTrigger className="w-40">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pending">En attente</SelectItem>
                        <SelectItem value="compliant">Conforme</SelectItem>
                        <SelectItem value="non_compliant">Non-conforme</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              ))}
              {canEdit && (
                <Button onClick={handleComplianceUpdate} className="w-full">
                  Mettre à jour les vérifications
                </Button>
              )}
            </div>
          </TabsContent>

          <TabsContent value="non-compliance" className="space-y-4">
            {control.status === 'non_compliant' && canEdit ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Détails de la non-conformité</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Type de non-conformité</Label>
                    <Select value={nonComplianceData.non_compliance_type} onValueChange={(value) => 
                      setNonComplianceData({...nonComplianceData, non_compliance_type: value})}>
                      <SelectTrigger>
                        <SelectValue placeholder="Sélectionner le type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="species">Espèce</SelectItem>
                        <SelectItem value="origin">Origine</SelectItem>
                        <SelectItem value="value">Valeur</SelectItem>
                        <SelectItem value="classification">Classification</SelectItem>
                        <SelectItem value="documentation">Documentation</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Impact fiscal (XPF)</Label>
                    <Input
                      type="number"
                      value={nonComplianceData.fiscal_impact}
                      onChange={(e) => setNonComplianceData({...nonComplianceData, fiscal_impact: e.target.value})}
                      placeholder="Montant en XPF"
                    />
                  </div>
                </div>
                <div>
                  <Label>Détails</Label>
                  <Textarea
                    value={nonComplianceData.non_compliance_details}
                    onChange={(e) => setNonComplianceData({...nonComplianceData, non_compliance_details: e.target.value})}
                    placeholder="Décrivez la non-conformité constatée..."
                  />
                </div>
                <div>
                  <Label>Réglementation applicable</Label>
                  <Input
                    value={nonComplianceData.applicable_regulation}
                    onChange={(e) => setNonComplianceData({...nonComplianceData, applicable_regulation: e.target.value})}
                    placeholder="Ex: Article 215 du Code des Douanes"
                  />
                </div>
                <Button onClick={handleNonComplianceSubmit} className="w-full bg-red-600 hover:bg-red-700">
                  Générer le certificat de visite
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {control.certificate_path && (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h4 className="font-medium text-yellow-800 mb-2">Certificat de visite généré</h4>
                    <p className="text-sm text-yellow-700 mb-3">
                      Type: {control.non_compliance_type} • Impact: {control.fiscal_impact?.toLocaleString()} XPF
                    </p>
                    <Button onClick={downloadCertificate} variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Télécharger le certificat
                    </Button>
                  </div>
                )}
              </div>
            )}
          </TabsContent>

          <TabsContent value="validation" className="space-y-4">
            {control.status === 'certificate_generated' && canEdit ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Validation du déclarant</h3>
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center space-x-2 mb-4">
                    <Checkbox
                      id="acknowledged"
                      checked={declarantValidation.acknowledged}
                      onCheckedChange={(checked) => 
                        setDeclarantValidation({...declarantValidation, acknowledged: checked})}
                    />
                    <Label htmlFor="acknowledged">
                      Le déclarant a signé et reconnu le certificat de visite
                    </Label>
                  </div>
                  
                  {declarantValidation.acknowledged && (
                    <div className="space-y-4">
                      <Label>Décision</Label>
                      <Select value={declarantValidation.fine_decision} onValueChange={(value) => 
                        setDeclarantValidation({...declarantValidation, fine_decision: value})}>
                        <SelectTrigger>
                          <SelectValue placeholder="Choisir la décision" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="pass_over">Passer outre</SelectItem>
                          <SelectItem value="customs_fine">Amende douanière</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
                
                {declarantValidation.acknowledged && declarantValidation.fine_decision && (
                  <Button onClick={handleDeclarantValidation} className="w-full">
                    Finaliser le contrôle
                  </Button>
                )}
              </div>
            ) : (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <h4 className="font-medium text-green-800">Contrôle finalisé</h4>
                <p className="text-sm text-green-700 mt-1">
                  Décision: {control.fine_decision === 'pass_over' ? 'Passer outre' : 'Amende douanière'}
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="history" className="space-y-4">
            <h3 className="text-lg font-semibold">Historique du contrôle</h3>
            <div className="space-y-3">
              {control.history?.map((action, index) => (
                <div key={index} className="p-3 bg-slate-50 rounded-lg">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{action.action}</p>
                      <p className="text-sm text-slate-600">Par {action.user_name}</p>
                    </div>
                    <p className="text-xs text-slate-500">
                      {new Date(action.timestamp).toLocaleString('fr-FR')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};

// Stats View Component  
const StatsView = ({ documents, controls = [] }) => {
  const documentStatusCounts = documents.reduce((acc, doc) => {
    acc[doc.status] = (acc[doc.status] || 0) + 1;
    return acc;
  }, {});

  const controlStatusCounts = controls.reduce((acc, control) => {
    acc[control.status] = (acc[control.status] || 0) + 1;
    return acc;
  }, {});

  const documentStats = [
    { label: 'Total Documents', value: documents.length, icon: FileText, color: 'bg-blue-500' },
    { label: 'Brouillons', value: documentStatusCounts.draft || 0, icon: Clock, color: 'bg-slate-500' },
    { label: 'En contrôle', value: documentStatusCounts.under_control || 0, icon: AlertTriangle, color: 'bg-orange-500' },
    { label: 'Validés', value: documentStatusCounts.validated || 0, icon: CheckCircle, color: 'bg-green-500' }
  ];

  const controlStats = [
    { label: 'Total Contrôles', value: controls.length, icon: Settings, color: 'bg-purple-500' },
    { label: 'En cours', value: controlStatusCounts.in_progress || 0, icon: PlayCircle, color: 'bg-blue-500' },
    { label: 'Non-conformes', value: controlStatusCounts.non_compliant || 0, icon: XCircle, color: 'bg-red-500' },
    { label: 'Terminés', value: (controlStatusCounts.completed || 0) + (controlStatusCounts.fine_issued || 0), icon: CheckCircle, color: 'bg-green-500' }
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Statistiques</h2>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {documentStats.map((stat, index) => (
          <Card key={index}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-600">{stat.label}</p>
                  <p className="text-3xl font-bold text-slate-800">{stat.value}</p>
                </div>
                <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// Main App Component
const App = () => {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  );
};

const AppContent = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Chargement...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={!user ? <LoginPage /> : <Navigate to="/" replace />} />
      <Route path="/" element={user ? <Dashboard /> : <Navigate to="/login" replace />} />
    </Routes>
  );
};

export default App;