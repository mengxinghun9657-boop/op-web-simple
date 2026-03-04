/**
 * 全局错误处理工具
 * 
 * 提供统一的错误处理、重试逻辑和用户友好的错误提示
 */

let toastInstance = null;

/**
 * 设置 Toast 实例
 */
export function setToastInstance(instance) {
  toastInstance = instance;
}

/**
 * 显示错误提示
 */
export function showError(error, options = {}) {
  const errorInfo = parseError(error);
  
  if (toastInstance) {
    toastInstance.addToast({
      type: 'error',
      title: options.title || errorInfo.title,
      message: errorInfo.message,
      retryable: options.retryable || false,
      retryFn: options.retryFn || null,
      duration: options.duration || 5000
    });
  } else {
    // 降级到 alert
    alert(`${errorInfo.title}: ${errorInfo.message}`);
  }
}

/**
 * 显示成功提示
 */
export function showSuccess(message, options = {}) {
  if (toastInstance) {
    toastInstance.addToast({
      type: 'success',
      title: options.title || '成功',
      message: message,
      duration: options.duration || 3000
    });
  }
}

/**
 * 显示警告提示
 */
export function showWarning(message, options = {}) {
  if (toastInstance) {
    toastInstance.addToast({
      type: 'warning',
      title: options.title || '警告',
      message: message,
      duration: options.duration || 4000
    });
  }
}

/**
 * 显示信息提示
 */
export function showInfo(message, options = {}) {
  if (toastInstance) {
    toastInstance.addToast({
      type: 'info',
      title: options.title || '提示',
      message: message,
      duration: options.duration || 3000
    });
  }
}

/**
 * 解析错误对象，返回用户友好的错误信息
 */
export function parseError(error) {
  // 网络错误
  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return {
        title: '请求超时',
        message: '服务器响应超时，请检查网络连接或稍后重试',
        code: 'TIMEOUT'
      };
    }
    return {
      title: '网络错误',
      message: '无法连接到服务器，请检查网络连接',
      code: 'NETWORK_ERROR'
    };
  }

  const status = error.response.status;
  const data = error.response.data;

  // HTTP 状态码错误
  switch (status) {
    case 400:
      return {
        title: '请求错误',
        message: data?.detail || data?.message || '请求参数有误',
        code: 'BAD_REQUEST'
      };
    
    case 401:
      return {
        title: '未授权',
        message: '登录已过期，请重新登录',
        code: 'UNAUTHORIZED'
      };
    
    case 403:
      return {
        title: '权限不足',
        message: '您没有权限执行此操作',
        code: 'FORBIDDEN'
      };
    
    case 404:
      return {
        title: '资源不存在',
        message: '请求的资源不存在',
        code: 'NOT_FOUND'
      };
    
    case 500:
      return {
        title: '服务器错误',
        message: data?.detail || '服务器内部错误，请稍后重试',
        code: 'SERVER_ERROR'
      };
    
    case 502:
    case 503:
    case 504:
      return {
        title: '服务不可用',
        message: '服务暂时不可用，请稍后重试',
        code: 'SERVICE_UNAVAILABLE'
      };
    
    default:
      return {
        title: '请求失败',
        message: data?.detail || data?.message || `请求失败 (${status})`,
        code: 'UNKNOWN_ERROR'
      };
  }
}

/**
 * 带重试的请求包装器
 */
export async function withRetry(requestFn, options = {}) {
  const {
    maxRetries = 2,
    retryDelay = 1000,
    retryableErrors = ['TIMEOUT', 'NETWORK_ERROR', 'SERVICE_UNAVAILABLE'],
    onRetry = null
  } = options;

  let lastError = null;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error;
      const errorInfo = parseError(error);
      
      // 检查是否可重试
      const isRetryable = retryableErrors.includes(errorInfo.code);
      const hasMoreAttempts = attempt < maxRetries;
      
      if (isRetryable && hasMoreAttempts) {
        if (onRetry) {
          onRetry(attempt + 1, maxRetries);
        }
        
        // 等待后重试
        await new Promise(resolve => setTimeout(resolve, retryDelay * (attempt + 1)));
        continue;
      }
      
      // 不可重试或已达最大重试次数
      throw error;
    }
  }
  
  throw lastError;
}

/**
 * 超时控制包装器
 */
export function withTimeout(promise, timeoutMs = 30000) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error('TIMEOUT'));
      }, timeoutMs);
    })
  ]);
}

/**
 * 处理 401 错误（登录过期）
 */
export function handleUnauthorized() {
  // 清除本地存储
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  
  // 跳转到登录页
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

/**
 * Axios 拦截器配置
 */
export function setupAxiosInterceptors(axios) {
  // 请求拦截器
  axios.interceptors.request.use(
    config => {
      // 添加 token
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    error => {
      return Promise.reject(error);
    }
  );

  // 响应拦截器
  axios.interceptors.response.use(
    response => response,
    error => {
      // 处理 401 错误
      if (error.response?.status === 401) {
        handleUnauthorized();
      }
      
      return Promise.reject(error);
    }
  );
}

/**
 * 全局错误处理器（用于 Vue errorHandler）
 */
export function globalErrorHandler(error, instance, info) {
  console.error('Vue Error:', error, info);
  
  // 显示错误提示
  showError(error, {
    title: '应用错误',
    message: error.message || '发生未知错误'
  });
}

/**
 * 全局未捕获的 Promise 错误处理
 */
export function setupGlobalErrorHandlers() {
  window.addEventListener('unhandledrejection', event => {
    console.error('Unhandled Promise Rejection:', event.reason);
    
    showError(event.reason, {
      title: 'Promise 错误',
      message: event.reason?.message || '发生未处理的异步错误'
    });
    
    event.preventDefault();
  });
}

export default {
  setToastInstance,
  showError,
  showSuccess,
  showWarning,
  showInfo,
  parseError,
  withRetry,
  withTimeout,
  handleUnauthorized,
  setupAxiosInterceptors,
  globalErrorHandler,
  setupGlobalErrorHandlers
};
