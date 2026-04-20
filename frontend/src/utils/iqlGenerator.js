/**
 * IQL Generator Utility
 * 
 * 提供IQL（icafe Query Language）语句生成、验证和解析功能
 * 严格遵循icafe语法规范
 */

/**
 * 生成时间条件IQL语句
 * 
 * @param {string} field - 时间字段名（如"最后修改时间"、"创建时间"、"完成时间"）
 * @param {Date} startDate - 开始日期
 * @param {Date} endDate - 结束日期
 * @returns {string} IQL时间条件，格式：field > "YYYY-MM-DD 00:00:00" AND field < "YYYY-MM-DD 23:59:59"
 * 
 * @example
 * const condition = generateTimeCondition('最后修改时间', new Date('2025-01-01'), new Date('2025-01-31'))
 * // 返回: 最后修改时间 > "2025-01-01 00:00:00" AND 最后修改时间 < "2025-01-31 23:59:59"
 */
export function generateTimeCondition(field, startDate, endDate) {
  if (!field || !startDate || !endDate) {
    throw new Error('field, startDate, and endDate are required')
  }

  /**
   * 格式化日期为开始时间（00:00:00）
   */
  const formatStartDate = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day} 00:00:00`
  }

  /**
   * 格式化日期为结束时间（23:59:59）
   */
  const formatEndDate = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day} 23:59:59`
  }

  const start = formatStartDate(startDate)
  const end = formatEndDate(endDate)

  // 根据icafe语法：
  // > 表示从该时间当天的 00:00:00 之后（包含当天）
  // < 表示到该时间当天的 23:59:59 之前（包含当天）
  return `${field} > "${start}" AND ${field} < "${end}"`
}

/**
 * 生成字段条件IQL语句
 * 
 * @param {string} field - 字段名（如"负责人"、"流程状态"、"类型"等）
 * @param {Array<string>} values - 值数组
 * @returns {string} IQL条件
 * 
 * @example
 * generateFieldCondition('负责人', ['v_liuxiang'])
 * // 返回: 负责人 = v_liuxiang
 * 
 * generateFieldCondition('类型', ['Bug', 'Story', 'Task'])
 * // 返回: 类型 in (Bug, Story, Task)
 */
export function generateFieldCondition(field, values) {
  if (!field) {
    throw new Error('field is required')
  }

  if (!values || values.length === 0) {
    return ''
  }

  // 对值加引号（已有引号的不重复加）
  const quote = (v) => {
    const s = String(v).trim()
    if (s.startsWith('"') && s.endsWith('"')) return s
    return `"${s}"`
  }

  // 单个值：使用 = 操作符
  if (values.length === 1) {
    return `${field} = ${quote(values[0])}`
  }

  // 多个值：使用 in 操作符
  const valueList = values.map(quote).join(', ')
  return `${field} in (${valueList})`
}

/**
 * 验证IQL语法
 * 
 * @param {string} iql - IQL语句
 * @returns {Object} 验证结果 { valid: boolean, errors: Array<string> }
 * 
 * @example
 * validateIQL('负责人 = v_liuxiang AND 类型 in (Bug, Story)')
 * // 返回: { valid: true, errors: [] }
 * 
 * validateIQL('类型 in (Bug, Story')
 * // 返回: { valid: false, errors: ['括号不匹配'] }
 */
export function validateIQL(iql) {
  if (!iql || iql.trim() === '') {
    return { valid: true, errors: [] }
  }

  const errors = []

  // 检查括号匹配
  const openParens = (iql.match(/\(/g) || []).length
  const closeParens = (iql.match(/\)/g) || []).length
  if (openParens !== closeParens) {
    errors.push('括号不匹配')
  }

  // 检查引号匹配
  const quotes = (iql.match(/"/g) || []).length
  if (quotes % 2 !== 0) {
    errors.push('引号不匹配')
  }

  // 检查操作符后是否有值
  const operatorPattern = /\s+(=|!=|>|<|>=|<=|~|!~|in|not in)\s*$/i
  if (operatorPattern.test(iql)) {
    errors.push('操作符后缺少值')
  }

  // 检查in操作符是否有括号
  const inPattern = /\s+in\s+(?!\()/gi
  if (inPattern.test(iql)) {
    errors.push('in 操作符后需要使用括号，如: in (值1, 值2)')
  }

  return {
    valid: errors.length === 0,
    errors
  }
}

/**
 * 合并时间条件到现有IQL
 * 
 * @param {string} currentIql - 当前IQL语句
 * @param {string} timeCondition - 新的时间条件
 * @param {string} timeField - 时间字段名
 * @returns {string} 合并后的IQL
 * 
 * @example
 * mergeTimeCondition('负责人 = v_liuxiang', '最后修改时间 > "2025-01-01 00:00:00" AND 最后修改时间 < "2025-01-31 23:59:59"', '最后修改时间')
 * // 返回: 负责人 = v_liuxiang AND 最后修改时间 > "2025-01-01 00:00:00" AND 最后修改时间 < "2025-01-31 23:59:59"
 */
export function mergeTimeCondition(currentIql, timeCondition, timeField) {
  if (!timeCondition) {
    return currentIql || ''
  }

  if (!currentIql || currentIql.trim() === '') {
    return timeCondition
  }

  // 移除现有的时间条件（如果存在）
  const withoutTime = removeTimeCondition(currentIql, timeField)

  // 追加新的时间条件
  if (withoutTime.trim() === '') {
    return timeCondition
  }

  return `${withoutTime} AND ${timeCondition}`
}

/**
 * 从IQL中移除时间条件
 * 
 * @param {string} iql - IQL语句
 * @param {string} timeField - 时间字段名（可选，如果不指定则移除所有时间字段的条件）
 * @returns {string} 移除时间条件后的IQL
 * 
 * @example
 * removeTimeCondition('负责人 = v_liuxiang AND 最后修改时间 > "2025-01-01 00:00:00" AND 最后修改时间 < "2025-01-31 23:59:59"', '最后修改时间')
 * // 返回: 负责人 = v_liuxiang
 */
export function removeTimeCondition(iql, timeField = null) {
  if (!iql) return ''

  // 如果指定了时间字段，只移除该字段的条件
  if (timeField) {
    // 匹配模式：时间字段 > "..." AND 时间字段 < "..."
    // 需要转义特殊字符
    const escapedField = timeField.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const pattern = new RegExp(
      `${escapedField}\\s*>\\s*"[^"]*"\\s*AND\\s*${escapedField}\\s*<\\s*"[^"]*"`,
      'gi'
    )
    let result = iql.replace(pattern, '')

    // 清理多余的AND
    result = result.replace(/\s*AND\s*AND\s*/gi, ' AND ')
    result = result.replace(/^\s*AND\s*/i, '')
    result = result.replace(/\s*AND\s*$/i, '')

    return result.trim()
  }

  // 如果没有指定字段，移除所有时间条件
  const timeFields = ['创建时间', '最后修改时间', '完成时间']
  let result = iql

  timeFields.forEach(field => {
    result = removeTimeCondition(result, field)
  })

  return result.trim()
}

/**
 * 解析IQL语句（简化版）
 * 尝试提取字段条件，用于同步查询构建器
 * 
 * @param {string} iql - IQL语句
 * @returns {Object} 解析出的条件对象
 * 
 * @example
 * parseIQL('负责人 in (v_liuxiang, v_zhangsan) AND 流程状态 in (新建, 进行中)')
 * // 返回: { responsiblePeople: ['v_liuxiang', 'v_zhangsan'], status: ['新建', '进行中'], type: [], labels: [], plan: [] }
 */
export function parseIQL(iql) {
  // 简单的解析逻辑，用于同步查询构建器
  // 注意：这是一个简化版本，不能处理所有复杂情况
  const conditions = {
    responsiblePeople: [],
    status: [],
    type: [],
    labels: [],
    plan: []
  }

  if (!iql || iql.trim() === '') {
    return conditions
  }

  // 尝试提取 in (...) 格式的条件
  const inPattern = /(\S+)\s+in\s+\(([^)]+)\)/gi
  let match

  while ((match = inPattern.exec(iql)) !== null) {
    const field = match[1]
    const values = match[2].split(',').map(v => v.trim())

    if (field === '负责人') {
      conditions.responsiblePeople = values
    } else if (field === '流程状态') {
      conditions.status = values
    } else if (field === '类型') {
      conditions.type = values
    } else if (field.includes('Label') || field.includes('标签')) {
      conditions.labels = values
    } else if (field === '所属计划') {
      conditions.plan = values
    }
  }

  // 尝试提取 = 格式的单值条件
  const equalPattern = /(\S+)\s+=\s+(\S+)/gi

  while ((match = equalPattern.exec(iql)) !== null) {
    const field = match[1]
    const value = match[2]

    if (field === '负责人' && conditions.responsiblePeople.length === 0) {
      conditions.responsiblePeople = [value]
    } else if (field === '流程状态' && conditions.status.length === 0) {
      conditions.status = [value]
    } else if (field === '类型' && conditions.type.length === 0) {
      conditions.type = [value]
    } else if ((field.includes('Label') || field.includes('标签')) && conditions.labels.length === 0) {
      conditions.labels = [value]
    } else if (field === '所属计划' && conditions.plan.length === 0) {
      conditions.plan = [value]
    }
  }

  return conditions
}
