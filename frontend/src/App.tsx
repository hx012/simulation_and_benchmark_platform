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
import { CollaborationAdminPage } from './pages/CollaborationAdminPage';

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
        <Route path="/simulation/new" element={<PermissionGate resource="simulation.task" fallbackPermission="normal"><CreateTaskPage /></PermissionGate>} />
        <Route path="/simulation/tasks" element={<PermissionGate resource="simulation.task" fallbackPermission="normal"><TaskListPage /></PermissionGate>} />
        <Route path="/simulation/tasks/:taskId" element={<PermissionGate resource="simulation.task" fallbackPermission="normal"><TaskDetailPage /></PermissionGate>} />
        <Route path="/simulation/tasks/:taskId/result" element={<PermissionGate resource="simulation.task" fallbackPermission="normal"><TaskResultPage /></PermissionGate>} />
        <Route path="/permissions" element={<PermissionCenterPage />} />
        <Route path="/performance" element={<PermissionGate resource="performance.view" fallbackPermission="performance_access"><PerformancePage /></PermissionGate>} />
        <Route path="/team" element={<PermissionGate resource="team.view" fallbackPermission="team_access"><TeamPage /></PermissionGate>} />
        <Route path="/demands" element={<PermissionGate resource="demand.view" fallbackPermission="demand_access"><DemandPoolPage /></PermissionGate>} />
        <Route path="/usage-analytics" element={<RequireAdmin><UsageAnalyticsPage /></RequireAdmin>} />
        <Route path="/collaboration-admin" element={<RequireAdmin><CollaborationAdminPage /></RequireAdmin>} />
        <Route path="/benchmark" element={<PermissionGate resource="benchmark.view" fallbackPermission="benchmark_access"><BenchmarkBrowsePage /></PermissionGate>} />
        <Route path="/benchmark/chips/:vendor/:chip" element={<PermissionGate resource="benchmark.view" fallbackPermission="benchmark_access"><ChipBenchmarkPage /></PermissionGate>} />
        <Route path="/benchmark/chips/:vendor/:chip/benchmarks/:benchmarkName" element={<PermissionGate resource="benchmark.view" fallbackPermission="benchmark_access"><BenchmarkDetailPage /></PermissionGate>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
