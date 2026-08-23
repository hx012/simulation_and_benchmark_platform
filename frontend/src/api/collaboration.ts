import { apiRequest } from './client';

export interface CommunityLink {
  key: string;
  name: string;
  url: string;
  enabled: boolean;
}

export interface PlatformConfig {
  communities: CommunityLink[];
}

export interface TeamAchievement {
  title: string;
  category: string;
  summary: string;
  contributors: string;
  date: string;
}

export interface TeamConfig {
  name: string;
  description: string;
  team_size: string;
  specialties: string[];
  achievements: TeamAchievement[];
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
  support_count: number;
  voted_by_me: boolean;
  is_own: boolean;
  created_at: string;
  updated_at: string;
}

export const collaborationApi = {
  getPlatformConfig: () => apiRequest<PlatformConfig>('/api/platform-config'),
  getTeam: () => apiRequest<TeamConfig>('/api/team'),
  submitFeedback: (payload: FeedbackPayload) => apiRequest('/api/feedback', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  listDemands: () => apiRequest<{ items: DemandItem[]; total: number }>('/api/demands'),
  submitDemand: (payload: DemandPayload) => apiRequest<DemandItem>('/api/demands', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  setDemandVote: (demandId: string, enabled: boolean) => apiRequest<{
    demand_id: string;
    support_count: number;
    voted_by_me: boolean;
  }>(`/api/demands/${encodeURIComponent(demandId)}/vote`, {
    method: enabled ? 'PUT' : 'DELETE',
  }),
};
