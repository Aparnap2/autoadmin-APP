"""
Firebase Configuration Validator
Validates Firebase environment configuration and provides setup guidance
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse


@dataclass
class ValidationResult:
    """Result of Firebase configuration validation"""
    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class FirebaseValidator:
    """Validates Firebase environment configuration"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate_all(self) -> ValidationResult:
        """Validate all Firebase configuration"""
        result = ValidationResult()

        # Check basic Firebase configuration
        self._validate_basic_config(result)

        # Check service account key format
        self._validate_service_account_key(result)

        # Check project configuration
        self._validate_project_config(result)

        # Check optional configurations
        self._validate_optional_config(result)

        # Generate recommendations
        self._generate_recommendations(result)

        # Set final validity
        result.is_valid = len(result.errors) == 0

        return result

    def _validate_basic_config(self, result: ValidationResult):
        """Validate basic Firebase configuration"""
        required_vars = ['FIREBASE_PROJECT_ID', 'FIREBASE_CLIENT_EMAIL', 'FIREBASE_PRIVATE_KEY']

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                result.errors.append(f"Missing required environment variable: {var}")
            elif var == 'FIREBASE_PRIVATE_KEY' and value == "TestKeyForDebuggingPurposesOnly":
                result.errors.append(f"Firebase private key is a placeholder value")
            elif not value.strip():
                result.errors.append(f"Environment variable {var} is empty")

    def _validate_service_account_key(self, result: ValidationResult):
        """Validate Firebase service account private key format"""
        private_key = os.getenv('FIREBASE_PRIVATE_KEY')

        if not private_key or private_key == "TestKeyForDebuggingPurposesOnly":
            return

        # Check for key header
        if not private_key.strip().startswith('-----BEGIN PRIVATE KEY-----'):
            result.errors.append("Firebase private key must start with '-----BEGIN PRIVATE KEY-----'")

        # Check for key footer
        if not private_key.strip().endswith('-----END PRIVATE KEY-----'):
            result.errors.append("Firebase private key must end with '-----END PRIVATE KEY-----'")

        # Check for newlines in key
        if '\\n' in private_key:
            result.warnings.append("Firebase private key contains literal '\\n' instead of actual newlines")
            result.recommendations.append("Replace literal '\\n' with actual newline characters in private key")

        # Check key length (RSA keys are typically around 1700 characters for 2048-bit)
        if len(private_key.replace('\n', '').strip()) < 1000:
            result.warnings.append("Firebase private key seems shorter than expected for a standard RSA key")

    def _validate_project_config(self, result: ValidationResult):
        """Validate Firebase project configuration"""
        project_id = os.getenv('FIREBASE_PROJECT_ID')

        if not project_id:
            return

        # Check project ID format (should be lowercase, alphanumeric with hyphens)
        if not project_id.replace('-', '').replace('_', '').isalnum():
            result.errors.append("Firebase project ID should contain only alphanumeric characters and hyphens")

        if project_id != project_id.lower():
            result.warnings.append("Firebase project ID should be lowercase")

        if len(project_id) < 6 or len(project_id) > 30:
            result.warnings.append("Firebase project ID should be between 6 and 30 characters")

    def _validate_optional_config(self, result: ValidationResult):
        """Validate optional Firebase configurations"""
        # Check for Firebase URL configurations
        firebase_url = os.getenv('FIREBASE_URL')
        if firebase_url:
            try:
                parsed = urlparse(firebase_url)
                if not parsed.scheme in ['https', 'http']:
                    result.errors.append("Firebase URL must use http or https scheme")
                if parsed.hostname and not parsed.hostname.endswith('firebaseio.com'):
                    result.warnings.append("Firebase URL should typically end with 'firebaseio.com'")
            except Exception:
                result.errors.append("Invalid Firebase URL format")

        # Check for database URL
        database_url = os.getenv('FIREBASE_DATABASE_URL')
        if database_url and not database_url.startswith('https://'):
            result.warnings.append("Firebase database URL should use HTTPS")

    def _generate_recommendations(self, result: ValidationResult):
        """Generate setup recommendations"""
        if not os.getenv('FIREBASE_PROJECT_ID'):
            result.recommendations.append("Set FIREBASE_PROJECT_ID to your Firebase project ID from Firebase Console")

        if not os.getenv('FIREBASE_CLIENT_EMAIL'):
            result.recommendations.append("Set FIREBASE_CLIENT_EMAIL to your service account email")

        if not os.getenv('FIREBASE_PRIVATE_KEY') or os.getenv('FIREBASE_PRIVATE_KEY') == "TestKeyForDebuggingPurposesOnly":
            result.recommendations.append("Download service account key from Firebase Console > Project Settings > Service Accounts")
            result.recommendations.append("Set FIREBASE_PRIVATE_KEY to contents of downloaded JSON key file")

        # Add general Firebase setup recommendations
        if len(result.errors) > 0:
            result.recommendations.extend([
                "1. Go to Firebase Console (https://console.firebase.google.com/)",
                "2. Create a new project or select existing project",
                "3. Go to Project Settings > Service Accounts",
                "4. Click 'Generate new private key'",
                "5. Download the JSON file and extract required values:",
                "   - project_id -> FIREBASE_PROJECT_ID",
                "   - client_email -> FIREBASE_CLIENT_EMAIL",
                "   - private_key -> FIREBASE_PRIVATE_KEY",
                "6. Add these values to your .env file"
            ])

        # Add development recommendations
        if not os.getenv('FIREBASE_URL'):
            result.recommendations.append("Optionally set FIREBASE_URL for direct database access")

        # Add monitoring recommendations
        result.recommendations.append("Consider setting up Firebase monitoring for production use")
        result.recommendations.append("Enable security rules in Firebase Console for data protection")

    def validate_service_account_json(self, json_path: str) -> ValidationResult:
        """Validate a Firebase service account JSON file"""
        result = ValidationResult()

        try:
            if not os.path.exists(json_path):
                result.errors.append(f"Service account JSON file not found: {json_path}")
                return result

            with open(json_path, 'r') as f:
                service_account_data = json.load(f)

            # Check required fields
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            for field in required_fields:
                if field not in service_account_data:
                    result.errors.append(f"Missing required field in service account JSON: {field}")

            # Check values
            if service_account_data.get('type') != 'service_account':
                result.errors.append("JSON file type must be 'service_account'")

            if not service_account_data.get('project_id'):
                result.errors.append("project_id cannot be empty in service account JSON")

            if not service_account_data.get('private_key'):
                result.errors.append("private_key cannot be empty in service account JSON")

            if not service_account_data.get('client_email'):
                result.errors.append("client_email cannot be empty in service account JSON")

            # Check private key format
            private_key = service_account_data.get('private_key', '')
            if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
                result.errors.append("private_key in JSON should start with '-----BEGIN PRIVATE KEY-----'")

            # Set validity based on errors
            result.is_valid = len(result.errors) == 0

            if result.is_valid:
                result.recommendations.extend([
                    f"Use these values from {json_path}:",
                    f"FIREBASE_PROJECT_ID={service_account_data.get('project_id', '')}",
                    f"FIREBASE_CLIENT_EMAIL={service_account_data.get('client_email', '')}",
                    f"FIREBASE_PRIVATE_KEY={private_key[:50]}...{private_key[-50:]}"  # Show partial key
                ])

        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON format in service account file: {e}")
        except Exception as e:
            result.errors.append(f"Error reading service account file: {e}")

        return result