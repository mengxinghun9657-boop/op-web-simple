import axios from '@/utils/axios'

/**
 * 系统配置管理API
 * 集中管理CMDB、监控、分析等模块的配置
 */

// 保存系统配置
export const saveConfig = (module, config) => {
  return axios.post('/api/v1/config/save', {
    module,
    config
  })
}

// 加载系统配置
export const loadConfig = (module) => {
  return axios.get('/api/v1/config/load', {
    params: { module }
  })
}

// 测试iCafe连接
export const testICafeConnection = () => {
  return axios.post('/api/v1/config/icafe/test-connection')
}
