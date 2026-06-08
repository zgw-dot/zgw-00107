import request from './interceptor'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function getCurrentUser() {
  return request.get('/auth/user')
}

export function getUsers() {
  return request.get('/users')
}
