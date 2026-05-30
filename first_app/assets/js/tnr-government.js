/**
 * TNR Government JS - government-specific functions
 */
function exportLedger() { alert('导出台账数据'); }
function exportReport() { alert('导出报表'); }

function switchLedgerTab(tabName) {
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

function addHospital() { alert("🏥 新增医院（演示模式）"); }
function disableHospital(name) { alert("医院 " + name + " 已停用（演示模式）"); }
function viewHospitalDetail(id) { alert("查看医院详情：" + id); }
function viewShelterDetail(id) { alert("查看捕捉站详情：" + id); }
function viewDetail(id) { alert("查看详情：" + id); }
function viewMaterialDetail(id) { alert("查看物料详情：" + id); }
function viewLedgerDetail(id) { alert("查看台账明细：" + id); }
function applyFilter() { alert("筛选已应用（演示模式）"); }
