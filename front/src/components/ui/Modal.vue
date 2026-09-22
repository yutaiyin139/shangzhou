<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="ui-modal-mask" @click.self="handleMaskClick">
        <div class="ui-modal" :class="[`ui-modal--${size}`, { 'ui-modal--fullscreen': fullscreen }]">
          <!-- 头部 -->
          <div class="ui-modal__header" v-if="showHeader">
            <slot name="header">
              <span class="ui-modal__title">{{ title }}</span>
            </slot>
            <button v-if="closable" class="ui-modal__close" @click="handleClose">✕</button>
          </div>

          <!-- 内容 -->
          <div class="ui-modal__body">
            <slot />
          </div>

          <!-- 底部 -->
          <div class="ui-modal__footer" v-if="showFooter">
            <slot name="footer">
              <Button v-if="showCancel" type="secondary" @click="handleCancel">{{ cancelText }}</Button>
              <Button type="primary" :loading="confirmLoading" @click="handleConfirm">{{ confirmText }}</Button>
            </slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import Button from './Button.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  size: { type: String, default: 'medium' }, // small | medium | large
  fullscreen: { type: Boolean, default: false },
  closable: { type: Boolean, default: true },
  maskClosable: { type: Boolean, default: true },
  showHeader: { type: Boolean, default: true },
  showFooter: { type: Boolean, default: true },
  showCancel: { type: Boolean, default: true },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  confirmLoading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'close', 'cancel', 'confirm'])

function handleClose() {
  emit('update:modelValue', false)
  emit('close')
}

function handleCancel() {
  emit('update:modelValue', false)
  emit('cancel')
}

function handleConfirm() {
  emit('confirm')
}

function handleMaskClick() {
  if (props.maskClosable) {
    handleClose()
  }
}

function handleEsc(e) {
  if (e.key === 'Escape' && props.modelValue && props.closable) {
    handleClose()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEsc)
  if (props.modelValue) {
    document.body.style.overflow = 'hidden'
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEsc)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.ui-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.ui-modal {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  max-height: 85vh;
  overflow: hidden;
}

.ui-modal--small { width: 400px; }
.ui-modal--medium { width: 560px; }
.ui-modal--large { width: 720px; }
.ui-modal--fullscreen {
  width: 95vw;
  height: 90vh;
  max-height: 90vh;
}

.ui-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
}

.ui-modal__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-1);
}

.ui-modal__close {
  background: transparent;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: var(--text-3);
  padding: 4px;
  border-radius: 4px;
}
.ui-modal__close:hover {
  background: var(--border-light);
  color: var(--text-1);
}

.ui-modal__body {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
}

.ui-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 24px;
  border-top: 1px solid var(--border-light);
}

/* 动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-active .ui-modal,
.modal-leave-active .ui-modal {
  transition: transform 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .ui-modal {
  transform: scale(0.95) translateY(-10px);
}
.modal-leave-to .ui-modal {
  transform: scale(0.95) translateY(10px);
}
</style>
