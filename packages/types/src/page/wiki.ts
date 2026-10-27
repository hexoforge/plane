import type { TLogoProps } from "../common";

export type TWikiAccess = 0 | 1;

export type TPageShareRole = 0 | 1 | 2;

export type TPageCollection = {
  id: string;
  workspace: string;
  project: string | null;
  name: string;
  description: string;
  access: TWikiAccess;
  owned_by: string;
  sort_order: number;
  is_default: boolean;
  archived_at: string | null;
  page_count?: number;
  created_at: string;
  updated_at: string;
};

export type TPageShare = {
  id: string;
  page: string;
  user: string;
  role: TPageShareRole;
  created_at: string;
};

export type TPageComment = {
  id: string;
  page: string;
  actor: string;
  comment_html: string;
  comment_json: object;
  parent: string | null;
  resolved: boolean;
  created_at: string;
  updated_at: string;
};

export type TWikiTreeNode = {
  id: string;
  name: string | null;
  parent: string | null;
  collection: string | null;
  access: TWikiAccess;
  sort_order: number;
  archived_at: string | null;
  logo_props?: TLogoProps;
};

export type TWikiTree = {
  collections: TPageCollection[];
  pages: TWikiTreeNode[];
};
