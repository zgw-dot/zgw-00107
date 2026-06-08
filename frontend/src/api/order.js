import request from './interceptor'

export function getOrders() {
  return request.get('/orders')
}

export function getOrderDetail(id) {
  return request.get(`/orders/${id}`)
}

export function createOrder(data) {
  return request.post('/orders', data)
}

export function approveOrder(id, reason) {
  return request.post(`/orders/${id}/approve`, { reason })
}

export function rejectOrder(id, reason) {
  return request.post(`/orders/${id}/reject`, { reason })
}

export function receiveOrder(id, reason) {
  return request.post(`/orders/${id}/receive`, { reason })
}

export function returnOrder(id, data) {
  return request.post(`/orders/${id}/return`, data)
}

export function damageOrder(id, data) {
  return request.post(`/orders/${id}/damage`, data)
}

export function getAuditLogs() {
  return request.get('/audit-logs')
}
