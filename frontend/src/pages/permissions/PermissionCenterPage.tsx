import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button, Card, Empty, Form, Input, message, Modal, Popconfirm, Select, Space, Table, Tabs, Tag,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  SafetyCertificateOutlined, SearchOutlined, SettingOutlined, StopOutlined,
  UnlockOutlined, UserAddOutlined,
} from '@ant-design/icons';
import { authApi } from '../../api/auth';
import { useAuth } from '../../auth/AuthContext';
import type {
  AdminUserRecord, PermissionCode, PermissionRequestRecord, ProtectedResourceRecord,
} from '../../auth/types';
import { PageHeading } from '../../components/PageHeading';
import { PermissionRequestButton } from '../../components/PermissionRequestButton';

const accessModeLabels: Record<ProtectedResourceRecord['access_mode'], string> = {
  normal: '普通用户可访问',
  permission: '申请后访问',
  advanced: '高级用户可访问',
  admin: '仅管理员访问',
  disabled: '暂不开放',
};

const accessModeColors: Record<ProtectedResourceRecord['access_mode'], string> = {
  normal: 'success', permission: 'processing', advanced: 'gold', admin: 'purple', disabled: 'default',
};

const fixedAdminResources = new Set(['admin.manage', 'permission.manage', 'analytics.usage']);
const resourceDisplayOrder = [
  'simulation.task',
  'simulation.log',
  'benchmark.view',
  'performance.view',
  'team.view',
  'demand.view',
  'analytics.usage',
  'permission.manage',
  'admin.manage',
];

type AdminFormValues = {
  display_name: string;
  password?: string;
};

type PasswordFormValues = {
  currentPassword: string;
  newPassword: string;
};

export function PermissionCenterPage() {
  const { user, refreshUser, permissionCatalog } = useAuth();
  const isAdmin = user?.authMode === 'admin';
  const [pendingRequests, setPendingRequests] = useState<PermissionRequestRecord[]>([]);
  const [resources, setResources] = useState<ProtectedResourceRecord[]>([]);
  const [users, setUsers] = useState<AdminUserRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [resourceDrafts, setResourceDrafts] = useState<Record<string, ProtectedResourceRecord>>({});
  const [expandedResources, setExpandedResources] = useState<string[]>([]);
  const [userSearch, setUserSearch] = useState('');
  const [userRoleFilter, setUserRoleFilter] = useState<'all' | 'admin' | 'advanced' | 'team' | 'normal'>('all');
  const [userStatusFilter, setUserStatusFilter] = useState<'all' | 'active' | 'blocked'>('all');
  const [adminEditing, setAdminEditing] = useState<AdminUserRecord | null>(null);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [adminForm] = Form.useForm<AdminFormValues>();
  const [passwordForm] = Form.useForm<PasswordFormValues>();

  const personalPermissions = useMemo(
    () => Object.values(permissionCatalog).filter((item) => (
      item.active && (item.code === 'normal' || item.requestable)
    )),
    [permissionCatalog],
  );

  const orderedResources = useMemo(() => {
    const order = new Map(resourceDisplayOrder.map((code, index) => [code, index]));
    return [...resources].sort((left, right) => (
      (order.get(left.code) ?? resourceDisplayOrder.length)
      - (order.get(right.code) ?? resourceDisplayOrder.length)
      || left.name.localeCompare(right.name, 'zh-CN')
    ));
  }, [resources]);

  const filteredUsers = useMemo(() => {
    const keyword = userSearch.trim().toLocaleLowerCase();
    return [...users]
      .sort((left, right) => (
        (left.role === 'admin' ? 0 : left.is_team_member ? 1 : left.is_advanced_user ? 2 : 3)
        - (right.role === 'admin' ? 0 : right.is_team_member ? 1 : right.is_advanced_user ? 2 : 3)
        || left.user_id.localeCompare(right.user_id, 'zh-CN')
      ))
      .filter((item) => (
        (!keyword
          || item.user_id.toLocaleLowerCase().includes(keyword)
          || item.display_name.toLocaleLowerCase().includes(keyword))
        && (userRoleFilter === 'all'
          || (userRoleFilter === 'admin' && item.role === 'admin')
          || (userRoleFilter === 'advanced' && item.is_advanced_user)
          || (userRoleFilter === 'team' && item.is_team_member)
          || (userRoleFilter === 'normal' && item.role !== 'admin' && !item.is_advanced_user && !item.is_team_member))
        && (userStatusFilter === 'all'
          || (userStatusFilter === 'active' ? item.active : !item.active))
      ));
  }, [userRoleFilter, userSearch, userStatusFilter, users]);

  const loadAdminData = useCallback(async () => {
    if (!isAdmin) return;
    setLoading(true);
    try {
      const [requests, nextResources, nextUsers] = await Promise.all([
        authApi.listPendingRequests(), authApi.listResources(), authApi.listUsers(),
      ]);
      setPendingRequests(requests);
      setResources(nextResources);
      setUsers(nextUsers);
      setResourceDrafts(Object.fromEntries(nextResources.map((item) => [item.code, item])));
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => { void loadAdminData(); }, [loadAdminData]);

  async function review(item: PermissionRequestRecord, decision: 'approved' | 'rejected') {
    try {
      await authApi.reviewRequest(item.request_id, decision);
      message.success(decision === 'approved' ? '权限已批准' : '申请已拒绝');
      await Promise.all([loadAdminData(), refreshUser()]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  function expandResource(item: ProtectedResourceRecord) {
    setResourceDrafts((current) => ({ ...current, [item.code]: current[item.code] || item }));
    setExpandedResources((current) => current.includes(item.code) ? current : [...current, item.code]);
  }

  function changeAccessMode(item: ProtectedResourceRecord, accessMode: ProtectedResourceRecord['access_mode']) {
    const draft = resourceDrafts[item.code] || item;
    setResourceDrafts((current) => ({ ...current, [item.code]: { ...draft, access_mode: accessMode } }));
    expandResource(item);
  }

  async function saveResource(item: ProtectedResourceRecord) {
    const draft = resourceDrafts[item.code] || item;
    try {
      await authApi.updateResource(draft);
      message.success(`${draft.name}访问方式已更新`);
      setExpandedResources((current) => current.filter((code) => code !== item.code));
      await Promise.all([loadAdminData(), refreshUser()]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  function openAdminEditor(item: AdminUserRecord) {
    setAdminEditing(item);
    adminForm.setFieldsValue({ display_name: item.display_name, password: '' });
  }

  async function saveAdministrator() {
    if (!adminEditing) return;
    try {
      const values = await adminForm.validateFields();
      await authApi.updateUser(adminEditing.user_id, {
        role: 'admin',
        display_name: values.display_name,
        password: values.password || undefined,
        active: adminEditing.active,
      });
      message.success(`${values.display_name || adminEditing.user_id}已设为管理员`);
      setAdminEditing(null);
      adminForm.resetFields();
      await loadAdminData();
    } catch (error) {
      if (error instanceof Error) message.error(error.message);
    }
  }

  async function removeAdministrator(item: AdminUserRecord) {
    try {
      await authApi.updateUser(item.user_id, {
        role: 'normal', display_name: item.display_name, active: item.active,
      });
      message.success(`已移除 ${item.display_name} 的管理员身份`);
      await loadAdminData();
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  async function setUserActive(item: AdminUserRecord, active: boolean) {
    try {
      await authApi.updateUser(item.user_id, {
        role: item.role,
        display_name: item.display_name,
        active,
        is_team_member: item.is_team_member,
        is_advanced_user: item.is_advanced_user,
      });
      message.success(active ? `已解除 ${item.display_name} 的登录屏蔽` : `已屏蔽 ${item.display_name} 登录`);
      await loadAdminData();
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  async function setTeamMember(item: AdminUserRecord, enabled: boolean) {
    try {
      await authApi.updateUser(item.user_id, {
        role: item.role,
        display_name: item.display_name,
        active: item.active,
        is_team_member: enabled,
        is_advanced_user: item.is_advanced_user,
      });
      message.success(enabled ? `已将 ${item.display_name} 标记为团队成员` : `已取消 ${item.display_name} 的团队成员标签`);
      await loadAdminData();
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  async function setAdvancedUser(item: AdminUserRecord, enabled: boolean) {
    try {
      await authApi.updateUser(item.user_id, {
        role: item.role,
        display_name: item.display_name,
        active: item.active,
        is_team_member: item.is_team_member,
        is_advanced_user: enabled,
      });
      message.success(enabled ? `已将 ${item.display_name} 设为高级用户` : `已取消 ${item.display_name} 的高级用户身份`);
      await loadAdminData();
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    }
  }

  async function savePassword() {
    try {
      const values = await passwordForm.validateFields();
      await authApi.changePassword(values.currentPassword, values.newPassword);
      passwordForm.resetFields();
      setPasswordOpen(false);
      message.success('管理员密码已修改');
    } catch (error) {
      if (error instanceof Error) message.error(error.message);
    }
  }

  const requestColumns: ColumnsType<PermissionRequestRecord> = [
    { title: '申请人', render: (_, item) => <div><strong>{item.display_name}</strong><small className="permission-table-secondary">{item.user_id}</small></div> },
    { title: '申请模块', dataIndex: 'permission_code', render: (value: PermissionCode) => permissionCatalog[value]?.name || value },
    { title: '申请理由', dataIndex: 'reason', render: (value: string) => value || '未填写' },
    { title: '操作', width: 160, render: (_, item) => <Space><Button type="primary" size="small" onClick={() => void review(item, 'approved')}>批准</Button><Button size="small" onClick={() => void review(item, 'rejected')}>拒绝</Button></Space> },
  ];

  const resourceColumns: ColumnsType<ProtectedResourceRecord> = [
    {
      title: '模块',
      render: (_, item) => <div className="permission-resource-name"><strong>{item.name}</strong><small>{item.description}</small></div>,
    },
    {
      title: '访问方式', width: 210,
      render: (_, item) => (
        <Select
          value={(resourceDrafts[item.code] || item).access_mode}
          disabled={fixedAdminResources.has(item.code)}
          options={Object.entries(accessModeLabels).map(([value, label]) => ({ value, label }))}
          onChange={(value) => changeAccessMode(item, value)}
        />
      ),
    },
    {
      title: '状态', width: 150,
      render: (_, item) => <Tag color={accessModeColors[(resourceDrafts[item.code] || item).access_mode]}>{accessModeLabels[(resourceDrafts[item.code] || item).access_mode]}</Tag>,
    },
    {
      title: '操作', width: 100,
      render: (_, item) => (
        <Button size="small" icon={<SettingOutlined />} disabled={fixedAdminResources.has(item.code)} onClick={() => expandResource(item)}>配置</Button>
      ),
    },
  ];

  const userColumns: ColumnsType<AdminUserRecord> = [
    { title: '用户', render: (_, item) => <div><strong>{item.display_name}</strong><small className="permission-table-secondary">{item.user_id}</small></div> },
    {
      title: '身份', width: 130,
      render: (_, item) => <Space wrap><Tag color={item.role === 'admin' ? 'purple' : 'default'}>{item.role === 'admin' ? '管理员' : '普通用户'}</Tag>{item.is_advanced_user ? <Tag color="gold">高级用户</Tag> : null}{item.is_team_member ? <Tag color="cyan">团队成员</Tag> : null}{item.bootstrap_admin ? <Tag color="blue">恢复管理员</Tag> : null}</Space>,
    },
    {
      title: '登录状态', width: 120,
      render: (_, item) => <Tag color={item.active ? 'success' : 'error'}>{item.active ? '正常' : '已屏蔽'}</Tag>,
    },
    {
      title: '操作', width: 350,
      render: (_, item) => {
        const isSelf = item.user_id === user?.userId;
        const blockDisabled = item.bootstrap_admin || isSelf;
        return (
          <Space wrap>
            {item.is_advanced_user ? (
              <Popconfirm title="取消高级用户身份？" description="该用户将不能再在页面内修改 Chip Config。" okText="确认" cancelText="取消" onConfirm={() => void setAdvancedUser(item, false)}>
                <Button size="small">取消高级用户</Button>
              </Popconfirm>
            ) : <Button size="small" onClick={() => void setAdvancedUser(item, true)}>设为高级用户</Button>}
            {item.is_team_member ? (
              <Popconfirm title="取消团队成员标签？" description="历史成果保留，但该用户将不能再访问完整成果档案。" okText="确认" cancelText="取消" onConfirm={() => void setTeamMember(item, false)}>
                <Button size="small">取消团队成员</Button>
              </Popconfirm>
            ) : <Button size="small" onClick={() => void setTeamMember(item, true)}>设为团队成员</Button>}
            {item.role === 'admin' ? (
              <>
                <Button size="small" onClick={() => openAdminEditor(item)}>配置管理员</Button>
                <Popconfirm title="移除管理员身份？" description="该用户账号仍会保留，并恢复为普通用户。" okText="移除" cancelText="取消" disabled={item.bootstrap_admin || isSelf} onConfirm={() => void removeAdministrator(item)}>
                  <Button danger size="small" disabled={item.bootstrap_admin || isSelf}>移除管理员</Button>
                </Popconfirm>
              </>
            ) : (
              <Button type="primary" size="small" icon={<UserAddOutlined />} disabled={!item.active} onClick={() => openAdminEditor(item)}>设为管理员</Button>
            )}
            {item.active ? (
              <Popconfirm
                title="屏蔽该用户登录？"
                description="已有会话将立即失效，历史任务和数据不会删除。"
                okText="确认屏蔽"
                cancelText="取消"
                disabled={blockDisabled}
                onConfirm={() => void setUserActive(item, false)}
              >
                <Button danger size="small" icon={<StopOutlined />} disabled={blockDisabled}>屏蔽登录</Button>
              </Popconfirm>
            ) : (
              <Popconfirm title="解除登录屏蔽？" okText="解除屏蔽" cancelText="取消" onConfirm={() => void setUserActive(item, true)}>
                <Button size="small" icon={<UnlockOutlined />}>解除屏蔽</Button>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  if (!isAdmin) {
    return (
      <div className="page-container permission-center-page">
        <PageHeading title="个人权限" subtitle="查看当前权限，并按工作需要申请受限模块的访问权限" />
        <Card className="section-card clean-card permission-personal-panel">
          <div className="permission-personal-list">
            {personalPermissions.map((item) => {
              const owned = user?.permissions.includes(item.code);
              return (
                <div className="permission-personal-row" key={item.code}>
                  <div className="permission-row-icon"><SafetyCertificateOutlined /></div>
                  <div className="permission-row-copy"><strong>{item.name}</strong><p>{item.description}</p></div>
                  <div className="permission-row-action">{owned ? <Tag color="success">已开通</Tag> : item.requestable ? <PermissionRequestButton permission={item.code} reason="从权限中心申请" /> : <Tag>无需申请</Tag>}</div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    );
  }

  const resourceManagement = (
    <div className="permission-resource-panel">
      <div className="permission-section-intro"><div><strong>统一配置各模块的访问方式</strong><p>保存配置后立即生效，无需修改代码。选择“申请后访问”时可查看申请说明和已授权用户。</p></div></div>
      <Table
        rowKey="code"
        columns={resourceColumns}
        dataSource={orderedResources}
        loading={loading}
        pagination={false}
        expandable={{
          expandedRowKeys: expandedResources,
          showExpandColumn: false,
          onExpandedRowsChange: (keys) => setExpandedResources(keys.map(String)),
          expandedRowRender: (item) => {
            const draft = resourceDrafts[item.code] || item;
            return (
              <div className="permission-resource-editor">
                <div className="permission-resource-editor-main">
                  <label htmlFor={`resource-description-${item.code}`}>模块及申请说明</label>
                  <Input.TextArea id={`resource-description-${item.code}`} rows={3} value={draft.description} onChange={(event) => setResourceDrafts((current) => ({ ...current, [item.code]: { ...draft, description: event.target.value } }))} />
                  <small>该说明会展示给需要申请权限的普通用户。</small>
                </div>
                {draft.access_mode === 'permission' ? (
                  <div className="permission-authorized-users">
                    <div><strong>已授权用户</strong><Tag>{item.authorized_users.length} 人</Tag></div>
                    <div className="permission-authorized-tags">{item.authorized_users.length ? item.authorized_users.map((authorizedUser) => <Tag key={authorizedUser.user_id}>{authorizedUser.display_name} · {authorizedUser.user_id}</Tag>) : <span>暂无已授权用户，用户提交申请后由管理员审批。</span>}</div>
                  </div>
                ) : <div className="permission-mode-hint">{draft.access_mode === 'normal' ? '所有已登录用户均可直接访问。' : draft.access_mode === 'advanced' ? '高级用户、团队成员和管理员可以访问；普通用户不可访问。' : draft.access_mode === 'admin' ? '仅管理员登录模式可以访问。' : '该模块将对所有用户隐藏并拒绝访问。'}</div>}
                <div className="permission-resource-actions"><Button onClick={() => setExpandedResources((current) => current.filter((code) => code !== item.code))}>取消</Button><Button type="primary" onClick={() => void saveResource(item)}>保存配置</Button></div>
              </div>
            );
          },
        }}
      />
    </div>
  );

  const userManagement = (
    <div className="permission-user-panel">
      <div className="permission-admin-toolbar"><div><strong>统一管理平台用户</strong><p>按管理员、团队成员、高级用户、普通用户排序；身份可叠加，高级用户可以在页面内修改 Chip Config。</p></div><Button onClick={() => setPasswordOpen(true)}>修改我的密码</Button></div>
      <div className="permission-user-filters">
        <Input allowClear prefix={<SearchOutlined />} placeholder="搜索姓名或工号" value={userSearch} onChange={(event) => setUserSearch(event.target.value)} />
        <Select value={userRoleFilter} onChange={setUserRoleFilter} options={[{ value: 'all', label: '全部身份' }, { value: 'admin', label: '管理员' }, { value: 'advanced', label: '高级用户' }, { value: 'team', label: '团队成员' }, { value: 'normal', label: '普通用户' }]} />
        <Select value={userStatusFilter} onChange={setUserStatusFilter} options={[{ value: 'all', label: '全部状态' }, { value: 'active', label: '正常' }, { value: 'blocked', label: '已屏蔽' }]} />
      </div>
      <Table rowKey="user_id" columns={userColumns} dataSource={filteredUsers} loading={loading} pagination={{ pageSize: 10, hideOnSinglePage: true }} scroll={{ x: 900 }} />
    </div>
  );

  return (
    <div className="page-container permission-center-page">
      <PageHeading title="权限管理" subtitle="审批访问申请、配置模块访问方式并管理平台用户" />
      <Card className="section-card clean-card permission-admin-card">
        <Tabs items={[
          { key: 'requests', label: `待审批申请 (${pendingRequests.length})`, children: pendingRequests.length ? <Table rowKey="request_id" columns={requestColumns} dataSource={pendingRequests} loading={loading} pagination={false} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待审批申请" /> },
          { key: 'resources', label: '模块访问管理', children: resourceManagement },
          { key: 'users', label: '用户管理', children: userManagement },
        ]} />
      </Card>

      <Modal title={adminEditing?.role === 'admin' ? '配置管理员' : '设为管理员'} open={Boolean(adminEditing)} onCancel={() => { setAdminEditing(null); adminForm.resetFields(); }} onOk={() => void saveAdministrator()} okText="保存">
        <Form form={adminForm} layout="vertical">
          <Form.Item label="用户"><Input value={adminEditing ? `${adminEditing.display_name} · ${adminEditing.user_id}` : ''} disabled /></Form.Item>
          <Form.Item label="显示名称" name="display_name" rules={[{ required: true, message: '请输入显示名称' }]}><Input /></Form.Item>
          <Form.Item label={adminEditing?.password_configured ? '重置管理员密码（选填）' : '管理员密码'} name="password" extra="至少 8 位，并同时包含字母和数字" rules={adminEditing?.password_configured ? [] : [{ required: true, message: '首次设为管理员时需要配置密码' }, { min: 8, message: '密码至少 8 位' }]}><Input.Password autoComplete="new-password" /></Form.Item>
        </Form>
      </Modal>

      <Modal title="修改管理员密码" open={passwordOpen} onCancel={() => setPasswordOpen(false)} onOk={() => void savePassword()}>
        <Form form={passwordForm} layout="vertical"><Form.Item label="当前密码" name="currentPassword" rules={[{ required: true }]}><Input.Password /></Form.Item><Form.Item label="新密码" name="newPassword" rules={[{ required: true, min: 8, message: '密码至少 8 位' }]}><Input.Password /></Form.Item></Form>
      </Modal>
    </div>
  );
}
