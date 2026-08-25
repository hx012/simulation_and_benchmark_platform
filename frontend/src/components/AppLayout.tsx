import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Button, Dropdown, Form, Input, Layout, message, Modal, Select, Typography } from 'antd';
import {
  BarChartOutlined,
  BulbOutlined,
  CommentOutlined,
  ExperimentOutlined,
  GlobalOutlined,
  HomeOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusSquareOutlined,
  SafetyCertificateOutlined,
  UnorderedListOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { collaborationApi, type CommunityLink, type FeedbackPayload } from '../api/collaboration';

const { Header, Sider, Content } = Layout;

type NavItem = {
  path: string;
  label: string;
  icon: ReactNode;
};

type NavGroup = {
  key: string;
  label: string;
  items: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    key: 'overview',
    label: '平台总览',
    items: [{ path: '/home', label: '首页', icon: <HomeOutlined /> }],
  },
  {
    key: 'simulation',
    label: '仿真',
    items: [
      { path: '/simulation/new', label: '新建仿真任务', icon: <PlusSquareOutlined /> },
      { path: '/simulation/tasks', label: '我的任务', icon: <UnorderedListOutlined /> },
    ],
  },
  {
    key: 'benchmark',
    label: 'Benchmark',
    items: [{ path: '/benchmark', label: 'Benchmark 浏览', icon: <BarChartOutlined /> }],
  },
  {
    key: 'performance',
    label: '性能分析',
    items: [{ path: '/performance', label: '分析工作台', icon: <BulbOutlined /> }],
  },
  {
    key: 'collaboration',
    label: '团队与共建',
    items: [
      { path: '/team', label: '团队风采', icon: <TeamOutlined /> },
      { path: '/demands', label: '需求池', icon: <CommentOutlined /> },
    ],
  },
  {
    key: 'account',
    label: '账户',
    items: [{ path: '/permissions', label: '权限中心', icon: <SafetyCertificateOutlined /> }],
  },
];

function isActivePath(current: string, target: string) {
  if (target === '/home') return current === '/home';
  if (target === '/simulation/tasks') return current.startsWith('/simulation/tasks');
  return current.startsWith(target);
}

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    overview: true,
    simulation: true,
    benchmark: true,
    performance: true,
    collaboration: true,
    account: true,
  });
  const [communities, setCommunities] = useState<CommunityLink[]>([]);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackForm] = Form.useForm<FeedbackPayload>();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const pageTitle = useMemo(() => {
    if (location.pathname === '/home') return '首页';
    if (location.pathname === '/simulation/new') return '新建仿真任务';
    if (/^\/simulation\/tasks\/[^/]+\/result$/.test(location.pathname)) return '仿真结果';
    if (/^\/simulation\/tasks\/[^/]+$/.test(location.pathname)) return '任务详情';
    if (location.pathname.startsWith('/simulation/tasks')) return '我的任务';
    if (/^\/benchmark\/chips\/[^/]+\/[^/]+\/benchmarks\/[^/]+$/.test(location.pathname)) return 'Benchmark 详情';
    if (/^\/benchmark\/chips\/[^/]+\/[^/]+$/.test(location.pathname)) return '芯片 Benchmark';
    if (location.pathname.startsWith('/benchmark')) return 'Benchmark 浏览';
    if (location.pathname.startsWith('/performance')) return '性能分析';
    if (location.pathname.startsWith('/team')) return '团队风采';
    if (location.pathname.startsWith('/demands')) return '需求池';
    if (location.pathname.startsWith('/permissions')) return '权限中心';
    return 'AI Chip Platform';
  }, [location.pathname]);

  useEffect(() => {
    void collaborationApi.getPlatformConfig()
      .then((config) => setCommunities(config.communities))
      .catch(() => setCommunities([]));
  }, []);

  async function submitFeedback(values: FeedbackPayload) {
    setFeedbackSubmitting(true);
    try {
      await collaborationApi.submitFeedback({
        ...values,
        page_title: pageTitle,
        page_path: `${location.pathname}${location.search}`,
      });
      message.success('反馈已提交，感谢你的建议');
      feedbackForm.resetFields();
      setFeedbackOpen(false);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '反馈提交失败');
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate('/', { replace: true });
  }

  return (
    <Layout className="app-shell">
      <Sider
        width={252}
        collapsedWidth={76}
        collapsed={collapsed}
        theme="light"
        className="app-sider"
      >
        <button
          type="button"
          className="brand-block brand-home-button"
          onClick={() => navigate('/')}
          title="返回平台展示页"
          aria-label="返回平台展示页"
        >
          <div className="brand-mark"><ExperimentOutlined /></div>
          {!collapsed ? (
            <div className="brand-copy">
              <div className="brand-title">AI Chip Platform</div>
              <div className="brand-subtitle">Simulation · Benchmark</div>
            </div>
          ) : null}
        </button>

        <nav className="sidebar-nav" aria-label="主导航">
          {navGroups.map((group) => {
            const opened = openGroups[group.key] !== false;
            return (
              <div className="sidebar-group" key={group.key}>
                {!collapsed ? (
                  <button
                    type="button"
                    className="sidebar-group-title"
                    onClick={() => setOpenGroups((current) => ({
                      ...current,
                      [group.key]: !opened,
                    }))}
                  >
                    <span>{group.label}</span>
                    <span className={opened ? 'sidebar-caret open' : 'sidebar-caret'}>⌄</span>
                  </button>
                ) : null}

                {(collapsed || opened) ? (
                  <div className="sidebar-group-items">
                    {group.items.map((item) => {
                      const active = isActivePath(location.pathname, item.path);
                      return (
                        <button
                          key={item.path}
                          type="button"
                          title={collapsed ? item.label : undefined}
                          className={active ? 'sidebar-item active' : 'sidebar-item'}
                          onClick={() => navigate(item.path)}
                        >
                          <span className="sidebar-item-icon">{item.icon}</span>
                          {!collapsed ? <span>{item.label}</span> : null}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          })}
        </nav>

        <button
          type="button"
          className="sider-collapse"
          onClick={() => setCollapsed((value) => !value)}
          title={collapsed ? '展开导航' : '收起导航'}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          {!collapsed ? <span>收起导航</span> : null}
        </button>
      </Sider>

      <Layout>
        <Header className="app-header">
          <Typography.Text className="header-page-title">{pageTitle}</Typography.Text>
          <div className="header-user">
            <Dropdown
              trigger={['click']}
              menu={{
                items: communities.map((item) => ({
                  key: item.key,
                  label: item.enabled ? item.name : `${item.name}（暂未配置）`,
                  disabled: !item.enabled,
                  icon: <GlobalOutlined />,
                  onClick: () => {
                    if (item.enabled) window.open(item.url, '_blank', 'noopener,noreferrer');
                  },
                })),
              }}
            >
              <Button type="text" icon={<GlobalOutlined />}>生态社区</Button>
            </Dropdown>
            <Button type="text" icon={<CommentOutlined />} onClick={() => setFeedbackOpen(true)}>意见反馈</Button>
            <span className="internal-badge">内部平台</span>
            <Dropdown
              trigger={['click']}
              menu={{
                items: [
                  {
                    key: 'identity',
                    label: user?.userId || '当前用户',
                    icon: <UserOutlined />,
                    disabled: true,
                  },
                  { type: 'divider' },
                  {
                    key: 'permissions',
                    label: '权限中心',
                    icon: <SafetyCertificateOutlined />,
                    onClick: () => navigate('/permissions'),
                  },
                  { type: 'divider' },
                  {
                    key: 'logout',
                    label: '退出登录',
                    icon: <LogoutOutlined />,
                    onClick: handleLogout,
                  },
                ],
              }}
            >
              <button type="button" className="header-user-button">
                <UserOutlined />
                <span>{user?.userId}</span>
                {user?.authMode === 'admin' ? <span className="admin-mode-badge">管理员</span> : null}
              </button>
            </Dropdown>
          </div>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
      <Modal
        title="意见反馈"
        open={feedbackOpen}
        onCancel={() => setFeedbackOpen(false)}
        onOk={() => feedbackForm.submit()}
        confirmLoading={feedbackSubmitting}
        okText="提交反馈"
      >
        <Form
          form={feedbackForm}
          layout="vertical"
          initialValues={{ feedback_type: 'experience', page_title: '', page_path: '', content: '' }}
          onFinish={(values) => void submitFeedback(values)}
        >
          <Form.Item label="反馈页面"><Input value={pageTitle} disabled /></Form.Item>
          <Form.Item name="feedback_type" label="反馈类型" rules={[{ required: true }]}>
            <Select options={[
              { value: 'experience', label: '体验建议' },
              { value: 'function', label: '功能问题' },
              { value: 'data', label: '数据问题' },
              { value: 'other', label: '其他' },
            ]} />
          </Form.Item>
          <Form.Item name="content" label="反馈内容" rules={[{ required: true, min: 2, message: '请至少输入 2 个字符' }]}>
            <Input.TextArea rows={5} maxLength={5000} showCount placeholder="请描述遇到的问题或改进建议" />
          </Form.Item>
          <div className="feedback-attachment-note">截图和附件将在后续版本支持。</div>
        </Form>
      </Modal>
    </Layout>
  );
}
