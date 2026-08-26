export interface RecentActivityItem {
  id: string;
  event_name: string;
  domain: string;
  icon: string;
  title: string;
  description: string;
  action_label: string;
  href: string;
  occurred_at: string;
}

export interface RecentActivityList {
  title: string;
  description: string;
  empty_text: string;
  items: RecentActivityItem[];
}
