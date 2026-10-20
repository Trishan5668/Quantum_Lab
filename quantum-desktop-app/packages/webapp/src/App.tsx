import { lazy, Suspense } from "react";
import {
  BrowserRouter,
  HashRouter,
  Route,
  Routes,
} from "react-router-dom";
import { PlatformLayout } from "./components/platform/PlatformLayout";
import { QuantHubLayout } from "./quanthub/components/QuantHubLayout";

const LandingPage = lazy(() => import("./pages/LandingPage"));
const SimulatorPage = lazy(() => import("./pages/SimulatorPage"));
const EditorPage = lazy(() => import("./pages/EditorPage"));
const LearnPage = lazy(() => import("./pages/LearnPage"));
const AlgorithmsPage = lazy(() => import("./pages/AlgorithmsPage"));
const DocsPage = lazy(() => import("./pages/DocsPage"));
const ResearchPage = lazy(() => import("./pages/ResearchPage"));
const ApiPage = lazy(() => import("./pages/ApiPage"));
const BlogPage = lazy(() => import("./pages/BlogPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));

const HomePage = lazy(() => import("./quanthub/pages/HomePage"));
const ExplorePage = lazy(() => import("./quanthub/pages/ExplorePage"));
const ProjectsPage = lazy(() => import("./quanthub/pages/ProjectsPage"));
const NewProjectPage = lazy(() => import("./quanthub/pages/NewProjectPage"));
const ProjectPage = lazy(() => import("./quanthub/pages/ProjectPage"));
const BlobPage = lazy(() => import("./quanthub/pages/BlobPage"));
const CommitsPage = lazy(() => import("./quanthub/pages/CommitsPage"));
const ImportPage = lazy(() => import("./quanthub/pages/ImportPage"));
const ProjectSettingsPage = lazy(() => import("./quanthub/pages/ProjectSettingsPage"));
const ExperimentsPage = lazy(() => import("./quanthub/pages/ExperimentsPage"));
const ExperimentDetailPage = lazy(() => import("./quanthub/pages/ExperimentDetailPage"));
const GlobalExperimentsPage = lazy(() => import("./quanthub/pages/GlobalExperimentsPage"));
const RunsPage = lazy(() => import("./quanthub/pages/RunsPage"));
const RunDetailPage = lazy(() => import("./quanthub/pages/RunDetailPage"));
const QecWorkbenchPage = lazy(() => import("./quanthub/pages/QecWorkbenchPage"));
const CommunityPage = lazy(() => import("./quanthub/pages/CommunityPage"));
const ProfilePage = lazy(() => import("./quanthub/pages/ProfilePage"));
const AccountSettingsPage = lazy(() => import("./quanthub/pages/AccountSettingsPage"));
const WelcomePage = lazy(() => import("./quanthub/pages/WelcomePage"));
const NotFoundPage = lazy(() => import("./quanthub/pages/NotFoundPage"));

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
        {/* QuantHub workspace: project-centric home, discovery and experiments. */}
        <Route element={<QuantHubLayout />}>
          <Route index element={<HomePage />} />
          <Route path="explore" element={<ExplorePage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="new" element={<NewProjectPage />} />
          <Route path="experiments" element={<GlobalExperimentsPage />} />
          <Route path="qec" element={<QecWorkbenchPage />} />
          <Route path="community" element={<CommunityPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="settings" element={<AccountSettingsPage />} />
          <Route path="welcome" element={<WelcomePage />} />
          <Route path=":owner/:slug" element={<ProjectPage />} />
          <Route path=":owner/:slug/blob/*" element={<BlobPage />} />
          <Route path=":owner/:slug/commits" element={<CommitsPage />} />
          <Route path=":owner/:slug/import" element={<ImportPage />} />
          <Route path=":owner/:slug/settings" element={<ProjectSettingsPage />} />
          <Route path=":owner/:slug/experiments" element={<ExperimentsPage />} />
          <Route path=":owner/:slug/experiments/:specId" element={<ExperimentDetailPage />} />
          <Route path=":owner/:slug/runs" element={<RunsPage />} />
          <Route path=":owner/:slug/runs/:runId" element={<RunDetailPage />} />
          <Route path=":handle" element={<ProfilePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        {/* Existing platform pages keep their URLs. */}
        <Route element={<PlatformLayout />}>
          <Route path="learn" element={<LearnPage />} />
          <Route path="algorithms" element={<AlgorithmsPage />} />
          <Route path="algorithms/:id" element={<AlgorithmsPage />} />
          <Route path="docs" element={<DocsPage />} />
          <Route path="docs/:slug" element={<DocsPage />} />
          <Route path="research" element={<ResearchPage />} />
          <Route path="research/:slug" element={<ResearchPage />} />
          <Route path="api" element={<ApiPage />} />
          <Route path="blog" element={<BlogPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="landing" element={<LandingPage />} />
        </Route>

        <Route path="app" element={<SimulatorPage />} />
        <Route path="app/editor" element={<EditorPage />} />
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
