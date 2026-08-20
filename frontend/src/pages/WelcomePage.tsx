import { Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { ArchitectureBackground } from '../components/ArchitectureBackground';

export function WelcomePage() {
  const navigate = useNavigate();
  const { authenticated } = useAuth();

  return (
    <div className="welcome-page">
      <ArchitectureBackground variant="welcome" />
      <main className="welcome-main">
        <div className="welcome-eyebrow">AI CHIP SIMULATION &amp; BENCHMARK PLATFORM</div>
        <h1>AI 芯片仿真与 Benchmark 平台</h1>
        <p>芯片仿真 · 性能 Benchmark · Trace 与微架构分析</p>
        <Button
          type="primary"
          size="large"
          className="welcome-enter-button"
          onClick={() => navigate(authenticated ? '/home' : '/login')}
        >
          进入平台
        </Button>
      </main>
    </div>
  );
}
