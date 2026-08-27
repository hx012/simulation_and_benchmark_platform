import { useEffect, useState } from 'react';
import { ArrowRightOutlined, UserAddOutlined } from '@ant-design/icons';
import { Button, Empty, Modal, Skeleton, Table, Tabs, Typography } from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { collaborationApi, type TeamConfig } from '../api/collaboration';
import { PageHeading } from '../components/PageHeading';

function openConfiguredUrl(url: string, navigate: (path: string) => void) {
  if (url.startsWith('/')) navigate(url);
  else window.open(url, '_blank', 'noopener,noreferrer');
}

export function TeamPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [team, setTeam] = useState<TeamConfig | null>(null);
  const [joinOpen, setJoinOpen] = useState(false);
  const activeTab = searchParams.get('tab') === 'results' ? 'results' : 'intro';

  useEffect(() => {
    void collaborationApi.getTeam().then(setTeam).catch(() => setTeam({
      name: '芯片仿真与性能分析团队', description: '团队内容暂时无法加载。', team_size: '', specialties: [], members: [], achievements: [], contributions: [], all_achievements_url: '',
    }));
  }, []);

  if (!team) return <div className="page-container"><Skeleton active /></div>;

  return (
    <div className="page-container team-page">
      <PageHeading title="团队风采" />
      <Tabs
        className="team-tabs"
        activeKey={activeTab}
        onChange={(key) => setSearchParams(key === 'results' ? { tab: 'results' } : {}, { replace: true })}
        items={[
          { key: 'intro', label: '团队介绍' },
          { key: 'results', label: '成果与贡献' },
        ]}
      />

      {activeTab === 'intro' ? (
        <>
          <section className="team-intro-panel">
            <h2>{team.name}</h2>
            <p>{team.description}</p>
          </section>
          <div className="team-section-heading">
            <h2>团队成员</h2>
            <button className="team-contact-button" type="button" onClick={() => setJoinOpen(true)}>
              <UserAddOutlined /> 加入团队 <ArrowRightOutlined />
            </button>
          </div>
          {team.members.length ? (
            <div className="team-member-grid">
              {team.members.map((member) => (
                <article className="team-member-card" key={member.employee_id}>
                  <h3>{member.name} <span>{member.employee_id}</span></h3>
                  <strong>{member.direction}</strong>
                  <p>{member.description}</p>
                  {member.tags?.length ? <div className="team-member-tags">{member.tags.map((tag) => <span key={tag}>{tag}</span>)}</div> : null}
                </article>
              ))}
            </div>
          ) : <div className="team-empty"><Empty description="团队成员配置待补充" /></div>}
        </>
      ) : (
        <>
          <div className="team-section-heading team-results-heading">
            <h2>重点成果</h2>
            <Button type="link" disabled={!team.all_achievements_url} onClick={() => team.all_achievements_url && openConfiguredUrl(team.all_achievements_url, navigate)}>
              查看全部成果 <ArrowRightOutlined />
            </Button>
          </div>
          {team.achievements.length ? (
            <div className="team-achievement-grid">
              {team.achievements.slice(0, 3).map((item) => (
                <button
                  type="button"
                  className="team-achievement-card"
                  key={item.id || `${item.title}-${item.date}`}
                  disabled={!item.detail_url}
                  onClick={() => item.detail_url && openConfiguredUrl(item.detail_url, navigate)}
                >
                  <span>{item.category}</span><h3>{item.title}</h3><p>{item.summary}</p>
                  <small>{item.contributors}{item.date ? ` · ${item.date}` : ''}</small>
                  {item.detail_url ? <em>查看成果 →</em> : null}
                </button>
              ))}
            </div>
          ) : <div className="team-empty"><Empty description="暂无团队成果" /></div>}

          <div className="team-section-heading"><h2>贡献榜 · 本季度</h2><span>贡献值用于鼓励协作与成果沉淀</span></div>
          <div className="team-contribution-table">
            <Table
              rowKey="member" pagination={false} dataSource={team.contributions} locale={{ emptyText: '暂无贡献数据' }}
              columns={[
                { title: '成员', dataIndex: 'member', render: (value: string) => <strong>{value}</strong> },
                { title: '主要贡献', dataIndex: 'contribution' },
                { title: '成果数', dataIndex: 'achievement_count', width: 100 },
                { title: '贡献值', dataIndex: 'contribution_score', width: 110 },
                { title: '浏览量', dataIndex: 'views', width: 110, render: (value: number) => value.toLocaleString() },
              ]}
            />
          </div>
        </>
      )}
      <Modal title="加入团队" open={joinOpen} footer={null} onCancel={() => setJoinOpen(false)}>
        <Typography.Paragraph style={{ margin: 0, lineHeight: 1.8 }}>
          欢迎对芯片微架构、MSKPP 仿真器、Benchmark 和性能分析感兴趣的同学加入。可联系管理员郝雪桐 h00517730。
        </Typography.Paragraph>
      </Modal>
    </div>
  );
}
