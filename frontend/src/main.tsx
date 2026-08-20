import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import { AuthProvider } from './auth/AuthContext';
import './styles/global.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#171717',
          colorInfo: '#2563eb',
          colorSuccess: '#238636',
          colorWarning: '#ad6800',
          colorError: '#cf222e',
          colorText: '#202124',
          colorTextSecondary: '#6b7280',
          colorBorder: '#d9dde3',
          colorBgLayout: '#f6f7f9',
          borderRadius: 8,
          fontFamily: '"PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif',
        },
        components: {
          Button: { controlHeight: 34 },
          Card: { headerFontSize: 15 },
          Table: { headerBg: '#fafafa' },
          Select: {
            optionActiveBg: '#f7f7f8',
            optionSelectedBg: '#f1f3f5',
            optionSelectedColor: '#111827',
            optionSelectedFontWeight: 600,
          },
        },
      }}
    >
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  </StrictMode>,
);
