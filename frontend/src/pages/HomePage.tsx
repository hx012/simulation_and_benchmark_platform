import { useEffect, useState } from 'react';
import { Button, Card, Skeleton } from 'antd';
import { useNavigate } from 'react-router-dom';
import { benchmarkApi } from '../api/benchmark';
import { useAuth } from '../auth/AuthContext';
import { simulationApi } from '../api/simulation';
import { PageHeading } from '../components/PageHeading';

interface PlatformAssetStats {
  chips: number;
  benchmarks: number;
  simulationTasks: number;
}

export function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats] = useState<PlatformAssetStats | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const chips = await benchmarkApi.listChips();
        const benchmarkLists = await Promise.all(
          chips.items.map((item) => benchmarkApi.listBenchmarks(item.vendor, item.chip)),
        );
        const tasks = await simulationApi.listTasks({
          ownerId: user?.userId,
          archived: false,
          pageSize: 1,
        });

        if (!cancelled) {
          setStats({
            chips: chips.total,
            benchmarks: benchmarkLists.reduce((sum, item) => sum + item.total, 0),
            simulationTasks: tasks.total,
          });
        }
      } catch {
        if (!cancelled) {
          setStats({ chips: 0, benchmarks: 0, simulationTasks: 0 });
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [user?.userId]);

  return (
    <div className="page-container platform-home-page">
      <PageHeading
        title="AI 芯片仿真与 Benchmark 平台"
        subtitle="芯片仿真 · 性能 Benchmark · 微架构研究与分析"
      />

      <div className="platform-home-entry-grid">
        <Card className="platform-home-entry-card">
          <h2>仿真开发</h2>
          <p>提交 Simulator Version + Chip Config Bundle + Workload Package。</p>
          <div className="platform-home-actions">
            <Button type="primary" onClick={() => navigate('/simulation/new')}>新建仿真任务</Button>
            <Button onClick={() => navigate('/simulation/tasks')}>我的任务</Button>
          </div>
        </Card>

        <Card className="platform-home-entry-card">
          <h2>Benchmark</h2>
          <p>筛选厂商并选择芯片，进入芯片档案与 Benchmark 资产。</p>
          <Button type="primary" block onClick={() => navigate('/benchmark')}>查看 Benchmark</Button>
        </Card>
      </div>

      <h2 className="platform-home-section-title">平台资产</h2>
      {stats ? (
        <div className="platform-asset-grid">
          <div className="platform-asset-card">
            <span>支持芯片</span>
            <strong>{stats.chips}</strong>
          </div>
          <div className="platform-asset-card">
            <span>Benchmark</span>
            <strong>{stats.benchmarks}</strong>
          </div>
          <div className="platform-asset-card">
            <span>分析报告</span>
            <strong>—</strong>
          </div>
          <div className="platform-asset-card">
            <span>仿真器版本</span>
            <strong>1</strong>
          </div>
        </div>
      ) : (
        <Skeleton active paragraph={{ rows: 2 }} />
      )}

      <div className="platform-home-lower-grid">
        <Card className="platform-home-list-card" title="最近新增 Benchmark">
          <div className="platform-home-empty-row">暂无可展示的新增记录</div>
        </Card>
        <Card className="platform-home-list-card" title="代表性成果">
          <div className="platform-home-empty-row">暂无代表性成果</div>
        </Card>
      </div>

      {stats ? (
        <div className="platform-home-footnote">当前用户共有 {stats.simulationTasks} 个未归档仿真任务</div>
      ) : null}
    </div>
  );
}
