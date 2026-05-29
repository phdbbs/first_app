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
