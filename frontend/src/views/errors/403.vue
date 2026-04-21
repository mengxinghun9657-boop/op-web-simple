<template>
  <div class="error-page">
    <div class="error-content">
      <h1 class="error-code">403</h1>
      <p class="error-message">抱歉，您没有权限访问此页面</p>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base);
}

.error-content {
  text-align: center;
}

.error-code {
  font-size: var(--text-6xl);
  font-weight: var(--font-bold);
  color: var(--color-error);
  margin-bottom: var(--space-4);
}

.error-message {
  font-size: var(--text-xl);
  color: var(--text-tertiary);
  margin-bottom: var(--space-6);
}
</style>
