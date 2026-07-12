import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile,
  type User,
} from "firebase/auth";
import { firebaseClient, firebaseReady } from "../firebase/config";
import {
  defaultPreferences,
  ensureUserDocument,
  syncQueuedCircuitSaves,
  updateUserPreferences,
} from "./firebaseService";
import type { QuantumLabUser, UserPreferences } from "./types";

interface AuthContextValue {
  firebaseReady: boolean;
  user: User | null;
  profile: QuantumLabUser | null;
  loading: boolean;
  authError: string | null;
  loginOpen: boolean;
  openLogin: () => void;
  closeLogin: () => void;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (name: string, email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  logout: () => Promise<void>;
  savePreferences: (preferences: UserPreferences) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function messageFromError(error: unknown): string {
  if (error instanceof Error) return error.message.replace(/^Firebase:\s*/i, "");
  return "Authentication failed. Please try again.";
}

export function AuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<QuantumLabUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);

  useEffect(() => {
    if (!firebaseClient) {
      setLoading(false);
      return;
    }
    return onAuthStateChanged(firebaseClient.auth, (nextUser) => {
      setUser(nextUser);
      if (!nextUser) {
        setProfile(null);
        setLoading(false);
        return;
      }
      void ensureUserDocument(nextUser)
        .then((nextProfile) => {
          setProfile(nextProfile);
          document.documentElement.dataset.theme = nextProfile.preferences.theme;
          void syncQueuedCircuitSaves(nextUser.uid);
        })
        .catch((error: unknown) => setAuthError(messageFromError(error)))
        .finally(() => setLoading(false));
    });
  }, []);

  useEffect(() => {
    const sync = () => {
      if (user) void syncQueuedCircuitSaves(user.uid);
    };
    window.addEventListener("online", sync);
    return () => window.removeEventListener("online", sync);
  }, [user]);

  const signInWithGoogle = useCallback(async () => {
    if (!firebaseClient) throw new Error("Firebase is not configured.");
    setAuthError(null);
    await signInWithPopup(firebaseClient.auth, firebaseClient.googleProvider);
    setLoginOpen(false);
  }, []);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    if (!firebaseClient) throw new Error("Firebase is not configured.");
    setAuthError(null);
    try {
      await signInWithEmailAndPassword(firebaseClient.auth, email, password);
      setLoginOpen(false);
    } catch (error) {
      const message = messageFromError(error);
      setAuthError(message);
      throw new Error(message);
    }
  }, []);

  const signUpWithEmail = useCallback(async (name: string, email: string, password: string) => {
    if (!firebaseClient) throw new Error("Firebase is not configured.");
    setAuthError(null);
    try {
      const credential = await createUserWithEmailAndPassword(firebaseClient.auth, email, password);
      await updateProfile(credential.user, { displayName: name });
      await ensureUserDocument(credential.user);
      setLoginOpen(false);
    } catch (error) {
      const message = messageFromError(error);
      setAuthError(message);
      throw new Error(message);
    }
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    if (!firebaseClient) throw new Error("Firebase is not configured.");
    setAuthError(null);
    await sendPasswordResetEmail(firebaseClient.auth, email);
  }, []);

  const logout = useCallback(async () => {
    if (!firebaseClient) return;
    await signOut(firebaseClient.auth);
  }, []);

  const savePreferences = useCallback(
    async (preferences: UserPreferences) => {
      if (!user) throw new Error("Please sign in to save settings.");
      await updateUserPreferences(user.uid, preferences);
      const nextProfile = {
        ...(profile ?? {
          uid: user.uid,
          name: user.displayName ?? "QuantumLab User",
          email: user.email ?? "",
          photoURL: user.photoURL ?? "",
          provider: "password",
          createdAt: new Date().toISOString(),
          lastLogin: new Date().toISOString(),
          role: "student" as const,
          savedCircuits: [],
          recentCircuits: [],
          favoriteCircuits: [],
          bookmarkedReports: [],
          totalSimulationsRun: 0,
          mostUsedGate: "None",
          favoriteSimulationMode: defaultPreferences.defaultSimulationMode,
        }),
        preferences,
        theme: preferences.theme,
        defaultSimulationMode: preferences.defaultSimulationMode,
        defaultExplanationLevel: preferences.defaultExplanationLevel,
      };
      setProfile(nextProfile);
      document.documentElement.dataset.theme = preferences.theme;
    },
    [profile, user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      firebaseReady,
      user,
      profile,
      loading,
      authError,
      loginOpen,
      openLogin: () => setLoginOpen(true),
      closeLogin: () => setLoginOpen(false),
      signInWithGoogle,
      signInWithEmail,
      signUpWithEmail,
      resetPassword,
      logout,
      savePreferences,
    }),
    [
      user,
      profile,
      loading,
      authError,
      loginOpen,
      signInWithGoogle,
      signInWithEmail,
      signUpWithEmail,
      resetPassword,
      logout,
      savePreferences,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

