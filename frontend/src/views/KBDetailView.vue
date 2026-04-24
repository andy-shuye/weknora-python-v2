<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchUpdateKnowledgeDocumentTags,
  createKnowledgeTag,
  deleteKnowledgeTag,
  getKnowledgeBaseDetail,
  listKnowledgeDocuments,
  listKnowledgeDocumentsByTag,
  listKnowledgeTags,
  updateKnowledgeBase,
  uploadKnowledgeDocument,
} from '../api/knowledge'

type DocItem = {
  id: string
  title: string
  file_type: string
  parse_status: string
  enable_status: string
  tag_id: string
  created_at: string
}

type TagItem = {
  id: string
  name: string
  color?: string
  sort_order?: number
}

const route = useRoute()
const router = useRouter()
const kbId = computed(() => Number(route.params.id))

const loading = ref(false)
const uploading = ref(false)
const saving = ref(false)

const base = ref<any>(null)
const docs = ref<DocItem[]>([])
const total = ref(0)

const tags = ref<TagItem[]>([])
const activeTagId = ref('')
const tagKeyword = ref('')
const uploadTagId = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

const searchKeyword = ref('')
const fileTypeFilter = ref('')

const editForm = ref({ name: '', description: '' })

const visibleTags = computed(() => {
  const keyword = tagKeyword.value.trim().toLowerCase()
  if (!keyword) return tags.value
  return tags.value.filter((t) => t.name.toLowerCase().includes(keyword))
})

const filteredDocs = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return docs.value.filter((d) => {
    const hitKeyword = !keyword || d.title.toLowerCase().includes(keyword)
    const hitType = !fileTypeFilter.value || d.file_type.toLowerCase() === fileTypeFilter.value.toLowerCase()
    return hitKeyword && hitType
  })
})

const tagNameMap = computed(() => {
  const map: Record<string, string> = {}
  tags.value.forEach((t) => {
    map[t.id] = t.name
  })
  return map
})

const tagSelectOptions = computed(() => {
  return [{ id: '', name: '未分类' }, ...tags.value]
})

function normalizeDoc(raw: any): DocItem {
  return {
    id: String(raw?.id || ''),
    title: String(raw?.title || raw?.file_name || raw?.name || '-'),
    file_type: String(raw?.file_type || raw?.type || '-'),
    parse_status: String(raw?.parse_status || raw?.status || '-'),
    enable_status: String(raw?.enable_status || '-'),
    tag_id: String(raw?.tag_id || ''),
    created_at: String(raw?.created_at || ''),
  }
}

async function loadBaseDetail() {
  if (!kbId.value) return
  const detailRes = await getKnowledgeBaseDetail(kbId.value)
  base.value = detailRes.data
  editForm.value = {
    name: base.value?.name || '',
    description: base.value?.weknora?.description || '',
  }
}

async function loadTags() {
  if (!kbId.value) return
  const tagRes = await listKnowledgeTags(kbId.value, '', 1, 200)
  tags.value = tagRes.data.items || []
}

async function loadDocs() {
  if (!kbId.value) return
  const docsRes = activeTagId.value
    ? await listKnowledgeDocumentsByTag(kbId.value, activeTagId.value, 1, 200)
    : await listKnowledgeDocuments(kbId.value, 1, 200)
  docs.value = (docsRes.data.items || []).map(normalizeDoc)
  total.value = docsRes.data.total || docs.value.length
}

async function loadAll() {
  if (!kbId.value) return
  loading.value = true
  try {
    await Promise.all([loadBaseDetail(), loadTags(), loadDocs()])
  } catch (e: any) {
    ElMessage.error(e.message || '加载知识库详情失败')
  } finally {
    loading.value = false
  }
}

async function saveBase() {
  if (!kbId.value) return
  if (!editForm.value.name.trim()) {
    ElMessage.warning('知识库名称不能为空')
    return
  }
  saving.value = true
  try {
    await updateKnowledgeBase(kbId.value, {
      name: editForm.value.name.trim(),
      description: editForm.value.description.trim(),
    })
    ElMessage.success('知识库信息已保存')
    await loadBaseDetail()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleCreateTag() {
  if (!kbId.value) return
  try {
    const { value } = await ElMessageBox.prompt('请输入分类名称', '新增文档分类', {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputPattern: /.+/,
      inputErrorMessage: '分类名称不能为空',
    })
    await createKnowledgeTag(kbId.value, { name: value.trim() })
    ElMessage.success('分类创建成功')
    await loadTags()
  } catch (e: any) {
    if (e?.action !== 'cancel' && e?.action !== 'close') {
      ElMessage.error(e?.message || '新增分类失败')
    }
  }
}

async function handleDeleteTag(tag: TagItem) {
  if (!kbId.value) return
  try {
    await ElMessageBox.confirm(`确认删除分类“${tag.name}”？`, '删除分类', { type: 'warning' })
    await deleteKnowledgeTag(kbId.value, tag.id, true)
    if (activeTagId.value === tag.id) {
      activeTagId.value = ''
    }
    if (uploadTagId.value === tag.id) {
      uploadTagId.value = ''
    }
    ElMessage.success('分类已删除')
    await Promise.all([loadTags(), loadDocs()])
  } catch {
    // canceled
  }
}

async function selectTag(tagId: string) {
  activeTagId.value = tagId
  await loadDocs()
}

async function onDocTagChange(row: DocItem, nextTagId: string) {
  if (!kbId.value || !row.id) return
  const tagValue = nextTagId || null
  try {
    await batchUpdateKnowledgeDocumentTags(kbId.value, { [row.id]: tagValue })
    row.tag_id = nextTagId
    ElMessage.success('文档分类已更新')
  } catch (e: any) {
    ElMessage.error(e.message || '更新文档分类失败')
  }
}

async function doUpload(file: File) {
  if (!kbId.value) return
  uploading.value = true
  try {
    await uploadKnowledgeDocument(kbId.value, file, true, uploadTagId.value || undefined)
    ElMessage.success('上传成功，文档正在解析')
    await loadDocs()
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function onChooseFile(evt: Event) {
  const target = evt.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    await doUpload(file)
  }
  target.value = ''
}

function triggerUpload() {
  fileInputRef.value?.click()
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  return dateStr.replace('T', ' ').slice(0, 16)
}

function getStatusTag(status: string) {
  const map: Record<string, { label: string; type: 'success' | 'warning' | 'info' | 'danger' }> = {
    pending: { label: '待解析', type: 'warning' },
    processing: { label: '解析中', type: 'info' },
    parsing: { label: '解析中', type: 'info' },
    completed: { label: '已完成', type: 'success' },
    done: { label: '已完成', type: 'success' },
    failed: { label: '失败', type: 'danger' },
  }
  return map[status] || { label: status || '-', type: 'info' }
}

onMounted(loadAll)
</script>

<template>
  <div class="kb-detail-page" v-loading="loading">
    <header class="kb-header">
      <div class="header-left">
        <div class="breadcrumbs">
          <span class="crumb-link" @click="router.push('/kb')">知识库</span>
          <span>/</span>
          <span>{{ base?.name || '详情' }}</span>
        </div>
        <h2>文档管理</h2>
      </div>
      <div class="header-actions">
        <el-button @click="saveBase" :loading="saving">保存信息</el-button>
      </div>
    </header>

    <section class="kb-edit">
      <el-form inline>
        <el-form-item label="知识库名称">
          <el-input v-model="editForm.name" style="width: 260px" />
        </el-form-item>
        <el-form-item label="知识库描述">
          <el-input v-model="editForm.description" style="width: 460px" />
        </el-form-item>
      </el-form>
    </section>

    <section class="kb-body">
      <aside class="tag-panel">
        <div class="tag-head">
          <span>文档分类</span>
          <el-button text type="primary" @click="handleCreateTag">新增</el-button>
        </div>
        <el-input v-model="tagKeyword" placeholder="搜索分类" size="small" clearable />

        <button
          class="tag-item"
          :class="{ active: activeTagId === '' }"
          @click="selectTag('')"
        >
          全部文档
          <span class="tag-count">{{ total }}</span>
        </button>

        <div class="tag-list">
          <div
            v-for="t in visibleTags"
            :key="t.id"
            class="tag-row"
          >
            <button class="tag-item" :class="{ active: activeTagId === t.id }" @click="selectTag(t.id)">
              <span class="tag-dot" :style="{ background: t.color || '#5b8def' }"></span>
              {{ t.name }}
            </button>
            <el-button text type="danger" size="small" @click="handleDeleteTag(t)">删</el-button>
          </div>
        </div>
      </aside>

      <div class="doc-panel">
        <div class="doc-toolbar">
          <el-input v-model="searchKeyword" placeholder="搜索文档名称" clearable />
          <el-select v-model="fileTypeFilter" placeholder="文件类型" clearable style="width: 130px">
            <el-option label="PDF" value="pdf" />
            <el-option label="Word" value="docx" />
            <el-option label="TXT" value="txt" />
            <el-option label="Markdown" value="md" />
          </el-select>
          <el-select v-model="uploadTagId" placeholder="上传默认分类" clearable style="width: 170px">
            <el-option v-for="opt in tagSelectOptions" :key="opt.id" :label="opt.name" :value="opt.id" />
          </el-select>
          <el-button type="primary" :loading="uploading" @click="triggerUpload">上传文档</el-button>
          <input ref="fileInputRef" type="file" class="hidden-input" @change="onChooseFile" />
        </div>

        <el-table :data="filteredDocs" border stripe height="100%">
          <el-table-column prop="title" label="文档名称" min-width="240" />
          <el-table-column prop="file_type" label="类型" width="110" />
          <el-table-column label="分类" min-width="200">
            <template #default="{ row }">
              <el-select
                :model-value="row.tag_id"
                placeholder="未分类"
                clearable
                size="small"
                @update:model-value="(val) => onDocTagChange(row, String(val || ''))"
              >
                <el-option
                  v-for="opt in tagSelectOptions"
                  :key="opt.id"
                  :label="opt.name"
                  :value="opt.id"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="解析状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusTag(row.parse_status).type" size="small">
                {{ getStatusTag(row.parse_status).label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="启用状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.enable_status === 'enabled' ? 'success' : 'info'" size="small">
                {{ row.enable_status === 'enabled' ? '已启用' : '已禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无文档，点击右上角上传文档" />
          </template>
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.kb-detail-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 18px;
  gap: 12px;
  background: #f6f7fb;
}

.kb-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.breadcrumbs {
  color: #8f96a3;
  font-size: 13px;
  margin-bottom: 6px;
  display: flex;
  gap: 6px;
}

.crumb-link {
  color: #5b8def;
  cursor: pointer;
}

.header-left h2 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.03em;
}

.kb-edit {
  border: 1px solid #e4e9f1;
  border-radius: 12px;
  background: #fff;
  padding: 12px 14px 4px;
}

.kb-body {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
  flex: 1;
}

.tag-panel {
  border: 1px solid #e4e9f1;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.tag-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.tag-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: auto;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tag-item {
  border: 1px solid #e9edf4;
  background: #fff;
  color: #4c5566;
  border-radius: 8px;
  height: 34px;
  padding: 0 10px;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tag-item.active {
  border-color: #8fc1ff;
  background: #eef6ff;
  color: #245ca8;
}

.tag-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.tag-count {
  margin-left: auto;
  font-size: 12px;
  color: #8f96a3;
}

.doc-panel {
  border: 1px solid #e4e9f1;
  border-radius: 12px;
  background: #fff;
  padding: 12px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 10px;
}

.doc-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 130px 170px 110px;
  gap: 8px;
}

.upload-trigger {
  display: inline-flex;
}

.hidden-input {
  display: none;
}

@media (max-width: 1200px) {
  .kb-body {
    grid-template-columns: 1fr;
  }

  .doc-toolbar {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
