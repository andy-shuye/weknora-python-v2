<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, FolderOpened, Plus, Setting, User } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import {
  addSpaceDepartments,
  addSpaceUsers,
  createSpace,
  getSpaceMembers,
  listDepartments,
  listSpaceKnowledgeBases,
  listSpaces,
  listUsers,
  removeSpaceDepartment,
  removeSpaceUser,
  SpaceItem,
  SpaceKnowledgeBase,
  updateSpace,
} from '../api/spaces'
import { listKnowledgeBases, shareKnowledgeBaseToSpace, unshareKnowledgeBaseFromSpace } from '../api/knowledge'

type UserMember = { user_id: number; login_name: string; full_name: string }
type DepartmentMember = { department_id: number; department_name: string }
type UserOption = { id: number; full_name: string; login_name: string; department_name: string | null }
type DepartmentOption = { id: number; name: string }
type SpaceScope = 'all' | 'owned' | 'joined'
type ManagePanel = 'basic' | 'member' | 'kb'

const auth = useAuthStore()

const spaces = ref<SpaceItem[]>([])
const loading = ref(false)

const createVisible = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', description: '' })

const manageVisible = ref(false)
const managing = ref(false)
const activeSpace = ref<SpaceItem | null>(null)
const editForm = ref({ name: '', description: '' })
const userMembers = ref<UserMember[]>([])
const deptMembers = ref<DepartmentMember[]>([])
const spaceKbs = ref<SpaceKnowledgeBase[]>([])

const users = ref<UserOption[]>([])
const departments = ref<DepartmentOption[]>([])
const selectedUserId = ref<number | null>(null)
const selectedDepartmentId = ref<number | null>(null)
const selectedKbIdToShare = ref<number | null>(null)
const activeScope = ref<SpaceScope>('all')
const activePanel = ref<ManagePanel>('basic')

const allKbs = ref<Array<{ id: number; name: string; owner_user_id: number; visibility: 'private' | 'space'; space_id: number | null }>>([])

const canCreate = computed(() => {
  const role = auth.user?.roleLevel
  return role === 'dept_admin' || role === 'super_admin'
})

const currentUserId = computed(() => auth.user?.id || 0)

const scopeCounts = computed(() => {
  const owned = spaces.value.filter((s) => s.owner_user_id === currentUserId.value).length
  const joined = spaces.value.filter((s) => s.owner_user_id !== currentUserId.value).length
  return {
    all: spaces.value.length,
    owned,
    joined,
  }
})

const filteredSpaces = computed(() => {
  if (activeScope.value === 'owned') {
    return spaces.value.filter((s) => s.owner_user_id === currentUserId.value)
  }
  if (activeScope.value === 'joined') {
    return spaces.value.filter((s) => s.owner_user_id !== currentUserId.value)
  }
  return spaces.value
})

const canManageActiveSpace = computed(() => activeSpace.value?.my_permission === 'manage')

const panelTitle = computed(() => {
  if (activePanel.value === 'member') return '成员管理'
  if (activePanel.value === 'kb') return '共享知识库'
  return '基本信息'
})

const panelHint = computed(() => {
  if (activePanel.value === 'member') return '支持单个添加成员和按部门添加成员'
  if (activePanel.value === 'kb') return '将知识库共享到当前空间，供成员协作使用'
  return '设置空间名称和描述，便于成员识别'
})

const shareableKbsForActiveSpace = computed(() => {
  return allKbs.value.filter((kb) => kb.visibility !== 'space')
})

function cardTone(index: number) {
  const tones = ['mint', 'peach', 'lavender']
  return tones[index % tones.length]
}

function ownerText(space: SpaceItem) {
  return space.owner_name || '未知'
}

function spaceBadge(space: SpaceItem) {
  return space.owner_user_id === currentUserId.value ? '创建者' : '已加入'
}

function permissionLabel(space: SpaceItem) {
  if (space.owner_user_id === currentUserId.value) return '管理员'
  if (space.my_permission === 'manage') return '编辑'
  return '只读'
}

function permissionClass(space: SpaceItem) {
  if (space.owner_user_id === currentUserId.value) return 'perm-admin'
  if (space.my_permission === 'manage') return 'perm-edit'
  return 'perm-read'
}

const avatarColors = [
  ['#4caf82', '#fff'],
  ['#e8a87c', '#fff'],
  ['#7c8fe8', '#fff'],
  ['#e87c9a', '#fff'],
  ['#7cc5e8', '#fff'],
]

function avatarColor(n: number) {
  const [bg, color] = avatarColors[(n - 1) % avatarColors.length]
  return { background: bg, color }
}

function ensureManagePermission() {
  if (canManageActiveSpace.value) return true
  ElMessage.warning('你在该空间仅有只读权限')
  return false
}

async function loadSpaces() {
  loading.value = true
  try {
    const res = await listSpaces()
    spaces.value = res.data || []
  } catch (e: any) {
    ElMessage.error(e.message || '加载空间失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.value = { name: '', description: '' }
  createVisible.value = true
}

async function submitCreate() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请输入空间名称')
    return
  }
  creating.value = true
  try {
    await createSpace({
      name: createForm.value.name.trim(),
      description: createForm.value.description.trim(),
    })
    ElMessage.success('空间创建成功')
    createVisible.value = false
    await loadSpaces()
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

async function loadManageData(space: SpaceItem) {
  const [membersRes, usersRes, deptRes, spaceKbsRes, kbRes] = await Promise.all([
    getSpaceMembers(space.id),
    listUsers(),
    listDepartments(),
    listSpaceKnowledgeBases(space.id),
    listKnowledgeBases(),
  ])

  userMembers.value = membersRes.data.user_members || []
  deptMembers.value = membersRes.data.department_members || []
  users.value = usersRes.data || []
  departments.value = deptRes.data || []
  spaceKbs.value = spaceKbsRes.data || []
  allKbs.value = (kbRes.data || []).map((i) => ({
    id: i.id,
    name: i.name,
    owner_user_id: i.owner_user_id,
    visibility: i.visibility,
    space_id: i.space_id,
  }))
}

async function openManage(space: SpaceItem) {
  activeSpace.value = space
  activePanel.value = 'basic'
  editForm.value = { name: space.name, description: space.description || '' }
  selectedKbIdToShare.value = null
  selectedUserId.value = null
  selectedDepartmentId.value = null
  manageVisible.value = true

  try {
    await loadManageData(space)
  } catch (e: any) {
    ElMessage.error(e.message || '加载管理信息失败')
  }
}

async function saveSpace() {
  if (!activeSpace.value) return
  if (!ensureManagePermission()) return
  if (!editForm.value.name.trim()) {
    ElMessage.warning('空间名称不能为空')
    return
  }
  managing.value = true
  try {
    await updateSpace(activeSpace.value.id, {
      name: editForm.value.name.trim(),
      description: editForm.value.description.trim(),
    })
    ElMessage.success('空间信息已更新')
    await loadSpaces()
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    managing.value = false
  }
}

async function handleAddUser() {
  if (!activeSpace.value || !selectedUserId.value) return
  if (!ensureManagePermission()) return
  managing.value = true
  try {
    await addSpaceUsers(activeSpace.value.id, [selectedUserId.value])
    selectedUserId.value = null
    await loadManageData(activeSpace.value)
    await loadSpaces()
    ElMessage.success('已添加用户')
  } catch (e: any) {
    ElMessage.error(e.message || '添加成员失败')
  } finally {
    managing.value = false
  }
}

async function handleRemoveUser(userId: number) {
  if (!activeSpace.value) return
  if (!ensureManagePermission()) return
  managing.value = true
  try {
    await removeSpaceUser(activeSpace.value.id, userId)
    await loadManageData(activeSpace.value)
    await loadSpaces()
    ElMessage.success('已移除用户')
  } catch (e: any) {
    ElMessage.error(e.message || '移除成员失败')
  } finally {
    managing.value = false
  }
}

async function handleAddDepartment() {
  if (!activeSpace.value || !selectedDepartmentId.value) return
  if (!ensureManagePermission()) return
  managing.value = true
  try {
    await addSpaceDepartments(activeSpace.value.id, [selectedDepartmentId.value])
    selectedDepartmentId.value = null
    await loadManageData(activeSpace.value)
    await loadSpaces()
    ElMessage.success('已添加部门')
  } catch (e: any) {
    ElMessage.error(e.message || '添加部门失败')
  } finally {
    managing.value = false
  }
}

async function handleRemoveDepartment(departmentId: number) {
  if (!activeSpace.value) return
  if (!ensureManagePermission()) return
  managing.value = true
  try {
    await removeSpaceDepartment(activeSpace.value.id, departmentId)
    await loadManageData(activeSpace.value)
    await loadSpaces()
    ElMessage.success('已移除部门')
  } catch (e: any) {
    ElMessage.error(e.message || '移除部门失败')
  } finally {
    managing.value = false
  }
}

async function handleShareKbToActiveSpace() {
  if (!activeSpace.value || !selectedKbIdToShare.value) return
  if (!ensureManagePermission()) return
  managing.value = true
  try {
    await shareKnowledgeBaseToSpace(selectedKbIdToShare.value, activeSpace.value.id, 'viewer')
    selectedKbIdToShare.value = null
    await loadManageData(activeSpace.value)
    await loadSpaces()
    ElMessage.success('知识库已共享到空间')
  } catch (e: any) {
    ElMessage.error(e.message || '共享失败')
  } finally {
    managing.value = false
  }
}

async function handleUnshareKbFromSpace(kbId: number) {
  if (!activeSpace.value) return
  if (!ensureManagePermission()) return
  managing.value = true
  try {
    await unshareKnowledgeBaseFromSpace(kbId)
    await loadManageData(activeSpace.value)
    await loadSpaces()
    ElMessage.success('已取消共享')
  } catch (e: any) {
    ElMessage.error(e.message || '取消共享失败')
  } finally {
    managing.value = false
  }
}

onMounted(loadSpaces)
</script>

<template>
  <div class="spaces-page" v-loading="loading">
    <header class="head">
      <div class="head-meta">COLLABORATIVE · WORKSPACES</div>
      <div class="head-row">
        <div class="head-main">
          <h1>共享空间</h1>
          <p>将知识库共享到空间，授权团队成员协作使用</p>
        </div>
        <el-button v-if="canCreate" class="create-btn" @click="openCreate">
          <el-icon><Plus /></el-icon>
          创建空间
        </el-button>
      </div>
    </header>

    <!-- Guide steps banner -->
    <div class="guide-banner">
      <span class="guide-icon">✦</span>
      <div class="guide-steps">
        <span class="guide-step active">创建空间</span>
        <span class="guide-arrow">›</span>
        <span class="guide-step">添加成员</span>
        <span class="guide-arrow">›</span>
        <span class="guide-step">共享知识库</span>
        <span class="guide-arrow">›</span>
        <span class="guide-step">成员即可协作检索与问答</span>
      </div>
    </div>

    <!-- Scope filter tabs -->
    <div class="scope-tabs">
      <button class="scope-tab" :class="{ active: activeScope === 'all' }" @click="activeScope = 'all'">
        全部 <span class="tab-count">{{ scopeCounts.all }}</span>
      </button>
      <button class="scope-tab" :class="{ active: activeScope === 'owned' }" @click="activeScope = 'owned'">
        我创建的 <span class="tab-count">{{ scopeCounts.owned }}</span>
      </button>
      <button class="scope-tab" :class="{ active: activeScope === 'joined' }" @click="activeScope = 'joined'">
        我加入的 <span class="tab-count">{{ scopeCounts.joined }}</span>
      </button>
    </div>

    <div class="workspace-shell">
      <section class="workspace-content">
        <section class="grid">
          <article
            v-for="(s, idx) in filteredSpaces"
            :key="s.id"
            class="card"
            @click="openManage(s)"
          >
            <div class="card-top">
              <div class="left">
                <div class="icon" :class="cardTone(idx)">
                  <el-icon><Connection /></el-icon>
                </div>
                <div class="card-title-block">
                  <h3>{{ s.name }}</h3>
                  <div class="owner">所有者 · {{ ownerText(s) }}</div>
                </div>
              </div>
              <span class="role-badge" :class="permissionClass(s)">
                {{ permissionLabel(s) }}
              </span>
            </div>

            <p class="desc">{{ s.description || '暂无描述' }}</p>

            <div class="card-foot">
              <div class="avatars-row">
                <span class="avatar-bubble" v-for="n in Math.min(s.member_count || 0, 4)" :key="n" :style="avatarColor(n)">
                  {{ String.fromCharCode(64 + n) }}
                </span>
                <span v-if="(s.member_count || 0) > 4" class="avatar-more">+{{ (s.member_count || 0) - 4 }}</span>
                <span class="foot-meta">{{ s.member_count || 0 }} 成员 · {{ s.kb_count || 0 }} 知识库</span>
              </div>
              <button class="manage-link" @click.stop="openManage(s)">
                <el-icon><Setting /></el-icon> 管理
              </button>
            </div>
          </article>

          <button v-if="canCreate" class="add-card" @click="openCreate">
            <div class="add-plus">＋</div>
            <span>创建新空间</span>
          </button>
        </section>

        <el-empty v-if="!loading && filteredSpaces.length === 0" description="该分组下暂无空间" />
      </section>
    </div>

    <el-dialog v-model="createVisible" title="创建空间" width="520px">
      <el-form label-position="top">
        <el-form-item label="空间名称" required>
          <el-input v-model="createForm.name" placeholder="例如：产品研发组" />
        </el-form-item>
        <el-form-item label="空间描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="manageVisible"
      width="1180px"
      top="3vh"
      class="space-manage-dialog"
      :show-close="false"
      destroy-on-close
    >
      <div v-if="activeSpace" class="manage-shell" v-loading="managing">
        <aside class="manage-side">
          <h3>空间设置</h3>
          <button class="panel-item" :class="{ active: activePanel === 'basic' }" @click="activePanel = 'basic'">
            基本信息
          </button>
          <button class="panel-item" :class="{ active: activePanel === 'member' }" @click="activePanel = 'member'">
            成员管理
          </button>
          <button class="panel-item" :class="{ active: activePanel === 'kb' }" @click="activePanel = 'kb'">
            共享知识库
          </button>
        </aside>

        <section class="manage-main">
          <div class="manage-head">
            <div>
              <h4>{{ panelTitle }}</h4>
              <p>{{ panelHint }}</p>
            </div>
            <el-tag round :type="canManageActiveSpace ? 'success' : 'info'">
              {{ canManageActiveSpace ? '可编辑' : '只读' }}
            </el-tag>
          </div>

          <section v-show="activePanel === 'basic'" class="panel-wrap">
            <el-form label-position="top" class="base-form">
              <el-form-item label="空间名称">
                <el-input v-model="editForm.name" :disabled="!canManageActiveSpace" />
              </el-form-item>
              <el-form-item label="空间描述">
                <el-input v-model="editForm.description" type="textarea" :rows="4" :disabled="!canManageActiveSpace" />
              </el-form-item>
              <el-button type="primary" :disabled="!canManageActiveSpace" @click="saveSpace">保存空间信息</el-button>
            </el-form>
          </section>

          <section v-show="activePanel === 'member'" class="panel-wrap split">
            <div class="manage-card">
              <div class="card-header">
                <h5>用户成员</h5>
              </div>
              <div class="inline-row">
                <el-select v-model="selectedUserId" placeholder="选择用户" filterable :disabled="!canManageActiveSpace">
                  <el-option
                    v-for="u in users"
                    :key="u.id"
                    :label="`${u.full_name} (${u.login_name})`"
                    :value="u.id"
                  />
                </el-select>
                <el-button type="primary" :disabled="!canManageActiveSpace" @click="handleAddUser">添加用户</el-button>
              </div>
              <el-table :data="userMembers" size="small" class="compact-table">
                <el-table-column prop="full_name" label="姓名" min-width="120" />
                <el-table-column prop="login_name" label="账号" min-width="120" />
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button
                      text
                      type="danger"
                      :disabled="!canManageActiveSpace"
                      @click="handleRemoveUser(row.user_id)"
                    >
                      移除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="manage-card">
              <div class="card-header">
                <h5>部门成员</h5>
              </div>
              <div class="inline-row">
                <el-select v-model="selectedDepartmentId" placeholder="选择部门" :disabled="!canManageActiveSpace">
                  <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
                </el-select>
                <el-button type="primary" :disabled="!canManageActiveSpace" @click="handleAddDepartment">添加部门</el-button>
              </div>
              <el-table :data="deptMembers" size="small" class="compact-table">
                <el-table-column prop="department_name" label="部门" min-width="180" />
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button
                      text
                      type="danger"
                      :disabled="!canManageActiveSpace"
                      @click="handleRemoveDepartment(row.department_id)"
                    >
                      移除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </section>

          <section v-show="activePanel === 'kb'" class="panel-wrap">
            <div class="manage-card">
              <div class="card-header">
                <h5>共享知识库</h5>
              </div>
              <div class="inline-row">
                <el-select v-model="selectedKbIdToShare" placeholder="选择知识库" filterable :disabled="!canManageActiveSpace">
                  <el-option v-for="kb in shareableKbsForActiveSpace" :key="kb.id" :label="kb.name" :value="kb.id" />
                </el-select>
                <el-button type="primary" :disabled="!canManageActiveSpace" @click="handleShareKbToActiveSpace">共享到当前空间</el-button>
              </div>
              <el-table :data="spaceKbs" size="small" class="compact-table">
                <el-table-column prop="name" label="知识库名称" min-width="260" />
                <el-table-column prop="visibility" label="可见性" width="110" />
                <el-table-column label="操作" width="120">
                  <template #default="{ row }">
                    <el-button
                      text
                      type="danger"
                      :disabled="!canManageActiveSpace"
                      @click="handleUnshareKbFromSpace(row.id)"
                    >
                      取消共享
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </section>
        </section>
      </div>
      <template #footer>
        <el-button @click="manageVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ─── Page Layout ─────────────────────────────────── */
.spaces-page {
  padding: 28px 32px 32px;
  max-width: 1320px;
}

/* ─── Header ──────────────────────────────────────── */
.head {
  margin-bottom: 20px;
}

.head-meta {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: #9ca3af;
  margin-bottom: 10px;
  text-transform: uppercase;
}

.head-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.head-main h1 {
  margin: 0;
  font-size: 34px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: #1a1d23;
}

.head-main p {
  margin: 6px 0 0;
  color: #8f96a3;
  font-size: 14px;
  line-height: 1.5;
}

.create-btn {
  height: 42px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  padding: 0 18px;
  background: #1a1d23;
  border-color: #1a1d23;
  color: #fff;
  white-space: nowrap;
  flex-shrink: 0;
}

.create-btn:hover {
  background: #2d3340;
  border-color: #2d3340;
}

.create-btn :deep(.el-icon) {
  margin-right: 5px;
  font-size: 14px;
}

/* ─── Guide Banner ────────────────────────────────── */
.guide-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f0faf5;
  border: 1px solid #c8ead8;
  border-radius: 10px;
  padding: 12px 18px;
  margin-bottom: 20px;
}

.guide-icon {
  color: #18b566;
  font-size: 16px;
  flex-shrink: 0;
}

.guide-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.guide-step {
  font-size: 13px;
  color: #4b7a5e;
}

.guide-step.active {
  font-weight: 600;
  color: #18b566;
}

.guide-arrow {
  color: #9ec9b3;
  font-size: 14px;
}

/* ─── Scope Tabs ──────────────────────────────────── */
.scope-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 18px;
  border-bottom: 1px solid #e8ecf1;
}

.scope-tab {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  padding: 8px 16px;
  font-size: 14px;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color 0.15s, border-color 0.15s;
}

.scope-tab.active {
  color: #1a1d23;
  font-weight: 600;
  border-bottom-color: #1a1d23;
}

.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #f0f2f5;
  color: #6b7280;
  font-size: 11px;
  font-weight: 500;
}

.scope-tab.active .tab-count {
  background: #e8ecf1;
  color: #374151;
}

/* ─── Workspace Shell ─────────────────────────────── */
.workspace-shell {
  display: flex;
}

.workspace-content {
  flex: 1;
}

/* ─── Card Grid ───────────────────────────────────── */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.card {
  background: #fff;
  border: 1px solid #e8ecf0;
  border-radius: 14px;
  padding: 18px;
  min-height: 175px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.card:hover {
  border-color: #b8d5c4;
  box-shadow: 0 4px 16px rgba(26, 29, 35, 0.07);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.icon {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}

.icon.mint {
  background: #d4f0e4;
  color: #18b566;
}

.icon.peach {
  background: #fde8d0;
  color: #e07b3a;
}

.icon.lavender {
  background: #e4e0f8;
  color: #7c65d9;
}

/* ─── Card Title ──────────────────────────────────── */
.card-title-block h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1a1d23;
  line-height: 1.2;
}

.owner {
  margin-top: 3px;
  color: #9ca3af;
  font-size: 12px;
}

/* ─── Permission Badge ────────────────────────────── */
.role-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.role-badge.perm-admin {
  background: #d4f0e4;
  color: #18b566;
}

.role-badge.perm-edit {
  background: #fde8d0;
  color: #c05c1a;
}

.role-badge.perm-read {
  background: #f0f2f5;
  color: #6b7280;
}

/* ─── Description ─────────────────────────────────── */
.desc {
  margin: 0 0 14px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ─── Card Footer ─────────────────────────────────── */
.card-foot {
  border-top: 1px solid #f0f2f5;
  padding-top: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.avatars-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.avatar-bubble {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  border: 2px solid #fff;
  margin-left: -6px;
}

.avatars-row .avatar-bubble:first-child {
  margin-left: 0;
}

.avatar-more {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e8ecf0;
  color: #6b7280;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 600;
  border: 2px solid #fff;
  margin-left: -6px;
}

.foot-meta {
  font-size: 12px;
  color: #9ca3af;
  margin-left: 8px;
}

.manage-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
}

.manage-link:hover {
  background: #f0f2f5;
  color: #1a1d23;
}

/* ─── Add Card ────────────────────────────────────── */
.add-card {
  min-height: 175px;
  border: 1.5px dashed #d1d8e0;
  border-radius: 14px;
  background: #fafbfc;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #9ca3af;
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.18s, background 0.18s, color 0.18s;
}

.add-card:hover {
  border-color: #18b566;
  background: #f0faf5;
  color: #18b566;
}

.add-plus {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1.5px dashed currentColor;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  line-height: 1;
}

.manage-shell {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  min-height: 72vh;
  max-height: 80vh;
  border: 1px solid #e8ecf0;
  border-radius: 14px;
  overflow: hidden;
}

.manage-side {
  border-right: 1px solid #e8ecf0;
  background: #f7f8fa;
  padding: 18px 12px;
}

.manage-side h3 {
  margin: 2px 10px 16px;
  font-size: 15px;
  font-weight: 700;
  color: #1a1d23;
}

.panel-item {
  width: 100%;
  border: 0;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  padding: 9px 12px;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  margin-bottom: 4px;
}

.panel-item.active {
  background: #e8f5ee;
  color: #18b566;
  font-weight: 600;
}

.manage-main {
  padding: 20px 22px 14px;
  overflow: auto;
}

.manage-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.manage-head h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1a1d23;
}

.manage-head p {
  margin: 6px 0 0;
  color: #9ca3af;
  font-size: 13px;
}

.panel-wrap {
  border-top: 1px solid #ebeef3;
  padding-top: 16px;
}

.panel-wrap.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.base-form {
  max-width: 980px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.base-form :deep(.el-form-item) {
  margin-bottom: 8px;
}

.base-form :deep(.el-textarea__inner) {
  min-height: 120px;
}

.base-form > .el-button {
  align-self: flex-start;
  margin-top: 4px;
}

.manage-card {
  border: 1px solid #ebeef3;
  border-radius: 12px;
  background: #fafbfd;
  padding: 12px;
}

.card-header {
  margin-bottom: 10px;
}

.card-header h5 {
  margin: 0;
  font-size: 24px;
}

.inline-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}

.inline-row :deep(.el-select) {
  flex: 1;
}

.inline-row .el-button {
  flex-shrink: 0;
}

.compact-table {
  margin-top: 8px;
}

.manage-card :deep(.el-table) {
  border-radius: 10px;
  overflow: hidden;
}

.manage-card :deep(.el-table .el-table__body-wrapper) {
  max-height: 240px;
  overflow-y: auto;
}

:deep(.space-manage-dialog .el-dialog__body) {
  padding: 10px 18px 8px;
}

:deep(.space-manage-dialog .el-dialog) {
  max-width: calc(100vw - 30px);
  border-radius: 20px;
}

:deep(.space-manage-dialog .el-dialog__header) {
  padding: 0;
  margin-right: 0;
}

:deep(.space-manage-dialog .el-dialog__footer) {
  padding: 0 20px 16px;
  display: flex;
  justify-content: flex-end;
  margin-right: 0;
}

@media (max-width: 1200px) {
  .spaces-page {
    padding: 16px;
  }

  .head-main h1 {
    font-size: 26px;
  }

  .create-btn {
    font-size: 13px;
    height: 38px;
  }

  .head-main p {
    font-size: 13px;
  }

  .grid {
    grid-template-columns: 1fr;
  }

  .manage-shell {
    grid-template-columns: 1fr;
    min-height: auto;
    max-height: 78vh;
  }

  .manage-side {
    border-right: none;
    border-bottom: 1px solid #ebeef3;
    padding: 14px;
  }

  .manage-side h3 {
    font-size: 20px;
    margin-bottom: 12px;
  }

  .manage-main {
    padding: 14px;
  }

  .manage-head h4 {
    font-size: 20px;
  }

  .manage-head p {
    font-size: 13px;
    margin-top: 6px;
  }

  .panel-wrap.split {
    grid-template-columns: 1fr;
  }

  .inline-row {
    flex-direction: column;
    align-items: stretch;
  }

  .inline-row .el-button {
    width: 100%;
  }

  .scope-tabs {
    overflow-x: auto;
    flex-wrap: nowrap;
  }
}
</style>
