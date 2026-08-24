import { useEffect, useState } from 'react';
import { Button, Card, Empty, Skeleton, Table, Tag } from 'antd';
import { collaborationApi, type TeamConfig } from '../api/collaboration';
import { PageHeading } from '../components/PageHeading';

export function TeamPage() {
  const [team, setTeam] = useState<TeamConfig | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    void collaborationApi.getTeam().then(setTeam).catch(() => setTeam({
      name: '芯片仿真与性能分析团队',
      description: '团队内容暂时无法加载。',
      team_size: '',
      specialties: [],
      achievements: [],
      contributions: [],
    }));
  }, []);

  if (!team) {
    return <div className="page-container"><Skeleton active /></div>;
  }

  return (
    <div className="page-container team-page">
      <PageHeading title="团队风采" />
      <Card className="team-intro-card">
        <h2>{team.name}</h2>
        <p>{team.description}</p>
        <div className="team-specialties">
          {team.team_size ? <Tag>团队规模 {team.team_size}</Tag> : null}
          {team.specialties.map((item) => <Tag key={item}>{item}</Tag>)}
        </div>
      </Card>

      <Card
        className="team-section-card"
        title="重点成果"
        extra={team.achievements.length > 3 ? (
          <Button onClick={() => setShowAll((value) => !value)}>{showAll ? '收起' : '查看全部成果 →'}</Button>
        ) : null}
      >
        {team.achievements.length ? (
          <div className="achievement-grid">
            {(showAll ? team.achievements : team.achievements.slice(0, 3)).map((item) => (
              <div key={`${item.title}-${item.date}`} className="achievement-card">
                <Tag color="blue">{item.category}</Tag>
                <h3>{item.title}</h3>
                <p>{item.summary}</p>
                <div className="achievement-meta">{item.contributors}{item.date ? ` · ${item.date}` : ''}</div>
              </div>
            ))}
          </div>
        ) : <Empty description="暂无团队成果" />}
      </Card>

      <Card className="team-section-card contribution-card" title="贡献榜 · 本季度">
        <Table
          rowKey="member"
          pagination={false}
          dataSource={team.contributions}
          locale={{ emptyText: '暂无贡献数据' }}
          columns={[
            { title: '成员', dataIndex: 'member', render: (value: string) => <strong>{value}</strong> },
            { title: '主要贡献', dataIndex: 'contribution' },
            { title: '成果数', dataIndex: 'achievement_count', width: 100 },
            { title: '贡献值 ⓘ', dataIndex: 'contribution_score', width: 120 },
            { title: '浏览量', dataIndex: 'views', width: 120, render: (value: number) => value.toLocaleString() },
          ]}
        />
      </Card>
      <div className="config-hint">本页内容由 backend/config/platform_content.yml 维护。</div>
    </div>
  );
}
