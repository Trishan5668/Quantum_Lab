import { initializeApp, type FirebaseApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, type Auth } from "firebase/auth";
import { getFirestore, type Firestore } from "firebase/firestore";

interface FirebaseClient {
  app: FirebaseApp;
  auth: Auth;
  db: Firestore;
  googleProvider: GoogleAuthProvider;
}

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY as string | undefined,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET as string | undefined,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID as string | undefined,
  appId: import.meta.env.VITE_FIREBASE_APP_ID as string | undefined,
};

export const firebaseReady = Object.values(firebaseConfig).every(Boolean);

export const firebaseClient: FirebaseClient | null = firebaseReady
  ? (() => {
      const app = initializeApp(firebaseConfig);
      const auth = getAuth(app);
      const db = getFirestore(app);
      const googleProvider = new GoogleAuthProvider();
      googleProvider.setCustomParameters({ prompt: "select_account" });
      return { app, auth, db, googleProvider };
    })()
  : null;

