import request from './interceptor'

export function getBatches() {
  return request.get('/batches')
}

export function getAvailableBatches() {
  return request.get('/batches/available')
}

export function getBatchDetail(id) {
  return request.get(`/batches/${id}`)
}

export function createBatch(data) {
  return request.post('/batches', data)
}

export function rotateBatch(id, data) {
  return request.post(`/batches/${id}/rotate`, data)
}

export function exportBatches() {
  return request.get('/batches/export', {
    responseType: 'blob'
  })
}

export function importBatches(file, reason) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('reason', reason)
  return request.post('/batches/import', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
