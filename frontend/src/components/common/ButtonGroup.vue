<template>
  <div class="button-group" :class="`button-group-${direction}`">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  direction: {
    type: String,
    default: 'horizontal',
    validator: (v) => ['horizontal', 'vertical'].includes(v)
  }
})
</script>

<style scoped>
.button-group {
  display: flex;
  gap: var(--spacing-2);
}

.button-group-horizontal {
  flex-direction: row;
}

.button-group-vertical {
  flex-direction: column;
}

:deep(.button-group .el-button) {
  min-width: 80px;
}
</style>
