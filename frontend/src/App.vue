<template>
  <router-view />
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.status-tag {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
}

.status-normal {
  background: #f0f9eb;
  color: #67c23a;
}

.status-expired {
  background: #fef0f0;
  color: #f56c6c;
}

.status-rotated {
  background: #fdf6ec;
  color: #e6a23c;
}
</style>
