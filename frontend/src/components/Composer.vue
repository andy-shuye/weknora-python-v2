<script setup lang="ts">
import { ArrowDown, Link, Plus, Promotion, Upload } from '@element-plus/icons-vue'

defineProps<{ modelValue: string; kbs: string[] }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void; (e: 'send'): void }>()

const onInput = (v: string) => emit('update:modelValue', v)
const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) emit('send')
}
</script>

<template>
  <div class="composer">
    <div class="kb-row">
      <span class="kb-prefix">KB ·</span>
      <el-tag v-for="k in kbs" :key="k" type="success" size="small" round closable>{{ k }}</el-tag>
      <el-button text size="small"><el-icon><Plus /></el-icon>添加</el-button>
    </div>

    <el-input
      type="textarea"
      :rows="3"
      :model-value="modelValue"
      @update:model-value="onInput"
      @keydown="onKeydown"
      placeholder="输入问题，将基于上方知识库回答。⌘ + Enter 发送"
      resize="none"
    />

    <div class="toolbar">
      <div>
        <el-button text>智能检索<el-icon><ArrowDown /></el-icon></el-button>
        <el-button text><el-icon><Upload /></el-icon></el-button>
        <el-button text><el-icon><Link /></el-icon></el-button>
      </div>
      <div class="right">
        <span class="model">qwen3.5-plus</span>
        <el-button type="primary" size="small" :disabled="!modelValue.trim()" @click="emit('send')">
          发送<el-icon><Promotion /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.composer {
  background: white;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px;
  max-width: 820px; margin: 0 auto;
}
.kb-row { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.kb-prefix { font-size: 11px; color: var(--ink-500); font-family: var(--font-mono); }
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-top: 6px; }
.right { display: flex; align-items: center; gap: 8px; }
.model { font-size: 11px; font-family: var(--font-mono); color: var(--ink-400); }

:deep(.el-textarea__inner) {
  border: none; box-shadow: none; resize: none;
  padding: 6px 8px; font-size: 14px; line-height: 1.6;
}
</style>
