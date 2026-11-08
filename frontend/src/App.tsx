import React from 'react';
import { Router, Routes, Redirect, Link, useRouter } from './lib/router';
import { I18nProvider, useT } from './lib/i18n';
import { AuthProvider, useAuth } from './lib/auth';
import { StatusProvider } from './lib/status';
import { ToastProvider } from './lib/toast';
import { AppShell } from './components/AppShell';
import { Button } from './components/ui';
import { Spinner } from './lib/progress';
import { Landing } from './pages/Landing';
import { Login, Register } from './pages/Auth';
import { Onboarding } from './pages/Onboarding';
import { Dashboard } from './pages/Dashboard';
import { Tutor } from './pages/Tutor';
import { Quizzes, QuizTake } from './pages/Quizzes';
import { Rooms, RoomView } from './pages/Rooms';
import { Documents, DocumentView } from './pages/Documents';
import { Roadmap } from './pages/Roadmap';
import { Notes } from './pages/Notes';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { Teacher } from './pages/Teacher';

function FullScreenLoader() {
  const t = useT();
  return (
    <div className="surface-glow flex min-h-screen items-center justify-center text-ink-soft">
      <span className="flex items-center gap-2 text-sm">
        <Spinner className="h-5 w-5 text-brand-600" />
        {t('common.loading')}
      </span>
    </div>
  );
}

/** Wraps authenticated pages: redirects to /login when logged out, to /onboarding when the diagnostic is pending. */
function Protected({ children, allowUndiagnosed = false }: { children: React.ReactNode; allowUndiagnosed?: boolean }) {
  const { user, loading, token } = useAuth();
  const { path } = useRouter();
  if (loading) return <FullScreenLoader />;
  if (!token || !user) return <Redirect to={`/login${path !== '/app' ? `?next=${encodeURIComponent(path)}` : ''}`} />;
  if (!allowUndiagnosed && user.role === 'learner' && !user.diagnostic_completed && path === '/app') return <Redirect to="/onboarding" />;
  return <>{children}</>;
}

function PublicOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) return <Redirect to="/app" />;
  return <>{children}</>;
}

function NotFound() {
  const t = useT();
  return (
    <div className="surface-glow flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <p className="display text-6xl text-brand-200">404</p>
      <p className="text-ink-soft">{t('err.not_found')}</p>
      <Link to="/app">
        <Button>{t('err.go_home')}</Button>
      </Link>
    </div>
  );
}

const app = (el: React.ReactNode) => (
  <Protected>
    <AppShell>{el}</AppShell>
  </Protected>
);

function AppRoutes() {
  return (
    <Routes
      routes={[
        { path: '/', element: <Landing /> },
        {
          path: '/login',
          element: (
            <PublicOnly>
              <Login />
            </PublicOnly>
          ),
        },
        {
          path: '/register',
          element: (
            <PublicOnly>
              <Register />
            </PublicOnly>
          ),
        },
        {
          path: '/onboarding',
          element: (
            <Protected allowUndiagnosed>
              <Onboarding />
            </Protected>
          ),
        },
        { path: '/app', element: app(<Dashboard />) },
        { path: '/app/tutor', element: app(<Tutor />) },
        { path: '/app/tutor/:id', element: app(<Tutor />) },
        { path: '/app/quizzes', element: app(<Quizzes />) },
        { path: '/app/quizzes/:id', element: app(<QuizTake />) },
        { path: '/app/rooms', element: app(<Rooms />) },
        { path: '/app/rooms/:id', element: app(<RoomView />) },
        { path: '/app/documents', element: app(<Documents />) },
        { path: '/app/documents/:id', element: app(<DocumentView />) },
        { path: '/app/roadmap', element: app(<Roadmap />) },
        { path: '/app/notes', element: app(<Notes />) },
        { path: '/app/analytics', element: app(<Analytics />) },
        { path: '/app/settings', element: app(<Settings />) },
        { path: '/app/teacher', element: app(<Teacher />) },
      ]}
      fallback={<NotFound />}
    />
  );
}

export function App() {
  return (
    <I18nProvider>
      <Router>
        <AuthProvider>
          <StatusProvider>
            <ToastProvider>
              <AppRoutes />
            </ToastProvider>
          </StatusProvider>
        </AuthProvider>
      </Router>
    </I18nProvider>
  );
}

export default App;
