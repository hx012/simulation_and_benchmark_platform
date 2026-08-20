import { useEffect, useState } from 'react';
import { Button, Form, Input, message } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArchitectureBackground } from '../../components/ArchitectureBackground';
import { useAuth } from '../../auth/AuthContext';

interface LoginFormValues {
  employeeId: string;
}

export function LoginPage() {
  const [form] = Form.useForm<LoginFormValues>();
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { authenticated, login } = useAuth();

  const defaultEmployeeId = import.meta.env.VITE_DEFAULT_OWNER_ID || '';
  const redirectTo = (location.state as { from?: string } | null)?.from || '/home';

  useEffect(() => {
    if (authenticated && !location.state) {
      navigate('/home', { replace: true });
    }
  }, [authenticated, location.state, navigate]);

  async function handleSubmit(values: LoginFormValues) {
    setSubmitting(true);
    try {
      await login(values.employeeId);
      navigate(redirectTo, { replace: true });
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setSubmitting(false);
    }
  }

  function handlePermissionRequest() {
    message.info('高阶权限申请功能将在权限模块接入后开放');
  }

  return (
    <div className="employee-login-page">
      <ArchitectureBackground variant="login" />
      <main className="employee-login-card">
        <h1>工号登录</h1>
        <p>普通功能可直接使用，高阶能力需申请相应权限</p>
        <Form<LoginFormValues>
          form={form}
          layout="vertical"
          requiredMark={false}
          initialValues={{ employeeId: defaultEmployeeId }}
          onFinish={handleSubmit}
        >
          <Form.Item
            label="工号"
            name="employeeId"
            rules={[{ required: true, message: '请输入工号' }]}
          >
            <Input
              autoFocus
              autoComplete="username"
              placeholder="请输入工号"
              size="large"
            />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            loading={submitting}
            block
            size="large"
            className="employee-login-submit"
          >
            进入平台
          </Button>
        </Form>
        <div className="employee-login-permission-row">
          <span>需要访问受限数据或高阶分析能力？</span>
          <Button type="link" onClick={handlePermissionRequest}>
            申请高阶权限
          </Button>
        </div>
      </main>
    </div>
  );
}
