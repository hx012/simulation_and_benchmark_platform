import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Form, Input, message, Modal, Select, Skeleton, Tag } from 'antd';
import { LikeOutlined, PlusOutlined } from '@ant-design/icons';
import { collaborationApi, type DemandItem, type DemandPayload } from '../api/collaboration';
import { PageHeading } from '../components/PageHeading';

const statusLabels: Record<string, { label: string; color: string }> = {
  pending: { label: '待审视', color: 'gold' },
  accepted: { label: '已采纳', color: 'green' },
  planned: { label: '规划中', color: 'blue' },
  delivered: { label: '已交付', color: 'cyan' },
  deferred: { label: '暂缓', color: 'default' },
  rejected: { label: '未采纳', color: 'red' },
};

export function DemandPoolPage() {
  const [items, setItems] = useState<DemandItem[] | null>(null);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [domain, setDomain] = useState('all');
  const [query, setQuery] = useState('');
  const [form] = Form.useForm<DemandPayload>();

  async function load() {
    const response = await collaborationApi.listDemands();
    setItems(response.items);
  }

  useEffect(() => {
    void load().catch(() => {
      message.error('需求池加载失败');
      setItems([]);
    });
  }, []);

  const filtered = useMemo(() => (items || []).filter((item) => {
    const domainMatch = domain === 'all' || item.domain === domain;
    const text = `${item.title} ${item.request_no} ${item.submitter_name}`.toLowerCase();
    return domainMatch && text.includes(query.trim().toLowerCase());
  }), [domain, items, query]);

  async function submit(values: DemandPayload) {
    setSubmitting(true);
    try {
      const created = await collaborationApi.submitDemand(values);
      setItems((current) => [created, ...(current || [])]);
      message.success(`需求 ${created.request_no} 已提交，审视前仅你和管理员可见`);
      form.resetFields();
      setOpen(false);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '需求提交失败');
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleVote(item: DemandItem) {
    try {
      const result = await collaborationApi.setDemandVote(item.demand_id, !item.voted_by_me);
      setItems((current) => (current || []).map((candidate) => candidate.demand_id === item.demand_id
        ? { ...candidate, support_count: result.support_count, voted_by_me: result.voted_by_me }
        : candidate));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '操作失败');
    }
  }

  return (
    <div className="page-container demand-page">
      <PageHeading
        title="平台需求池"
        subtitle="收集真实业务需求，审视后公开展示结论和交付进度"
        actions={<Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>提交需求</Button>}
      />

      <Card className="clean-card demand-filter-card">
        <Select value={domain} onChange={setDomain} options={[
          { value: 'all', label: '全部领域' },
          { value: '仿真', label: '仿真' },
          { value: '性能分析', label: '性能分析' },
          { value: 'Benchmark', label: 'Benchmark' },
          { value: '平台体验', label: '平台体验' },
        ]} />
        <Input.Search allowClear placeholder="搜索标题、编号或提交人" value={query} onChange={(event) => setQuery(event.target.value)} />
      </Card>

      {!items ? <Skeleton active /> : (
        <div className="demand-list">
          {filtered.map((item) => {
            const status = statusLabels[item.status] || { label: item.status, color: 'default' };
            return (
              <Card key={item.demand_id} className="demand-card">
                <div className="demand-card-main">
                  <div className="demand-card-heading">
                    <div>
                      <h3>{item.title}</h3>
                      <span>{item.request_no} · {item.submitter_name} · {item.domain}</span>
                    </div>
                    <div className="demand-tags">
                      {item.is_own && item.visibility !== 'public' ? <Tag>仅自己与管理员可见</Tag> : null}
                      <Tag color={status.color}>{status.label}</Tag>
                    </div>
                  </div>
                  <p><strong>需求内容：</strong>{item.description}</p>
                  <p><strong>业务价值：</strong>{item.business_value}</p>
                  {item.conclusion ? <div className="demand-conclusion"><strong>审视结论：</strong>{item.conclusion}</div> : null}
                </div>
                <Button
                  className={item.voted_by_me ? 'demand-vote active' : 'demand-vote'}
                  icon={<LikeOutlined />}
                  onClick={() => void toggleVote(item)}
                >
                  支持 {item.support_count}
                </Button>
              </Card>
            );
          })}
          {!filtered.length ? <Card className="clean-card"><div className="platform-home-empty-row">暂无符合条件的需求</div></Card> : null}
        </div>
      )}

      <Modal
        title="提交业务需求"
        open={open}
        width={760}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={submitting}
        okText="确认提交"
      >
        <div className="demand-submit-tip">提交后默认仅你和管理员可见；审视并配置为公开后进入公共需求池。</div>
        <Form form={form} layout="vertical" onFinish={(values) => void submit(values)} initialValues={{ expected_time: '', contact: '' }}>
          <Form.Item name="title" label="需求标题" rules={[{ required: true, min: 2 }]}><Input maxLength={255} /></Form.Item>
          <div className="demand-form-grid">
            <Form.Item name="domain" label="业务领域" rules={[{ required: true }]}>
              <Select options={['仿真', '性能分析', 'Benchmark', '平台体验'].map((value) => ({ value, label: value }))} />
            </Form.Item>
            <Form.Item name="expected_time" label="期望时间">
              <Select options={['', '1 个月内', '本季度', '无明确时间要求'].map((value) => ({ value, label: value || '请选择' }))} />
            </Form.Item>
          </div>
          <Form.Item name="background" label="需求背景" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={3} maxLength={10000} /></Form.Item>
          <Form.Item name="description" label="需求内容" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={3} maxLength={10000} /></Form.Item>
          <Form.Item name="business_value" label="业务价值" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={3} maxLength={10000} /></Form.Item>
          <Form.Item name="contact" label="联系人（可选）"><Input maxLength={255} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
