<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  KnowledgeBaseItem,
  listKnowledgeBases,
  listSpaces,
  shareKnowledgeBaseToSpace,
  unshareKnowledgeBaseFromSpace,
} from '../api/knowledge'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const items = ref<KnowledgeBaseItem[]>([])
const spaces = ref<Array<{ id: number; name: string }>>([])

const createVisible = ref(false)
const createForm = ref({ name: '', description: '', type: 'document' })
const creating = ref(false)

const shareVisible = ref(false)
const sharing = ref(false)
const selectedKb = ref<KnowledgeBaseItem | null>(null)
const selectedSpaceId = ref<number | null>(null)

const canShare = computed(() => {
  const role = auth.user?.roleLevel
  return role === 'dept_admin' || role === 'super_admin'
})

async function loadData() {
  loading.value = true
  try {
    const [kbRes, spaceRes] = await Promise.all([
      listKnowledgeBases(),
      canShare.value ? listSpaces() : Promise.resolve({ success: true, data: [] }),
    ])
    items.value = kbRes.data || []
    spaces.value = (spaceRes as any).data || []
  } catch (e: any) {
    ElMessage.error(e.message || '加载知识库失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.value = { name: '', description: '', type: 'document' }
  createVisible.value = true
}

async function submitCreate() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  creating.value = true
  try {
    await createKnowledgeBase(createForm.value)
    ElMessage.success('知识库创建成功')
    createVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

function openDetail(item: KnowledgeBaseItem) {
  router.push(`/kb/${item.id}`)
}

async function removeBase(item: KnowledgeBaseItem) {
  try {
    await ElMessageBox.confirm(`确认删除知识库“${item.name}”？`, '删除确认', { type: 'warning' })
    await deleteKnowledgeBase(item.id)
    ElMessage.success('删除成功')
    await loadData()
  } catch {
    // canceled
  }
}

function openShare(item: KnowledgeBaseItem) {
  selectedKb.value = item
  selectedSpaceId.value = item.space_id || null
  shareVisible.value = true
}

async function submitShare() {
  if (!selectedKb.value || !selectedSpaceId.value) {
    ElMessage.warning('请选择空间')
    return
  }
  sharing.value = true
  try {
    await shareKnowledgeBaseToSpace(selectedKb.value.id, selectedSpaceId.value, 'viewer')
    ElMessage.success('共享成功')
    shareVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e.message || '共享失败')
  } finally {
    sharing.value = false
  }
}

async function unshare(item: KnowledgeBaseItem) {
  try {
    await ElMessageBox.confirm(`确认取消“${item.name}”的空间共享？`, '取消共享', { type: 'warning' })
    await unshareKnowledgeBaseFromSpace(item.id)
    ElMessage.success('已取消共享')
    await loadData()
  } catch {
    // canceled
  }
}

onMounted(loadData)
</script>

<template>
  <div class="kb-page" v-loading="loading">
    <header class="kb-header">
      <div>
        <h2>知识库</h2>
        <p>管理你拥有的知识库，并按需共享到空间。</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建知识库
      </el-button>
    </header>

    <section class="kb-grid">
      <article v-for="item in items" :key="item.id" class="kb-card" @click="openDetail(item)">
        <div class="kb-title-row">
          <h3>{{ item.name }}</h3>
          <el-tag :type="item.visibility === 'space' ? 'success' : 'info'" size="small" round>
            {{ item.visibility === 'space' ? '已共享' : '私有' }}
          </el-tag>
        </div>

        <p class="kb-desc">{{ item.weknora?.description || '暂无描述' }}</p>

        <div class="kb-stats">
          <span>文档 {{ item.weknora?.knowledge_count ?? 0 }}</span>
          <span>分块 {{ item.weknora?.chunk_count ?? 0 }}</span>
          <span>处理中 {{ item.weknora?.processing_count ?? 0 }}</span>
        </div>

        <div class="kb-actions" @click.stop>
          <el-button size="small" @click="openDetail(item)">详情</el-button>
          <el-button size="small" type="danger" plain @click="removeBase(item)">删除</el-button>
          <template v-if="canShare">
            <el-button v-if="item.visibility !== 'space'" size="small" type="success" plain @click="openShare(item)">
              共享到空间
            </el-button>
            <el-button v-else size="small" type="warning" plain @click="unshare(item)">取消共享</el-button>
          </template>
        </div>
      </article>
    </section>

    <el-empty v-if="!loading && items.length === 0" description="暂无知识库，点击右上角新建" />

    <el-dialog v-model="createVisible" title="新建知识库" width="480px">
      <el-form label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="createForm.name" placeholder="请输入知识库名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="shareVisible" title="共享到空间" width="460px">
      <el-form label-position="top">
        <el-form-item label="目标空间" required>
          <el-select v-model="selectedSpaceId" placeholder="请选择空间" style="width: 100%">
            <el-option v-for="sp in spaces" :key="sp.id" :label="sp.name" :value="sp.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shareVisible = false">取消</el-button>
        <el-button type="primary" :loading="sharing" @click="submitShare">确认共享</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.kb-page {
  padding: 24px 28px;
}
.kb-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 18px;
}
.kb-header h2 {
  margin: 0;
  font-size: 20px;
  letter-spacing: -0.02em;
}
.kb-header p {
  margin: 6px 0 0;
  color: var(--ink-500);
  font-size: 13px;
}
.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}
.kb-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.kb-card:hover {
  transform: translateY(-2px);
  border-color: var(--border-strong);
  box-shadow: 0 8px 20px rgba(20, 22, 28, 0.06);
}
.kb-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.kb-title-row h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.kb-desc {
  margin: 10px 0 14px;
  color: var(--ink-600);
  font-size: 13px;
  line-height: 1.6;
  min-height: 42px;
}
.kb-stats {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: var(--ink-500);
}
.kb-actions {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
