/**
 * 路由规则创建智能辅助 API
 * 
 * 提供自然语言转换、验证、测试、智能辅助等功能
 */

import axios from 'axios'

/**
 * 自然语言转换为正则表达式
 * @param {string} naturalLanguage - 自然语言描述
 * @param {string} intentType - 意图类型
 * @returns {Promise<Object>} 转换结果
 */
export const convertNaturalLanguage = (naturalLanguage, intentType) => {
  return axios.post('/api/v1/routing/convert', {
    natural_language: naturalLanguage,
    intent_type: intentType
  })
}

/**
 * 验证正则表达式
 * @param {string} regex - 正则表达式
 * @param {string} intentType - 意图类型
 * @param {number} excludeRuleId - 排除的规则ID（编辑时使用）
 * @returns {Promise<Object>} 验证结果
 */
export const validateRegex = (regex, intentType, excludeRuleId = null) => {
  return axios.post('/api/v1/routing/validate', {
    regex,
    intent_type: intentType,
    exclude_rule_id: excludeRuleId
  })
}

/**
 * 测试正则表达式匹配
 * @param {string} regex - 正则表达式
 * @param {Array<string>} testQueries - 测试查询列表
 * @returns {Promise<Object>} 测试结果
 */
export const testMatch = (regex, testQueries) => {
  return axios.post('/api/v1/routing/test-match', {
    regex,
    test_queries: testQueries
  })
}

/**
 * 提取关键词
 * @param {string} pattern - 匹配模式
 * @param {string} patternType - 模式类型：natural_language 或 regex
 * @returns {Promise<Object>} 关键词列表
 */
export const extractKeywords = (pattern, patternType) => {
  return axios.post('/api/v1/routing/extract-keywords', {
    pattern,
    pattern_type: patternType
  })
}

/**
 * 推荐相关表
 * @param {Array<string>} keywords - 关键词列表
 * @param {string} intentType - 意图类型
 * @returns {Promise<Object>} 推荐表列表
 */
export const recommendTables = (keywords, intentType) => {
  return axios.get('/api/v1/routing/recommend-tables', {
    params: {
      keywords: keywords.join(','),
      intent_type: intentType
    }
  })
}

/**
 * 获取规则模板列表
 * @param {string} category - 模板分类（可选）
 * @returns {Promise<Object>} 模板列表
 */
export const getTemplates = (category = null) => {
  return axios.get('/api/v1/routing/templates', {
    params: category ? { category } : {}
  })
}

/**
 * 生成规则描述
 * @param {string} pattern - 匹配模式
 * @param {string} intentType - 意图类型
 * @param {Array<string>} keywords - 关键词列表（可选）
 * @returns {Promise<Object>} 生成的描述
 */
export const generateDescription = (pattern, intentType, keywords = null) => {
  return axios.post('/api/v1/routing/generate-description', {
    pattern,
    intent_type: intentType,
    keywords
  })
}

/**
 * 建议优先级
 * @param {string} pattern - 匹配模式
 * @param {string} intentType - 意图类型
 * @param {Array<string>} keywords - 关键词列表（可选）
 * @returns {Promise<Object>} 优先级建议
 */
export const suggestPriority = (pattern, intentType, keywords = null) => {
  return axios.post('/api/v1/routing/suggest-priority', {
    pattern,
    intent_type: intentType,
    keywords
  })
}

/**
 * 预测规则影响
 * @param {string} pattern - 匹配模式
 * @param {string} intentType - 意图类型
 * @returns {Promise<Object>} 影响预测结果
 */
export const predictImpact = (pattern, intentType) => {
  return axios.post('/api/v1/routing/predict-impact', {
    pattern,
    intent_type: intentType
  })
}

/**
 * 保存草稿
 * @param {Object} draftData - 草稿数据
 * @returns {Promise<Object>} 保存结果
 */
export const saveDraft = (draftData) => {
  return axios.post('/api/v1/routing/drafts', {
    draft_data: draftData
  })
}

/**
 * 获取草稿列表
 * @returns {Promise<Object>} 草稿列表
 */
export const getDrafts = () => {
  return axios.get('/api/v1/routing/drafts')
}

/**
 * 获取草稿详情
 * @param {number} draftId - 草稿ID
 * @returns {Promise<Object>} 草稿详情
 */
export const getDraft = (draftId) => {
  return axios.get(`/api/v1/routing/drafts/${draftId}`)
}

/**
 * 删除草稿
 * @param {number} draftId - 草稿ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteDraft = (draftId) => {
  return axios.delete(`/api/v1/routing/drafts/${draftId}`)
}

export default {
  convertNaturalLanguage,
  validateRegex,
  testMatch,
  extractKeywords,
  recommendTables,
  getTemplates,
  generateDescription,
  suggestPriority,
  predictImpact,
  saveDraft,
  getDrafts,
  getDraft,
  deleteDraft
}
