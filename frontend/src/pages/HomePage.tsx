import { useEffect, useState } from 'react';
import { Button, Card, Skeleton } from 'antd';
import { useNavigate } from 'react-router-dom';
import { benchmarkApi } from '../api/benchmark';
import { useAuth } from '../auth/AuthContext';
import { PageHeading } from '../components/PageHeading';
import { collaborationApi, type CommunityLink, type TeamConfig } from '../api/collaboration';
import { recentActivityApi } from '../api/recentActivity';
import type { RecentActivityList } from '../types/recentActivity';

interface PlatformAssetStats {
  chips: number | null;
  benchmarks: number | null;
}

export function HomePage() {
  const navigate = useNavigate();
  const { hasResource } = useAuth();
  const canViewBenchmark = hasResource('benchmark.view');
  const [stats, setStats] = useState<PlatformAssetStats | null>(null);
  const [communities, setCommunities] = useState<CommunityLink[]>([]);
  const [team, setTeam] = useState<TeamConfig | null>(null);
  const [recentWork, setRecentWork] = useState<RecentActivityList | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        let chipCount: number | null = null;
        let benchmarkCount: number | null = null;
        if (canViewBenchmark) {
          const chips = await benchmarkApi.listChips();
          const benchmarkLists = await Promise.all(
            chips.items.map((item) => benchmarkApi.listBenchmarks(item.vendor, item.chip)),
          );
          chipCount = chips.total;
          benchmarkCount = benchmarkLists.reduce((sum, item) => sum + item.total, 0);
        }

        if (!cancelled) {
          setStats({
            chips: chipCount,
            benchmarks: benchmarkCount,
          });
        }
      } catch {
        if (!cancelled) {
          setStats({ chips: null, benchmarks: null });
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [canViewBenchmark]);

  useEffect(() => {
    let cancelled = false;
    recentActivityApi.list()
      .then((response) => {
        if (!cancelled) setRecentWork(response);
      })
      .catch(() => {
        if (!cancelled) setRecentWork({
          title: '近期工作',
          description: '当前用户最近访问和操作',
          empty_text: '暂无近期工作',
          items: [],
        });
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    void Promise.all([
      collaborationApi.getPlatformConfig(),
      collaborationApi.getTeam(),
    ]).then(([config, teamConfig]) => {
      setCommunities(config.communities);
      setTeam(teamConfig);
    }).catch(() => {
      setCommunities([]);
      setTeam(null);
    });
  }, []);

  return (
    <div className="page-container platform-home-page">
      <PageHeading
        title="AI 芯片仿真与 Benchmark 平台"
        subtitle="芯片仿真 · 性能 Benchmark · Trace 与微架构分析"
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
          <h2>性能分析</h2>
          <p>选择仿真结果与 Trace，调用分析工具定位指令、内存与时间线瓶颈。</p>
          <Button type="primary" onClick={() => navigate('/performance')}>进入性能分析</Button>
        </Card>
      </div>

      <h2 className="platform-home-section-title">平台资产</h2>
      {stats ? (
        <div className="platform-asset-grid">
          <div className="platform-asset-card">
            <span>支持芯片</span>
            <strong>{stats.chips ?? '受限'}</strong>
          </div>
          <div className="platform-asset-card">
            <span>Benchmark</span>
            <strong>{stats.benchmarks ?? '受限'}</strong>
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
        <Card
          className="platform-home-list-card platform-recent-work-card"
          title={recentWork?.title || '近期工作'}
          extra={<span className="platform-recent-work-description">{recentWork?.description || '当前用户最近访问和操作'}</span>}
        >
          {recentWork?.items.length ? recentWork.items.map((item) => (
            <button
              type="button"
              className="platform-recent-work-row"
              key={item.id}
              onClick={() => navigate(item.href)}
            >
              <span className={`platform-recent-work-icon is-${item.domain}`}>{item.icon}</span>
              <span className="platform-recent-work-copy">
                <strong>{item.title}</strong>
                <small>{item.description}</small>
              </span>
              <span className="platform-recent-work-action">{item.action_label} →</span>
            </button>
          )) : <div className="platform-home-empty-row">{recentWork?.empty_text || '暂无近期工作'}</div>}
        </Card>
        <Card
          className="platform-home-list-card"
          title="团队最新成果"
          extra={<Button type="link" onClick={() => navigate('/team')}>进入团队风采</Button>}
        >
          {team?.achievements.length ? team.achievements.slice(0, 3).map((item) => (
            <div className="platform-home-list-row" key={`${item.title}-${item.date}`}>
              <span>{item.title}</span><em>{item.category}</em>
            </div>
          )) : <div className="platform-home-empty-row">暂无团队成果</div>}
        </Card>
      </div>

      <div className="platform-home-section-head">
        <h2 className="platform-home-section-title">社区生态</h2>
        <span>顶部“生态社区”菜单可在任意页面快捷访问</span>
      </div>
      <div className="community-card-grid">
        {[...communities].sort((a, b) => (a.key === 'jiaxian' ? -1 : b.key === 'jiaxian' ? 1 : 0)).map((item) => (
          <Card key={item.key} className="community-card">
            <div className="community-card-mark">{item.key === 'w3' ? 'W3' : '稼先'}</div>
            <div className="community-card-copy">
              <h3>{item.name}</h3>
              <p>{item.key === 'w3' ? '负载模型、建模方法和实践经验沉淀。' : '项目成果、技术文章发布与交流平台。'}</p>
            </div>
            <Button disabled={!item.enabled} onClick={() => window.open(item.url, '_blank', 'noopener,noreferrer')}>
              进入社区 ↗
            </Button>
          </Card>
        ))}
      </div>

      <Card className="platform-co-build-card">
        <div>
          <h3>平台共建</h3>
          <p>有新的业务场景或改进想法？提交到需求池，由团队定期审视并反馈处理结果。</p>
        </div>
        <Button type="primary" onClick={() => navigate('/demands')}>提交需求</Button>
      </Card>
    </div>
  );
}
