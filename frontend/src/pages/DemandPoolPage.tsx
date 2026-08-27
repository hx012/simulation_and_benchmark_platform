import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Drawer,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Select,
  Skeleton,
  Tabs,
  Tag,
  Timeline,
  Tooltip,
} from 'antd';
import { EditOutlined, EyeOutlined, LikeOutlined, PlusOutlined } from '@ant-design/icons';
import { collaborationApi, type DemandItem, type DemandPayload } from '../api/collaboration';
import { trackAnalyticsEventQuietly } from '../api/analytics';
import { PageHeading } from '../components/PageHeading';

export const demandStatusLabels: Record<string, { label: string; color: string }> = {
  pending: { label: '待审视', color: 'gold' },
  needs_info: { label: '待补充', color: 'orange' },
  accepted: { label: '已采纳', color: 'green' },
  planned: { label: '已规划', color: 'blue' },
  in_progress: { label: '实现中', color: 'processing' },
  delivered: { label: '已交付', color: 'cyan' },
  deferred: { label: '暂缓', color: 'default' },
  rejected: { label: '未采纳', color: 'red' },
  withdrawn: { label: '已撤回', color: 'default' },
};

const eventLabels: Record<string, string> = {
  submitted: '提交需求',
  updated: '更新需求',
  withdrawn: '撤回需求',
  reviewed: '平台审视',
  status_changed: '状态更新',
};

const domainOptions = ['仿真', '性能分析', 'Benchmark', '平台体验'];

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

export function DemandPoolPage() {
  const [publicItems, setPublicItems] = useState<DemandItem[] | null>(null);
  const [myItems, setMyItems] = useState<DemandItem[] | null>(null);
  const [activeTab, setActiveTab] = useState('public');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<DemandItem | null>(null);
  const [selected, setSelected] = useState<DemandItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [domain, setDomain] = useState('all');
  const [query, setQuery] = useState('');
  const [form] = Form.useForm<DemandPayload>();

  async function load() {
    const [publicResponse, myResponse] = await Promise.all([
      collaborationApi.listDemands('public'),
      collaborationApi.listDemands('mine'),
    ]);
    setPublicItems(publicResponse.items);
    setMyItems(myResponse.items);
  }

  useEffect(() => {
    void load().catch(() => {
      message.error('需求池加载失败');
      setPublicItems([]);
      setMyItems([]);
    });
  }, []);

  const source = activeTab === 'public' ? publicItems : myItems;
  const filtered = useMemo(() => (source || []).filter((item) => {
    const domainMatch = domain === 'all' || item.domain === domain;
    const text = `${item.title} ${item.request_no} ${item.submitter_name}`.toLowerCase();
    return domainMatch && text.includes(query.trim().toLowerCase());
  }), [domain, query, source]);

  const metrics = useMemo(() => ({
    publicCount: publicItems?.length || 0,
    progressing: (publicItems || []).filter((item) => ['planned', 'in_progress'].includes(item.status)).length,
    myPending: (myItems || []).filter((item) => ['pending', 'needs_info'].includes(item.status)).length,
  }), [myItems, publicItems]);

  function openCreate() {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ expected_time: '', contact: '' });
    setFormOpen(true);
  }

  function openEdit(item: DemandItem) {
    setEditing(item);
    form.setFieldsValue({
      title: item.title,
      domain: item.domain,
      expected_time: item.expected_time,
      background: item.background,
      description: item.description,
      business_value: item.business_value,
      contact: item.contact,
    });
    setFormOpen(true);
  }

  function replaceItem(updated: DemandItem) {
    setMyItems((current) => (current || []).map((item) => item.demand_id === updated.demand_id ? updated : item));
    setPublicItems((current) => {
      const existing = (current || []).some((item) => item.demand_id === updated.demand_id);
      if (updated.visibility !== 'public') return (current || []).filter((item) => item.demand_id !== updated.demand_id);
      return existing
        ? (current || []).map((item) => item.demand_id === updated.demand_id ? updated : item)
        : [updated, ...(current || [])];
    });
    setSelected((current) => current?.demand_id === updated.demand_id ? updated : current);
  }

  async function submit(values: DemandPayload) {
    setSubmitting(true);
    try {
      if (editing) {
        const updated = await collaborationApi.updateDemand(editing.demand_id, values);
        replaceItem(updated);
        message.success('需求内容已更新');
      } else {
        const created = await collaborationApi.submitDemand(values);
        trackAnalyticsEventQuietly({ event_name: 'demand.create', page_key: 'demands', result: 'success' });
        setMyItems((current) => [created, ...(current || [])]);
        setActiveTab('mine');
        message.success(`需求 ${created.request_no} 已提交，可在“我的需求”中跟踪`);
      }
      form.resetFields();
      setFormOpen(false);
      setEditing(null);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '需求提交失败');
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleVote(item: DemandItem) {
    try {
      const result = await collaborationApi.setDemandVote(item.demand_id, !item.voted_by_me);
      if (result.voted_by_me) trackAnalyticsEventQuietly({ event_name: 'demand.vote', page_key: 'demands', result: 'success' });
      const update = (current: DemandItem[] | null) => (current || []).map((candidate) => candidate.demand_id === item.demand_id
        ? { ...candidate, support_count: result.support_count, voted_by_me: result.voted_by_me }
        : candidate);
      setPublicItems(update);
      setMyItems(update);
      setSelected((current) => current?.demand_id === item.demand_id
        ? { ...current, support_count: result.support_count, voted_by_me: result.voted_by_me }
        : current);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '操作失败');
    }
  }

  async function withdraw(item: DemandItem) {
    try {
      replaceItem(await collaborationApi.withdrawDemand(item.demand_id));
      message.success('需求已撤回，历史记录仍会保留');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '撤回失败');
    }
  }

  return (
    <div className="page-container demand-page">
      <PageHeading
        title="平台需求池"
        subtitle="公共需求透明跟踪，个人提交独立管理；审视结论与交付进展都有记录"
        actions={(
          <Tooltip title="提交关于benchmark、仿真器、分析工具的新需求">
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>提交需求</Button>
          </Tooltip>
        )}
      />

      <div className="demand-metric-grid">
        <div><span>公共需求</span><strong>{metrics.publicCount}</strong><small>已完成平台审视并公开</small></div>
        <div><span>推进中</span><strong>{metrics.progressing}</strong><small>处于规划或实现阶段</small></div>
        <div><span>我的待办</span><strong>{metrics.myPending}</strong><small>待审视或等待补充</small></div>
      </div>

      <Card className="clean-card demand-workbench">
        <Tabs activeKey={activeTab} onChange={(value) => { setActiveTab(value); setDomain('all'); setQuery(''); }} items={[
          { key: 'public', label: `公共需求池 ${publicItems?.length ?? ''}` },
          { key: 'mine', label: `我的需求 ${myItems?.length ?? ''}` },
        ]} />
        <div className="demand-toolbar">
          <Select value={domain} onChange={setDomain} options={[
            { value: 'all', label: '全部领域' },
            ...domainOptions.map((value) => ({ value, label: value })),
          ]} />
          <Input.Search allowClear placeholder="搜索标题、编号或提交人" value={query} onChange={(event) => setQuery(event.target.value)} />
        </div>

        {!source ? <Skeleton active /> : (
          <div className="demand-list">
            {filtered.map((item) => {
              const status = demandStatusLabels[item.status] || { label: item.status, color: 'default' };
              return (
                <article key={item.demand_id} className="demand-row">
                  <div className="demand-row-status"><Tag color={status.color}>{status.label}</Tag><small>{item.domain}</small></div>
                  <button type="button" className="demand-row-copy" onClick={() => setSelected(item)}>
                    <strong>{item.title}</strong>
                    <span>{item.request_no} · {item.submitter_name} · 更新于 {formatTime(item.updated_at)}</span>
                    <p>{item.description}</p>
                  </button>
                  <div className="demand-row-progress">
                    {item.planned_time ? <small>计划：{item.planned_time}</small> : <small>{item.visibility === 'public' ? '公开跟踪' : '仅自己与管理员可见'}</small>}
                    <div>
                      <Button type="text" icon={<EyeOutlined />} onClick={() => setSelected(item)}>详情</Button>
                      {activeTab === 'public' ? (
                        <Button type="text" className={item.voted_by_me ? 'demand-vote active' : 'demand-vote'} icon={<LikeOutlined />} onClick={() => void toggleVote(item)}>{item.support_count}</Button>
                      ) : null}
                      {item.can_edit ? <Button type="text" icon={<EditOutlined />} onClick={() => openEdit(item)}>编辑</Button> : null}
                      {item.can_withdraw ? (
                        <Popconfirm title="撤回后处理记录仍会保留。" onConfirm={() => void withdraw(item)}>
                          <Button danger type="text">撤回</Button>
                        </Popconfirm>
                      ) : null}
                    </div>
                  </div>
                </article>
              );
            })}
            {!filtered.length ? <div className="platform-home-empty-row">{activeTab === 'public' ? '暂无公开需求' : '你还没有提交需求'}</div> : null}
          </div>
        )}
      </Card>

      <Modal
        title={editing ? `编辑需求 · ${editing.request_no}` : '提交业务需求'}
        open={formOpen}
        width={760}
        onCancel={() => { setFormOpen(false); setEditing(null); }}
        onOk={() => form.submit()}
        confirmLoading={submitting}
        okText={editing ? '保存修改' : '确认提交'}
      >
        {!editing ? <div className="demand-submit-tip">提交后默认仅你和管理员可见；平台审视并公开后进入公共需求池。</div> : null}
        <Form form={form} layout="vertical" onFinish={(values) => void submit(values)} initialValues={{ expected_time: '', contact: '' }}>
          <Form.Item name="title" label="需求标题" rules={[{ required: true, min: 2 }]}><Input maxLength={255} /></Form.Item>
          <div className="demand-form-grid">
            <Form.Item name="domain" label="业务领域" rules={[{ required: true }]}><Select options={domainOptions.map((value) => ({ value, label: value }))} /></Form.Item>
            <Form.Item name="expected_time" label="期望时间"><Select options={['', '1 个月内', '本季度', '无明确时间要求'].map((value) => ({ value, label: value || '请选择' }))} /></Form.Item>
          </div>
          <Form.Item name="background" label="需求背景" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={3} maxLength={10000} /></Form.Item>
          <Form.Item name="description" label="需求内容" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={3} maxLength={10000} /></Form.Item>
          <Form.Item name="business_value" label="业务价值" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={3} maxLength={10000} /></Form.Item>
          <Form.Item name="contact" label="联系人（可选）"><Input maxLength={255} /></Form.Item>
        </Form>
      </Modal>

      <Drawer title={selected?.request_no || '需求详情'} size={680} open={Boolean(selected)} onClose={() => setSelected(null)}>
        {selected ? (
          <div className="demand-detail">
            <div className="demand-detail-heading">
              <div><span>{selected.domain} · {selected.submitter_name}</span><h2>{selected.title}</h2></div>
              <Tag color={(demandStatusLabels[selected.status] || demandStatusLabels.pending).color}>{(demandStatusLabels[selected.status] || demandStatusLabels.pending).label}</Tag>
            </div>
            <div className="demand-detail-facts">
              <div><span>优先级</span><strong>{selected.priority || 'normal'}</strong></div>
              <div><span>计划时间</span><strong>{selected.planned_time || '待规划'}</strong></div>
              <div><span>支持数</span><strong>{selected.support_count}</strong></div>
            </div>
            <section><h3>需求背景</h3><p>{selected.background}</p></section>
            <section><h3>需求内容</h3><p>{selected.description}</p></section>
            <section><h3>业务价值</h3><p>{selected.business_value}</p></section>
            {selected.conclusion ? <section className="demand-detail-conclusion"><h3>平台审视结论</h3><p>{selected.conclusion}</p></section> : null}
            <section>
              <h3>处理记录</h3>
              <Timeline items={selected.history.map((event) => ({
                color: event.actor_role === 'admin' ? 'green' : 'blue',
                children: <><strong>{eventLabels[event.event_type] || event.event_type} · {event.actor_name}</strong><p>{event.comment}</p><small>{formatTime(event.created_at)}</small></>,
              }))} />
            </section>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
