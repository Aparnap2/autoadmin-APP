import { initializeApp, getApps } from 'firebase/app';
import { getFirestore, Firestore } from 'firebase/firestore';
import { getAnalytics, isSupported } from 'firebase/analytics';
import { getStorage, FirebaseStorage } from 'firebase/storage';
import { getAppCheck, AppCheck, ReCaptchaV3Provider } from 'firebase/app-check';

// Firebase configuration - replace with your config
const firebaseConfig = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY || '',
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN || '',
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID || '',
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET || '',
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || '',
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID || '',
  measurementId: process.env.EXPO_PUBLIC_FIREBASE_MEASUREMENT_ID || ''
};

// Initialize Firebase
let app: ReturnType<typeof initializeApp>;
let db: Firestore;
let storage: FirebaseStorage;
let appCheck: AppCheck;

// Validate required Firebase configuration
const requiredConfigs = ['apiKey', 'projectId', 'appId'];
const missingConfigs = requiredConfigs.filter(key => !firebaseConfig[key as keyof typeof firebaseConfig]);

if (missingConfigs.length > 0) {
  throw new Error(`Missing required Firebase configuration: ${missingConfigs.join(', ')}`);
}

try {
  // Check if Firebase app is already initialized
  const existingApps = getApps();

  if (existingApps.length > 0) {
    // Use existing app if available
    app = existingApps[0];
    console.log('Using existing Firebase app instance:', app.name);
  } else {
    // Initialize Firebase app
    app = initializeApp(firebaseConfig);
    console.log('Firebase initialized successfully for project:', firebaseConfig.projectId);
  }

  // Initialize services
  db = getFirestore(app);
  storage = getStorage(app);

  // Initialize analytics (only if supported and in web environment)
  if (typeof window !== 'undefined') {
    isSupported().then((supported) => {
      if (supported) {
        getAnalytics(app);
      }
    });
  }

  // Initialize App Check for security (web only)
  if (typeof window !== 'undefined' && process.env.EXPO_PUBLIC_FIREBASE_RECAPTCHA_SITE_KEY) {
    appCheck = getAppCheck(app);
    appCheck.activate(
      new ReCaptchaV3Provider(process.env.EXPO_PUBLIC_FIREBASE_RECAPTCHA_SITE_KEY),
      'optional-prod' // or 'mandatory-prod' for production
    );
  }

} catch (error) {
  console.error('Firebase initialization error:', error);
  throw new Error(`Failed to initialize Firebase: ${error instanceof Error ? error.message : 'Unknown error'}`);
}

// Export all Firebase services
export {
  app,
  db,
  storage,
  appCheck
};

// Export configuration for reference
export { firebaseConfig };

// Utility function to check if Firebase is initialized
export function isFirebaseInitialized(): boolean {
  return !!(app && db && storage);
}

// Export default app for backward compatibility
export default app;