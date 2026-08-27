import { apiRequest } from './client';

export interface CommunityLink {
  key: string;
  name: string;
  url: string;
  enabled: boolean;
  group: 'ecosystem' | 'support';
  order: number;
}

export interface PlatformSupport {
  key: string;
  name: string;
  resource: string;
  enabled: boolean;
}

export interface PlatformConfig {
  communities: CommunityLink[];
  support: PlatformSupport;
}

export interface FeatureReleaseItem {
  id: string;
  title: string;
  description: string;
  launched_at: string;
  action_text: string;
  action_url: string;
  enabled: boolean;
}

export interface FeatureReleaseConfig {
  enabled: boolean;
  title: string;
  max_items: number;
  new_badge_days: number;
  items: FeatureReleaseItem[];
}

export interface TeamAchievement {
  id: string;
  title: string;
  category: string;
  summary: string;
  contributors: string;
  date: string;
  featured: boolean;
  featured_order: number;
  enabled: boolean;
  detail_url: string;
}

export interface TeamMember {
  employee_id: string;
  name: string;
  avatar_file: string;
  avatar_url: string;
  direction: string;
  description: string;
  tags: string[];
  order: number;
  enabled: boolean;
  is_team_member: boolean;
  representative_achievements: string[];
  latest_completion_date: string | null;
}

export interface TeamAchievementArchiveItem {
  achievement_id: string;
  owner_employee_id: string;
  owner_name: string;
  title: string;
  category: string;
  summary: string;
  completion_date: string;
  reference_url: string;
  representative: boolean;
  score: number | null;
  can_edit: boolean;
  can_delete: boolean;
  can_score: boolean;
  created_at: string;
  updated_at: string;
}

export interface TeamAchievementPayload {
  owner_employee_id?: string;
  title: string;
  category: string;
  summary: string;
  completion_date: string;
  reference_url: string;
  representative: boolean;
}

export interface TeamConfig {
  name: string;
  description: string;
  team_size: string;
  specialties: string[];
  members: TeamMember[];
  achievements: TeamAchievement[];
  all_achievements_url: string;
  archive_visibility: 'team_only' | 'authenticated';
  viewer_is_team_member: boolean;
  viewer_is_admin: boolean;
  viewer_can_view_archives: boolean;
  contributions: Array<{
    member: string;
    contribution: string;
    achievement_count: number;
    contribution_score: number;
    views: number;
  }>;
}

export interface FeedbackPayload {
  feedback_type: 'experience' | 'function' | 'data' | 'other';
  page_title: string;
  page_path: string;
  content: string;
}

export interface FeedbackMessage {
  message_id: string;
  author_name: string;
  author_role: 'user' | 'admin';
  content: string;
  created_at: string;
}

export interface FeedbackItem extends FeedbackPayload {
  feedback_id: string;
  user_id: string;
  display_name: string;
  status: string;
  resolution: string;
  handler_name: string;
  messages: FeedbackMessage[];
  created_at: string;
  updated_at: string;
  can_withdraw: boolean;
  can_reply: boolean;
}

export interface FeedbackAdminPayload {
  status: 'pending' | 'processing' | 'needs_info' | 'resolved' | 'closed';
  resolution: string;
  reply: string;
}

export interface DemandPayload {
  title: string;
  domain: string;
  expected_time: string;
  background: string;
  description: string;
  business_value: string;
  contact: string;
}

export interface DemandItem extends DemandPayload {
  demand_id: string;
  request_no: string;
  submitter_id: string;
  submitter_name: string;
  status: string;
  conclusion: string;
  visibility: string;
  priority: string;
  planned_time: string;
  handler_name: string;
  support_count: number;
  voted_by_me: boolean;
  is_own: boolean;
  created_at: string;
  updated_at: string;
  can_edit: boolean;
  can_withdraw: boolean;
  history: Array<{
    event_id: string;
    actor_name: string;
    actor_role: 'user' | 'admin';
    event_type: string;
    from_status: string;
    to_status: string;
    comment: string;
    created_at: string;
  }>;
}

export interface DemandAdminPayload {
  status: 'pending' | 'needs_info' | 'accepted' | 'planned' | 'in_progress' | 'delivered' | 'deferred' | 'rejected';
  conclusion: string;
  visibility: 'private' | 'public';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  planned_time: string;
}

export const collaborationApi = {
  getPlatformConfig: () => apiRequest<PlatformConfig>('/api/platform-config'),
  getTeam: () => apiRequest<TeamConfig>('/api/team'),
  listTeamAchievementArchive: (employeeId: string) => apiRequest<TeamAchievementArchiveItem[]>(
    `/api/team/achievement-archives/${encodeURIComponent(employeeId)}`,
  ),
  createTeamAchievement: (payload: TeamAchievementPayload) => apiRequest<TeamAchievementArchiveItem>(
    '/api/team/achievement-archives', { method: 'POST', body: JSON.stringify(payload) },
  ),
  updateTeamAchievement: (achievementId: string, payload: TeamAchievementPayload) => apiRequest<TeamAchievementArchiveItem>(
    `/api/team/achievement-archives/${encodeURIComponent(achievementId)}`, { method: 'PATCH', body: JSON.stringify(payload) },
  ),
  deleteTeamAchievement: (achievementId: string) => apiRequest<void>(
    `/api/team/achievement-archives/${encodeURIComponent(achievementId)}`, { method: 'DELETE' },
  ),
  scoreTeamAchievement: (achievementId: string, score: number | null) => apiRequest<TeamAchievementArchiveItem>(
    `/api/admin/team/achievement-archives/${encodeURIComponent(achievementId)}/score`, {
      method: 'PATCH', body: JSON.stringify({ score }),
    },
  ),
  getFeatureReleases: () => apiRequest<FeatureReleaseConfig>('/api/feature-releases'),
  submitFeedback: (payload: FeedbackPayload) => apiRequest<FeedbackItem>('/api/feedback', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  listMyFeedback: () => apiRequest<FeedbackItem[]>('/api/feedback/mine'),
  supplementFeedback: (feedbackId: string, content: string) => apiRequest<FeedbackItem>(
    `/api/feedback/${encodeURIComponent(feedbackId)}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    },
  ),
  withdrawFeedback: (feedbackId: string) => apiRequest<FeedbackItem>(
    `/api/feedback/${encodeURIComponent(feedbackId)}/withdraw`, { method: 'POST' },
  ),
  listAdminFeedback: () => apiRequest<FeedbackItem[]>('/api/admin/feedback'),
  reviewFeedback: (feedbackId: string, payload: FeedbackAdminPayload) => apiRequest<FeedbackItem>(
    `/api/admin/feedback/${encodeURIComponent(feedbackId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  ),
  listDemands: (scope: 'public' | 'mine' = 'public') => apiRequest<{ items: DemandItem[]; total: number }>(
    '/api/demands', {}, { scope },
  ),
  submitDemand: (payload: DemandPayload) => apiRequest<DemandItem>('/api/demands', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateDemand: (demandId: string, payload: DemandPayload) => apiRequest<DemandItem>(
    `/api/demands/${encodeURIComponent(demandId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  ),
  withdrawDemand: (demandId: string) => apiRequest<DemandItem>(
    `/api/demands/${encodeURIComponent(demandId)}/withdraw`, { method: 'POST' },
  ),
  listAdminDemands: () => apiRequest<{ items: DemandItem[]; total: number }>('/api/admin/demands'),
  reviewDemand: (demandId: string, payload: DemandAdminPayload) => apiRequest<DemandItem>(
    `/api/admin/demands/${encodeURIComponent(demandId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  ),
  setDemandVote: (demandId: string, enabled: boolean) => apiRequest<{
    demand_id: string;
    support_count: number;
    voted_by_me: boolean;
  }>(`/api/demands/${encodeURIComponent(demandId)}/vote`, {
    method: enabled ? 'PUT' : 'DELETE',
  }),
};
