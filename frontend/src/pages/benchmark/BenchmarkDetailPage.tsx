import { useCallback, useEffect, useState } from 'react';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { Button, Card, Collapse, Descriptions, Empty, message, Skeleton } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { benchmarkApi } from '../../api/benchmark';
import { trackAnalyticsEventQuietly } from '../../api/analytics';
import { PageHeading } from '../../components/PageHeading';
import type { BenchmarkDefinition, BenchmarkResultListResponse } from '../../types/benchmark';

function displayVendor(value: string) {
  if (!value) return '—';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function displayChip(value: string) {
  return value.toUpperCase();
}

export function BenchmarkDetailPage() {
  const navigate = useNavigate();
  const params = useParams<{ vendor: string; chip: string; benchmarkName: string }>();
  const vendor = decodeURIComponent(params.vendor ?? '');
  const chip = decodeURIComponent(params.chip ?? '');
  const benchmarkName = decodeURIComponent(params.benchmarkName ?? '');

  const [definition, setDefinition] = useState<BenchmarkDefinition | null>(null);
  const [results, setResults] = useState<BenchmarkResultListResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!vendor || !chip || !benchmarkName) return;
    setLoading(true);
    try {
      const [benchmark, resultList] = await Promise.all([
        benchmarkApi.getBenchmark(vendor, chip, benchmarkName),
        benchmarkApi.listResults(vendor, chip, benchmarkName),
      ]);
      setDefinition(benchmark);
      setResults(resultList);
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
      setDefinition(null);
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, [benchmarkName, chip, vendor]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!definition) return;
    trackAnalyticsEventQuietly({
      event_name: 'benchmark.detail_view',
      page_key: 'benchmark.detail',
      vendor: definition.vendor,
      chip: definition.chip,
      benchmark_name: definition.name,
      benchmark_type: definition.category,
      test_target: definition.target,
      target_type: 'benchmark',
      target_id: `${definition.vendor}/${definition.chip}/${definition.name}`,
      target_name: definition.name,
    });
  }, [definition?.benchmark_id]);

  const backPath = `/benchmark/chips/${encodeURIComponent(vendor)}/${encodeURIComponent(chip)}`;

  if (loading) {
    return (
      <div className="page-container benchmark-page">
        <PageHeading title={benchmarkName || 'Benchmark'} />
        <Card className="clean-card"><Skeleton active paragraph={{ rows: 6 }} /></Card>
      </div>
    );
  }

  if (!definition) {
    return (
      <div className="page-container benchmark-page">
        <PageHeading
          title="Benchmark"
          actions={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate(backPath)}>返回</Button>}
        />
        <div className="benchmark-empty-panel">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未找到 Benchmark" />
        </div>
      </div>
    );
  }

  const implementationItems = [
    {
      key: 'implementation',
      label: '实现信息',
      children: (
        <Descriptions column={1} size="small" className="benchmark-implementation-info">
          <Descriptions.Item label="Module">{definition.module}</Descriptions.Item>
          <Descriptions.Item label="Class">{definition.class_name}</Descriptions.Item>
          <Descriptions.Item label="Benchmark ID">{definition.benchmark_id}</Descriptions.Item>
        </Descriptions>
      ),
    },
  ];

  return (
    <div className="page-container benchmark-page">
      <PageHeading
        title={definition.name}
        subtitle={`${displayVendor(definition.vendor)} / ${displayChip(definition.chip)}`}
        actions={<Button icon={<ArrowLeftOutlined />} onClick={() => navigate(backPath)}>返回</Button>}
      />

      <Card title="基本信息" className="clean-card benchmark-detail-card">
        <Descriptions column={{ xs: 1, sm: 2 }} size="small">
          <Descriptions.Item label="Vendor">{displayVendor(definition.vendor)}</Descriptions.Item>
          <Descriptions.Item label="Chip">{displayChip(definition.chip)}</Descriptions.Item>
          <Descriptions.Item label="说明" span={2}>{definition.description || '—'}</Descriptions.Item>
          {definition.category ? <Descriptions.Item label="类别">{definition.category}</Descriptions.Item> : null}
          {definition.target ? <Descriptions.Item label="Target">{definition.target}</Descriptions.Item> : null}
        </Descriptions>

        <Collapse
          ghost
          className="benchmark-implementation-collapse"
          items={implementationItems}
        />
      </Card>

      <h2 className="section-title">Benchmark 结果</h2>
      <Card className="clean-card benchmark-result-card">
        {results?.total ? (
          <div className="benchmark-result-pending-ui">
            已发现 {results.total} 条结果，结果展示组件将在 Result Schema 确定后接入。
          </div>
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={results?.configured ? '暂无已发布结果' : '结果存储尚未接入'}
          />
        )}
      </Card>
    </div>
  );
}
