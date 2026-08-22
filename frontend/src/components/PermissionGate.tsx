import type { ReactNode } from 'react';
import { Card, Result } from 'antd';
import { useAuth } from '../auth/AuthContext';
import { permissionCatalog } from '../auth/permissionCatalog';
import type { PermissionCode } from '../auth/types';
import { PermissionRequestButton } from './PermissionRequestButton';

interface PermissionGateProps {
  resource: string;
  fallbackPermission: PermissionCode;
  children: ReactNode;
}

export function PermissionGate({ resource, fallbackPermission, children }: PermissionGateProps) {
  const { user, hasResource, permissionCatalog: managedCatalog } = useAuth();
  if (hasResource(resource)) return children;

  const permission = user?.resourcePermissions[resource]?.[0] || fallbackPermission;
  const item = managedCatalog[permission] || permissionCatalog[permission] || {
    name: permission,
    description: '该内容需要额外权限。',
  };
  return (
    <div className="page-container">
      <Card className="permission-gate-card">
        <Result
          status="403"
          title={item.name}
          subTitle={`${item.description} 当前账号尚未获得该权限。`}
          extra={(
            <PermissionRequestButton
              permission={permission}
              reason="从受限内容页面申请"
            />
          )}
        />
      </Card>
    </div>
  );
}
