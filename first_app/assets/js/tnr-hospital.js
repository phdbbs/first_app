/**
 * TNR Hospital JS - hospital-specific functions
 */
function toggleTreatment(element, type) {
  element.classList.toggle('selected');
  var section = document.getElementById(type + '-section');
  if (section) section.style.display = element.classList.contains('selected') ? 'block' : 'none';
}

function selectChip(element) {
  if (element.classList.contains('unavailable')) return;
  document.querySelectorAll('.chip-item').forEach(function(item) { item.classList.remove('selected'); });
  element.classList.add('selected');
}

function submitTreatment() {
  var requiredInputs = document.querySelectorAll('input.required, textarea.required, select.required');
  var isValid = true;
  requiredInputs.forEach(function(input) {
    if (!input.value.trim()) { input.style.borderColor = '#d32f2f'; isValid = false; }
  });
  var selectedChip = document.querySelector('.chip-item.selected:not(.unavailable)');
  if (!selectedChip) { alert('请选择芯片编号'); isValid = false; }
  if (isValid) {
    alert('✅ 诊疗记录保存成功！');
    TNR.store.set('lastTreatment', { date: new Date().toISOString(), status: 'success' });
  } else { alert('请填写所有必填项'); }
}


// ====== Receive ======
function confirmReceive() { alert("✅ 已确认接收（演示模式）"); }
function confirmReject() { alert("❌ 已驳回（演示模式）"); }
function viewDetail(id) { alert("查看详情：" + id); }

// ====== Material ======
function filterMaterials() { /* handled by UI */ }
function confirmArrival(id) { alert("物料 " + id + " 已确认到货"); }
function applyRestock(type) { alert("补货申请：" + type); }

// ====== Adoption (Hospital) ======
function submitApply() { alert("申请已提交（演示模式）"); }

// ====== Euthanasia ======
function addMedicalRow(type) { alert("新增医疗记录：" + type); }
