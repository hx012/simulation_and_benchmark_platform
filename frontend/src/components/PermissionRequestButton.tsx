import { Button, message, Tag } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { authApi } from '../api/auth';
import { useAuth } from '../auth/AuthContext';
import { permissionCatalog } from '../auth/permissionCatalog';
import type { PermissionCode } from '../auth/types';

interface PermissionRequestButtonProps {
  permission: PermissionCode;
  reason?: string;
  block?: boolean;
}

export function PermissionRequestButton({
  permission,
  reason = '',
  block = false,
}: PermissionRequestButtonProps) {
  const { user, hasPermission, refreshUser, permissionCatalog: managedCatalog } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const pending = user?.permissionRequests.some(
    (item) => item.permission_code === permission && item.status === 'pending',
  );

  if (hasPermission(permission)) {
    return <Tag color="success">已开通</Tag>;
  }

  if (pending) {
    return <Tag color="processing">审批中</Tag>;
  }

  async function requestAccess() {
    setSubmitting(true);
    try {
      await authApi.requestPermission(permission, reason);
      await refreshUser();
      const name = managedCatalog[permission]?.name || permissionCatalog[permission]?.name || permission;
      message.success(`${name}申请已提交`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Button
      type="primary"
      icon={<LockOutlined />}
      loading={submitting}
      block={block}
      onClick={requestAccess}
    >
      申请权限
    </Button>
  );
}
