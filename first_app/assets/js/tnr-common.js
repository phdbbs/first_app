/* ===== TNR Common JavaScript - UX Enhancements ===== */

// Show current date/time in elements with id="currentTime"
function showCurrentDate() {
    const elements = document.querySelectorAll('#currentTime');
    if (elements.length === 0) return;
    
    function updateTime() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
        const weekDay = weekDays[now.getDay()];
        const dateStr = ${year}-- :: 周;
        elements.forEach(el => { el.textContent = dateStr; });
    }
    
    updateTime();
    setInterval(updateTime, 1000);
}

// Tab switching with smooth animation
function switchTab(tabName) {
    // Find all tab bars and their associated content
    const tabItems = document.querySelectorAll('.tab-item');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabItems.forEach(item => item.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    
    // Find the clicked tab and activate it
    tabItems.forEach(item => {
        if (item.getAttribute('onclick')?.includes(tabName)) {
            item.classList.add('active');
        }
    });
    
    const targetContent = document.getElementById(tabName + 'Tab');
    if (targetContent) {
        targetContent.classList.add('active');
    }
}

// Report tab switching
function switchReportTab(tabName) {
    const tabItems = document.querySelectorAll('[onclick*="switchReportTab"]');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabItems.forEach(item => item.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    
    tabItems.forEach(item => {
        if (item.getAttribute('onclick')?.includes(tabName)) {
            item.classList.add('active');
        }
    });
    
    const targetContent = document.getElementById(tabName + 'Tab');
    if (targetContent) {
        targetContent.classList.add('active');
    }
}

// Modal management
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

// Close modal on overlay click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay') && e.target.classList.contains('active')) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// Close modal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(modal => {
            modal.classList.remove('active');
        });
        document.body.style.overflow = '';
    }
});

// Photo upload simulation
function uploadPhoto(element) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(ev) {
                element.innerHTML = ''; // Clear content
                element.style.border = 'none';
                element.style.padding = '0';
                const img = document.createElement('img');
                img.src = ev.target.result;
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.objectFit = 'cover';
                img.style.borderRadius = '12px';
                element.appendChild(img);
            };
            reader.readAsDataURL(file);
        }
    };
    input.click();
}

// Signature pad functionality
function initSignaturePad(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    
    const ctx = canvas.getContext('2d');
    let isDrawing = false;
    let lastX = 0, lastY = 0;
    
    function resizeCanvas() {
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;
        ctx.strokeStyle = '#1e293b';
        ctx.lineWidth = 2.5;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
    }
    
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    function getPosition(e) {
        const rect = canvas.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return { x: clientX - rect.left, y: clientY - rect.top };
    }
    
    function startDrawing(e) {
        e.preventDefault();
        isDrawing = true;
        const pos = getPosition(e);
        lastX = pos.x;
        lastY = pos.y;
    }
    
    function draw(e) {
        e.preventDefault();
        if (!isDrawing) return;
        const pos = getPosition(e);
        ctx.beginPath();
        ctx.moveTo(lastX, lastY);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
        lastX = pos.x;
        lastY = pos.y;
    }
    
    function stopDrawing() {
        isDrawing = false;
    }
    
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseleave', stopDrawing);
    canvas.addEventListener('touchstart', startDrawing, { passive: false });
    canvas.addEventListener('touchmove', draw, { passive: false });
    canvas.addEventListener('touchend', stopDrawing);
    
    return { clear: () => ctx.clearRect(0, 0, canvas.width, canvas.height) };
}

function clearSignature() {
    const canvas = document.getElementById('signatureCanvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
}

// Location simulation
function getLocation() {
    const input = document.getElementById('community');
    if (input) {
        input.value = '阳光花园小区 📍 已定位';
        input.style.borderColor = '#22c55e';
    }
}

// Filter functions
function filterTransfers() { /* placeholder */ }
function filterApplications() { /* placeholder */ }
function filterMaterials() { /* placeholder */ }

// Placeholder action functions
function openTransferModal() { openModal('transferModal'); }
function openPurchaseModal() { openModal('purchaseModal'); }
function openOutboundModal() { openModal('outboundModal'); }
function openRecoverModal() { openModal('recoverModal'); }
function openReleaseModal() { openModal('releaseModal'); }
function openAdoptionHallModal() { openModal('adoptionHallModal'); }
function openOwnerReturnModal() { openModal('ownerReturnModal'); }
function openTreatmentModal() { openModal('treatmentModal'); }

function confirmDeparture(id) { alert('🚚 批次 ' + id + ' 已发车'); }
function confirmArrival(id) { alert('✅ 批次 ' + id + ' 已到达'); }
function confirmReceive(id) { alert('✅ 批次 ' + id + ' 已接收'); }
function confirmRecover(id) { alert('✅ 动物 ' + id + ' 已确认回收'); }
function approveApplication(id) { alert('✅ 申请 ' + id + ' 已通过'); }
function rejectApplication(id) { alert('❌ 申请 ' + id + ' 已拒绝'); }
function viewTransferDetail(id) { alert('📋 查看转运详情：' + id); }
function viewAnimalDetail(id) { alert('📋 查看动物详情：' + id); }
function viewApplicationDetail(id) { alert('📋 查看申请详情：' + id); }
function viewMaterialDetail(id) { alert('📋 查看物料详情：' + id); }
function viewReleaseDetail(id) { alert('📋 查看放归详情：' + id); }
function viewTransferDoc(id) { alert('📋 查看单据：' + id); }
function printTransferDoc(id) { alert('🖨️ 打印单据：' + id); }
function quickRestock(id, name) { alert('⚠️ 快速补货：' + name); }
function selectAnimalForAdoption(name) { alert('🐾 选择领养：' + name); }
function submitForm() { alert('✅ 提交成功！已生成捕捉单据'); }
function submitPurchase() { alert('✅ 采购入库成功'); }
function submitOutbound() { alert('✅ 下发出库成功'); }
function submitRestock() { alert('✅ 补货成功'); }
function submitTransfer() { alert('✅ 转运单已创建'); }
function submitReissue() { alert('✅ 已重新下发'); }
function submitRecover() { alert('✅ 回收成功'); }
function submitRelease() { alert('✅ 放归单已创建'); }
function submitPropertyConfirm() { alert('✅ 物业确认成功'); }
function submitAdoptApplication() { alert('✅ 领养申请已提交，请等待线下联系'); }
function generatePetIds() { alert('✅ 已重新生成宠物编号'); }
function openReissueModal(id) { alert('🔄 重新下发：' + id); }
function viewRejectDetail(id) { alert('📋 查看驳回详情：' + id); }
function recoverAnimal(name) { alert('⚠️ 已发起收回 ' + name + ' 的流程'); }
function exportReport(type) { alert('📥 导出 ' + type + ' 报表'); }
function printReport(type) { alert('🖨️ 打印 ' + type + ' 报表'); }

function viewPetArchive(id) {
    var data = {
        'A001': { name: '大橘', chip: 'Chip001', status: '已放归', type: '橘猫·公·2岁', timeline: [
            {step:'捕捉登记',desc:'阳光花园小区 · 物业交接人：张经理',date:'2025-01-05'},
            {step:'转运交接',desc:'批次号 TR20250105001 → 爱心宠物医院',date:'2025-01-05'},
            {step:'绝育手术',desc:'公猫绝育 · 术后恢复良好',date:'2025-01-06'},
            {step:'疫苗接种',desc:'狂犬疫苗 + 猫三联（已完成）',date:'2025-01-07'},
            {step:'芯片植入',desc:'芯片号 Chip001',date:'2025-01-07'},
            {step:'治愈回收',desc:'从爱心宠物医院回收至捕捉站',date:'2025-01-10'},
            {step:'放归确认',desc:'阳光花园小区 · 物业已签字确认',date:'2025-01-12'}
        ]},
        'A002': { name: '花花', chip: 'Chip002', status: '已放归', type: '狸花猫·母·1岁', timeline: [
            {step:'捕捉登记',desc:'幸福家园小区 · 物业交接人：李主任',date:'2025-01-03'},
            {step:'转运交接',desc:'批次号 TR20250103001 → 爱心宠物医院',date:'2025-01-03'},
            {step:'绝育手术',desc:'母猫绝育 · 术后恢复良好',date:'2025-01-04'},
            {step:'疫苗接种',desc:'狂犬疫苗 + 猫三联（已完成）',date:'2025-01-06'},
            {step:'芯片植入',desc:'芯片号 Chip002',date:'2025-01-06'},
            {step:'治愈回收',desc:'从爱心宠物医院回收至捕捉站',date:'2025-01-09'},
            {step:'放归确认',desc:'幸福家园小区 · 物业已签字确认',date:'2025-01-11'}
        ]},
        'A005': { name: '小橘', chip: 'Chip005', status: '已领养', type: '橘猫·公·2岁', timeline: [
            {step:'捕捉登记',desc:'阳光花园小区 · 物业交接人：张经理',date:'2024-12-20'},
            {step:'转运交接',desc:'批次号 TR20241220001 → 瑞鹏宠物医院',date:'2024-12-20'},
            {step:'绝育手术',desc:'公猫绝育 · 术后恢复良好',date:'2024-12-21'},
            {step:'疫苗接种',desc:'狂犬疫苗 + 猫三联（已完成）',date:'2024-12-23'},
            {step:'芯片植入',desc:'芯片号 Chip005',date:'2024-12-23'},
            {step:'治愈回收',desc:'从瑞鹏宠物医院回收至捕捉站',date:'2024-12-26'},
            {step:'领养审核',desc:'领养人：王女士 · 审核通过',date:'2024-12-28'},
            {step:'领养确认',desc:'已交接至领养人',date:'2024-12-30'}
        ]},
        'A008': { name: '雪球', chip: 'Chip008', status: '已领养', type: '白猫·母·1岁', timeline: [
            {step:'捕捉登记',desc:'幸福家园小区 · 物业交接人：李主任',date:'2024-12-15'},
            {step:'转运交接',desc:'批次号 TR20241215001 → 爱心宠物医院',date:'2024-12-15'},
            {step:'绝育手术',desc:'母猫绝育 · 术后恢复良好',date:'2024-12-16'},
            {step:'疫苗接种',desc:'狂犬疫苗 + 猫三联（已完成）',date:'2024-12-18'},
            {step:'芯片植入',desc:'芯片号 Chip008',date:'2024-12-18'},
            {step:'治愈回收',desc:'从爱心宠物医院回收至捕捉站',date:'2024-12-22'},
            {step:'领养审核',desc:'领养人：陈先生 · 审核通过',date:'2024-12-25'},
            {step:'领养确认',desc:'已交接至领养人',date:'2024-12-27'}
        ]}
    };
    var d = data[id] || data['A001'];
    document.getElementById('archAnimalId').textContent = id;
    document.getElementById('archAnimalName').textContent = d.name;
    document.getElementById('archChipNo').textContent = d.chip;
    document.getElementById('archStatus').textContent = d.status;
    var priorities = ['priority-high','priority-medium','priority-medium','priority-low','priority-low','priority-low','priority-low','priority-low'];
    var tl = document.getElementById('archTimeline');
    tl.innerHTML = '';
    d.timeline.forEach(function(item, i) {
        tl.innerHTML += '<div class="task-item"><div class="task-priority ' + (priorities[i]||'priority-low') + '"></div><div class="task-content"><div class="task-name">' + item.step + '</div><div class="task-desc">' + item.desc + '</div></div><div class="task-time">' + item.date + '</div><span class="badge badge-ok">已完成</span></div>';
    });
    openModal('archiveModal');
}
function approveOwnerReturn(id) { alert('✅ 领回申请 ' + id + ' 已通过'); }
function rejectOwnerReturn(id) { alert('❌ 领回申请 ' + id + ' 已拒绝'); }
function viewOwnerReturnDetail(id) { alert('📋 查看领回详情：' + id); }
function approveApplication(id) { alert('✅ 领养申请 ' + id + ' 已通过'); }
function rejectApplication(id) { alert('❌ 领养申请 ' + id + ' 已拒绝'); }
function viewApplicationDetail(id) { alert('📋 查看领养详情：' + id); }
function quickRestock(id, name) { alert('📦 补货：' + name + '（' + id + '）'); }
function viewMaterialDetail(id) { alert('📋 查看物料详情：' + id); }
function openTreatmentModal() { openModal('treatmentModal'); }
function selectAnimalForAdoption(name) { alert('✅ ' + name + ' 已设为可领养状态'); }
function viewDetail(id) { alert('📋 查看详情：' + id); }
function confirmReceive(id) { alert('✅ 转运单 ' + id + ' 已确认接收'); }
function exportLedger() { alert('📥 导出全局台账汇总'); }
function switchTab(tab) { alert('📑 切换到' + tab + '台账'); }
function addHospital() { alert('➕ 新增机构（演示模式）'); }
function viewShelterDetail(id) { alert('📋 查看捕捉站详情：' + id); }
function viewHospitalDetail(id) { alert('📋 查看医院详情：' + id); }
function submitCheckin() { alert('✅ 打卡成功，请上传照片'); }
function submitTreatment() { alert('✅ 诊疗记录已创建'); closeModal('treatmentModal'); }

// Initialize signature pad on page load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('signatureCanvas')) {
        initSignaturePad('signatureCanvas');
    }
});
