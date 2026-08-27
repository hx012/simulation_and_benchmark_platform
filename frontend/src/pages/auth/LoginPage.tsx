import { useEffect, useRef, useState } from 'react';
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
  const submitLockRef = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  const [w3Redirecting, setW3Redirecting] = useState(false);
  const [authMode, setAuthMode] = useState<'normal' | 'w3' | 'admin'>('w3');
  const [w3OAuthEnabled, setW3OAuthEnabled] = useState(true);
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

  useEffect(() => {
    void authApi.getConfig().then((config) => {
      setW3OAuthEnabled(config.w3_oauth_enabled);
      if (!config.w3_oauth_enabled) setAuthMode('normal');
    }).catch(() => undefined);
  }, []);

  async function handleSubmit(values: LoginFormValues) {
    if (submitLockRef.current) return;
    submitLockRef.current = true;
    setSubmitting(true);
    message.destroy('admin-login-error');
    try {
      await login(values.employeeId, authMode === 'admin' ? 'admin' : 'normal', values.password);
      navigate(redirectTo, { replace: true });
    } catch (error) {
      message.error({
        key: 'admin-login-error',
        content: error instanceof Error ? error.message : String(error),
      });
    } finally {
      submitLockRef.current = false;
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
        <div className="employee-login-brand">
          <span className="employee-login-brand-mark">AI</span>
          <div><strong>AI Chip Platform</strong><small>Internal Engineering Workspace</small></div>
        </div>
        <h1>登录平台</h1>
        <p className="employee-login-intro">{w3OAuthEnabled ? '使用 W3 统一认证，或通过管理员账号进入内部工程平台。' : '团队成员可通过工号进入平台；管理员需使用账号密码登录。'}</p>
        <Segmented
          block
          className="login-mode-switch"
          value={authMode}
          options={[
            { label: w3OAuthEnabled ? 'W3 登录' : '工号登录', value: w3OAuthEnabled ? 'w3' : 'normal' },
            { label: '管理员登录', value: 'admin' },
          ]}
          onChange={(value) => {
            setAuthMode(value as 'normal' | 'w3' | 'admin');
            form.setFieldValue('password', '');
          }}
        />
        {oauthError ? <Alert type="error" showIcon title={oauthError} style={{ marginBottom: 16 }} /> : null}
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
            disabled={submitting}
            block
            size="large"
            className="employee-login-submit"
          >
            {authMode === 'admin' ? '以管理员身份登录' : '进入平台'}
          </Button>
        </Form>}
        <Button type="text" className="employee-login-back" onClick={() => navigate('/')}>← 返回门户页</Button>
      </main>
    </div>
  );
}
