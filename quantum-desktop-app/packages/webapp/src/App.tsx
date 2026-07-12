import { lazy, Suspense } from "react";
import {
  BrowserRouter,
  HashRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { PlatformLayout } from "./components/platform/PlatformLayout";

const LandingPage = lazy(() => import("./pages/LandingPage"));
const SimulatorPage = lazy(() => import("./pages/SimulatorPage"));
const LearnPage = lazy(() => import("./pages/LearnPage"));
const AlgorithmsPage = lazy(() => import("./pages/AlgorithmsPage"));
const DocsPage = lazy(() => import("./pages/DocsPage"));
const ResearchPage = lazy(() => import("./pages/ResearchPage"));
const ApiPage = lazy(() => import("./pages/ApiPage"));
const CommunityPage = lazy(() => import("./pages/CommunityPage"));
const BlogPage = lazy(() => import("./pages/BlogPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));

function PageLoader(): JSX.Element {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <span className="font-mono text-xs text-text-muted">Loading…</span>
    </div>
  );
}

function AppRoutes(): JSX.Element {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route element={<PlatformLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="learn" element={<LearnPage />} />
          <Route path="algorithms" element={<AlgorithmsPage />} />
          <Route path="algorithms/:id" element={<AlgorithmsPage />} />
          <Route path="docs" element={<DocsPage />} />
          <Route path="docs/:slug" element={<DocsPage />} />
          <Route path="research" element={<ResearchPage />} />
          <Route path="research/:slug" element={<ResearchPage />} />
          <Route path="api" element={<ApiPage />} />
          <Route path="community" element={<CommunityPage />} />
          <Route path="blog" element={<BlogPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="history" element={<HistoryPage />} />
        </Route>
        <Route path="app" element={<SimulatorPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default function App(): JSX.Element {
  const isFileProtocol = window.location.protocol === "file:";
  const Router = isFileProtocol ? HashRouter : BrowserRouter;

  return (
    <Router>
      <AppRoutes />
    </Router>
  );
}
