import type { ReactElement } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { AppLayout } from './components/AppLayout';
import { HomePage } from './pages/HomePage';
import { WelcomePage } from './pages/WelcomePage';
import { LoginPage } from './pages/auth/LoginPage';
import { BenchmarkBrowsePage } from './pages/benchmark/BenchmarkBrowsePage';
import { BenchmarkDetailPage } from './pages/benchmark/BenchmarkDetailPage';
import { ChipBenchmarkPage } from './pages/benchmark/ChipBenchmarkPage';
import { CreateTaskPage } from './pages/simulation/CreateTaskPage';
import { TaskDetailPage } from './pages/simulation/TaskDetailPage';
import { TaskListPage } from './pages/simulation/TaskListPage';
import { TaskResultPage } from './pages/simulation/TaskResultPage';

function RequireAuth({ children }: { children: ReactElement }) {
  const { authenticated } = useAuth();
  const location = useLocation();

  if (!authenticated) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={(
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        )}
      >
        <Route path="/home" element={<HomePage />} />
        <Route path="/simulation/new" element={<CreateTaskPage />} />
        <Route path="/simulation/tasks" element={<TaskListPage />} />
        <Route path="/simulation/tasks/:taskId" element={<TaskDetailPage />} />
        <Route path="/simulation/tasks/:taskId/result" element={<TaskResultPage />} />
        <Route path="/benchmark" element={<BenchmarkBrowsePage />} />
        <Route path="/benchmark/chips/:vendor/:chip" element={<ChipBenchmarkPage />} />
        <Route path="/benchmark/chips/:vendor/:chip/benchmarks/:benchmarkName" element={<BenchmarkDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
