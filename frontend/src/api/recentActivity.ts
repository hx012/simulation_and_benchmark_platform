import type { RecentActivityList } from '../types/recentActivity';
import { apiRequest } from './client';


export const recentActivityApi = {
  list() {
    return apiRequest<RecentActivityList>('/api/recent-activities');
  },
};
