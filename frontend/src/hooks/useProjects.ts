import { useAsync } from './useAsync';
import { load } from '@/services/data';
import type { Project } from '@/types/project';
export const useProjects = () => useAsync(() => load<Project[]>('/api/projects'));
