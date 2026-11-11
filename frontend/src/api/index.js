// API kontraktas (spec. 10 skyrius)
import { api } from './client.js'

export const auth = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
}

export const queues = {
  map: (bbox, zoom) => api.get('/queues/map', { ...bbox, zoom }),
  create: (data) => api.post('/queues', data),
  get: (id) => api.get(`/queues/${id}`),
  checkin: (id) => api.post(`/queues/${id}/checkin`),
  checkout: (id) => api.post(`/queues/${id}/checkout`),
  review: (id, score) => api.post(`/queues/${id}/review`, { score }),
}

export const comments = {
  list: (queueId, page = 1) => api.get(`/queues/${queueId}/comments`, { page }),
  create: (queueId, text) => api.post(`/queues/${queueId}/comments`, { text }),
  remove: (id) => api.delete(`/comments/${id}`),
  like: (id) => api.post(`/comments/${id}/like`),
  unlike: (id) => api.delete(`/comments/${id}/like`),
}

export const me = {
  queues: (page = 1) => api.get('/me/queues', { page }),
}

export const reports = {
  activity: (params) => api.get('/reports/activity', params),
  checkins: (params) => api.get('/reports/checkins', params),
  waitTimes: (queueId) => api.get('/reports/wait-times', { queue_id: queueId }),
  popularQueues: (days = 7) => api.get('/reports/popular-queues', { days }),
  checkoutRate: (params) => api.get('/reports/checkout-rate', params),
  activityByAge: () => api.get('/reports/activity-by-age'),
}
