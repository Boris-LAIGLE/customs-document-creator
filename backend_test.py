import requests
import sys
import json
from datetime import datetime

class CustomsAPITester:
    def __init__(self, base_url="https://acts-manager.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_users = []
        self.created_documents = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 200:
                        print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_user_registration(self, username, email, password, full_name, role):
        """Test user registration"""
        user_data = {
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role
        }
        
        success, response = self.run_test(
            f"Register {role} user",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        
        if success and 'id' in response:
            self.created_users.append({
                'id': response['id'],
                'username': username,
                'role': role
            })
            return response['id']
        return None

    def test_user_login(self, username, password):
        """Test user login and get token"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"username": username, "password": password}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   Token obtained for user: {response['user']['full_name']}")
            return True
        return False

    def test_get_current_user(self):
        """Test getting current user info"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_initialize_templates(self):
        """Test template initialization"""
        success, response = self.run_test(
            "Initialize Templates",
            "POST",
            "init/templates",
            200
        )
        return success

    def test_get_templates(self):
        """Test getting templates"""
        success, response = self.run_test(
            "Get Templates",
            "GET",
            "templates",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} templates")
            return response
        return []

    def test_create_document(self, title, document_type, template_id):
        """Test document creation"""
        document_data = {
            "title": title,
            "document_type": document_type,
            "template_id": template_id,
            "content": {"test_field": "test_value"}
        }
        
        success, response = self.run_test(
            "Create Document",
            "POST",
            "documents",
            200,
            data=document_data
        )
        
        if success and 'id' in response:
            self.created_documents.append(response['id'])
            return response['id']
        return None

    def test_get_documents(self):
        """Test getting documents"""
        success, response = self.run_test(
            "Get Documents",
            "GET",
            "documents",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   Found {len(response)} documents")
            return response
        return []

    def test_get_document(self, document_id):
        """Test getting a specific document"""
        success, response = self.run_test(
            "Get Document by ID",
            "GET",
            f"documents/{document_id}",
            200
        )
        return success, response

    def test_submit_document(self, document_id):
        """Test document submission"""
        success, response = self.run_test(
            "Submit Document",
            "POST",
            f"documents/{document_id}/submit",
            200
        )
        return success

    def test_sydonia_api(self, declaration_id="TEST123"):
        """Test mock Sydonia API"""
        success, response = self.run_test(
            "Mock Sydonia API",
            "GET",
            f"sydonia/declaration/{declaration_id}",
            200
        )
        
        if success and 'data' in response:
            print(f"   Sydonia data: {response['data']['importer_name']}")
        return success

def main():
    print("🚀 Starting Customs Administration API Tests")
    print("=" * 60)
    
    tester = CustomsAPITester()
    timestamp = datetime.now().strftime('%H%M%S')
    
    # Test data
    test_users = [
        {
            'username': f'drafting_agent_{timestamp}',
            'email': f'drafting_{timestamp}@test.com',
            'password': 'TestPass123!',
            'full_name': 'Agent de Rédaction Test',
            'role': 'drafting_agent'
        },
        {
            'username': f'control_officer_{timestamp}',
            'email': f'control_{timestamp}@test.com',
            'password': 'TestPass123!',
            'full_name': 'Agent de Contrôle Test',
            'role': 'control_officer'
        },
        {
            'username': f'validation_officer_{timestamp}',
            'email': f'validation_{timestamp}@test.com',
            'password': 'TestPass123!',
            'full_name': 'Agent de Validation Test',
            'role': 'validation_officer'
        }
    ]

    print("\n📝 Phase 1: User Registration Tests")
    print("-" * 40)
    
    # Register users
    for user_data in test_users:
        user_id = tester.test_user_registration(
            user_data['username'],
            user_data['email'],
            user_data['password'],
            user_data['full_name'],
            user_data['role']
        )
        if not user_id:
            print(f"❌ Failed to register {user_data['role']} user")
            return 1

    print("\n🔐 Phase 2: Authentication Tests")
    print("-" * 40)
    
    # Test login with drafting agent
    drafting_user = test_users[0]
    if not tester.test_user_login(drafting_user['username'], drafting_user['password']):
        print("❌ Login failed, stopping tests")
        return 1

    # Test getting current user
    if not tester.test_get_current_user():
        print("❌ Get current user failed")
        return 1

    print("\n📋 Phase 3: Template Tests")
    print("-" * 40)
    
    # Initialize templates
    if not tester.test_initialize_templates():
        print("❌ Template initialization failed")
        return 1

    # Get templates
    templates = tester.test_get_templates()
    if not templates:
        print("❌ No templates found")
        return 1

    print("\n📄 Phase 4: Document Tests")
    print("-" * 40)
    
    # Create a document
    template_id = templates[0]['id'] if templates else None
    if not template_id:
        print("❌ No template available for document creation")
        return 1

    document_id = tester.test_create_document(
        "Test Document",
        "customs_report",
        template_id
    )
    
    if not document_id:
        print("❌ Document creation failed")
        return 1

    # Get documents
    documents = tester.test_get_documents()
    if not documents:
        print("❌ No documents found after creation")
        return 1

    # Get specific document
    success, doc_data = tester.test_get_document(document_id)
    if not success:
        print("❌ Failed to get document by ID")
        return 1

    # Submit document
    if not tester.test_submit_document(document_id):
        print("❌ Document submission failed")
        return 1

    print("\n🌐 Phase 5: Integration Tests")
    print("-" * 40)
    
    # Test Sydonia API
    if not tester.test_sydonia_api():
        print("❌ Sydonia API test failed")
        return 1

    print("\n🔄 Phase 6: Role-based Access Tests")
    print("-" * 40)
    
    # Test with control officer
    control_user = test_users[1]
    if tester.test_user_login(control_user['username'], control_user['password']):
        # Control officer should see documents under control
        control_docs = tester.test_get_documents()
        print(f"   Control officer sees {len(control_docs)} documents")
    
    # Test with validation officer
    validation_user = test_users[2]
    if tester.test_user_login(validation_user['username'], validation_user['password']):
        # Validation officer should see all documents
        validation_docs = tester.test_get_documents()
        print(f"   Validation officer sees {len(validation_docs)} documents")

    # Print final results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"✅ Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"📝 Users created: {len(tester.created_users)}")
    print(f"📄 Documents created: {len(tester.created_documents)}")
    
    if tester.tests_passed == tester.tests_run:
        print("\n🎉 ALL TESTS PASSED! Backend API is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {tester.tests_run - tester.tests_passed} tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())