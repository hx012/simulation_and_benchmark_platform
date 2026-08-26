import type { ReactElement } from 'react';
import { Spin } from 'antd';
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
import { PermissionCenterPage } from './pages/permissions/PermissionCenterPage';
import { PermissionGate } from './components/PermissionGate';
import { TaskResultPage } from './pages/simulation/TaskResultPage';
import { DemandPoolPage } from './pages/DemandPoolPage';
import { PerformancePage } from './pages/PerformancePage';
import { TeamPage } from './pages/TeamPage';
import { UsageAnalyticsPage } from './pages/UsageAnalyticsPage';

function RequireAuth({ children }: { children: ReactElement }) {
  const { authenticated, initializing } = useAuth();
  const location = useLocation();

  if (initializing) {
    return (
      <div className="auth-route-loading" role="status" aria-label="正在验证登录状态">
        <Spin size="large" />
      </div>
    );
  }
  if (!authenticated) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return children;
}

function RequireAdmin({ children }: { children: ReactElement }) {
  const { user } = useAuth();
  if (user?.authMode !== 'admin') {
    return <Navigate to="/home" replace />;
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
        <Route path="/permissions" element={<PermissionCenterPage />} />
        <Route path="/performance" element={<PerformancePage />} />
        <Route path="/team" element={<TeamPage />} />
        <Route path="/demands" element={<DemandPoolPage />} />
        <Route path="/usage-analytics" element={<RequireAdmin><UsageAnalyticsPage /></RequireAdmin>} />
        <Route path="/benchmark" element={<PermissionGate resource="benchmark.view" fallbackPermission="benchmark_access"><BenchmarkBrowsePage /></PermissionGate>} />
        <Route path="/benchmark/chips/:vendor/:chip" element={<PermissionGate resource="benchmark.view" fallbackPermission="benchmark_access"><ChipBenchmarkPage /></PermissionGate>} />
        <Route path="/benchmark/chips/:vendor/:chip/benchmarks/:benchmarkName" element={<PermissionGate resource="benchmark.view" fallbackPermission="benchmark_access"><BenchmarkDetailPage /></PermissionGate>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
