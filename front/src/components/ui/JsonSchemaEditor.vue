<template>
  <div class="json-schema-editor">
    <div class="jse-head">
      <span class="jse-title">{{ title || 'JSON Schema' }}</span>
      <div class="jse-actions">
        <button class="jse-btn" @click="formatSchema" title="格式化">{'{ }'}</button>
        <button class="jse-btn jse-btn-danger" @click="clearSchema" v-if="clearable">清空</button>
      </div>
    </div>
    <div class="jse-body">
      <div class="jse-toolbar">
        <button class="jse-tool" @click="addProperty('string')">+ 文本</button>
        <button class="jse-tool" @click="addProperty('number')">+ 数字</button>
        <button class="jse-tool" @click="addProperty('boolean')">+ 布尔</button>
        <button class="jse-tool" @click="addProperty('array')">+ 数组</button>
        <button class="jse-tool" @click="addProperty('object')">+ 对象</button>
      </div>
      <div class="jse-properties">
        <div v-for="(prop, key) in schemaProperties" :key="key" class="jse-prop">
          <input class="jse-prop-name" v-model="prop.name" placeholder="字段名" @change="emitChange">
          <select class="jse-prop-type" v-model="prop.type" @change="emitChange">
            <option value="string">文本</option>
            <option value="number">数字</option>
            <option value="integer">整数</option>
            <option value="boolean">布尔</option>
            <option value="array">数组</option>
            <option value="object">对象</option>
          </select>
          <input class="jse-prop-desc" v-model="prop.description" placeholder="描述" @change="emitChange">
          <label class="jse-prop-required">
            <input type="checkbox" v-model="prop.required" @change="emitChange"> 必填
          </label>
          <button class="jse-prop-del" @click="removeProperty(key)">✕</button>
        </div>
        <div v-if="schemaProperties.length === 0" class="jse-empty">
          点击上方按钮添加字段，或直接编辑右侧 JSON
        </div>
      </div>
      <div class="jse-json">
        <div class="jse-json-head">JSON 预览</div>
        <textarea
          class="jse-json-text"
          v-model="jsonText"
          @blur="parseJson"
          :placeholder="jsonPlaceholder"
          rows="10"
        ></textarea>
        <div v-if="jsonError" class="jse-error">{{ jsonError }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  title: { type: String, default: 'JSON Schema' },
  clearable: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue'])

const schemaProperties = ref([])
const jsonText = ref('')
const jsonError = ref('')

const jsonPlaceholder = `{
  "name": { "type": "string", "description": "名称" },
  "age": { "type": "number", "description": "年龄" }
}`

function buildSchema() {
  const properties = {}
  const required = []
  schemaProperties.value.forEach(prop => {
    if (!prop.name) return
    const field = { type: prop.type, description: prop.description || '' }
    if (prop.type === 'array') {
      field.items = { type: 'string' }
    }
    if (prop.type === 'object') {
      field.properties = {}
    }
    properties[prop.name] = field
    if (prop.required) {
      required.push(prop.name)
    }
  })
  return { type: 'object', properties, required }
}

function emitChange() {
  const schema = buildSchema()
  emit('update:modelValue', schema)
  jsonText.value = JSON.stringify(schema, null, 2)
  jsonError.value = ''
}

function parseJson() {
  try {
    const parsed = JSON.parse(jsonText.value)
    // 反向解析为属性列表
    const props = []
    if (parsed && parsed.properties) {
      const requiredSet = new Set(parsed.required || [])
      Object.entries(parsed.properties).forEach(([name, def]) => {
        props.push({
          name,
          type: def.type || 'string',
          description: def.description || '',
          required: requiredSet.has(name),
        })
      })
    }
    schemaProperties.value = props
    jsonError.value = ''
    emit('update:modelValue', parsed)
  } catch (e) {
    jsonError.value = 'JSON 格式错误: ' + e.message
  }
}

function formatSchema() {
  jsonText.value = JSON.stringify(buildSchema(), null, 2)
  jsonError.value = ''
}

function clearSchema() {
  schemaProperties.value = []
  jsonText.value = ''
  jsonError.value = ''
  emit('update:modelValue', { type: 'object', properties: {}, required: [] })
}

function addProperty(type) {
  const idx = schemaProperties.value.length + 1
  schemaProperties.value.push({
    name: `field_${idx}`,
    type,
    description: '',
    required: false,
  })
  emitChange()
}

function removeProperty(idx) {
  schemaProperties.value.splice(idx, 1)
  emitChange()
}

onMounted(() => {
  // 从 modelValue 初始化
  if (props.modelValue && props.modelValue.properties) {
    const props2 = []
    const requiredSet = new Set(props.modelValue.required || [])
    Object.entries(props.modelValue.properties).forEach(([name, def]) => {
      props2.push({
        name,
        type: def.type || 'string',
        description: def.description || '',
        required: requiredSet.has(name),
      })
    })
    schemaProperties.value = props2
    jsonText.value = JSON.stringify(props.modelValue, null, 2)
  } else {
    jsonText.value = JSON.stringify({ type: 'object', properties: {}, required: [] }, null, 2)
  }
})
</script>

<style scoped>
.json-schema-editor {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.jse-head {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-page);
  border-bottom: 1px solid var(--border-light);
}
.jse-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-1);
}
.jse-actions { margin-left: auto; display: flex; gap: 6px; }
.jse-btn {
  font-size: 12px;
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  color: var(--text-2);
  font-family: monospace;
}
.jse-btn:hover { border-color: var(--primary); color: var(--primary); }
.jse-btn-danger:hover { border-color: var(--red); color: var(--red); }
.jse-body { display: flex; flex-direction: column; }
.jse-toolbar {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
  flex-wrap: wrap;
}
.jse-tool {
  font-size: 11px;
  padding: 3px 8px;
  border: 1px dashed var(--border);
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  color: var(--text-2);
}
.jse-tool:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-light); }
.jse-properties { padding: 8px 12px; max-height: 200px; overflow-y: auto; }
.jse-prop {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.jse-prop-name {
  width: 100px;
  font-size: 12px;
  padding: 4px 6px;
  border: 1px solid var(--border);
  border-radius: 4px;
}
.jse-prop-type {
  width: 70px;
  font-size: 12px;
  padding: 4px 6px;
  border: 1px solid var(--border);
  border-radius: 4px;
}
.jse-prop-desc {
  flex: 1;
  font-size: 12px;
  padding: 4px 6px;
  border: 1px solid var(--border);
  border-radius: 4px;
}
.jse-prop-required {
  font-size: 11px;
  color: var(--text-3);
  display: flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}
.jse-prop-del {
  border: none;
  background: none;
  color: var(--text-4);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
}
.jse-prop-del:hover { color: var(--red); }
.jse-empty {
  font-size: 12px;
  color: var(--text-4);
  text-align: center;
  padding: 16px 0;
}
.jse-json {
  border-top: 1px solid var(--border-light);
}
.jse-json-head {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-3);
  padding: 6px 12px;
  background: var(--bg-page);
}
.jse-json-text {
  width: 100%;
  border: none;
  padding: 8px 12px;
  font-family: monospace;
  font-size: 12px;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  color: var(--text-1);
}
.jse-error {
  font-size: 11px;
  color: var(--red);
  padding: 4px 12px;
  background: var(--red-bg);
}
</style>
