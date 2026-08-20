import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Dropdown, Layout, Typography } from 'antd';
import {
  BarChartOutlined,
  ExperimentOutlined,
  HomeOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlusSquareOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

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
  });
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
    return 'AI Chip Platform';
  }, [location.pathname]);

  function handleLogout() {
    logout();
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
            <span className="internal-badge">内部平台</span>
            <Dropdown
              trigger={['click']}
              menu={{
                items: [
                  {
                    key: 'identity',
                    label: user?.displayName || user?.userId || '当前用户',
                    icon: <UserOutlined />,
                    disabled: true,
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
                <span>{user?.displayName || user?.userId}</span>
              </button>
            </Dropdown>
          </div>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
