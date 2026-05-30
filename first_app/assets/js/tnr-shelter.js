/* ===== TNR Shelter (捕捉站) JavaScript ===== */

// Inject sidebar navigation
function injectSidebar(activePage) {
    const sidebar = document.createElement('div');
    sidebar.className = 'sidebar';
    
    const navItems = [
        { icon: '📊', label: '首页看板', page: 'homepage', href: 'homepage.html' },
        { icon: '➕', label: '新增捕捉', page: 'add-shelter', href: 'add-shelter.html' },
        { icon: '🚚', label: '转运交接', page: 'transfer', href: 'transfer.html' },
        { icon: '🏠', label: '主人领回', page: 'owner-return', href: 'owner-return.html' },
        { icon: '🌿', label: '放归管理', page: 'release', href: 'release.html' },
        { icon: '👤', label: '领养管理', page: 'adoption', href: 'adoption.html' },
        { icon: '📦', label: '物料管理', page: 'material', href: 'material.html' },
        { icon: '📋', label: '宠物档案', page: 'pet-archive', href: 'pet-archive.html' },
        { icon: '📱', label: '一宠一码', page: 'pet-code', href: 'pet-code.html' },
        { icon: '📈', label: '数据报表', page: 'report', href: 'report.html' },
    ];
    
    let navHtml = navItems.map(item => 
        <a href="" class="nav-item ">
            <span class="nav-icon"></span>
            <span class="nav-label"></span>
        </a>
    ).join('');
    
    sidebar.innerHTML = 
        <div class="sidebar-header">
            <div class="sidebar-logo">
                <div class="sidebar-logo-icon">🏠</div>
                <div><h1>捕捉站端</h1><div class="sidebar-subtitle">TNR 管理系统</div></div>
            </div>
        </div>
        <nav class="nav-menu">
            <div class="nav-divider"></div>
            <a href="settings.html" class="nav-item ">
                <span class="nav-icon">⚙️</span>
                <span class="nav-label">系统设置</span>
            </a>
        </nav>
        <div class="sidebar-footer">
            <div class="user-section">
                <div class="user-info">
                    <div class="user-avatar">管</div>
                    <div class="user-details">
                        <div class="user-name">管理员</div>
                        <div class="user-role">捕捉站 · 超级管理员</div>
                    </div>
                </div>
            </div>
        </div>
    ;
    
    document.body.insertBefore(sidebar, document.body.firstChild);
}

function openCodeModal() {
    document.getElementById('codeModalTitle').textContent = '生成二维码';
    document.getElementById('codeAnimalId').value = '';
    document.getElementById('codeChipNo').value = '';
    document.getElementById('codePreview').style.display = 'none';
    document.getElementById('codeActionBtn').textContent = '确认生成';
    openModal('codeModal');
}

function viewPetCode(id) {
    var data = {
        'A001': { chip: 'Chip001', name: '大橘' },
        'A002': { chip: 'Chip002', name: '花花' },
        'A005': { chip: 'Chip005', name: '小橘' },
        'A008': { chip: 'Chip008', name: '雪球' }
    };
    var d = data[id] || { chip: '未知', name: '未知' };
    document.getElementById('codeModalTitle').textContent = '查看二维码 - ' + id;
    document.getElementById('codeAnimalId').value = id;
    document.getElementById('codeChipNo').value = d.chip;
    document.getElementById('codePreview').style.display = 'block';
    document.getElementById('codePreviewInfo').textContent = id + ' · ' + d.name + ' · ' + d.chip;
    document.getElementById('codeActionBtn').textContent = '重新生成';
    openModal('codeModal');
}

function printPetCode(id) {
    alert('🖨️ 打印 ' + id + ' 的二维码标签（演示模式）');
}

function generatePetCode(id) {
    var data = {
        'A012': { chip: 'Chip012', name: '橘猫' },
        'A015': { chip: 'Chip015', name: '狸花猫' }
    };
    var d = data[id] || { chip: '未知', name: '未知' };
    document.getElementById('codeModalTitle').textContent = '生成二维码 - ' + id;
    document.getElementById('codeAnimalId').value = id;
    document.getElementById('codeChipNo').value = d.chip;
    document.getElementById('codePreview').style.display = 'none';
    document.getElementById('codeActionBtn').textContent = '确认生成';
    openModal('codeModal');
}

function confirmGenerate() {
    var id = document.getElementById('codeAnimalId').value;
    if (!id) { alert('请输入动物编号'); return; }
    document.getElementById('codePreview').style.display = 'block';
    document.getElementById('codePreviewInfo').textContent = id + ' · 二维码已生成';
    document.getElementById('codeActionBtn').textContent = '打印二维码';
    alert('✅ ' + id + ' 的二维码已生成成功！');
}

function switchMaterialTab(tabName) {
    var tabItems = document.querySelectorAll('.tab-item');
    var tabContents = document.querySelectorAll('.tab-content');
    tabItems.forEach(function(item) { item.classList.remove('active'); });
    tabContents.forEach(function(content) { content.classList.remove('active'); });
    tabItems.forEach(function(item) {
        if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(tabName)) {
            item.classList.add('active');
        }
    });
    var targetContent = document.getElementById(tabName + 'Tab');
    if (targetContent) { targetContent.classList.add('active'); }
}

function switchTransferTab(tabName) {
    var tabItems = document.querySelectorAll('.tab-item');
    var tabContents = document.querySelectorAll('.tab-content');
    tabItems.forEach(function(item) { item.classList.remove('active'); });
    tabContents.forEach(function(content) { content.classList.remove('active'); });
    tabItems.forEach(function(item) {
        if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(tabName)) {
            item.classList.add('active');
        }
    });
    var targetContent = document.getElementById(tabName + 'Tab');
    if (targetContent) { targetContent.classList.add('active'); }
}

function openPurchaseModal() { openModal('purchaseModal'); }
function submitPurchase() { alert('✅ 采购入库申请已提交'); closeModal('purchaseModal'); }
function openOutboundModal() { openModal('outboundModal'); }
function submitOutbound() { alert('✅ 下发出库申请已提交'); closeModal('outboundModal'); }
function confirmReceive(id) { alert('✅ 已确认接收：' + id); }
function submitOwnerReturn() { alert('✅ 领回申请已提交'); closeModal('ownerReturnModal'); }

function openTransferModal() { openModal('transferModal'); }
function submitTransfer() { alert('✅ 转运单已创建成功'); closeModal('transferModal'); }
function confirmDeparture(id) { alert('🚚 转运批次 ' + id + ' 已发车'); }
function confirmArrival(id) { alert('✅ 转运批次 ' + id + ' 已到达医院'); }
function viewTransferDetail(id) { alert('📋 查看转运详情：' + id); }
function printTransferDoc(id) { alert('🖨️ 打印转运单据：' + id); }
function openReissueModal(id) {
    document.getElementById('reissueBatchNo').value = id;
    openModal('reissueModal');
}
function submitReissue() {
    var id = document.getElementById('reissueBatchNo').value;
    alert('✅ 转运批次 ' + id + ' 已重新发起');
    closeModal('reissueModal');
}
