<template>
  <div v-if="visible" class="tutorial-overlay" @click.self="handleSkip">
    <div class="tutorial-container">
      <!-- 进度指示器 -->
      <div class="tutorial-progress">
        <div
          v-for="(step, index) in steps"
          :key="index"
          class="progress-dot"
          :class="{
            'active': index === currentStep,
            'completed': index < currentStep
          }"
        />
      </div>

      <!-- 教程内容 -->
      <div class="tutorial-content">
        <div class="tutorial-step">
          <div class="step-number">步骤 {{ currentStep + 1 }} / {{ steps.length }}</div>
          <h3 class="step-title">{{ currentStepData.title }}</h3>
          <p class="step-description">{{ currentStepData.description }}</p>
          
          <div v-if="currentStepData.tips && currentStepData.tips.length > 0" class="step-tips">
            <div class="tips-title">
              <el-icon><InfoFilled /></el-icon>
              提示
            </div>
            <ul class="tips-list">
              <li v-for="(tip, index) in currentStepData.tips" :key="index">
                {{ tip }}
              </li>
            </ul>
          </div>
          
          <div v-if="currentStepData.example" class="step-example">
            <div class="example-title">示例：</div>
            <div class="example-content">
              <code>{{ currentStepData.example }}</code>
            </div>
          </div>
        </div>
      </div>

      <!-- 导航按钮 -->
      <div class="tutorial-actions">
        <el-button @click="handleSkip" text>
          跳过教程
        </el-button>
        
        <div class="nav-buttons">
          <el-button
            v-if="currentStep > 0"
            @click="handlePrevious"
          >
            上一步
          </el-button>
          
          <el-button
            v-if="currentStep < steps.length - 1"
            type="primary"
            @click="handleNext"
          >
            下一步
          </el-button>
          
          <el-button
            v-else
            type="primary"
            @click="handleComplete"
          >
            完成教程
          </el-button>
        </div>
      </div>

      <!-- 高亮遮罩 -->
      <div
        v-if="currentStepData.target"
        class="tutorial-highlight"
        :style="highlightStyle"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  autoStart: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'complete', 'skip'])

// 状态
const currentStep = ref(0)
const highlightStyle = ref({})

// 教程步骤定义
const steps = [
  {
    title: '欢迎使用路由规则创建向导',
    description: '本教程将引导您快速创建一个路由规则。路由规则用于将用户查询自动路由到正确的处理模块，提高查询准确率。',
    tips: [
      '整个教程大约需要2-3分钟',
      '您可以随时跳过教程',
      '完成教程后可以在帮助菜单中重新查看'
    ],
    target: null
  },
  {
    title: '选择输入模式',
    description: '您可以选择使用自然语言描述规则，或者直接编写正则表达式。对于初学者，我们推荐使用自然语言模式。',
    tips: [
      '自然语言模式：用简单的语言描述匹配规则',
      '正则表达式模式：适合有经验的用户',
      '两种模式可以随时切换'
    ],
    example: '自然语言: "查询包含IP地址的内容"',
    target: '.intelligent-input'
  },
  {
    title: '设置意图类型',
    description: '意图类型决定了匹配到此规则的查询将被路由到哪个处理模块。选择正确的意图类型非常重要。',
    tips: [
      'SQL查询：用于数据库查询和统计',
      '报告查询：用于检索历史报告',
      '知识查询：用于查找文档和指南',
      '对话：用于一般性交流'
    ],
    target: '.intent-type-select'
  },
  {
    title: '验证规则',
    description: '在验证结果标签页中，系统会自动检查正则表达式语法、检测与现有规则的冲突、评估复杂度。',
    tips: [
      '语法错误会显示具体位置',
      '冲突检测帮助避免规则重复',
      '复杂度评分建议保持在6以下'
    ],
    target: '.validation-panel'
  },
  {
    title: '测试匹配',
    description: '在测试匹配标签页中，您可以输入实际查询来测试规则的匹配效果。建议测试多种场景以确保规则准确性。',
    tips: [
      '每行输入一个测试查询',
      '系统会显示匹配结果和匹配率',
      '可以保存测试用例供后续使用'
    ],
    example: '查询10.90.1.4的信息\n统计所有物理机数量',
    target: '.test-match-panel'
  },
  {
    title: '使用智能辅助',
    description: '智能辅助标签页提供AI驱动的功能，包括自动生成描述、提取关键词、推荐数据库表、建议优先级。',
    tips: [
      '所有生成的内容都可以手动编辑',
      '表推荐仅对SQL查询有效',
      '优先级建议考虑了规则类型和冲突情况'
    ],
    target: '.assistant-panel'
  },
  {
    title: '预览和保存',
    description: '在保存前，建议先预览规则。预览会显示完整信息、测试结果、冲突警告和影响预测。',
    tips: [
      '预览可以帮助发现潜在问题',
      '影响预测基于历史查询数据',
      '可以从预览返回继续编辑'
    ],
    target: '.preview-button'
  },
  {
    title: '教程完成',
    description: '恭喜！您已经了解了路由规则创建的基本流程。现在可以开始创建您的第一个规则了。',
    tips: [
      '可以使用模板快速开始',
      '遇到问题可以查看字段旁的帮助图标',
      '在帮助菜单中可以重新查看教程'
    ],
    target: null
  }
]

// 计算属性
const currentStepData = computed(() => steps[currentStep.value])

// 方法
const updateHighlight = () => {
  if (!currentStepData.value.target) {
    highlightStyle.value = {}
    return
  }
  
  const element = document.querySelector(currentStepData.value.target)
  if (element) {
    const rect = element.getBoundingClientRect()
    highlightStyle.value = {
      top: `${rect.top - 8}px`,
      left: `${rect.left - 8}px`,
      width: `${rect.width + 16}px`,
      height: `${rect.height + 16}px`
    }
  }
}

const handleNext = () => {
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
    updateHighlight()
  }
}

const handlePrevious = () => {
  if (currentStep.value > 0) {
    currentStep.value--
    updateHighlight()
  }
}

const handleSkip = () => {
  emit('skip')
  emit('update:visible', false)
  // 记录用户跳过了教程
  localStorage.setItem('routing_tutorial_skipped', 'true')
}

const handleComplete = () => {
  emit('complete')
  emit('update:visible', false)
  // 记录用户完成了教程
  localStorage.setItem('routing_tutorial_completed', 'true')
}

// 监听步骤变化
watch(currentStep, () => {
  updateHighlight()
})

// 监听可见性变化
watch(() => props.visible, (newVal) => {
  if (newVal) {
    currentStep.value = 0
    updateHighlight()
  }
})

// 生命周期
onMounted(() => {
  if (props.autoStart) {
    updateHighlight()
  }
})
</script>

<style scoped>
.tutorial-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.tutorial-container {
  position: relative;
  width: 90%;
  max-width: 600px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.3s;
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.tutorial-progress {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 20px 20px 0;
}

.progress-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #e4e7ed;
  transition: all 0.3s;
}

.progress-dot.active {
  width: 24px;
  border-radius: 4px;
  background-color: #409eff;
}

.progress-dot.completed {
  background-color: #67c23a;
}

.tutorial-content {
  padding: 24px 32px;
}

.tutorial-step {
  min-height: 200px;
}

.step-number {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.step-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px;
}

.step-description {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin: 0 0 16px;
}

.step-tips {
  padding: 12px;
  background-color: #f0f9ff;
  border-left: 3px solid #409eff;
  border-radius: 4px;
  margin-bottom: 16px;
}

.tips-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 13px;
  color: #409eff;
  margin-bottom: 8px;
}

.tips-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}

.step-example {
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.example-title {
  font-weight: 500;
  font-size: 13px;
  color: #303133;
  margin-bottom: 8px;
}

.example-content code {
  display: block;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #e6a23c;
  white-space: pre-wrap;
}

.tutorial-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px 24px;
  border-top: 1px solid #e4e7ed;
}

.nav-buttons {
  display: flex;
  gap: 12px;
}

.tutorial-highlight {
  position: fixed;
  border: 2px solid #409eff;
  border-radius: 4px;
  pointer-events: none;
  z-index: 10000;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.4);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(64, 158, 255, 0);
  }
}
</style>
