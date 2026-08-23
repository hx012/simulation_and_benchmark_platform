import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button, Card, Form, Input, message, Modal, Select, Space, Switch, Table, Tabs, Tag,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import { authApi } from '../../api/auth';
import { useAuth } from '../../auth/AuthContext';
import type {
  AdminUserRecord, PermissionCatalogItem, PermissionCode, PermissionRequestRecord,
  ProtectedResourceRecord,
} from '../../auth/types';
import { PageHeading } from '../../components/PageHeading';
import { PermissionRequestButton } from '../../components/PermissionRequestButton';

const accessModeLabels = {
  normal: '普通用户', permission: '指定权限', admin: '仅管理员', disabled: '未开放',
};

export function PermissionCenterPage() {
  const { user, refreshUser, permissionCatalog, refreshPermissionCatalog } = useAuth();
  const [pendingRequests, setPendingRequests] = useState<PermissionRequestRecord[]>([]);
  const [resources, setResources] = useState<ProtectedResourceRecord[]>([]);
  const [users, setUsers] = useState<AdminUserRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [permissionEditing, setPermissionEditing] = useState<PermissionCatalogItem | null>(null);
  const [resourceEditing, setResourceEditing] = useState<ProtectedResourceRecord | null>(null);
  const [userEditing, setUserEditing] = useState<AdminUserRecord | null>(null);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [permissionForm] = Form.useForm<PermissionCatalogItem>();
  const [resourceForm] = Form.useForm<ProtectedResourceRecord>();
  const [userForm] = Form.useForm();
  const [passwordForm] = Form.useForm();

  const catalogItems = useMemo(
    () => Object.values(permissionCatalog).filter((item) => item.active),
    [permissionCatalog],
  );

  const loadAdminData = useCallback(async () => {
    if (user?.role !== 'admin') return;
    setLoading(true);
    try {
      const [requests, nextResources, nextUsers] = await Promise.all([
        authApi.listPendingRequests(), authApi.listResources(), authApi.listUsers(),
      ]);
      setPendingRequests(requests);
      setResources(nextResources);
      setUsers(nextUsers);
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }, [user?.role]);

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

  const requestColumns: ColumnsType<PermissionRequestRecord> = [
    { title: '申请人', dataIndex: 'display_name' },
    { title: '申请权限', dataIndex: 'permission_code', render: (value: PermissionCode) => permissionCatalog[value]?.name || value },
    { title: '申请理由', dataIndex: 'reason', render: (value: string) => value || '—' },
    { title: '操作', render: (_, item) => <Space><Button type="primary" size="small" onClick={() => review(item, 'approved')}>批准</Button><Button danger size="small" onClick={() => review(item, 'rejected')}>拒绝</Button></Space> },
  ];

  const resourceColumns: ColumnsType<ProtectedResourceRecord> = [
    { title: '模块', dataIndex: 'name' },
    { title: '资源代码', dataIndex: 'code' },
    { title: '访问方式', dataIndex: 'access_mode', render: (value: ProtectedResourceRecord['access_mode']) => <Tag>{accessModeLabels[value]}</Tag> },
    { title: '所需 Permission Set', dataIndex: 'permission_codes', render: (values: string[]) => values.length ? values.map((value) => <Tag key={value}>{permissionCatalog[value]?.name || value}</Tag>) : '—' },
    { title: '操作', render: (_, item) => <Button size="small" disabled={['admin.manage', 'permission.manage'].includes(item.code)} onClick={() => { setResourceEditing(item); resourceForm.setFieldsValue(item); }}>配置</Button> },
  ];

  const permissionColumns: ColumnsType<PermissionCatalogItem> = [
    { title: '名称', dataIndex: 'name' },
    { title: '代码', dataIndex: 'code' },
    { title: '可申请', dataIndex: 'requestable', render: (value) => value ? '是' : '否' },
    { title: '状态', dataIndex: 'active', render: (value) => <Tag color={value ? 'success' : 'default'}>{value ? '启用' : '停用'}</Tag> },
    { title: '操作', render: (_, item) => <Button size="small" onClick={() => { setPermissionEditing(item); permissionForm.setFieldsValue(item); }}>编辑</Button> },
  ];

  const userColumns: ColumnsType<AdminUserRecord> = [
    { title: '工号', dataIndex: 'user_id' },
    { title: '显示名称', dataIndex: 'display_name' },
    { title: '角色', dataIndex: 'role', render: (value) => <Tag color={value === 'admin' ? 'purple' : 'default'}>{value === 'admin' ? '管理员' : '普通用户'}</Tag> },
    { title: '管理员密码', dataIndex: 'password_configured', render: (value) => value ? '已配置' : '未配置' },
    { title: '操作', render: (_, item) => <Button size="small" onClick={() => { setUserEditing(item); userForm.setFieldsValue({ employeeId: item.user_id, display_name: item.display_name, role: item.role, active: item.active, password: '' }); }}>配置</Button> },
  ];

  async function savePermissionSet() {
    try {
      const values = await permissionForm.validateFields();
      await authApi.updatePermissionSet({ ...permissionEditing!, ...values });
      await refreshPermissionCatalog();
      setPermissionEditing(null);
      message.success('Permission Set 已更新');
    } catch (error) {
      if (error instanceof Error) message.error(error.message);
    }
  }

  async function saveResource() {
    try {
      const values = await resourceForm.validateFields();
      await authApi.updateResource({ ...resourceEditing!, ...values });
      await loadAdminData();
      setResourceEditing(null);
      message.success('模块访问策略已更新');
    } catch (error) {
      if (error instanceof Error) message.error(error.message);
    }
  }

  async function saveUser() {
    try {
      const values = await userForm.validateFields();
      await authApi.updateUser(values.employeeId, {
        role: values.role, display_name: values.display_name,
        password: values.password || undefined, active: values.active,
      });
      await loadAdminData();
      setUserEditing(null);
      message.success('用户角色已更新');
    } catch (error) {
      if (error instanceof Error) message.error(error.message);
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

  return (
    <div className="page-container permission-center-page">
      <PageHeading title="权限中心" subtitle="查看当前权限，并按工作需要申请受限内容访问权限" />
      <div className="permission-card-grid">
        {catalogItems.map((item) => (
          <Card className="permission-card" key={item.code}>
            <div className="permission-card-icon"><SafetyCertificateOutlined /></div>
            <div className="permission-card-content"><h2>{item.name}</h2><p>{item.description}</p></div>
            {item.code === 'normal' || user?.permissions.includes(item.code) ? <Tag color="success">已开通</Tag> : item.requestable ? <PermissionRequestButton permission={item.code} reason="从权限中心申请" /> : <Tag>不可申请</Tag>}
          </Card>
        ))}
      </div>

      {user?.role === 'admin' ? (
        <Card className="section-card clean-card permission-admin-card" title="权限管理" extra={<Button onClick={() => setPasswordOpen(true)}>修改管理员密码</Button>}>
          <Tabs items={[
            { key: 'requests', label: `待审批申请 (${pendingRequests.length})`, children: <Table rowKey="request_id" columns={requestColumns} dataSource={pendingRequests} loading={loading} pagination={false} /> },
            { key: 'resources', label: '模块访问策略', children: <Table rowKey="code" columns={resourceColumns} dataSource={resources} loading={loading} pagination={false} /> },
            { key: 'sets', label: 'Permission Sets', children: <Table rowKey="code" columns={permissionColumns} dataSource={Object.values(permissionCatalog)} loading={loading} pagination={false} /> },
            { key: 'admins', label: '管理员配置', children: <><Button type="primary" style={{ marginBottom: 12 }} onClick={() => { const blank = { user_id: '', display_name: '', role: 'admin' as const, active: true, password_configured: false, last_login_at: null }; setUserEditing(blank); userForm.setFieldsValue({ employeeId: '', display_name: '', role: 'admin', active: true, password: '' }); }}>配置新管理员</Button><Table rowKey="user_id" columns={userColumns} dataSource={users} loading={loading} pagination={false} /></> },
          ]} />
        </Card>
      ) : null}

      <Modal title="编辑 Permission Set" open={Boolean(permissionEditing)} onCancel={() => setPermissionEditing(null)} onOk={() => void savePermissionSet()}>
        <Form form={permissionForm} layout="vertical"><Form.Item label="名称" name="name" rules={[{ required: true }]}><Input /></Form.Item><Form.Item label="说明" name="description"><Input.TextArea rows={3} /></Form.Item><Form.Item label="允许用户申请" name="requestable" valuePropName="checked"><Switch /></Form.Item><Form.Item label="启用" name="active" valuePropName="checked"><Switch disabled={permissionEditing?.system_managed} /></Form.Item></Form>
      </Modal>
      <Modal title="配置模块访问策略" open={Boolean(resourceEditing)} onCancel={() => setResourceEditing(null)} onOk={() => void saveResource()}>
        <Form form={resourceForm} layout="vertical"><Form.Item label="模块名称" name="name" rules={[{ required: true }]}><Input /></Form.Item><Form.Item label="说明" name="description"><Input.TextArea rows={3} /></Form.Item><Form.Item label="访问方式" name="access_mode" rules={[{ required: true }]}><Select options={Object.entries(accessModeLabels).map(([value, label]) => ({ value, label }))} /></Form.Item><Form.Item noStyle shouldUpdate={(before, after) => before.access_mode !== after.access_mode}>{({ getFieldValue }) => getFieldValue('access_mode') === 'permission' ? <Form.Item label="所需 Permission Set" name="permission_codes" rules={[{ required: true, type: 'array', min: 1 }]}><Select mode="multiple" options={catalogItems.filter((item) => item.code !== 'normal').map((item) => ({ value: item.code, label: item.name }))} /></Form.Item> : null}</Form.Item></Form>
      </Modal>
      <Modal title="配置用户角色" open={Boolean(userEditing)} onCancel={() => setUserEditing(null)} onOk={() => void saveUser()}>
        <Form form={userForm} layout="vertical"><Form.Item label="工号" name="employeeId" rules={[{ required: true }]}><Input disabled={Boolean(userEditing?.user_id)} /></Form.Item><Form.Item label="显示名称" name="display_name"><Input /></Form.Item><Form.Item label="角色" name="role" rules={[{ required: true }]}><Select options={[{ value: 'normal', label: '普通用户' }, { value: 'admin', label: '管理员' }]} /></Form.Item><Form.Item label="管理员密码" name="password" extra="新增管理员或重置密码时填写，至少 8 位且包含字母和数字"><Input.Password autoComplete="new-password" /></Form.Item><Form.Item label="启用账号" name="active" valuePropName="checked"><Switch /></Form.Item></Form>
      </Modal>
      <Modal title="修改管理员密码" open={passwordOpen} onCancel={() => setPasswordOpen(false)} onOk={() => void savePassword()}>
        <Form form={passwordForm} layout="vertical"><Form.Item label="当前密码" name="currentPassword" rules={[{ required: true }]}><Input.Password /></Form.Item><Form.Item label="新密码" name="newPassword" rules={[{ required: true, min: 8, message: '密码至少 8 位' }]}><Input.Password /></Form.Item></Form>
      </Modal>
    </div>
  );
}
