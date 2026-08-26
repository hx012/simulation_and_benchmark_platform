import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Drawer, Form, Input, message, Select, Skeleton, Table, Tabs, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { CheckCircleOutlined, ClockCircleOutlined, InboxOutlined } from '@ant-design/icons';
import {
  collaborationApi,
  type DemandAdminPayload,
  type DemandItem,
  type FeedbackAdminPayload,
  type FeedbackItem,
} from '../api/collaboration';
import { PageHeading } from '../components/PageHeading';
import { demandStatusLabels } from './DemandPoolPage';

const feedbackStatusLabels: Record<string, { label: string; color: string }> = {
  pending: { label: '待处理', color: 'gold' },
  processing: { label: '处理中', color: 'blue' },
  needs_info: { label: '待用户补充', color: 'orange' },
  resolved: { label: '已解决', color: 'green' },
  closed: { label: '已关闭', color: 'default' },
  withdrawn: { label: '用户已撤回', color: 'default' },
};

const feedbackTypeLabels: Record<string, string> = {
  experience: '体验建议', function: '功能问题', data: '数据问题', other: '其他',
};

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

export function CollaborationAdminPage() {
  const [demands, setDemands] = useState<DemandItem[] | null>(null);
  const [feedback, setFeedback] = useState<FeedbackItem[] | null>(null);
  const [selectedDemand, setSelectedDemand] = useState<DemandItem | null>(null);
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [demandForm] = Form.useForm<DemandAdminPayload>();
  const [feedbackForm] = Form.useForm<FeedbackAdminPayload>();

  async function load() {
    const [demandResponse, feedbackResponse] = await Promise.all([
      collaborationApi.listAdminDemands(),
      collaborationApi.listAdminFeedback(),
    ]);
    setDemands(demandResponse.items);
    setFeedback(feedbackResponse);
  }

  useEffect(() => {
    void load().catch((error) => {
      message.error(error instanceof Error ? error.message : '共建数据加载失败');
      setDemands([]);
      setFeedback([]);
    });
  }, []);

  const filteredDemands = useMemo(() => (demands || []).filter((item) => {
    const text = `${item.title} ${item.request_no} ${item.submitter_name}`.toLowerCase();
    return (status === 'all' || item.status === status) && text.includes(query.trim().toLowerCase());
  }), [demands, query, status]);

  const filteredFeedback = useMemo(() => (feedback || []).filter((item) => {
    const text = `${item.content} ${item.display_name} ${item.page_title}`.toLowerCase();
    return (status === 'all' || item.status === status) && text.includes(query.trim().toLowerCase());
  }), [feedback, query, status]);

  const metrics = useMemo(() => ({
    pending: (demands || []).filter((item) => item.status === 'pending').length + (feedback || []).filter((item) => item.status === 'pending').length,
    processing: (demands || []).filter((item) => ['planned', 'in_progress'].includes(item.status)).length + (feedback || []).filter((item) => item.status === 'processing').length,
    completed: (demands || []).filter((item) => item.status === 'delivered').length + (feedback || []).filter((item) => ['resolved', 'closed'].includes(item.status)).length,
  }), [demands, feedback]);

  function openDemand(item: DemandItem) {
    setSelectedDemand(item);
    demandForm.setFieldsValue({
      status: item.status as DemandAdminPayload['status'],
      conclusion: item.conclusion,
      visibility: item.visibility as DemandAdminPayload['visibility'],
      priority: item.priority as DemandAdminPayload['priority'],
      planned_time: item.planned_time,
    });
  }

  function openFeedback(item: FeedbackItem) {
    setSelectedFeedback(item);
    feedbackForm.setFieldsValue({
      status: (item.status === 'withdrawn' ? 'closed' : item.status) as FeedbackAdminPayload['status'],
      resolution: item.resolution,
      reply: '',
    });
  }

  async function saveDemand(values: DemandAdminPayload) {
    if (!selectedDemand) return;
    setSaving(true);
    try {
      const updated = await collaborationApi.reviewDemand(selectedDemand.demand_id, values);
      setDemands((current) => (current || []).map((item) => item.demand_id === updated.demand_id ? updated : item));
      setSelectedDemand(updated);
      message.success('需求处理结果已保存');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }

  async function saveFeedback(values: FeedbackAdminPayload) {
    if (!selectedFeedback) return;
    setSaving(true);
    try {
      const updated = await collaborationApi.reviewFeedback(selectedFeedback.feedback_id, values);
      setFeedback((current) => (current || []).map((item) => item.feedback_id === updated.feedback_id ? updated : item));
      setSelectedFeedback(updated);
      feedbackForm.setFieldValue('reply', '');
      message.success('反馈处理结果已保存并同步给用户');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }

  const demandColumns: ColumnsType<DemandItem> = [
    { title: '需求', key: 'title', render: (_, item) => <div className="collab-title-cell"><strong>{item.title}</strong><small>{item.request_no} · {item.domain}</small></div> },
    { title: '提交人', dataIndex: 'submitter_name', width: 120 },
    { title: '状态', dataIndex: 'status', width: 110, render: (value) => { const item = demandStatusLabels[value] || { label: value, color: 'default' }; return <Tag color={item.color}>{item.label}</Tag>; } },
    { title: '可见性', dataIndex: 'visibility', width: 100, render: (value) => value === 'public' ? <Tag color="blue">公开</Tag> : <Tag>私有</Tag> },
    { title: '支持', dataIndex: 'support_count', width: 80, align: 'right' },
    { title: '更新于', dataIndex: 'updated_at', width: 170, render: formatTime },
    { title: '', key: 'action', width: 90, render: (_, item) => <Button type="link" onClick={() => openDemand(item)}>处理</Button> },
  ];

  const feedbackColumns: ColumnsType<FeedbackItem> = [
    { title: '反馈', key: 'content', render: (_, item) => <div className="collab-title-cell"><strong>{item.content}</strong><small>{feedbackTypeLabels[item.feedback_type]} · {item.page_title || '平台页面'}</small></div> },
    { title: '提交人', dataIndex: 'display_name', width: 120 },
    { title: '状态', dataIndex: 'status', width: 120, render: (value) => { const item = feedbackStatusLabels[value] || { label: value, color: 'default' }; return <Tag color={item.color}>{item.label}</Tag>; } },
    { title: '处理人', dataIndex: 'handler_name', width: 120, render: (value) => value || '未分配' },
    { title: '更新于', dataIndex: 'updated_at', width: 170, render: formatTime },
    { title: '', key: 'action', width: 90, render: (_, item) => <Button type="link" disabled={item.status === 'withdrawn'} onClick={() => openFeedback(item)}>处理</Button> },
  ];

  const toolbar = (statusOptions: Array<{ value: string; label: string }>) => (
    <div className="collab-admin-toolbar">
      <Input.Search allowClear placeholder="搜索编号、标题或提交人" value={query} onChange={(event) => setQuery(event.target.value)} />
      <Select value={status} onChange={setStatus} options={[{ value: 'all', label: '全部状态' }, ...statusOptions]} />
    </div>
  );

  return (
    <div className="page-container collaboration-admin-page">
      <PageHeading title="共建管理" subtitle="统一审视需求、处理意见反馈，并将结果同步给提交人" />
      <div className="collab-metric-grid">
        <Card><ClockCircleOutlined /><div><span>待处理</span><strong>{metrics.pending}</strong></div></Card>
        <Card><InboxOutlined /><div><span>推进中</span><strong>{metrics.processing}</strong></div></Card>
        <Card><CheckCircleOutlined /><div><span>已完成</span><strong>{metrics.completed}</strong></div></Card>
      </div>
      <Card className="clean-card collaboration-admin-card">
        {!demands || !feedback ? <Skeleton active /> : (
          <Tabs onChange={() => { setQuery(''); setStatus('all'); }} items={[
            {
              key: 'demands',
              label: `需求审视 ${demands.filter((item) => item.status === 'pending').length}`,
              children: <>{toolbar(Object.entries(demandStatusLabels).map(([value, item]) => ({ value, label: item.label })))}<Table rowKey="demand_id" columns={demandColumns} dataSource={filteredDemands} pagination={{ pageSize: 10 }} /></>,
            },
            {
              key: 'feedback',
              label: `反馈处理 ${feedback.filter((item) => item.status === 'pending').length}`,
              children: <>{toolbar(Object.entries(feedbackStatusLabels).map(([value, item]) => ({ value, label: item.label })))}<Table rowKey="feedback_id" columns={feedbackColumns} dataSource={filteredFeedback} pagination={{ pageSize: 10 }} /></>,
            },
          ]} />
        )}
      </Card>

      <Drawer title={selectedDemand ? `处理需求 · ${selectedDemand.request_no}` : '处理需求'} size={700} open={Boolean(selectedDemand)} onClose={() => setSelectedDemand(null)}>
        {selectedDemand ? <div className="collab-review-drawer">
          <div className="collab-review-summary"><span>{selectedDemand.domain} · {selectedDemand.submitter_name}</span><h2>{selectedDemand.title}</h2><p>{selectedDemand.description}</p></div>
          <Form form={demandForm} layout="vertical" onFinish={(values) => void saveDemand(values)}>
            <div className="collab-review-grid">
              <Form.Item name="status" label="处理状态" rules={[{ required: true }]}><Select options={Object.entries(demandStatusLabels).filter(([value]) => value !== 'withdrawn').map(([value, item]) => ({ value, label: item.label }))} /></Form.Item>
              <Form.Item name="visibility" label="需求可见性" rules={[{ required: true }]}><Select options={[{ value: 'private', label: '仅提交人和管理员' }, { value: 'public', label: '进入公共需求池' }]} /></Form.Item>
              <Form.Item name="priority" label="优先级" rules={[{ required: true }]}><Select options={[{ value: 'low', label: '低' }, { value: 'normal', label: '普通' }, { value: 'high', label: '高' }, { value: 'urgent', label: '紧急' }]} /></Form.Item>
              <Form.Item name="planned_time" label="计划时间"><Input placeholder="例如：2026 Q4" maxLength={64} /></Form.Item>
            </div>
            <Form.Item name="conclusion" label="审视结论 / 进展说明"><Input.TextArea rows={6} maxLength={10000} placeholder="该内容会展示给需求提交人，并随公开需求对平台用户可见" /></Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} block>保存处理结果</Button>
          </Form>
        </div> : null}
      </Drawer>

      <Drawer title="处理意见反馈" size={700} open={Boolean(selectedFeedback)} onClose={() => setSelectedFeedback(null)}>
        {selectedFeedback ? <div className="collab-review-drawer">
          <div className="collab-review-summary"><span>{feedbackTypeLabels[selectedFeedback.feedback_type]} · {selectedFeedback.display_name} · {selectedFeedback.page_title}</span><h2>{selectedFeedback.content}</h2></div>
          {selectedFeedback.messages.length ? <div className="collab-message-history">{selectedFeedback.messages.map((item) => <div key={item.message_id} className={item.author_role === 'admin' ? 'is-admin' : ''}><strong>{item.author_name}</strong><p>{item.content}</p><small>{formatTime(item.created_at)}</small></div>)}</div> : null}
          <Form form={feedbackForm} layout="vertical" onFinish={(values) => void saveFeedback(values)}>
            <Form.Item name="status" label="处理状态" rules={[{ required: true }]}><Select options={Object.entries(feedbackStatusLabels).filter(([value]) => value !== 'withdrawn').map(([value, item]) => ({ value, label: item.label }))} /></Form.Item>
            <Form.Item name="reply" label="回复用户"><Input.TextArea rows={4} maxLength={5000} placeholder="需要补充信息时必须填写；其他状态可选" /></Form.Item>
            <Form.Item name="resolution" label="最终处理结论"><Input.TextArea rows={4} maxLength={5000} placeholder="解决或关闭时填写，用户可持续查看" /></Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} block>保存并同步给用户</Button>
          </Form>
        </div> : null}
      </Drawer>
    </div>
  );
}
