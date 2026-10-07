import { useAsync } from './useAsync';
import { load } from '@/services/data';
import { projectsMock } from '@/services/mocks/projects.mock';
import type { Project } from '@/types/project';
export const useProjects = () => useAsync(() => load<Project[]>('/api/projects', projectsMock));
