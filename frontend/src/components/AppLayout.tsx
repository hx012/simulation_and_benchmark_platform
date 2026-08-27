import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Button, Dropdown, Layout, Typography } from 'antd';
import {
  BarChartOutlined,
  LineChartOutlined,
  BulbOutlined,
  CommentOutlined,
  ExperimentOutlined,
  HomeOutlined,
  LogoutOutlined,
  MenuOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusSquareOutlined,
  QuestionCircleOutlined,
  SafetyCertificateOutlined,
  SolutionOutlined,
  UnorderedListOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { AnalyticsTracker } from './AnalyticsTracker';
import { FeedbackCenterDrawer } from './FeedbackCenterDrawer';
import { SupportGroupModal } from './SupportGroupModal';

const { Header, Sider, Content } = Layout;

type NavItem = {
  path: string;
  label: string;
  icon: ReactNode;
  adminOnly?: boolean;
};

type NavGroup = {
  key: string;
  label: string;
  items: NavItem[];
  adminOnly?: boolean;
};

const navGroups: NavGroup[] = [
  {
    key: 'overview',
    label: '平台总览',
    items: [{ path: '/home', label: '首页', icon: <HomeOutlined /> }],
  },
  {
    key: 'simulation',
    label: '仿真器',
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
    key: 'team',
    label: '团队风采',
    items: [{ path: '/team', label: '团队风采', icon: <TeamOutlined /> }],
  },
  {
    key: 'demands',
    label: '需求池',
    items: [{ path: '/demands', label: '需求列表', icon: <CommentOutlined /> }],
  },
  {
    key: 'management',
    label: '管理中心',
    items: [
      { path: '/permissions', label: '权限中心', icon: <SafetyCertificateOutlined /> },
      { path: '/collaboration-admin', label: '共建管理', icon: <SolutionOutlined />, adminOnly: true },
      { path: '/usage-analytics', label: '使用分析', icon: <LineChartOutlined />, adminOnly: true },
    ],
  },
];

function isActivePath(current: string, target: string) {
  if (target === '/home') return current === '/home';
  if (target === '/simulation/tasks') return current.startsWith('/simulation/tasks');
  return current.startsWith(target);
}

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    overview: true,
    simulation: true,
    benchmark: true,
    performance: true,
    team: true,
    demands: true,
    management: true,
  });
  const [supportOpen, setSupportOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const pageTitle = useMemo(() => {
    if (location.pathname === '/home') return '平台总览';
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
    if (location.pathname.startsWith('/usage-analytics')) return '使用分析';
    if (location.pathname.startsWith('/collaboration-admin')) return '共建管理';
    return 'AI Chip Platform';
  }, [location.pathname]);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

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
        className={mobileNavOpen ? 'app-sider mobile-open' : 'app-sider'}
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
          {navGroups.filter((group) => !group.adminOnly || user?.authMode === 'admin').map((group) => {
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
                    {group.items.filter((item) => !item.adminOnly || user?.authMode === 'admin').map((item) => {
                      const active = isActivePath(location.pathname, item.path);
                      return (
                        <button
                          key={item.path}
                          type="button"
                          title={collapsed ? item.label : undefined}
                          className={active ? 'sidebar-item active' : 'sidebar-item'}
                          onClick={() => {
                            navigate(item.path);
                            setMobileNavOpen(false);
                          }}
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

      {mobileNavOpen ? (
        <button type="button" className="mobile-nav-backdrop" aria-label="关闭导航" onClick={() => setMobileNavOpen(false)} />
      ) : null}

      <Layout>
        <Header className="app-header">
          <div className="header-leading">
            <Button className="mobile-nav-trigger" type="text" icon={<MenuOutlined />} aria-label="打开导航" onClick={() => setMobileNavOpen(true)} />
            <Typography.Text className="header-page-title">{pageTitle}</Typography.Text>
          </div>
          <div className="header-user">
            <Dropdown trigger={['click']} menu={{
              items: [
                { key: 'support-group', label: 'MSKPP 技术支撑群', icon: <QuestionCircleOutlined />, onClick: () => setSupportOpen(true) },
                { key: 'feedback', label: '意见反馈', icon: <CommentOutlined />, onClick: () => setFeedbackOpen(true) },
              ],
            }}>
              <Button type="text" icon={<QuestionCircleOutlined />}>帮助与反馈</Button>
            </Dropdown>
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
          <AnalyticsTracker />
          <Outlet />
        </Content>
      </Layout>
      <FeedbackCenterDrawer
        open={feedbackOpen}
        pageTitle={pageTitle}
        pagePath={`${location.pathname}${location.search}`}
        onClose={() => setFeedbackOpen(false)}
      />
      <SupportGroupModal open={supportOpen} onClose={() => setSupportOpen(false)} />
    </Layout>
  );
}
