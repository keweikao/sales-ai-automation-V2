import createClient from 'openapi-fetch';
import type { paths } from './schema';

const getBaseUrl = () => {
  if (typeof window !== 'undefined') {
    return (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
  }
  return process.env.API_URL || 'http://localhost:8000';
};

export const api = createClient<paths>({
  baseUrl: getBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

export function createAuthenticatedClient(token: string) {
  return createClient<paths>({
    baseUrl: getBaseUrl(),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });
}
