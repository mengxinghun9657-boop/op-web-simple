# 前端错误处理使用指南

## 概述

前端错误处理系统提供统一的错误提示、重试逻辑和超时控制。

## 组件

### 1. ErrorToast 组件

全局错误提示组件，已在 `App.vue` 中注册。

### 2. errorHandler 工具类

提供错误处理相关的工具函数。

## 使用方法

### 基本错误提示

```javascript
import { showError, showSuccess, showWarning, showInfo } from '@/utils/errorHandler';

// 显示错误
showError(error, {
  title: '操作失败',
  retryable: true,
  retryFn: () => {
    // 重试逻辑
  }
});

// 显示成功
showSuccess('操作成功');

// 显示警告
showWarning('请注意...');

// 显示信息
showInfo('提示信息');
```

### 带重试的请求

```javascript
import { withRetry } from '@/utils/errorHandler';
import axios from '@/utils/axios';

async function loadData() {
  try {
    const data = await withRetry(
      () => axios.get('/api/v1/data'),
      {
        maxRetries: 2,
        retryDelay: 1000,
        onRetry: (attempt, maxRetries) => {
          console.log(`重试 ${attempt}/${maxRetries}`);
        }
      }
    );
    return data;
  } catch (error) {
    showError(error, {
      title: '加载数据失败',
      retryable: true,
      retryFn: loadData
    });
  }
}
```

### 超时控制

```javascript
import { withTimeout } from '@/utils/errorHandler';
import axios from '@/utils/axios';

async function loadLargeData() {
  try {
    const data = await withTimeout(
      axios.get('/api/v1/large-data'),
      30000 // 30秒超时
    );
    return data;
  } catch (error) {
    if (error.message === 'TIMEOUT') {
      showError(error, {
        title: '请求超时',
        message: '数据加载时间过长，请稍后重试'
      });
    } else {
      showError(error);
    }
  }
}
```

### 在组件中使用

```vue
<template>
  <div>
    <button @click="handleSubmit">提交</button>
  </div>
</template>

<script>
import { showError, showSuccess, withRetry } from '@/utils/errorHandler';
import axios from '@/utils/axios';

export default {
  setup() {
    const handleSubmit = async () => {
      try {
        await withRetry(
          () => axios.post('/api/v1/submit', { data: '...' }),
          {
            maxRetries: 2,
            onRetry: (attempt) => {
              showInfo(`正在重试 (${attempt}/2)...`);
            }
          }
        );
        
        showSuccess('提交成功');
      } catch (error) {
        showError(error, {
          title: '提交失败',
          retryable: true,
          retryFn: handleSubmit
        });
      }
    };

    return {
      handleSubmit
    };
  }
};
</script>
```

## 错误类型

系统会自动识别以下错误类型：

- `TIMEOUT`: 请求超时
- `NETWORK_ERROR`: 网络错误
- `BAD_REQUEST`: 请求参数错误 (400)
- `UNAUTHORIZED`: 未授权 (401)
- `FORBIDDEN`: 权限不足 (403)
- `NOT_FOUND`: 资源不存在 (404)
- `SERVER_ERROR`: 服务器错误 (500)
- `SERVICE_UNAVAILABLE`: 服务不可用 (502/503/504)

## 自动处理

以下错误会被自动处理：

1. **401 未授权**: 自动跳转到登录页
2. **网络错误**: 显示网络连接提示
3. **超时错误**: 显示超时提示
4. **未捕获的 Promise 错误**: 全局捕获并显示

## 配置

### Axios 拦截器

已在 `main.js` 中自动配置：

```javascript
import errorHandler from './utils/errorHandler';
import axios from './utils/axios';

errorHandler.setupAxiosInterceptors(axios);
```

### 全局错误处理

已在 `main.js` 中自动配置：

```javascript
app.config.errorHandler = errorHandler.globalErrorHandler;
errorHandler.setupGlobalErrorHandlers();
```

## 注意事项

1. **不要重复处理错误**: axios 拦截器已经处理了基本错误，组件中只需处理特定业务逻辑
2. **合理使用重试**: 只对网络错误、超时等临时性错误使用重试
3. **提供友好的错误信息**: 使用 `title` 和 `message` 参数提供清晰的错误说明
4. **避免过度提示**: 对于预期内的错误（如表单验证），使用表单验证而不是错误提示

## 示例：完整的数据加载流程

```vue
<template>
  <div>
    <div v-if="loading">加载中...</div>
    <div v-else-if="error">
      <p>{{ error }}</p>
      <button @click="loadData">重试</button>
    </div>
    <div v-else>
      <!-- 数据展示 -->
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import { showError, withRetry, withTimeout } from '@/utils/errorHandler';
import axios from '@/utils/axios';

export default {
  setup() {
    const loading = ref(false);
    const error = ref(null);
    const data = ref(null);

    const loadData = async () => {
      loading.value = true;
      error.value = null;

      try {
        // 带超时和重试的请求
        data.value = await withTimeout(
          withRetry(
            () => axios.get('/api/v1/data'),
            {
              maxRetries: 2,
              retryDelay: 1000
            }
          ),
          30000
        );
      } catch (err) {
        error.value = '加载失败';
        showError(err, {
          title: '加载数据失败',
          retryable: true,
          retryFn: loadData
        });
      } finally {
        loading.value = false;
      }
    };

    // 初始加载
    loadData();

    return {
      loading,
      error,
      data,
      loadData
    };
  }
};
</script>
```
