<template>
  <router-view />
  <ErrorToast ref="errorToast" />
</template>

<script>
import { ref, onMounted } from 'vue';
import ErrorToast from './components/common/ErrorToast.vue';
import errorHandler from './utils/errorHandler';

export default {
  name: 'App',
  components: {
    ErrorToast
  },
  setup() {
    const errorToast = ref(null);

    onMounted(() => {
      // 设置全局 Toast 实例
      if (errorToast.value) {
        errorHandler.setToastInstance(errorToast.value);
      }
    });

    return {
      errorToast
    };
  }
};
</script>

<style>
/* 全局样式已在 main.css 中定义 */
#app {
  width: 100%;
  height: 100vh;
}
</style>