// src/utils/api.js
// Lightweight API helper that auto-attaches the JWT token from localStorage

// Use VITE_API_URL in production (Vercel), otherwise fallback to relative /api/v1 (which uses Vite proxy locally)
const API_DOMAIN = import.meta.env.VITE_API_URL || '';
const BASE_URL = `${API_DOMAIN}/api/v1`;

function getHeaders(contentType = 'application/json') {
  const token = localStorage.getItem('satquery_access_token');
  const headers = {};
  if (contentType !== 'multipart') {
    headers['Content-Type'] = contentType;
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// On 401, clear the expired token and redirect to /auth
function handle401() {
  localStorage.removeItem('satquery_access_token');
  localStorage.removeItem('satquery_refresh_token');
  window.location.href = '/auth';
}

async function handleResponse(res) {
  if (res.status === 401) {
    handle401();
    throw new Error('Session expired. Please log in again.');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    if (Array.isArray(err.detail)) {
      throw new Error(err.detail.map(e => e.msg).join(', '));
    }
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export async function apiGet(path) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'GET',
    headers: getHeaders(),
  });
  return handleResponse(res);
}

export async function apiPost(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}

export async function apiPut(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}

export async function apiUpload(path, formData) {
  const token = localStorage.getItem('satquery_access_token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: formData,
  });
  return handleResponse(res);
}
