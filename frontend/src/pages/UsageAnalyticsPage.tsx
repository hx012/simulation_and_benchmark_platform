import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Input,
  message,
  Row,
  Segmented,
  Space,
  Skeleton,
  Statistic,
  Table,
  Tabs,
  Tag,
  Timeline,
  Typography,
} from 'antd';
import type { TableColumnsType, TableProps } from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { analyticsApi } from '../api/analytics';
import { PageHeading } from '../components/PageHeading';
import type {
  AnalyticsOverview,
  AnalyticsRankingItem,
  AnalyticsSimulationDimensionItem,
  AnalyticsTrendPoint,
  AnalyticsUserDetail,
  AnalyticsUserItem,
  AnalyticsUserSort,
} from '../types/analytics';
import { formatDateTime } from '../utils/format';

function formatCount(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value);
}

function formatActiveSeconds(seconds: number) {
  if (!seconds) return '0 分钟';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.max(1, Math.round((seconds % 3600) / 60));
  if (!hours) return `${minutes} 分钟`;
  return `${hours} 小时 ${minutes} 分`;
}

function TrendChart({ points }: { points: AnalyticsTrendPoint[] }) {
  const width = 760;
  const height = 230;
  const left = 44;
  const right = 16;
  const top = 20;
  const bottom = 36;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const maxValue = Math.max(1, ...points.map((item) => item.active_users));
  const coordinates = points.map((item, index) => {
    const x = left + (points.length <= 1 ? plotWidth / 2 : index / (points.length - 1) * plotWidth);
    const y = top + plotHeight - item.active_users / maxValue * plotHeight;
    return { x, y, item };
  });
  const line = coordinates.map(({ x, y }) => `${x},${y}`).join(' ');
  const area = coordinates.length
    ? `${left},${top + plotHeight} ${line} ${left + plotWidth},${top + plotHeight}`
    : '';
  const labels = coordinates.length
    ? [coordinates[0], coordinates[Math.floor(coordinates.length / 2)], coordinates.at(-1)!]
    : [];

  if (!points.some((item) => item.active_users > 0)) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前时间范围内暂无访问数据" />;
  }

  return (
    <svg className="analytics-trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="平台每日活跃用户趋势">
      {[0, 0.5, 1].map((ratio) => {
        const y = top + plotHeight * ratio;
        return (
          <g key={ratio}>
            <line x1={left} y1={y} x2={left + plotWidth} y2={y} className="analytics-chart-grid" />
            <text x={left - 8} y={y + 4} textAnchor="end">{Math.round(maxValue * (1 - ratio))}</text>
          </g>
        );
      })}
      <polygon points={area} className="analytics-chart-area" />
      <polyline points={line} className="analytics-chart-line" />
      {coordinates.map(({ x, y, item }) => (
        <circle key={item.date} cx={x} cy={y} r="8" className="analytics-chart-hit">
          <title>{item.date}：{item.active_users} 人，{item.page_views} PV</title>
        </circle>
      ))}
      {labels.map(({ x, item }) => (
        <text key={item.date} x={x} y={height - 9} textAnchor={x === left ? 'start' : x > width / 2 ? 'end' : 'middle'}>{item.date.slice(5)}</text>
      ))}
    </svg>
  );
}

function RankingTable({ data, kind }: { data: AnalyticsRankingItem[]; kind: 'page' | 'feature' | 'chip' | 'benchmark' }) {
  const nameTitle = kind === 'chip' ? '芯片' : kind === 'benchmark' ? 'Benchmark' : kind === 'feature' ? '功能' : '页面';
  const columns: TableColumnsType<AnalyticsRankingItem> = [
    {
      title: nameTitle,
      dataIndex: 'label',
      render: (value: string, item) => (
        <div className="analytics-ranking-name">
          <Typography.Text strong>{value || '—'}</Typography.Text>
          {kind === 'benchmark' && item.chip ? <Typography.Text type="secondary">{item.vendor} / {item.chip}</Typography.Text> : null}
        </div>
      ),
    },
    { title: '人数', dataIndex: 'users', align: 'right', width: 82 },
    { title: '次数', dataIndex: 'count', align: 'right', width: 82 },
    ...(kind === 'page' ? [{
      title: '有效停留',
      dataIndex: 'active_seconds',
      align: 'right' as const,
      width: 120,
      render: (value: number) => formatActiveSeconds(value),
    }] : []),
    ...(kind === 'benchmark' ? [{
      title: '类型 / Target',
      width: 150,
      render: (_: unknown, item: AnalyticsRankingItem) => [item.benchmark_type, item.test_target].filter(Boolean).join(' / ') || '—',
    }] : []),
  ];
  return (
    <Table<AnalyticsRankingItem>
      rowKey="key"
      size="small"
      columns={columns}
      dataSource={data}
      pagination={false}
      locale={{ emptyText: '暂无数据' }}
      scroll={{ x: kind === 'benchmark' ? 620 : 460 }}
    />
  );
}

export function UsageAnalyticsPage() {
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [users, setUsers] = useState<AnalyticsUserItem[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [usersLoading, setUsersLoading] = useState(true);
  const [userSearch, setUserSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [userPage, setUserPage] = useState(1);
  const [userPageSize, setUserPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<AnalyticsUserSort>('last_active_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [userDetail, setUserDetail] = useState<AnalyticsUserDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadOverview = useCallback(async (silent = false) => {
    if (!silent) setOverviewLoading(true);
    try {
      setOverview(await analyticsApi.getOverview(days));
      setOverviewError(null);
      setLastUpdatedAt(new Date());
    } catch (error) {
      setOverviewError(error instanceof Error ? error.message : '使用分析数据加载失败');
    } finally {
      if (!silent) setOverviewLoading(false);
    }
  }, [days]);

  const loadUsers = useCallback(async (silent = false) => {
    if (!silent) setUsersLoading(true);
    try {
      const response = await analyticsApi.listUsers({
        days,
        search: userSearch,
        sortBy,
        sortOrder,
        page: userPage,
        pageSize: userPageSize,
      });
      setUsers(response.items);
      setUserTotal(response.total);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '用户行为数据加载失败');
    } finally {
      if (!silent) setUsersLoading(false);
    }
  }, [days, sortBy, sortOrder, userPage, userPageSize, userSearch]);

  useEffect(() => { void loadOverview(); }, [loadOverview]);
  useEffect(() => { void loadUsers(); }, [loadUsers]);

  const refreshAll = useCallback(async (silent = false) => {
    await Promise.all([loadOverview(silent), loadUsers(silent)]);
  }, [loadOverview, loadUsers]);

  useEffect(() => {
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') void refreshAll(true);
    };
    const interval = window.setInterval(refreshWhenVisible, 60_000);
    document.addEventListener('visibilitychange', refreshWhenVisible);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', refreshWhenVisible);
    };
  }, [refreshAll]);

  async function openUserDetail(item: AnalyticsUserItem) {
    setDetailOpen(true);
    setDetailLoading(true);
    setUserDetail(null);
    try {
      setUserDetail(await analyticsApi.getUserDetail(item.user_id, days));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '用户详情加载失败');
    } finally {
      setDetailLoading(false);
    }
  }

  const userColumns = useMemo<TableColumnsType<AnalyticsUserItem>>(() => [
    {
      title: '用户',
      key: 'user',
      fixed: 'left',
      width: 170,
      render: (_, item) => (
        <button type="button" className="analytics-user-link" onClick={() => void openUserDetail(item)}>
          <strong>{item.display_name}</strong><span>{item.user_id}</span>
        </button>
      ),
    },
    {
      title: '最近活跃', dataIndex: 'last_active_at', key: 'last_active_at', sorter: true, width: 170,
      sortOrder: sortBy === 'last_active_at' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : null,
      render: (value: string | null) => value ? formatDateTime(value) : '—',
    },
    { title: '活跃天数', dataIndex: 'active_days', key: 'active_days', sorter: true, align: 'right', width: 105, sortOrder: sortBy === 'active_days' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : null },
    { title: '会话数', dataIndex: 'visits', key: 'visits', sorter: true, align: 'right', width: 90, sortOrder: sortBy === 'visits' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : null },
    { title: 'PV', dataIndex: 'page_views', key: 'page_views', sorter: true, align: 'right', width: 80, sortOrder: sortBy === 'page_views' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : null },
    {
      title: '有效停留', dataIndex: 'active_seconds', key: 'active_seconds', sorter: true, align: 'right', width: 125,
      sortOrder: sortBy === 'active_seconds' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : null,
      render: (value: number) => formatActiveSeconds(value),
    },
    { title: '仿真任务', dataIndex: 'simulation_tasks', key: 'simulation_tasks', sorter: true, align: 'right', width: 105, sortOrder: sortBy === 'simulation_tasks' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : null },
    { title: '需求/反馈', dataIndex: 'demand_feedback', key: 'demand_feedback', sorter: true, align: 'right', width: 110, sortOrder: sortBy === 'demand_feedback' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : null },
    { title: '主要关注', dataIndex: 'top_page', width: 150, render: (value: string | null) => value ? <Tag>{value}</Tag> : '—' },
    { title: '关注芯片', dataIndex: 'top_chip', width: 130, render: (value: string | null) => value || '—' },
  ], [sortBy, sortOrder]);

  const handleUserTableChange: TableProps<AnalyticsUserItem>['onChange'] = (pagination, _filters, sorter) => {
    setUserPage(pagination.current || 1);
    setUserPageSize(pagination.pageSize || 20);
    const selected = Array.isArray(sorter) ? sorter[0] : sorter;
    if (selected?.columnKey && selected.order) {
      setSortBy(selected.columnKey as AnalyticsUserSort);
      setSortOrder(selected.order === 'ascend' ? 'asc' : 'desc');
    }
  };

  const summary = overview?.summary;
  const summaryCards = [
    { label: '访问人数 UV', value: summary?.active_users || 0, suffix: '人' },
    { label: '访问会话数', value: summary?.visits || 0, suffix: '次' },
    { label: '页面浏览量 PV', value: summary?.page_views || 0, suffix: '次' },
    { label: '有效停留时长', value: formatActiveSeconds(summary?.active_seconds || 0), suffix: '' },
    { label: '仿真任务提交', value: summary?.simulation_tasks || 0, suffix: '个' },
    { label: '需求与反馈', value: summary?.demand_feedback || 0, suffix: '条' },
  ];

  const simulationColumns: TableColumnsType<AnalyticsSimulationDimensionItem> = [
    { title: '芯片', dataIndex: 'chip_variant', render: (value: string | null) => value || '默认芯片' },
    { title: 'Simulator', dataIndex: 'simulator_version' },
    { title: '模式', dataIndex: 'simulation_mode' },
    { title: '使用人数', dataIndex: 'users', align: 'right' },
    { title: '任务数', dataIndex: 'tasks', align: 'right' },
    { title: '完成成功率', dataIndex: 'success_rate', align: 'right', render: (value: number) => `${value}%` },
  ];

  return (
    <div className="page-container usage-analytics-page">
      <PageHeading
        title="平台使用分析"
        subtitle="按真实访问和业务行为识别重点用户、芯片与 Benchmark 需求"
        actions={(
          <Space wrap className="analytics-refresh-actions">
            <Typography.Text type="secondary">
              {lastUpdatedAt ? `数据更新于 ${lastUpdatedAt.toLocaleTimeString('zh-CN', { hour12: false })}` : '正在加载数据'}
            </Typography.Text>
            <Button icon={<ReloadOutlined />} loading={overviewLoading || usersLoading} onClick={() => void refreshAll()}>
              立即刷新
            </Button>
            <Segmented<number> value={days} onChange={(value) => { setDays(value); setUserPage(1); }} options={[{ label: '近 7 天', value: 7 }, { label: '近 30 天', value: 30 }, { label: '近 90 天', value: 90 }]} />
          </Space>
        )}
      />

      {overviewError ? <Alert className="analytics-error" type="error" showIcon title="统计数据加载失败" description={overviewError} action={<a onClick={() => void loadOverview()}>重试</a>} /> : null}

      <Tabs
        items={[
          {
            key: 'overview',
            label: '总览',
            children: overviewLoading && !overview ? <Skeleton active /> : (
              <>
                <Row gutter={[14, 14]} className="analytics-summary-grid">
                  {summaryCards.map((item) => (
                    <Col xs={12} md={8} xl={4} key={item.label}>
                      <Card className="analytics-stat-card">
                        <Statistic title={item.label} value={item.value} suffix={item.suffix} formatter={(value) => typeof value === 'number' ? formatCount(value) : value} />
                      </Card>
                    </Col>
                  ))}
                </Row>
                <Row gutter={[16, 16]}>
                  <Col xs={24} xl={12}>
                    <Card title="访问趋势" extra="每日活跃用户（北京时间）" className="clean-card analytics-panel-card">
                      <TrendChart points={overview?.trend || []} />
                    </Card>
                  </Col>
                  <Col xs={24} xl={12}>
                    <Card title="页面访问排行" extra="按 PV" className="clean-card analytics-panel-card">
                      <RankingTable data={overview?.pages || []} kind="page" />
                    </Card>
                  </Col>
                  <Col xs={24}>
                    <Card title="关键功能使用" extra="成功及高意向行为" className="clean-card analytics-panel-card">
                      <RankingTable data={overview?.features || []} kind="feature" />
                    </Card>
                  </Col>
                </Row>
              </>
            ),
          },
          {
            key: 'dimensions',
            label: '芯片与 Benchmark',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} xl={10}><Card title="热门芯片" extra="Benchmark 访问" className="clean-card analytics-panel-card"><RankingTable data={overview?.chips || []} kind="chip" /></Card></Col>
                <Col xs={24} xl={14}><Card title="热门 Benchmark" extra="具体内容关注" className="clean-card analytics-panel-card"><RankingTable data={overview?.benchmarks || []} kind="benchmark" /></Card></Col>
                <Col xs={24}><Card title="仿真配置使用" extra="来自实际提交任务" className="clean-card analytics-panel-card"><Table<AnalyticsSimulationDimensionItem> rowKey="key" size="small" columns={simulationColumns} dataSource={overview?.simulation_dimensions || []} pagination={false} locale={{ emptyText: '当前时间范围内暂无仿真任务' }} scroll={{ x: 720 }} /></Card></Col>
              </Row>
            ),
          },
          {
            key: 'users',
            label: '用户分析',
            children: (
              <Card className="clean-card analytics-users-card">
                <div className="analytics-user-toolbar">
                  <Input.Search
                    allowClear
                    value={searchInput}
                    prefix={<SearchOutlined />}
                    placeholder="搜索姓名或工号"
                    onChange={(event) => {
                      setSearchInput(event.target.value);
                      if (!event.target.value) { setUserSearch(''); setUserPage(1); }
                    }}
                    onSearch={(value) => { setUserSearch(value.trim()); setUserPage(1); }}
                  />
                  <Typography.Text type="secondary">共 {userTotal} 名活跃用户，点击姓名查看详情</Typography.Text>
                </div>
                <Table<AnalyticsUserItem>
                  rowKey="user_id"
                  loading={usersLoading}
                  columns={userColumns}
                  dataSource={users}
                  onChange={handleUserTableChange}
                  pagination={{ current: userPage, pageSize: userPageSize, total: userTotal, showSizeChanger: true, showTotal: (total) => `共 ${total} 人` }}
                  locale={{ emptyText: '没有符合条件的用户行为数据' }}
                  scroll={{ x: 1240 }}
                />
              </Card>
            ),
          },
        ]}
      />

      <Drawer title="用户行为详情" size={760} open={detailOpen} onClose={() => setDetailOpen(false)}>
        {detailLoading ? <Skeleton active /> : userDetail ? (
          <div className="analytics-user-detail">
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="用户">{userDetail.user.display_name}（{userDetail.user.user_id}）</Descriptions.Item>
              <Descriptions.Item label="最近活跃">{userDetail.user.last_active_at ? formatDateTime(userDetail.user.last_active_at) : '—'}</Descriptions.Item>
              <Descriptions.Item label="活跃天数">{userDetail.user.active_days} 天</Descriptions.Item>
              <Descriptions.Item label="有效停留">{formatActiveSeconds(userDetail.user.active_seconds)}</Descriptions.Item>
              <Descriptions.Item label="主要关注">{userDetail.user.top_page || '—'}</Descriptions.Item>
              <Descriptions.Item label="芯片 / Benchmark">{[userDetail.user.top_chip, userDetail.user.top_benchmark].filter(Boolean).join(' / ') || '—'}</Descriptions.Item>
            </Descriptions>
            <h3>页面偏好</h3>
            <Table rowKey="page_key" size="small" pagination={false} dataSource={userDetail.pages} columns={[
              { title: '页面', dataIndex: 'label' },
              { title: 'PV', dataIndex: 'page_views', align: 'right' },
              { title: '有效停留', dataIndex: 'active_seconds', align: 'right', render: (value: number) => formatActiveSeconds(value) },
            ]} />
            <h3>最近行为</h3>
            <Timeline items={userDetail.recent_events.map((event) => ({
              children: (
                <div><strong>{event.label}</strong><span className="analytics-event-time">{formatDateTime(event.occurred_at)}</span><div className="analytics-event-context">{[event.vendor, event.chip, event.benchmark_name, event.simulator_version, event.chip_variant].filter(Boolean).join(' / ')}</div></div>
              ),
            }))} />
          </div>
        ) : <Empty description="没有用户详情数据" />}
      </Drawer>
    </div>
  );
}
