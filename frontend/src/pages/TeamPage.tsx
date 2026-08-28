import { useEffect, useState } from 'react';
import { ArrowRightOutlined, DeleteOutlined, EditOutlined, PlusOutlined, StarFilled, StarOutlined, UserAddOutlined } from '@ant-design/icons';
import {
  Button, Drawer, Empty, Form, Input, InputNumber, message, Modal,
  Popconfirm, Popover, Skeleton, Space, Table, Tabs, Tag, Typography,
} from 'antd';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  collaborationApi, type TeamAchievementArchiveItem, type TeamAchievementPayload,
  type TeamConfig, type TeamMember,
} from '../api/collaboration';
import { useAuth } from '../auth/AuthContext';
import { apiResourceUrl } from '../api/client';
import { PageHeading } from '../components/PageHeading';
import { ResultWatermark } from '../components/ResultWatermark';

function openConfiguredUrl(url: string, navigate: (path: string) => void) {
  if (url.startsWith('/')) navigate(url);
  else window.open(url, '_blank', 'noopener,noreferrer');
}

function MemberPhoto({ member, small = false }: { member: TeamMember; small?: boolean }) {
  return <div className={`team-member-photo${small ? ' is-small' : ''}`}><span>{member.name.slice(-2)}</span>{member.avatar_url ? <img src={apiResourceUrl(member.avatar_url)} alt={`${member.name}头像`} onError={(event) => { event.currentTarget.style.display = 'none'; }} /> : null}</div>;
}

function RepresentativeAchievements({ items }: { items: string[] }) {
  if (!items.length) return <span className="team-summary-empty">暂未设置</span>;
  const visible = items.slice(0, 2);
  const remaining = items.length - visible.length;
  return <div className="team-representative-cell"><span>{visible.join(' · ')}</span>{remaining > 0 ? <Popover trigger="click" title={`核心成果（${items.length}）`} content={<ol className="team-representative-popover">{items.map((item) => <li key={item}>{item}</li>)}</ol>}><Button type="link" size="small">+{remaining} 项</Button></Popover> : null}</div>;
}

type AchievementFormValues = TeamAchievementPayload;

export function TeamPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [team, setTeam] = useState<TeamConfig | null>(null);
  const [joinOpen, setJoinOpen] = useState(false);
  const [archiveMember, setArchiveMember] = useState<TeamMember | null>(null);
  const [archiveItems, setArchiveItems] = useState<TeamAchievementArchiveItem[]>([]);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [editing, setEditing] = useState<TeamAchievementArchiveItem | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [scoreDrafts, setScoreDrafts] = useState<Record<string, number | null>>({});
  const [evaluationDrafts, setEvaluationDrafts] = useState<Record<string, string>>({});
  const [form] = Form.useForm<AchievementFormValues>();
  const activeTab = searchParams.get('tab') === 'results' ? 'results' : 'intro';

  async function loadTeam() {
    try { setTeam(await collaborationApi.getTeam()); }
    catch { setTeam({ name: '芯片仿真与性能分析团队', description: '团队内容暂时无法加载。', team_size: '', specialties: [], members: [], achievements: [], contributions: [], all_achievements_url: '', archive_visibility: 'team_only', viewer_is_team_member: false, viewer_is_admin: false, viewer_can_view_archives: false }); }
  }

  useEffect(() => {
    void loadTeam();
  }, []);

  async function loadArchive(member: TeamMember) {
    setArchiveLoading(true);
    try {
      const items = await collaborationApi.listTeamAchievementArchive(member.employee_id);
      setArchiveMember(member);
      setArchiveItems(items);
      setScoreDrafts(Object.fromEntries(items.map((item) => [item.achievement_id, item.score])));
      setEvaluationDrafts(Object.fromEntries(items.map((item) => [item.achievement_id, item.evaluation])));
    }
    catch (error) { message.error(error instanceof Error ? error.message : String(error)); }
    finally { setArchiveLoading(false); }
  }

  function openCreate() {
    setEditing(null);
    form.setFieldsValue({ owner_employee_id: user?.userId || '', title: '', category: '工作成果', summary: '', completion_date: '', reference_url: '' });
    setEditorOpen(true);
  }

  function openEdit(item: TeamAchievementArchiveItem) {
    setEditing(item);
    form.setFieldsValue({ owner_employee_id: item.owner_employee_id, title: item.title, category: item.category, summary: item.summary, completion_date: item.completion_date, reference_url: item.reference_url });
    setEditorOpen(true);
  }

  async function saveAchievement() {
    try {
      const values = await form.validateFields();
      if (editing) await collaborationApi.updateTeamAchievement(editing.achievement_id, values); else await collaborationApi.createTeamAchievement(values);
      message.success(editing ? '成果已更新' : '成果已登记'); setEditorOpen(false); setEditing(null); await loadTeam(); if (archiveMember) await loadArchive(archiveMember);
    } catch (error) { if (error instanceof Error) message.error(error.message); }
  }

  async function removeAchievement(item: TeamAchievementArchiveItem) {
    try { await collaborationApi.deleteTeamAchievement(item.achievement_id); message.success('成果已删除'); if (archiveMember) await loadArchive(archiveMember); await loadTeam(); }
    catch (error) { message.error(error instanceof Error ? error.message : String(error)); }
  }

  async function saveScore(item: TeamAchievementArchiveItem) {
    const score = scoreDrafts[item.achievement_id] ?? null;
    const evaluation = (evaluationDrafts[item.achievement_id] || '').trim();
    if (score !== null && evaluation.length < 10) {
      message.error('填写评分时，评价至少需要 10 个字');
      return;
    }
    try { await collaborationApi.scoreTeamAchievement(item.achievement_id, { score, evaluation }); message.success('评分与评价已保存'); if (archiveMember) await loadArchive(archiveMember); }
    catch (error) { message.error(error instanceof Error ? error.message : String(error)); }
  }

  async function toggleRepresentative(item: TeamAchievementArchiveItem) {
    try {
      await collaborationApi.setTeamAchievementRepresentative(item.achievement_id, !item.representative);
      message.success(item.representative ? '已取消核心成果' : '已设为核心成果');
      if (archiveMember) await loadArchive(archiveMember);
      await loadTeam();
    } catch (error) { message.error(error instanceof Error ? error.message : String(error)); }
  }

  const canCreate = Boolean(team?.viewer_is_team_member && !team?.viewer_is_admin);
  if (!team) return <div className="page-container"><Skeleton active /></div>;

  const summaryColumns = [
    { title: '成员', key: 'member', width: 190, render: (_: unknown, member: TeamMember) => <div className="team-summary-member"><div><strong>{member.name}</strong><small>{member.employee_id}</small></div></div> },
    { title: '核心成果', dataIndex: 'representative_achievements', render: (items: string[]) => <RepresentativeAchievements items={items} /> },
    { title: '成果更新日期', dataIndex: 'latest_completion_date', width: 150, render: (value: string | null) => value || '—' },
    { title: '成果档案', key: 'action', width: 140, render: (_: unknown, member: TeamMember) => <Button type="link" onClick={() => void loadArchive(member)}>查看成果档案</Button> },
  ];

  return <div className="page-container team-page">
    <PageHeading title="团队风采" actions={canCreate ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增我的成果</Button> : undefined} />
    <Tabs className="team-tabs" activeKey={activeTab} onChange={(key) => setSearchParams(key === 'results' ? { tab: 'results' } : {}, { replace: true })} items={[{ key: 'intro', label: '团队介绍' }, { key: 'results', label: '成果与贡献' }]} />

    {activeTab === 'intro' ? <>
      <section className="team-intro-panel"><h2>{team.name}</h2><p>{team.description}</p></section>
      <div className="team-section-heading"><h2>团队成员</h2><button className="team-contact-button" type="button" onClick={() => setJoinOpen(true)}><UserAddOutlined /> 加入团队 <ArrowRightOutlined /></button></div>
      {team.members.length ? <div className="team-member-grid">{team.members.map((member) => <article className="team-member-card" key={member.employee_id}><MemberPhoto member={member} /><div className="team-member-content"><div className="team-member-name"><h3>{member.name} <span>{member.employee_id}</span></h3></div><strong>{member.direction}</strong><p>{member.description}</p>{member.tags?.length ? <div className="team-member-tags">{member.tags.map((tag) => <span key={tag}>{tag}</span>)}</div> : null}</div></article>)}</div> : <div className="team-empty"><Empty description="团队成员配置待补充" /></div>}
    </> : <>
      <div className="team-section-heading team-results-heading"><h2>重点成果</h2><Button type="link" disabled={!team.all_achievements_url} onClick={() => team.all_achievements_url && openConfiguredUrl(team.all_achievements_url, navigate)}>查看全部成果 <ArrowRightOutlined /></Button></div>
      {team.achievements.length ? <div className="team-achievement-grid">{team.achievements.slice(0, 3).map((item) => <button type="button" className="team-achievement-card" key={item.id || `${item.title}-${item.date}`} disabled={!item.detail_url} onClick={() => item.detail_url && openConfiguredUrl(item.detail_url, navigate)}><span>{item.category}</span><h3>{item.title}</h3><p>{item.summary}</p><small>{item.contributors}{item.date ? ` · ${item.date}` : ''}</small>{item.detail_url ? <em>查看成果 →</em> : null}</button>)}</div> : <div className="team-empty"><Empty description="暂无团队成果" /></div>}
      <div className="team-section-heading"><h2>成果榜</h2></div>
      <div className="team-contribution-table"><Table rowKey="employee_id" pagination={false} dataSource={team.members} locale={{ emptyText: '暂无成员成果' }} columns={summaryColumns} /></div>
    </>}

    <Drawer size={560} open={Boolean(archiveMember)} onClose={() => setArchiveMember(null)} title={archiveMember ? `${archiveMember.name}的成果档案` : '成果档案'}>
      <ResultWatermark className="team-archive-watermark">
        {archiveMember ? <div className="team-archive-profile"><MemberPhoto member={archiveMember} /><div><h3>{archiveMember.name}</h3><p>{archiveMember.direction}</p></div>{canCreate && archiveMember.employee_id === user?.userId ? <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增成果</Button> : null}</div> : null}
        {archiveLoading ? <Skeleton active /> : archiveItems.length ? <div className="team-archive-list">{archiveItems.map((item) => <article className="team-archive-item" key={item.achievement_id}>
          <div className="team-archive-meta"><time>{item.completion_date}</time><Tag>{item.category}</Tag>{item.representative ? <Tag color="blue">核心成果</Tag> : null}</div>
          <h3>{item.title}</h3>{item.summary ? <p>{item.summary}</p> : null}{item.reference_url ? <a href={item.reference_url} target="_blank" rel="noreferrer">查看关联材料 <ArrowRightOutlined /></a> : null}
          <div className="team-archive-review">
            <div><strong>评分：{item.score ?? '未评分'}</strong>{item.evaluation ? <p>评价：{item.evaluation}</p> : null}{item.scored_at ? <small>{item.scored_by_name || item.scored_by_employee_id} · {new Date(item.scored_at).toLocaleString('zh-CN', { hour12: false })}</small> : null}</div>
            {item.can_score ? <div className="team-archive-review-editor"><InputNumber min={0} max={100} value={scoreDrafts[item.achievement_id]} placeholder="0-100" onChange={(value) => setScoreDrafts((current) => ({ ...current, [item.achievement_id]: value }))} /><Input.TextArea rows={3} maxLength={300} showCount value={evaluationDrafts[item.achievement_id]} placeholder="管理员评价（评分时至少 10 个字）" onChange={(event) => setEvaluationDrafts((current) => ({ ...current, [item.achievement_id]: event.target.value }))} /><Button size="small" type="primary" onClick={() => void saveScore(item)}>保存评分与评价</Button></div> : null}
          </div>
          {(item.can_edit || item.can_delete) ? <div className="team-archive-actions"><Space wrap>{item.can_edit ? <Button size="small" icon={item.representative ? <StarFilled /> : <StarOutlined />} onClick={() => void toggleRepresentative(item)}>{item.representative ? '取消核心成果' : '设为核心成果'}</Button> : null}{item.can_edit ? <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(item)}>编辑</Button> : null}{item.can_delete ? <Popconfirm title="删除这条成果？" okText="删除" cancelText="取消" onConfirm={() => void removeAchievement(item)}><Button danger size="small" icon={<DeleteOutlined />}>删除</Button></Popconfirm> : null}</Space></div> : null}
        </article>)}</div> : <Empty description="暂无成果记录" />}
      </ResultWatermark>
    </Drawer>

    <Modal title={editing ? '编辑成果' : '新增成果'} open={editorOpen} onCancel={() => setEditorOpen(false)} onOk={() => void saveAchievement()} okText="保存">
      <Form form={form} layout="vertical">
        <Form.Item label="成果标题" name="title" rules={[{ required: true, message: '请输入成果标题' }]}><Input maxLength={255} /></Form.Item>
        <Form.Item label="成果类型" name="category" rules={[{ required: true, message: '请输入成果类型' }]}><Input maxLength={64} /></Form.Item>
        <Form.Item label="成果完成日期" name="completion_date" rules={[{ required: true, message: '请选择成果完成日期' }]}><Input type="date" /></Form.Item>
        <Form.Item label="成果内容" name="summary"><Input.TextArea rows={4} maxLength={5000} showCount /></Form.Item>
        <Form.Item label="关联材料地址" name="reference_url"><Input placeholder="内部文档、代码或任务地址" maxLength={2048} /></Form.Item>
      </Form>
    </Modal>
    <Modal title="加入团队" open={joinOpen} footer={null} onCancel={() => setJoinOpen(false)}>
      <Typography.Paragraph style={{ margin: 0, lineHeight: 1.8 }}>
        欢迎对芯片微架构、MSKPP 仿真器、Benchmark 和性能分析感兴趣的同学加入。可联系管理员郝雪桐 h00517730。
      </Typography.Paragraph>
    </Modal>
  </div>;
}
