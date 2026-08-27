import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeftOutlined, EyeOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, Card, Empty, Input, message, Space, Table, Tag, Typography } from 'antd';
import type { TableColumnsType } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { benchmarkApi } from '../../api/benchmark';
import { PageHeading } from '../../components/PageHeading';
import { ResultWatermark } from '../../components/ResultWatermark';
import type { BenchmarkDefinition, ChipDetail } from '../../types/benchmark';

function displayVendor(value: string) {
  if (!value) return '—';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function displayChip(value: string) {
  return value.toUpperCase();
}

export function ChipBenchmarkPage() {
  const navigate = useNavigate();
  const params = useParams<{ vendor: string; chip: string }>();
  const vendor = decodeURIComponent(params.vendor ?? '');
  const chip = decodeURIComponent(params.chip ?? '');

  const [detail, setDetail] = useState<ChipDetail | null>(null);
  const [items, setItems] = useState<BenchmarkDefinition[]>([]);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!vendor || !chip) return;
    setLoading(true);
    try {
      const [chipDetail, benchmarks] = await Promise.all([
        benchmarkApi.getChip(vendor, chip),
        benchmarkApi.listBenchmarks(vendor, chip),
      ]);
      setDetail(chipDetail);
      setItems(benchmarks.items);
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
      setDetail(null);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [chip, vendor]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const normalized = keyword.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter((item) => (
      item.name.toLowerCase().includes(normalized)
      || item.description.toLowerCase().includes(normalized)
    ));
  }, [items, keyword]);

  const hasCategory = items.some((item) => Boolean(item.category));
  const hasTarget = items.some((item) => Boolean(item.target));

  const columns: TableColumnsType<BenchmarkDefinition> = [
    {
      title: 'Benchmark',
      dataIndex: 'name',
      width: 340,
      render: (_, item) => (
        <Typography.Link
          strong
          onClick={() => navigate(`/benchmark/chips/${encodeURIComponent(vendor)}/${encodeURIComponent(chip)}/benchmarks/${encodeURIComponent(item.name)}`)}
        >
          {item.name}
        </Typography.Link>
      ),
    },
    {
      title: '说明',
      dataIndex: 'description',
      render: (value: string) => value || '—',
    },
    ...(hasCategory ? [{
      title: '类别',
      dataIndex: 'category',
      width: 120,
      render: (value: string | null) => value ? <Tag>{value.toUpperCase()}</Tag> : '—',
    } as const] : []),
    ...(hasTarget ? [{
      title: 'Target',
      dataIndex: 'target',
      width: 140,
      render: (value: string | null) => value ? <Tag>{value}</Tag> : '—',
    } as const] : []),
    {
      title: '操作',
      width: 110,
      fixed: 'right',
      render: (_, item) => (
        <Button
          type="text"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/benchmark/chips/${encodeURIComponent(vendor)}/${encodeURIComponent(chip)}/benchmarks/${encodeURIComponent(item.name)}`)}
        >
          查看
        </Button>
      ),
    },
  ];

  const title = detail
    ? `${displayVendor(detail.vendor)} ${displayChip(detail.chip)}`
    : `${displayVendor(vendor)} ${displayChip(chip)}`;

  return (
    <div className="page-container benchmark-page">
      <PageHeading
        title={title}
        subtitle={detail ? `${detail.benchmark_count} 个已注册 Benchmark` : undefined}
        actions={(
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/benchmark')}>
            返回
          </Button>
        )}
      />

      <ResultWatermark>
        <Card className="table-card benchmark-table-card">
          <div className="benchmark-list-toolbar">
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="搜索 Benchmark"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
            <Space size={8} className="benchmark-list-count">
              <span>{filtered.length}</span>
              <span>Benchmarks</span>
            </Space>
          </div>
          <Table<BenchmarkDefinition>
            rowKey="benchmark_id"
            columns={columns}
            dataSource={filtered}
            loading={loading}
            pagination={filtered.length > 20 ? { pageSize: 20, showSizeChanger: false } : false}
            locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无已注册 Benchmark" /> }}
            scroll={{ x: 760 }}
          />
        </Card>
      </ResultWatermark>
    </div>
  );
}
