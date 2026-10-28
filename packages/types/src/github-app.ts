export type TGithubInstallation = {
  id: string;
  installation_id: number;
  account_login: string;
  account_type: "User" | "Organization";
  suspended_at: string | null;
  created_at: string;
};

export type TGithubIntegrationStatus = {
  configured: boolean;
  app_slug: string | null;
  install_url: string | null;
  installation: TGithubInstallation | null;
};

export type TGithubAvailableRepository = {
  id: number;
  full_name: string;
  private: boolean;
  html_url: string;
  default_branch: string;
  linked_project_id: string | null;
};

export type TGithubLinkedRepository = {
  id: string;
  project: string;
  repo_id: number;
  full_name: string;
  private: boolean;
  html_url: string;
  default_branch: string;
  is_active: boolean;
  created_at: string;
};

export type TGithubStateMapping = {
  pr_opened_state: string | null;
  pr_merged_state: string | null;
  issue_closed_state: string | null;
  issue_reopened_state: string | null;
  auto_create_issues: boolean;
  sync_comments: boolean;
};

export type TGithubPullRequestState = "open" | "draft" | "merged" | "closed";

export type TGithubPullRequestLink = {
  id: string;
  pr_number: number;
  title: string;
  url: string;
  author_login: string;
  author_avatar_url: string;
  state: TGithubPullRequestState;
  head_branch: string;
  repository_full_name: string;
  merged_at: string | null;
  gh_updated_at: string;
};

export type TGithubIssueLink = {
  id: string;
  gh_issue_number: number;
  url: string;
  gh_state: "open" | "closed";
  repository_full_name: string;
};

export type TWorkItemGithubLinks = {
  pull_requests: TGithubPullRequestLink[];
  issue_link: TGithubIssueLink | null;
};
