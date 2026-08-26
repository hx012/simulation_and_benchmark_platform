import { useEffect, useState } from 'react';
import { Alert, Button, Form, Input, message, Segmented } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../../api/auth';
import w3Logo from '../../assets/w3-logo.png';
import { ArchitectureBackground } from '../../components/ArchitectureBackground';
import { useAuth } from '../../auth/AuthContext';

interface LoginFormValues {
  employeeId: string;
  password?: string;
}

export function LoginPage() {
  const [form] = Form.useForm<LoginFormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [w3Redirecting, setW3Redirecting] = useState(false);
  const [authMode, setAuthMode] = useState<'w3' | 'admin'>('w3');
  const navigate = useNavigate();
  const location = useLocation();
  const { authenticated, initializing, login } = useAuth();

  const defaultEmployeeId = import.meta.env.VITE_DEFAULT_OWNER_ID || '';
  const redirectTo = (location.state as { from?: string } | null)?.from || '/home';
  const oauthError = new URLSearchParams(location.search).get('oauth_error');

  useEffect(() => {
    if (!initializing && authenticated) {
      navigate(redirectTo, { replace: true });
    }
  }, [authenticated, initializing, navigate, redirectTo]);

  async function handleSubmit(values: LoginFormValues) {
    setSubmitting(true);
    try {
      await login(values.employeeId, 'admin', values.password);
      navigate(redirectTo, { replace: true });
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setSubmitting(false);
    }
  }

  function startW3Login() {
    if (w3Redirecting) return;
    setW3Redirecting(true);
    window.location.assign(authApi.w3LoginUrl(redirectTo));
  }

  return (
    <div className="employee-login-page">
      <ArchitectureBackground variant="login" />
      <main className="employee-login-card">
        <h1>登录平台</h1>
        <Segmented
          block
          className="login-mode-switch"
          value={authMode}
          options={[
            { label: 'W3 登录', value: 'w3' },
            { label: '管理员登录', value: 'admin' },
          ]}
          onChange={(value) => {
            setAuthMode(value as 'w3' | 'admin');
            form.setFieldValue('password', '');
          }}
        />
        {oauthError ? <Alert type="error" showIcon message={oauthError} style={{ marginBottom: 16 }} /> : null}
        {authMode === 'w3' ? (
          <Button
            type="primary"
            onClick={startW3Login}
            loading={w3Redirecting}
            disabled={w3Redirecting}
            icon={w3Redirecting ? undefined : (
              <img className="w3-login-logo" src={w3Logo} alt="" aria-hidden="true" />
            )}
            block
            size="large"
            className="employee-login-submit"
          >
            {w3Redirecting ? '正在前往 W3…' : '使用 W3 账号登录'}
          </Button>
        ) : <Form<LoginFormValues>
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
          {authMode === 'admin' ? (
            <Form.Item
              label="管理员密码"
              name="password"
              rules={[{ required: true, message: '请输入管理员密码' }]}
            >
              <Input.Password
                autoComplete="current-password"
                placeholder="请输入管理员密码"
                size="large"
              />
            </Form.Item>
          ) : null}
          <Button
            type="primary"
            htmlType="submit"
            loading={submitting}
            block
            size="large"
            className="employee-login-submit"
          >
            {authMode === 'admin' ? '以管理员身份登录' : '进入平台'}
          </Button>
        </Form>}
      </main>
    </div>
  );
}
