/**
 * Contrato de la API de Django, tipado.
 *
 * Estos tipos son un espejo manual de los serializadores del backend. Al ser
 * un monorepo, cuando cambia un serializador el tipo se actualiza en el mismo
 * commit y `astro check` avisa si alguna página quedó desalineada.
 */

export type Language = 'es' | 'en';

export interface Technology {
  slug: string;
  name: string;
  category: 'mobile' | 'backend' | 'frontend' | 'devops' | 'database' | 'design';
  color: string;
  icon: string;
}

export interface ProjectLinks {
  repo?: string;
  live?: string;
  store?: string;
  video?: string;
}

export interface ProjectSummary {
  slug: string;
  title: string;
  tagline: string;
  summary: string;
  cover_url: string | null;
  year: number;
  featured: boolean;
  technologies: Technology[];
  links: ProjectLinks;
}

export interface ProjectDetail extends ProjectSummary {
  body_html: string;
  role: string;
  images: { url: string | null; caption: string }[];
  metrics: { label: string; value: string }[];
}

export interface Category {
  slug: string;
  name: string;
  description: string;
}

export interface Tag {
  slug: string;
  name: string;
}

export interface PostSummary {
  slug: string;
  title: string;
  excerpt: string;
  cover_url: string | null;
  category: Category;
  tags: Tag[];
  published_at: string;
  reading_minutes: number;
}

export interface PostDetail extends PostSummary {
  body_html: string;
  views: number;
}

export interface SocialLink {
  name: string;
  url: string;
  icon: string;
}

export interface Skill {
  name: string;
  level: number;
  is_primary: boolean;
}

export interface SkillGroup {
  name: string;
  skills: Skill[];
}

export interface ExperienceItem {
  role: string;
  organization: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  description: string;
  highlights: string[];
}

export interface Profile {
  full_name: string;
  role: string;
  headline: string;
  bio_html: string;
  email: string;
  phone: string;
  location: string;
  availability: string;
  avatar_url: string | null;
  cv_url: string | null;
  socials: SocialLink[];
  skill_groups: SkillGroup[];
  experience: ExperienceItem[];
}

export interface Game {
  slug: string;
  kind: 'quiz' | 'arcade';
  name: string;
  description: string;
  icon: string;
}

export interface QuizOption {
  id: number;
  text: string;
}

export interface QuizQuestion {
  id: number;
  text: string;
  difficulty: number;
  points: number;
  options: QuizOption[];
}

export interface Score {
  nickname: string;
  score: number;
  duration_ms: number;
  meta: Record<string, number>;
  created_at: string;
}

export interface LiveMetrics {
  cpu_percent: number;
  memory: { used_mb: number; total_mb: number; percent: number };
  disk: { used_gb: number; total_gb: number; percent: number };
  load_1m: number;
  uptime_seconds: number;
  measured_at: string;
}

export interface MetricSnapshot {
  cpu_percent: number;
  mem_used_mb: number;
  mem_total_mb: number;
  disk_used_gb: number;
  disk_total_gb: number;
  load_1m: number;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  detail: string;
  code: string;
  errors: Record<string, string[]>;
}
