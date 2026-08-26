import { useEffect, useMemo, useState } from 'react';
import { ArrowRightOutlined, BarChartOutlined, ExperimentOutlined, LineChartOutlined } from '@ant-design/icons';
import { Button, Card } from 'antd';
import { useNavigate } from 'react-router-dom';
import { collaborationApi, type TeamConfig } from '../api/collaboration';
import { recentActivityApi } from '../api/recentActivity';
import { PageHeading } from '../components/PageHeading';
import type { RecentActivityList } from '../types/recentActivity';

const entries = [
  { title: 'MSKPP 芯片仿真器', description: '配置、提交并跟踪芯片仿真任务。', path: '/simulation/tasks', icon: <ExperimentOutlined />, tone: 'cyan' },
  { title: 'Benchmark', description: '浏览芯片档案、典型负载与性能基线。', path: '/benchmark', icon: <BarChartOutlined />, tone: 'blue' },
  { title: '性能分析', description: '接入仿真结果与 Trace，定位性能瓶颈。', path: '/performance', icon: <LineChartOutlined />, tone: 'violet' },
];

function openConfiguredUrl(url: string, navigate: (path: string) => void) {
  if (url.startsWith('/')) navigate(url);
  else window.open(url, '_blank', 'noopener,noreferrer');
}

export function HomePage() {
  const navigate = useNavigate();
  const [team, setTeam] = useState<TeamConfig | null>(null);
  const [recentWork, setRecentWork] = useState<RecentActivityList | null>(null);

  useEffect(() => {
    let cancelled = false;
    recentActivityApi.list()
      .then((response) => { if (!cancelled) setRecentWork(response); })
      .catch(() => {
        if (!cancelled) setRecentWork({ title: '近期工作', description: '当前用户最近访问和操作', empty_text: '暂无近期工作', items: [] });
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    void collaborationApi.getTeam().then(setTeam).catch(() => setTeam(null));
  }, []);

  const featuredAchievements = useMemo(() => (
    (team?.achievements || [])
      .filter((item) => item.enabled && item.featured)
      .sort((a, b) => a.featured_order - b.featured_order)
      .slice(0, 5)
  ), [team]);

  return (
    <div className="page-container platform-home-page">
      <PageHeading title="开始工作" subtitle="选择工作空间，或继续最近的仿真与分析任务" />

      <div className="platform-core-grid" aria-label="核心能力入口">
        {entries.map((entry) => (
          <button type="button" key={entry.path} className={`platform-core-card is-${entry.tone}`} onClick={() => navigate(entry.path)}>
            <span className="platform-core-icon">{entry.icon}</span>
            <span className="platform-core-copy"><strong>{entry.title}</strong><small>{entry.description}</small></span>
            <span className="platform-core-arrow">进入 <ArrowRightOutlined /></span>
          </button>
        ))}
      </div>

      <div className="platform-home-panels">
        <Card className={`platform-home-list-card${recentWork?.items.length ? '' : ' is-empty'}`} title={recentWork?.title || '近期工作'} extra={<span className="platform-panel-meta">{recentWork?.description || '当前用户最近访问和操作'}</span>}>
          {recentWork?.items.length ? recentWork.items.slice(0, 5).map((item) => (
            <button type="button" className="platform-compact-row" key={item.id} onClick={() => navigate(item.href)}>
              <span className={`platform-recent-work-icon is-${item.domain}`}>{item.icon}</span>
              <span className="platform-compact-copy"><strong>{item.title}</strong><small>{item.description}</small></span>
              <span className="platform-row-action">{item.action_label} <ArrowRightOutlined /></span>
            </button>
          )) : <div className="platform-home-empty-row">{recentWork?.empty_text || '暂无近期工作'}</div>}
        </Card>

        <Card className="platform-home-list-card" title="重点成果" extra={<Button type="link" onClick={() => navigate('/team?tab=results')}>查看全部成果</Button>}>
          {featuredAchievements.length ? featuredAchievements.map((item) => (
            <button
              type="button"
              className="platform-compact-row platform-achievement-row"
              key={item.id || `${item.title}-${item.date}`}
              disabled={!item.detail_url}
              onClick={() => item.detail_url && openConfiguredUrl(item.detail_url, navigate)}
            >
              <span className="platform-achievement-category">{item.category}</span>
              <span className="platform-compact-copy"><strong>{item.title}</strong><small>{item.contributors}{item.date ? ` · ${item.date}` : ''}</small></span>
              <span className="platform-row-action">{item.detail_url ? '查看成果' : '详情待开放'}</span>
            </button>
          )) : <div className="platform-home-empty-row">暂无重点成果</div>}
        </Card>
      </div>

      <Card className="platform-co-build-card">
        <div><h3>平台共建</h3><p>提交真实业务需求，由团队定期审视并反馈处理结论。</p></div>
        <Button type="primary" onClick={() => navigate('/demands')}>进入需求池</Button>
      </Card>
    </div>
  );
}
