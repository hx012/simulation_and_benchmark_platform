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
          colorPrimary: '#3168e8',
          colorInfo: '#3168e8',
          colorSuccess: '#1c9a59',
          colorWarning: '#ca7a13',
          colorError: '#d14848',
          colorText: '#10233f',
          colorTextSecondary: '#687b94',
          colorBorder: '#d7e1ed',
          colorBgLayout: '#f3f7fb',
          borderRadius: 10,
          fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", sans-serif',
        },
        components: {
          Button: { controlHeight: 38, borderRadius: 9 },
          Card: { headerFontSize: 16, borderRadiusLG: 14 },
          Table: { headerBg: '#f6f9fc', headerColor: '#60748c' },
          Select: {
            optionActiveBg: '#f3f7fb',
            optionSelectedBg: '#eaf1ff',
            optionSelectedColor: '#10233f',
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
