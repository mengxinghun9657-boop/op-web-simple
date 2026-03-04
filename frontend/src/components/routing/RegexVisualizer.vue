<template>
  <div class="regex-visualizer">
    <!-- 可视化显示区域 -->
    <div class="visualizer-container" v-loading="loading">
      <el-empty v-if="!regex" description="请输入正则表达式" />
      
      <div v-else class="visualization-content">
        <!-- 正则表达式分解显示 -->
        <div class="regex-breakdown">
          <div class="breakdown-title">正则表达式分解</div>
          <div class="breakdown-content">
            <div
              v-for="(element, index) in regexElements"
              :key="index"
              class="regex-element"
              :class="{ 'highlighted': highlightedIndex === index }"
              @mouseenter="highlightElement(index)"
              @mouseleave="clearHighlight"
            >
              <div class="element-pattern">{{ element.pattern }}</div>
              <div class="element-type">{{ element.type }}</div>
              <div class="element-description">{{ element.description }}</div>
            </div>
          </div>
        </div>

        <!-- 铁路图显示（简化版） -->
        <div class="railroad-diagram">
          <div class="diagram-title">结构图</div>
          <div class="diagram-content">
            <svg :width="diagramWidth" :height="diagramHeight" class="diagram-svg">
              <!-- 绘制铁路图元素 -->
              <g v-for="(node, index) in diagramNodes" :key="index">
                <!-- 连接线 -->
                <line
                  v-if="index > 0"
                  :x1="diagramNodes[index - 1].x + diagramNodes[index - 1].width"
                  :y1="diagramNodes[index - 1].y + 20"
                  :x2="node.x"
                  :y2="node.y + 20"
                  stroke="#409eff"
                  stroke-width="2"
                />
                
                <!-- 节点 -->
                <rect
                  :x="node.x"
                  :y="node.y"
                  :width="node.width"
                  :height="40"
                  :fill="node.color"
                  stroke="#409eff"
                  stroke-width="2"
                  rx="5"
                  class="diagram-node"
                  :class="{ 'highlighted': highlightedIndex === index }"
                  @mouseenter="highlightElement(index)"
                  @mouseleave="clearHighlight"
                />
                
                <!-- 节点文本 -->
                <text
                  :x="node.x + node.width / 2"
                  :y="node.y + 25"
                  text-anchor="middle"
                  fill="#333"
                  font-size="12"
                >
                  {{ node.label }}
                </text>
              </g>
            </svg>
          </div>
        </div>

        <!-- 复杂度评分 -->
        <div class="complexity-score">
          <div class="score-title">复杂度评分</div>
          <div class="score-content">
            <el-progress
              :percentage="complexityPercentage"
              :color="complexityColor"
              :stroke-width="20"
            >
              <span class="score-text">{{ complexityScore }}/10</span>
            </el-progress>
            <div class="score-description">
              {{ complexityDescription }}
            </div>
          </div>
        </div>

        <!-- 正则元素统计 -->
        <div class="element-statistics">
          <div class="stat-title">元素统计</div>
          <div class="stat-content">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-statistic title="字符类" :value="statistics.characterClasses" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="量词" :value="statistics.quantifiers" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="分组" :value="statistics.groups" />
              </el-col>
            </el-row>
            <el-row :gutter="16" style="margin-top: 16px;">
              <el-col :span="8">
                <el-statistic title="选择符" :value="statistics.alternations" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="锚点" :value="statistics.anchors" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="嵌套深度" :value="statistics.nestingDepth" />
              </el-col>
            </el-row>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  regex: {
    type: String,
    default: ''
  },
  complexityScore: {
    type: Number,
    default: 0
  }
})

// 数据
const loading = ref(false)
const highlightedIndex = ref(-1)
const regexElements = ref([])
const diagramNodes = ref([])
const statistics = ref({
  characterClasses: 0,
  quantifiers: 0,
  groups: 0,
  alternations: 0,
  anchors: 0,
  nestingDepth: 0
})

// 计算属性
const complexityPercentage = computed(() => {
  return Math.min((props.complexityScore / 10) * 100, 100)
})

const complexityColor = computed(() => {
  if (props.complexityScore <= 3) return '#67c23a'
  if (props.complexityScore <= 6) return '#e6a23c'
  return '#f56c6c'
})

const complexityDescription = computed(() => {
  if (props.complexityScore <= 3) return '简单 - 易于理解和维护'
  if (props.complexityScore <= 6) return '中等 - 需要一定的正则表达式知识'
  return '复杂 - 建议简化或添加详细注释'
})

const diagramWidth = computed(() => {
  return Math.max(600, diagramNodes.value.length * 100)
})

const diagramHeight = computed(() => {
  return 100
})

// 方法
const parseRegex = (regex) => {
  if (!regex) {
    regexElements.value = []
    diagramNodes.value = []
    return
  }

  const elements = []
  const nodes = []
  let x = 20
  
  // 正则表达式元素类型定义
  const elementTypes = {
    literal: { type: '字面量', color: '#e3f2fd' },
    characterClass: { type: '字符类', color: '#fff3e0' },
    quantifier: { type: '量词', color: '#f3e5f5' },
    group: { type: '分组', color: '#e8f5e9' },
    anchor: { type: '锚点', color: '#fce4ec' },
    alternation: { type: '选择符', color: '#fff9c4' }
  }

  // 简化的正则解析（实际应用中可以使用更复杂的解析器）
  let i = 0
  let groupDepth = 0
  let maxDepth = 0
  
  const stats = {
    characterClasses: 0,
    quantifiers: 0,
    groups: 0,
    alternations: 0,
    anchors: 0,
    nestingDepth: 0
  }

  while (i < regex.length) {
    const char = regex[i]
    let element = null
    let nodeWidth = 60

    if (char === '\\' && i + 1 < regex.length) {
      // 转义字符
      const nextChar = regex[i + 1]
      const escapeMap = {
        'd': '数字',
        'w': '单词字符',
        's': '空白字符',
        'D': '非数字',
        'W': '非单词字符',
        'S': '非空白字符',
        'b': '单词边界',
        'B': '非单词边界'
      }
      
      element = {
        pattern: `\\${nextChar}`,
        type: escapeMap[nextChar] ? elementTypes.characterClass.type : elementTypes.literal.type,
        description: escapeMap[nextChar] || `转义字符 ${nextChar}`,
        color: escapeMap[nextChar] ? elementTypes.characterClass.color : elementTypes.literal.color
      }
      
      if (escapeMap[nextChar]) stats.characterClasses++
      i += 2
      nodeWidth = 80
    } else if (char === '[') {
      // 字符类
      const endIndex = regex.indexOf(']', i)
      if (endIndex !== -1) {
        const classContent = regex.substring(i, endIndex + 1)
        element = {
          pattern: classContent,
          type: elementTypes.characterClass.type,
          description: '字符类 - 匹配括号内的任意字符',
          color: elementTypes.characterClass.color
        }
        stats.characterClasses++
        i = endIndex + 1
        nodeWidth = Math.min(classContent.length * 10 + 40, 150)
      }
    } else if (char === '(') {
      // 分组
      groupDepth++
      maxDepth = Math.max(maxDepth, groupDepth)
      element = {
        pattern: '(',
        type: elementTypes.group.type,
        description: '分组开始',
        color: elementTypes.group.color
      }
      stats.groups++
      i++
    } else if (char === ')') {
      // 分组结束
      groupDepth--
      element = {
        pattern: ')',
        type: elementTypes.group.type,
        description: '分组结束',
        color: elementTypes.group.color
      }
      i++
    } else if (['+', '*', '?', '{'].includes(char)) {
      // 量词
      let quantifier = char
      if (char === '{') {
        const endIndex = regex.indexOf('}', i)
        if (endIndex !== -1) {
          quantifier = regex.substring(i, endIndex + 1)
          i = endIndex + 1
        }
      } else {
        i++
      }
      
      const quantifierDesc = {
        '+': '一次或多次',
        '*': '零次或多次',
        '?': '零次或一次'
      }
      
      element = {
        pattern: quantifier,
        type: elementTypes.quantifier.type,
        description: quantifierDesc[char] || '指定次数',
        color: elementTypes.quantifier.color
      }
      stats.quantifiers++
      nodeWidth = 50
    } else if (char === '^' || char === '$') {
      // 锚点
      element = {
        pattern: char,
        type: elementTypes.anchor.type,
        description: char === '^' ? '字符串开始' : '字符串结束',
        color: elementTypes.anchor.color
      }
      stats.anchors++
      i++
      nodeWidth = 50
    } else if (char === '|') {
      // 选择符
      element = {
        pattern: '|',
        type: elementTypes.alternation.type,
        description: '或',
        color: elementTypes.alternation.color
      }
      stats.alternations++
      i++
      nodeWidth = 40
    } else if (char === '.') {
      // 任意字符
      element = {
        pattern: '.',
        type: elementTypes.characterClass.type,
        description: '任意字符',
        color: elementTypes.characterClass.color
      }
      stats.characterClasses++
      i++
      nodeWidth = 50
    } else {
      // 普通字符
      element = {
        pattern: char,
        type: elementTypes.literal.type,
        description: `字面量字符 '${char}'`,
        color: elementTypes.literal.color
      }
      i++
      nodeWidth = 40
    }

    if (element) {
      elements.push(element)
      nodes.push({
        x,
        y: 30,
        width: nodeWidth,
        label: element.pattern,
        color: element.color
      })
      x += nodeWidth + 20
    }
  }

  stats.nestingDepth = maxDepth
  
  regexElements.value = elements
  diagramNodes.value = nodes
  statistics.value = stats
}

const highlightElement = (index) => {
  highlightedIndex.value = index
}

const clearHighlight = () => {
  highlightedIndex.value = -1
}

// 监听正则表达式变化
watch(() => props.regex, (newRegex) => {
  parseRegex(newRegex)
}, { immediate: true })
</script>

<style scoped>
.regex-visualizer {
  padding: 16px;
}

.visualizer-container {
  min-height: 400px;
}

.visualization-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.regex-breakdown,
.railroad-diagram,
.complexity-score,
.element-statistics {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 16px;
  background-color: #fff;
}

.breakdown-title,
.diagram-title,
.score-title,
.stat-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 12px;
  color: #303133;
}

.breakdown-content {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.regex-element {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background-color: #f5f7fa;
  cursor: pointer;
  transition: all 0.3s;
}

.regex-element:hover,
.regex-element.highlighted {
  border-color: #409eff;
  background-color: #ecf5ff;
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.element-pattern {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.element-type {
  font-size: 12px;
  color: #409eff;
  margin-bottom: 2px;
}

.element-description {
  font-size: 11px;
  color: #909399;
  text-align: center;
}

.diagram-content {
  overflow-x: auto;
}

.diagram-svg {
  display: block;
}

.diagram-node {
  cursor: pointer;
  transition: all 0.3s;
}

.diagram-node:hover,
.diagram-node.highlighted {
  filter: brightness(0.9);
  stroke-width: 3;
}

.score-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.score-text {
  font-weight: 600;
  font-size: 14px;
}

.score-description {
  color: #606266;
  font-size: 13px;
  text-align: center;
}

.stat-content {
  margin-top: 8px;
}
</style>
