import { useEffect, useState } from 'react';
import { ArrowRightOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { collaborationApi, type CommunityLink } from '../api/collaboration';
import { useAuth } from '../auth/AuthContext';
import { PortalLoopDiagram } from '../components/PortalLoopDiagram';
import { SupportGroupModal } from '../components/SupportGroupModal';

const communityFallback: CommunityLink[] = [
  { key: 'jiaxian', name: '稼先社区', url: '', enabled: false, group: 'ecosystem', order: 10 },
  { key: 'w3', name: 'W3 负载建模社区', url: '', enabled: false, group: 'ecosystem', order: 20 },
  { key: 'benchmark_wiki', name: 'Benchmark Wiki', url: '', enabled: false, group: 'ecosystem', order: 30 },
];

const capabilities = [
  { index: '01 / BENCHMARK', title: 'Benchmark', description: '浏览芯片档案、负载定义及可复现的性能基线。', tone: 'blue' },
  { index: '02 / SIMULATION', title: 'MSKPP芯片仿真器', description: '统一管理芯片配置、Workload和仿真任务生命周期。', tone: 'cyan' },
  { index: '03 / ANALYSIS', title: '性能分析', description: '基于仿真结果、指标和Trace定位性能瓶颈。', tone: 'violet' },
];

const communityDescriptions: Record<string, string> = {
  jiaxian: '成果发布与技术交流',
  w3: '模型、方法与实践沉淀',
  benchmark_wiki: '基准说明与使用文档',
};

function openExternal(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer');
}

export function WelcomePage() {
  const navigate = useNavigate();
  const { authenticated } = useAuth();
  const [communities, setCommunities] = useState(communityFallback);
  const [supportOpen, setSupportOpen] = useState(false);

  useEffect(() => {
    void collaborationApi.getPlatformConfig()
      .then((config) => setCommunities(config.communities))
      .catch(() => setCommunities(communityFallback));
  }, []);

  const enterPlatform = () => navigate(authenticated ? '/home' : '/login');
  const enterTeam = () => navigate(authenticated ? '/team' : '/login', { state: { from: '/team' } });

  return (
    <div className="portal-page">
      <header className="portal-header">
        <div className="portal-header-inner">
          <button type="button" className="portal-brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <span className="portal-brand-mark">AI</span>
            <span><strong>AI Chip Platform</strong><small>Simulation · Benchmark · Analysis</small></span>
          </button>
          <nav className="portal-nav" aria-label="门户导航">
            <a href="#team">关于平台</a><a href="#capabilities">核心能力</a><a href="#support">社区生态</a>
            <Button type="primary" onClick={enterPlatform}>进入平台</Button>
          </nav>
        </div>
      </header>

      <main>
        <section className="portal-hero">
          <div className="portal-hero-copy">
            <div className="portal-kicker">AI CHIP ENGINEERING PLATFORM</div>
            <h1>AI芯片仿真与<br /><span className="portal-title-line portal-gradient-text">性能分析平台</span></h1>
            <p>以仿真与Benchmark数据驱动微架构分析、验证与优化。</p>
            <Button type="primary" size="large" icon={<ArrowRightOutlined />} iconPlacement="end" onClick={enterPlatform}>进入平台</Button>
          </div>
          <div className="portal-loop-shell">
            <PortalLoopDiagram />
          </div>
        </section>

        <section className="portal-team-band" id="team">
          <div className="portal-team-inner">
            <div><span className="portal-team-kicker">ABOUT THE PLATFORM</span><h2>让芯片性能研究形成统一工作流</h2></div>
            <div className="portal-team-copy">
              <p>芯片仿真与性能分析团队面向架构研究、负载建模，持续沉淀可复用的仿真能力、Benchmark 和性能分析工具。</p>
              <strong>架构仿真 · 负载建模 · 性能分析</strong>
              <button type="button" onClick={enterTeam}>了解团队与成果 →</button>
            </div>
          </div>
        </section>

        <section className="portal-capabilities portal-section" id="capabilities">
          <div className="portal-section-heading"><span className="portal-kicker">CORE CAPABILITIES</span><h2>三项核心能力</h2></div>
          <div className="portal-capability-grid">
            {capabilities.map((item) => (
              <article key={item.index} className={`portal-capability-card is-${item.tone}`}>
                <div className="portal-capability-top"><em>{item.index}</em></div><h3>{item.title}</h3><p>{item.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="portal-support portal-section" id="support">
          <div className="portal-section-heading"><span className="portal-kicker">ECOSYSTEM &amp; SUPPORT</span><h2>社区与支持</h2></div>
          <div className="portal-support-grid">
            <div className="portal-support-group">
              <div className="portal-support-label">社区生态</div>
              <div className="portal-community-links">
                {[...communities].sort((a, b) => a.order - b.order).map((item) => (
                  <button type="button" key={item.key} className="portal-support-link" disabled={!item.enabled} onClick={() => item.enabled && openExternal(item.url)}>
                    <span><strong>{item.name}</strong><small>{communityDescriptions[item.key] || (item.enabled ? '访问社区与技术资料' : '敬请期待')}</small></span><ArrowRightOutlined />
                  </button>
                ))}
              </div>
            </div>
            <div className="portal-support-group is-support">
              <div className="portal-support-label">平台支持</div>
              <button type="button" className="portal-support-link" onClick={() => setSupportOpen(true)}>
                <span><strong>MSKPP 技术支撑群</strong><small>平台答疑与问题响应</small></span><ArrowRightOutlined />
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="portal-footer"><span>AI Chip Platform · Internal</span><span>芯片仿真 · Benchmark · 性能分析</span></footer>
      <SupportGroupModal open={supportOpen} onClose={() => setSupportOpen(false)} />
    </div>
  );
}
