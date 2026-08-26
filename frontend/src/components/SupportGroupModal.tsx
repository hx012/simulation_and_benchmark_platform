import { Modal } from 'antd';
import supportGroupImage from '../assets/welink支撑群.png';

interface SupportGroupModalProps {
  open: boolean;
  onClose: () => void;
}

export function SupportGroupModal({ open, onClose }: SupportGroupModalProps) {
  return (
    <Modal
      className="support-group-modal"
      title="MSKPP 技术支撑群"
      open={open}
      footer={null}
      centered
      width={520}
      onCancel={onClose}
    >
      <p className="support-group-copy">使用 WeLink 扫码加入支撑群，获取平台答疑与问题响应。</p>
      <div className="support-group-image-shell">
        <img src={supportGroupImage} alt="MSKPP 技术支撑群二维码" />
      </div>
    </Modal>
  );
}
