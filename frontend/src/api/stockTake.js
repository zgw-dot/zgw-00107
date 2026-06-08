import request from './interceptor'

export function getStockTakes() {
  return request.get('/stock-takes')
}

export function getStockTakeDetail(id) {
  return request.get(`/stock-takes/${id}`)
}

export function createStockTake(data) {
  return request.post('/stock-takes', data)
}

export function updateStockTake(id, data) {
  return request.post(`/stock-takes/${id}/update`, data)
}

export function confirmStockTake(id, data) {
  return request.post(`/stock-takes/${id}/confirm`, data)
}

export function cancelStockTake(id, reason) {
  return request.post(`/stock-takes/${id}/cancel`, { reason })
}
