import { useEffect, useState } from 'react';
import { Alert, Button, Form, Input, message, Segmented } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { authApi } from '../../api/auth';
import { ArchitectureBackground } from '../../components/ArchitectureBackground';
import { useAuth } from '../../auth/AuthContext';

interface LoginFormValues {
  employeeId: string;
  password?: string;
}

export function LoginPage() {
  const [form] = Form.useForm<LoginFormValues>();
  const [submitting, setSubmitting] = useState(false);
  const [authMode, setAuthMode] = useState<'normal' | 'admin'>('normal');
  const [w3Enabled, setW3Enabled] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { authenticated, login } = useAuth();

  const defaultEmployeeId = import.meta.env.VITE_DEFAULT_OWNER_ID || '';
  const redirectTo = (location.state as { from?: string } | null)?.from || '/home';
  const oauthError = new URLSearchParams(location.search).get('oauth_error');

  useEffect(() => {
    if (authenticated && !location.state) {
      navigate('/home', { replace: true });
    }
  }, [authenticated, location.state, navigate]);

  useEffect(() => {
    void authApi.getConfig()
      .then((config) => setW3Enabled(config.w3_oauth_enabled))
      .catch(() => setW3Enabled(false));
  }, []);

  async function handleSubmit(values: LoginFormValues) {
    setSubmitting(true);
    try {
      await login(values.employeeId, authMode, values.password);
      navigate(redirectTo, { replace: true });
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setSubmitting(false);
    }
  }

  function startW3Login() {
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
            { label: w3Enabled ? 'W3 登录' : '普通登录', value: 'normal' },
            { label: '管理员登录', value: 'admin' },
          ]}
          onChange={(value) => {
            setAuthMode(value as 'normal' | 'admin');
            form.setFieldValue('password', '');
          }}
        />
        {oauthError ? <Alert type="error" showIcon message={oauthError} style={{ marginBottom: 16 }} /> : null}
        {w3Enabled && authMode === 'normal' ? (
          <Button
            type="primary"
            onClick={startW3Login}
            block
            size="large"
            className="employee-login-submit"
          >
            使用 W3 账号登录
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
