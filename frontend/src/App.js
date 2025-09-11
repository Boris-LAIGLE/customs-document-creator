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
import { FileText, Users, CheckCircle, Clock, AlertTriangle, Plus, LogOut, Search, Filter } from 'lucide-react';
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
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState('documents');

  useEffect(() => {
    fetchData();
    initializeTemplates();
  }, []);

  const fetchData = async () => {
    try {
      const [docsResponse, templatesResponse] = await Promise.all([
        axios.get(`${API}/documents`),
        axios.get(`${API}/templates`)
      ]);
      setDocuments(docsResponse.data);
      setTemplates(templatesResponse.data);
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
      validation_officer: 'Agent de validation'
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
          <TabsList className="grid w-full grid-cols-3 lg:w-96">
            <TabsTrigger value="documents" className="flex items-center space-x-2">
              <FileText className="h-4 w-4" />
              <span>Documents</span>
            </TabsTrigger>
            <TabsTrigger value="templates" className="flex items-center space-x-2">
              <Users className="h-4 w-4" />
              <span>Modèles</span>
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex items-center space-x-2">
              <CheckCircle className="h-4 w-4" />
              <span>Statistiques</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="documents" className="space-y-6">
            <DocumentsView documents={documents} templates={templates} onRefresh={fetchData} />
          </TabsContent>

          <TabsContent value="templates" className="space-y-6">
            <TemplatesView templates={templates} onRefresh={fetchData} />
          </TabsContent>

          <TabsContent value="stats" className="space-y-6">
            <StatsView documents={documents} />
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

// Stats View Component  
const StatsView = ({ documents }) => {
  const statusCounts = documents.reduce((acc, doc) => {
    acc[doc.status] = (acc[doc.status] || 0) + 1;
    return acc;
  }, {});

  const stats = [
    { label: 'Total Documents', value: documents.length, icon: FileText, color: 'bg-blue-500' },
    { label: 'Brouillons', value: statusCounts.draft || 0, icon: Clock, color: 'bg-slate-500' },
    { label: 'En contrôle', value: statusCounts.under_control || 0, icon: AlertTriangle, color: 'bg-orange-500' },
    { label: 'Validés', value: statusCounts.validated || 0, icon: CheckCircle, color: 'bg-green-500' }
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800">Statistiques</h2>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
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