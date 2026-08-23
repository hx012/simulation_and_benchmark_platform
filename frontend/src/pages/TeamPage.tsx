import { useEffect, useState } from 'react';
import { Card, Empty, Skeleton, Tag } from 'antd';
import { collaborationApi, type TeamConfig } from '../api/collaboration';
import { PageHeading } from '../components/PageHeading';

export function TeamPage() {
  const [team, setTeam] = useState<TeamConfig | null>(null);

  useEffect(() => {
    void collaborationApi.getTeam().then(setTeam).catch(() => setTeam({
      name: '芯片仿真与性能分析团队',
      description: '团队内容暂时无法加载。',
      specialties: [],
      achievements: [],
    }));
  }, []);

  if (!team) {
    return <div className="page-container"><Skeleton active /></div>;
  }

  return (
    <div className="page-container team-page">
      <PageHeading title="团队风采" subtitle="展示团队方向、工具平台和工程成果" />
      <Card className="team-intro-card">
        <h2>{team.name}</h2>
        <p>{team.description}</p>
        <div className="team-specialties">
          {team.specialties.map((item) => <Tag key={item}>{item}</Tag>)}
        </div>
      </Card>

      <h2 className="platform-home-section-title">重点成果</h2>
      {team.achievements.length ? (
        <div className="achievement-grid">
          {team.achievements.map((item) => (
            <Card key={`${item.title}-${item.date}`} className="achievement-card">
              <Tag color="blue">{item.category}</Tag>
              <h3>{item.title}</h3>
              <p>{item.summary}</p>
              <div className="achievement-meta">{item.contributors}{item.date ? ` · ${item.date}` : ''}</div>
            </Card>
          ))}
        </div>
      ) : <Card className="clean-card"><Empty description="暂无团队成果" /></Card>}
      <div className="config-hint">本页内容由 backend/config/platform_content.yml 维护。</div>
    </div>
  );
}
