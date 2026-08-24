import { Card, Empty, Tag } from 'antd';
import { PageHeading } from '../components/PageHeading';

export function PerformancePage() {
  return (
    <div className="page-container performance-page">
      <PageHeading
        title="性能分析"
        subtitle="面向仿真结果、Trace 与 Benchmark 的统一性能分析平台"
        actions={<Tag>规划中</Tag>}
      />
      <Card className="clean-card performance-empty-card">
        <Empty
          description={(
            <div>
              <strong>功能建设中</strong>
              <p>数据源接入、分析工具和报告能力将在后续版本逐步开放。</p>
            </div>
          )}
        />
      </Card>
    </div>
  );
}
