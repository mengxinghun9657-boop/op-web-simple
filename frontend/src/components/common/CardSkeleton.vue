<template>
  <div class="card-skeleton">
    <div class="skeleton-header">
      <Skeleton width="120px" height="16px" />
      <Skeleton width="36px" height="36px" border-radius="8px" />
    </div>
    <Skeleton width="80px" height="32px" style="margin-top: 12px" />
  </div>
</template>

<script setup>
import Skeleton from './Skeleton.vue'
</script>

<style scoped>
.card-skeleton {
  background: var(--bg-container);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
}
.skeleton-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
</style>
