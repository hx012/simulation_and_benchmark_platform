import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button, Card, Empty, Form, Input, message, Modal, Popconfirm, Select, Space, Table, Tabs, Tag,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  SafetyCertificateOutlined, SearchOutlined, SettingOutlined, TeamOutlined, UserAddOutlined,
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
  admin: '仅管理员访问',
  disabled: '暂不开放',
};

const accessModeColors: Record<ProtectedResourceRecord['access_mode'], string> = {
  normal: 'success', permission: 'processing', admin: 'purple', disabled: 'default',
};

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
  const [adminDirectoryOpen, setAdminDirectoryOpen] = useState(false);
  const [adminSearch, setAdminSearch] = useState('');
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

  const administrators = useMemo(
    () => users.filter((item) => item.role === 'admin'),
    [users],
  );

  const filteredUsers = useMemo(() => {
    const keyword = adminSearch.trim().toLocaleLowerCase();
    if (!keyword) return users;
    return users.filter((item) => (
      item.user_id.toLocaleLowerCase().includes(keyword)
      || item.display_name.toLocaleLowerCase().includes(keyword)
    ));
  }, [adminSearch, users]);

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
        active: true,
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
          disabled={['admin.manage', 'permission.manage'].includes(item.code)}
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
        <Button size="small" icon={<SettingOutlined />} disabled={['admin.manage', 'permission.manage'].includes(item.code)} onClick={() => expandResource(item)}>配置</Button>
      ),
    },
  ];

  const adminColumns: ColumnsType<AdminUserRecord> = [
    { title: '管理员', render: (_, item) => <div><strong>{item.display_name}</strong><small className="permission-table-secondary">{item.user_id}</small></div> },
    { title: '账号状态', render: (_, item) => <Space><Tag color={item.active ? 'success' : 'default'}>{item.active ? '正常' : '已停用'}</Tag>{item.bootstrap_admin ? <Tag color="blue">恢复管理员</Tag> : null}</Space> },
    { title: '管理员密码', dataIndex: 'password_configured', render: (value) => value ? '已配置' : '未配置' },
    { title: '最近登录', dataIndex: 'last_login_at', render: (value: string | null) => value ? new Date(value).toLocaleString('zh-CN') : '尚未登录' },
    {
      title: '操作', width: 170,
      render: (_, item) => <Space><Button size="small" onClick={() => openAdminEditor(item)}>配置</Button><Popconfirm title="移除管理员身份？" description="该用户账号仍会保留，并恢复为普通用户。" okText="移除" cancelText="取消" disabled={item.bootstrap_admin} onConfirm={() => void removeAdministrator(item)}><Button danger size="small" disabled={item.bootstrap_admin}>移除</Button></Popconfirm></Space>,
    },
  ];

  const directoryColumns: ColumnsType<AdminUserRecord> = [
    { title: '用户', render: (_, item) => <div><strong>{item.display_name}</strong><small className="permission-table-secondary">{item.user_id}</small></div> },
    { title: '当前身份', render: (_, item) => <Tag color={item.role === 'admin' ? 'purple' : 'default'}>{item.role === 'admin' ? '管理员' : '普通用户'}</Tag> },
    { title: '操作', width: 130, render: (_, item) => item.role === 'admin' ? <Button size="small" onClick={() => openAdminEditor(item)}>配置管理员</Button> : <Button type="primary" size="small" icon={<UserAddOutlined />} onClick={() => openAdminEditor(item)}>设为管理员</Button> },
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
        dataSource={resources}
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
                ) : <div className="permission-mode-hint">{draft.access_mode === 'normal' ? '所有已登录普通用户均可直接访问。' : draft.access_mode === 'admin' ? '仅管理员登录模式可以访问。' : '该模块将对所有用户隐藏并拒绝访问。'}</div>}
                <div className="permission-resource-actions"><Button onClick={() => setExpandedResources((current) => current.filter((code) => code !== item.code))}>取消</Button><Button type="primary" onClick={() => void saveResource(item)}>保存配置</Button></div>
              </div>
            );
          },
        }}
      />
    </div>
  );

  const administratorManagement = (
    <div className="permission-admin-panel">
      <div className="permission-admin-toolbar"><div><strong>当前管理员</strong><p>这里只展示管理员账号；需要新增管理员时，从完整用户目录中搜索。</p></div><Space><Button onClick={() => setPasswordOpen(true)}>修改我的密码</Button><Button type="primary" icon={<TeamOutlined />} onClick={() => setAdminDirectoryOpen(true)}>配置管理员</Button></Space></div>
      <Table rowKey="user_id" columns={adminColumns} dataSource={administrators} loading={loading} pagination={false} />
    </div>
  );

  return (
    <div className="page-container permission-center-page">
      <PageHeading title="权限管理" subtitle="审批访问申请、配置模块访问方式并维护平台管理员" />
      <Card className="section-card clean-card permission-admin-card">
        <Tabs items={[
          { key: 'requests', label: `待审批申请 (${pendingRequests.length})`, children: pendingRequests.length ? <Table rowKey="request_id" columns={requestColumns} dataSource={pendingRequests} loading={loading} pagination={false} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待审批申请" /> },
          { key: 'resources', label: '模块访问管理', children: resourceManagement },
          { key: 'admins', label: '管理员配置', children: administratorManagement },
        ]} />
      </Card>

      <Modal title="配置管理员" width={760} open={adminDirectoryOpen} footer={null} onCancel={() => { setAdminDirectoryOpen(false); setAdminSearch(''); }}>
        <Input allowClear prefix={<SearchOutlined />} placeholder="搜索姓名或工号" value={adminSearch} onChange={(event) => setAdminSearch(event.target.value)} className="permission-admin-search" />
        <Table rowKey="user_id" columns={directoryColumns} dataSource={filteredUsers} loading={loading} pagination={{ pageSize: 6, hideOnSinglePage: true }} />
      </Modal>

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
