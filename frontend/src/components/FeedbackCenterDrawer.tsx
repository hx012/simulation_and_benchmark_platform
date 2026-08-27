import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Drawer,
  Empty,
  Form,
  Input,
  message,
  Popconfirm,
  Select,
  Skeleton,
  Tabs,
  Tag,
  Timeline,
} from 'antd';
import { ArrowLeftOutlined, SendOutlined } from '@ant-design/icons';
import {
  collaborationApi,
  type FeedbackItem,
  type FeedbackPayload,
} from '../api/collaboration';
import { trackAnalyticsEventQuietly } from '../api/analytics';

const statusLabels: Record<string, { label: string; color: string }> = {
  pending: { label: '待处理', color: 'gold' },
  processing: { label: '处理中', color: 'blue' },
  needs_info: { label: '待补充', color: 'orange' },
  resolved: { label: '已解决', color: 'green' },
  closed: { label: '已关闭', color: 'default' },
  withdrawn: { label: '已撤回', color: 'default' },
};

const typeLabels: Record<string, string> = {
  experience: '体验建议',
  function: '功能问题',
  data: '数据问题',
  other: '其他',
};

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

interface FeedbackCenterDrawerProps {
  open: boolean;
  pageTitle: string;
  pagePath: string;
  onClose: () => void;
}

export function FeedbackCenterDrawer({ open, pageTitle, pagePath, onClose }: FeedbackCenterDrawerProps) {
  const [activeTab, setActiveTab] = useState('submit');
  const [items, setItems] = useState<FeedbackItem[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [replying, setReplying] = useState(false);
  const [reply, setReply] = useState('');
  const [form] = Form.useForm<FeedbackPayload>();

  const selected = useMemo(
    () => (items || []).find((item) => item.feedback_id === selectedId) || null,
    [items, selectedId],
  );

  async function loadMine() {
    setItems(null);
    try {
      setItems(await collaborationApi.listMyFeedback());
    } catch (error) {
      message.error(error instanceof Error ? error.message : '反馈记录加载失败');
      setItems([]);
    }
  }

  useEffect(() => {
    if (open && activeTab === 'mine') void loadMine();
  }, [open, activeTab]);

  async function submit(values: FeedbackPayload) {
    setSubmitting(true);
    try {
      const created = await collaborationApi.submitFeedback({
        ...values,
        page_title: pageTitle,
        page_path: pagePath,
      });
      trackAnalyticsEventQuietly({ event_name: 'feedback.submit', result: 'success' });
      message.success('反馈已提交，可在“我的反馈”中跟踪进度');
      form.resetFields();
      setActiveTab('mine');
      setItems([created]);
      setSelectedId(created.feedback_id);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '反馈提交失败');
    } finally {
      setSubmitting(false);
    }
  }

  async function supplement() {
    if (!selected || reply.trim().length < 2) return;
    setReplying(true);
    try {
      const updated = await collaborationApi.supplementFeedback(selected.feedback_id, reply.trim());
      setItems((current) => (current || []).map((item) => item.feedback_id === updated.feedback_id ? updated : item));
      setReply('');
      message.success('补充内容已提交');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '提交失败');
    } finally {
      setReplying(false);
    }
  }

  async function withdraw(item: FeedbackItem) {
    try {
      const updated = await collaborationApi.withdrawFeedback(item.feedback_id);
      setItems((current) => (current || []).map((candidate) => candidate.feedback_id === updated.feedback_id ? updated : candidate));
      message.success('反馈已撤回，处理记录仍会保留');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '撤回失败');
    }
  }

  return (
    <Drawer
      title="意见反馈"
      size={640}
      open={open}
      onClose={onClose}
      destroyOnClose={false}
      className="feedback-center-drawer"
    >
      <Tabs activeKey={activeTab} onChange={(key) => { setActiveTab(key); setSelectedId(null); }} items={[
        {
          key: 'submit',
          label: '提交反馈',
          children: (
            <div className="feedback-submit-panel">
              <div className="feedback-intro">
                <strong>告诉我们哪里需要改进</strong>
                <p>提交后可随时查看处理状态、平台回复并补充说明。</p>
              </div>
              <Form
                form={form}
                layout="vertical"
                initialValues={{ feedback_type: 'experience', page_title: '', page_path: '', content: '' }}
                onFinish={(values) => void submit(values)}
              >
                <Form.Item label="反馈页面"><Input value={pageTitle} disabled /></Form.Item>
                <Form.Item name="feedback_type" label="反馈类型" rules={[{ required: true }]}>
                  <Select options={Object.entries(typeLabels).map(([value, label]) => ({ value, label }))} />
                </Form.Item>
                <Form.Item name="content" label="反馈内容" rules={[{ required: true, min: 2, message: '请至少输入 2 个字符' }]}>
                  <Input.TextArea rows={7} maxLength={5000} showCount placeholder="请描述遇到的问题、影响范围或改进建议" />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={submitting} icon={<SendOutlined />} block>提交反馈</Button>
              </Form>
            </div>
          ),
        },
        {
          key: 'mine',
          label: '我的反馈',
          children: selected ? (
            <div className="feedback-detail">
              <Button type="link" className="feedback-back" icon={<ArrowLeftOutlined />} onClick={() => setSelectedId(null)}>返回反馈列表</Button>
              <div className="feedback-detail-head">
                <div>
                  <span>{typeLabels[selected.feedback_type] || selected.feedback_type} · {selected.page_title || '平台页面'}</span>
                  <h3>{selected.content}</h3>
                </div>
                <Tag color={(statusLabels[selected.status] || statusLabels.pending).color}>{(statusLabels[selected.status] || statusLabels.pending).label}</Tag>
              </div>
              <div className="feedback-detail-meta">提交于 {formatTime(selected.created_at)}{selected.handler_name ? ` · 处理人 ${selected.handler_name}` : ''}</div>
              {selected.resolution ? <div className="feedback-resolution"><strong>处理结论</strong><p>{selected.resolution}</p></div> : null}
              <Timeline className="feedback-timeline" items={[
                { color: 'blue', children: <><strong>提交反馈</strong><p>{selected.content}</p><small>{formatTime(selected.created_at)}</small></> },
                ...selected.messages.map((item) => ({
                  color: item.author_role === 'admin' ? 'green' : 'blue',
                  children: <><strong>{item.author_role === 'admin' ? '平台回复' : '你补充了说明'} · {item.author_name}</strong><p>{item.content}</p><small>{formatTime(item.created_at)}</small></>,
                })),
              ]} />
              {selected.can_reply ? (
                <div className="feedback-reply-box">
                  <Input.TextArea value={reply} onChange={(event) => setReply(event.target.value)} rows={3} maxLength={5000} placeholder="补充说明或回复处理人" />
                  <Button type="primary" loading={replying} disabled={reply.trim().length < 2} onClick={() => void supplement()}>提交补充</Button>
                </div>
              ) : null}
              {selected.can_withdraw ? (
                <Popconfirm title="撤回后将停止处理，但记录仍会保留。" onConfirm={() => void withdraw(selected)}>
                  <Button danger type="link">撤回反馈</Button>
                </Popconfirm>
              ) : null}
            </div>
          ) : !items ? <Skeleton active /> : items.length ? (
            <div className="feedback-list">
              {items.map((item) => {
                const status = statusLabels[item.status] || statusLabels.pending;
                return (
                  <button type="button" key={item.feedback_id} className="feedback-list-item" onClick={() => setSelectedId(item.feedback_id)}>
                    <div>
                      <span>{typeLabels[item.feedback_type] || item.feedback_type} · {item.page_title || '平台页面'}</span>
                      <strong>{item.content}</strong>
                      <small>更新于 {formatTime(item.updated_at)}</small>
                    </div>
                    <Tag color={status.color}>{status.label}</Tag>
                  </button>
                );
              })}
            </div>
          ) : <Empty description="还没有提交过反馈" />,
        },
      ]} />
    </Drawer>
  );
}
