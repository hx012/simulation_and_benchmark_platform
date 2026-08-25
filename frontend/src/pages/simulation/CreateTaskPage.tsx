import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Collapse,
  Form,
  Input,
  message,
  Modal,
  Select,
  Space,
  Spin,
  Steps,
  Tabs,
} from 'antd';
import {
  CheckCircleOutlined,
  CopyOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { simulationApi } from '../../api/simulation';
import { trackAnalyticsEventQuietly } from '../../api/analytics';
import { PageHeading } from '../../components/PageHeading';
import { RemoteBundleEditor } from '../../components/RemoteBundleEditor';
import type {
  ChipVariantCapability,
  LocalFileEntry,
  SimulationMode,
  SimulatorCapability,
  SimulationTaskQuotaResponse,
  UploadValidationResponse,
} from '../../types/simulation';

interface BasicFormValues {
  taskName: string;
}

type PackageSource = '未准备' | '样例' | '自定义上传';

const validationItems = [
  'Chip Config / Workload 目录存在且包含 YAML / JSON 配置',
  'YAML / JSON 文件可以正常解析',
  'workload 中 kernel_file / input_bin 为安全的相对路径',
  'kernel_file / input_bin 引用的资产文件真实存在',
  '禁止绝对路径、../ 等越界路径',
];

function taskNameSuffix() {
  return new Date().toISOString().slice(0, 16).replace(/[-T:]/g, '');
}

export function CreateTaskPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const ownerId = user?.userId || import.meta.env.VITE_DEFAULT_OWNER_ID || 'admin';
  const [form] = Form.useForm<BasicFormValues>();
  const [quota, setQuota] = useState<SimulationTaskQuotaResponse | null>(null);

  const [simulators, setSimulators] = useState<SimulatorCapability[]>([]);
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true);
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(null);
  const [simulatorKey, setSimulatorKey] = useState<string | null>(null);
  const [variantKey, setVariantKey] = useState<string | null>(null);
  const [modeKey, setModeKey] = useState<SimulationMode | null>(null);

  const [uploadSessionId, setUploadSessionId] = useState<string | null>(null);
  const [validation, setValidation] = useState<UploadValidationResponse | null>(null);
  const [hasValidatedOnce, setHasValidatedOnce] = useState(false);
  const [validationDirty, setValidationDirty] = useState(false);
  const [validationDetailOpen, setValidationDetailOpen] = useState(false);
  const [chipSource, setChipSource] = useState<PackageSource>('未准备');
  const [workloadSource, setWorkloadSource] = useState<PackageSource>('未准备');
  const [chipRefreshToken, setChipRefreshToken] = useState(0);
  const [workloadRefreshToken, setWorkloadRefreshToken] = useState(0);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectedSimulator = useMemo(
    () => simulators.find((item) => item.key === simulatorKey) || null,
    [simulators, simulatorKey],
  );
  const selectedVariant = useMemo(
    () => selectedSimulator?.variants.find((item) => item.key === variantKey) || null,
    [selectedSimulator, variantKey],
  );
  const selectedMode = useMemo(
    () => selectedVariant?.modes.find((item) => item.key === modeKey) || null,
    [selectedVariant, modeKey],
  );

  const hasCapabilitySelection = Boolean(selectedSimulator && selectedVariant && selectedMode);
  const hasConfiguration = chipSource !== '未准备' && workloadSource !== '未准备';
  const validationReady = Boolean(
    validation?.valid === true
    && validation.status === 'READY'
    && uploadSessionId,
  );

  const step = useMemo(() => {
    if (validationReady) return 2;
    if (hasConfiguration) return 1;
    return 0;
  }, [hasConfiguration, validationReady]);

  const validationState = useMemo(() => {
    if (!hasConfiguration) return { tone: 'idle', title: '等待配置' };
    if (validating) return { tone: 'progress', title: validationReady ? '正在重新校验' : '正在校验配置' };
    if (validationReady) return { tone: 'success', title: '配置已校验，可以提交任务' };
    if (validation?.valid === false) return { tone: 'error', title: '配置校验未通过' };
    if (hasValidatedOnce && validationDirty) return { tone: 'warning', title: '配置已修改，需要重新校验' };
    return { tone: 'pending', title: '配置已准备，等待校验' };
  }, [hasConfiguration, hasValidatedOnce, validation, validationDirty, validationReady, validating]);

  useEffect(() => {
    let cancelled = false;
    simulationApi.getTaskQuota(ownerId)
      .then((response) => {
        if (!cancelled) setQuota(response);
      })
      .catch(() => {
        if (!cancelled) setQuota(null);
      });
    return () => { cancelled = true; };
  }, [ownerId]);

  useEffect(() => {
    let cancelled = false;
    setCapabilitiesLoading(true);
    simulationApi.getCapabilities()
      .then((response) => {
        if (cancelled) return;
        setSimulators(response.simulators);
        const firstSimulator = response.simulators[0];
        const firstVariant = firstSimulator?.variants[0];
        const firstMode = firstVariant?.modes[0];
        if (!firstSimulator || !firstVariant || !firstMode) {
          setCapabilitiesError('当前没有可用的仿真配置');
          return;
        }
        setSimulatorKey(firstSimulator.key);
        setVariantKey(firstVariant.key);
        setModeKey(firstMode.key);
        if (!form.isFieldTouched('taskName')) {
          form.setFieldValue('taskName', `${firstSimulator.label}_Simulation_${taskNameSuffix()}`);
        }
        setCapabilitiesError(null);
      })
      .catch((error) => {
        if (!cancelled) setCapabilitiesError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        if (!cancelled) setCapabilitiesLoading(false);
      });
    return () => { cancelled = true; };
  }, [form]);

  useEffect(() => {
    if (validation?.valid === false) setValidationDetailOpen(true);
    if (validation?.valid === true) setValidationDetailOpen(false);
  }, [validation]);

  async function ensureUploadSession(): Promise<string> {
    if (quota && !quota.can_create) {
      throw new Error(`已达到任务保留上限 ${quota.limit} 个，请先删除不再需要的任务`);
    }
    if (uploadSessionId) return uploadSessionId;
    const session = await simulationApi.createUploadSession(ownerId);
    setUploadSessionId(session.upload_session_id);
    return session.upload_session_id;
  }

  function invalidateValidation() {
    if (hasValidatedOnce) setValidationDirty(true);
    setValidation(null);
  }

  function resetPreparedConfiguration() {
    setUploadSessionId(null);
    setChipSource('未准备');
    setWorkloadSource('未准备');
    setValidation(null);
    setHasValidatedOnce(false);
    setValidationDirty(false);
    setValidationDetailOpen(false);
    setChipRefreshToken((value) => value + 1);
    setWorkloadRefreshToken((value) => value + 1);
  }

  function withCapabilityChange(apply: () => void) {
    if (!uploadSessionId && !hasConfiguration) {
      apply();
      return;
    }
    Modal.confirm({
      title: '切换仿真配置？',
      content: '当前已载入或上传的配置可能与新的仿真组合不兼容。切换后本页面将重新准备配置。',
      okText: '切换',
      cancelText: '取消',
      onOk: () => {
        resetPreparedConfiguration();
        apply();
      },
    });
  }

  function handleSimulatorChange(nextKey: string) {
    const simulator = simulators.find((item) => item.key === nextKey);
    const variant = simulator?.variants[0];
    const mode = variant?.modes[0];
    if (!simulator || !variant || !mode) return;
    withCapabilityChange(() => {
      setSimulatorKey(simulator.key);
      setVariantKey(variant.key);
      setModeKey(mode.key);
    });
  }

  function handleVariantChange(nextKey: string) {
    const variant = selectedSimulator?.variants.find((item) => item.key === nextKey);
    const mode = variant?.modes[0];
    if (!variant || !mode) return;
    withCapabilityChange(() => {
      setVariantKey(variant.key);
      setModeKey(mode.key);
    });
  }

  function handleModeChange(nextKey: SimulationMode) {
    if (!selectedVariant?.modes.some((item) => item.key === nextKey)) return;
    withCapabilityChange(() => setModeKey(nextKey));
  }

  async function handleApplySample() {
    if (!selectedSimulator || !selectedVariant || !selectedMode) {
      message.warning('请选择完整的仿真配置');
      return;
    }
    setSampleLoading(true);
    try {
      const sessionId = await ensureUploadSession();
      const result = await simulationApi.applySample(sessionId, {
        simulator_version: selectedSimulator.key,
        chip_variant: selectedVariant.key,
        simulation_mode: selectedMode.key,
      });
      setChipSource('样例');
      setWorkloadSource('样例');
      setChipRefreshToken((value) => value + 1);
      setWorkloadRefreshToken((value) => value + 1);
      invalidateValidation();
      message.success(
        `已载入 ${selectedSimulator.label} / ${selectedVariant.label} / ${selectedMode.label} 样例：`
        + `Chip Config ${result.chip_config_files} 个文件，Workload ${result.workload_files} 个文件`,
      );
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setSampleLoading(false);
    }
  }

  async function uploadPackage(
    endpoint: 'chip-config' | 'workload',
    entries: LocalFileEntry[],
  ) {
    const sessionId = await ensureUploadSession();
    await simulationApi.uploadPackage(sessionId, endpoint, entries);
    if (endpoint === 'chip-config') {
      setChipSource('自定义上传');
      setChipRefreshToken((value) => value + 1);
    } else {
      setWorkloadSource('自定义上传');
      setWorkloadRefreshToken((value) => value + 1);
    }
    invalidateValidation();
  }

  async function handleValidate() {
    try {
      await form.validateFields();
      if (!hasCapabilitySelection) {
        message.warning('请选择完整的仿真配置');
        return;
      }
      if (!uploadSessionId || !hasConfiguration) {
        message.warning('请先载入当前样例，或分别上传 Chip Config 与 Workload');
        return;
      }

      setValidating(true);
      const result = await simulationApi.validateUploadSession(uploadSessionId);
      setValidation(result);
      setHasValidatedOnce(true);
      setValidationDirty(false);
      if (result.valid) {
        message.success('配置校验通过，可以提交仿真任务');
      } else {
        message.error('配置校验未通过，请根据错误信息修改后重新校验');
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setValidating(false);
    }
  }

  async function handleSubmit() {
    let submissionAttempted = false;
    if (!validationReady || !uploadSessionId) {
      message.warning('请先完成配置校验');
      return;
    }
    if (!selectedSimulator || !selectedVariant || !selectedMode) {
      message.warning('请选择完整的仿真配置');
      return;
    }

    try {
      const values = await form.validateFields();
      setSubmitting(true);
      submissionAttempted = true;
      const response = await simulationApi.submitUploadSession(uploadSessionId, {
        task_name: values.taskName,
        simulator_version: selectedSimulator.key,
        chip_variant: selectedVariant.key,
        simulation_mode: selectedMode.key,
      });

      trackAnalyticsEventQuietly({
        event_name: 'simulation.task_create_success',
        page_key: 'simulation.create',
        result: 'success',
        simulator_version: selectedSimulator.key,
        chip_variant: selectedVariant.key,
        simulation_mode: selectedMode.key,
      });

      message.success(`任务已提交，前方 ${response.queued_ahead} 个任务`);
      navigate(`/simulation/tasks/${response.task.task_id}`);
    } catch (error) {
      if (submissionAttempted) {
        trackAnalyticsEventQuietly({
          event_name: 'simulation.task_create_failed',
          page_key: 'simulation.create',
          result: 'failed',
          simulator_version: selectedSimulator?.key,
          chip_variant: selectedVariant?.key,
          simulation_mode: selectedMode?.key,
        });
      }
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setSubmitting(false);
    }
  }

  const quotaFull = quota ? !quota.can_create : false;

  const configTabs = [
    {
      key: 'chip_config',
      label: 'Chip Config',
      children: (
        <RemoteBundleEditor
          title="Chip Config"
          packageType="chip_config"
          uploadSessionId={uploadSessionId}
          refreshToken={chipRefreshToken}
          onUpload={(entries) => uploadPackage('chip-config', entries)}
          onChanged={invalidateValidation}
        />
      ),
    },
    {
      key: 'workload',
      label: 'Workload',
      children: (
        <RemoteBundleEditor
          title="Workload"
          packageType="workload"
          uploadSessionId={uploadSessionId}
          refreshToken={workloadRefreshToken}
          onUpload={(entries) => uploadPackage('workload', entries)}
          onChanged={invalidateValidation}
        />
      ),
    },
  ];

  return (
    <div className="page-container create-task-page">
      <PageHeading title="新建仿真任务" />

      {quotaFull ? (
        <Alert
          className="task-quota-alert"
          type="warning"
          showIcon
          message={`已达到任务保留上限（${quota?.retained_count} / ${quota?.limit}）`}
          description="请先在“我的任务”中删除不再需要的任务，再创建新的仿真任务。"
          action={<Button onClick={() => navigate('/simulation/tasks')}>管理任务</Button>}
        />
      ) : null}

      <div className="workflow-strip">
        <Steps
          current={step}
          items={[
            { title: '准备配置' },
            { title: '修改并校验' },
            { title: '提交任务' },
          ]}
        />
      </div>

      <section className="create-major-section create-major-basic">
        <div className="create-major-head">
          <h2>基本信息</h2>
        </div>

        <Form
          form={form}
          layout="vertical"
          initialValues={{ taskName: `Simulation_${taskNameSuffix()}` }}
        >
          <Form.Item
            name="taskName"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如 V310_VectorAdd_001" maxLength={255} />
          </Form.Item>
        </Form>

        {capabilitiesLoading ? (
          <div className="simulator-capability-loading"><Spin size="small" /> 正在读取仿真能力…</div>
        ) : capabilitiesError ? (
          <Alert type="error" showIcon message="仿真能力读取失败" description={capabilitiesError} />
        ) : (
          <div className="simulator-capability-grid">
            <div className="simulator-capability-field">
              <label>Simulator Version</label>
              <Select
                value={simulatorKey}
                options={simulators.map((item) => ({ value: item.key, label: item.label }))}
                onChange={handleSimulatorChange}
              />
            </div>
            <div className="simulator-capability-field">
              <label>Chip Variant</label>
              <Select
                value={variantKey}
                options={(selectedSimulator?.variants || []).map((item: ChipVariantCapability) => ({
                  value: item.key,
                  label: item.label,
                }))}
                onChange={handleVariantChange}
              />
            </div>
            <div className="simulator-capability-field">
              <label>Simulation Mode</label>
              <Select
                value={modeKey}
                options={(selectedVariant?.modes || []).map((item) => ({ value: item.key, label: item.label }))}
                onChange={handleModeChange}
              />
            </div>
          </div>
        )}
      </section>

      <section className="create-major-section create-major-config">
        <div className="create-major-head">
          <h2>配置</h2>
          <Button
            className="sample-action-button"
            icon={<CopyOutlined />}
            loading={sampleLoading}
            disabled={!hasCapabilitySelection || capabilitiesLoading || quotaFull}
            onClick={() => void handleApplySample()}
          >
            载入当前样例
          </Button>
        </div>

        <Tabs
          className="config-package-tabs"
          type="card"
          defaultActiveKey="chip_config"
          items={configTabs}
        />
      </section>

      <section className="create-major-section create-major-validation">
        <div className="create-major-head validation-major-head">
          <h2>配置校验与提交</h2>
        </div>

        <Alert
          className="validation-summary-alert"
          type={
            validationState.tone === 'success'
              ? 'success'
              : validationState.tone === 'error'
                ? 'error'
                : validationState.tone === 'warning'
                  ? 'warning'
                  : 'info'
          }
          showIcon
          message={validationState.title}
        />

        {validation?.valid === false && validation.errors.length ? (
          <div className="validation-error-panel">
            <div className="validation-error-title">需要处理的问题</div>
            <ul className="validation-errors">
              {validation.errors.map((error) => <li key={error}>{error}</li>)}
            </ul>
          </div>
        ) : null}

        <Collapse
          ghost
          className="validation-detail-collapse"
          activeKey={validationDetailOpen ? ['rules'] : []}
          onChange={(keys) => {
            const next = Array.isArray(keys) ? keys.includes('rules') : keys === 'rules';
            setValidationDetailOpen(next);
          }}
          items={[
            {
              key: 'rules',
              label: '查看校验内容',
              children: (
                <div className="validation-check-grid">
                  {validationItems.map((item) => (
                    <div className="validation-check-item" key={item}>
                      <CheckCircleOutlined />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              ),
            },
          ]}
        />

        <div className={`create-action-row create-action-row-${validationState.tone}`}>
          <div className="create-action-status">
            <span className="submit-state-dot" aria-hidden="true" />
            <strong>{validationState.title}</strong>
          </div>
          <Space size={12} className="submit-actions">
            <Button
              size="large"
              className={`action-button ${validationReady ? 'action-button-secondary' : 'action-button-primary'}`}
              icon={<SafetyCertificateOutlined />}
              loading={validating}
              disabled={!hasConfiguration || !hasCapabilitySelection || submitting || quotaFull}
              onClick={() => void handleValidate()}
            >
              {validationReady ? '重新校验' : '校验配置'}
            </Button>
            <Button
              size="large"
              className="action-button action-button-primary submit-primary-action"
              icon={validationReady ? <CheckCircleOutlined /> : <RocketOutlined />}
              loading={submitting}
              disabled={!validationReady || !hasCapabilitySelection || validating || quotaFull}
              onClick={() => void handleSubmit()}
            >
              提交仿真任务
            </Button>
          </Space>
        </div>
      </section>
    </div>
  );
}
