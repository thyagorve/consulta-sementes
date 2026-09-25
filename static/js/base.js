// Theme management
(function() {
    'use strict';

    // Aplicar tema ao carregar
    function applyTheme() {
        const theme = localStorage.getItem("theme") || "light";
        document.documentElement.classList.toggle("dark-mode", theme === "dark");
        updateThemeIcon();
    }

    // Alternar tema
    function toggleTheme() {
        const isDarkMode = document.documentElement.classList.toggle("dark-mode");
        localStorage.setItem("theme", isDarkMode ? "dark" : "light");
        updateThemeIcon();
        showThemeNotification(isDarkMode);
    }

    // Atualizar ícone do tema
    function updateThemeIcon() {
        const themeIcons = document.querySelectorAll('.theme-toggle i');
        const isDarkMode = document.documentElement.classList.contains("dark-mode");
        
        themeIcons.forEach(icon => {
            icon.className = isDarkMode ? 'fas fa-sun' : 'fas fa-moon';
        });
    }

    // Mostrar notificação de tema alterado
    function showThemeNotification(isDarkMode) {
        // Criar notificação temporária
        const notification = document.createElement('div');
        notification.className = 'theme-notification';
        notification.innerHTML = `
            <i class="fas ${isDarkMode ? 'fa-moon' : 'fa-sun'}"></i>
            <span>Tema ${isDarkMode ? 'escuro' : 'claro'} ativado</span>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 90px;
            right: 20px;
            background: var(--card-bg);
            color: var(--text-color);
            padding: 1rem 1.5rem;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow-lg);
            z-index: 1002;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 500;
            border-left: 4px solid var(--accent-color);
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    // Menu sidebar
    function initSidebar() {
        const menuToggle = document.getElementById('menuToggle');
        const sidebar = document.getElementById('sidebar');
        const content = document.getElementById('content');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        const menuItems = document.querySelectorAll('.menu-toggle');

        function toggleSidebar() {
            const isMobile = window.innerWidth <= 768;
            
            if (isMobile) {
                sidebar.classList.toggle('mobile-open');
                sidebarOverlay.classList.toggle('show');
                document.body.style.overflow = sidebar.classList.contains('mobile-open') ? 'hidden' : '';
            } else {
                sidebar.classList.toggle('collapsed');
                content.classList.toggle('expanded');
            }
        }

        function closeSidebar() {
            sidebar.classList.remove('mobile-open');
            sidebarOverlay.classList.remove('show');
            document.body.style.overflow = '';
        }

        // Event listeners
        menuToggle.addEventListener('click', toggleSidebar);
        sidebarOverlay.addEventListener('click', closeSidebar);

        // Menu toggle functionality
        menuItems.forEach(item => {
            item.addEventListener('click', function() {
                const target = this.getAttribute('data-target');
                const submenu = document.getElementById(target);
                const arrow = this.querySelector('.dropdown-arrow');
                
                this.classList.toggle('active');
                submenu.classList.toggle('expanded');
                
                // Close other open submenus
                if (this.classList.contains('active')) {
                    menuItems.forEach(otherItem => {
                        if (otherItem !== this && otherItem.classList.contains('active')) {
                            const otherTarget = otherItem.getAttribute('data-target');
                            const otherSubmenu = document.getElementById(otherTarget);
                            otherItem.classList.remove('active');
                            otherSubmenu.classList.remove('expanded');
                        }
                    });
                }
            });
        });

        // Close sidebar when clicking on links in mobile
        document.querySelectorAll('.sidebar a').forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    closeSidebar();
                }
            });
        });

        // Adicionar efeito de hover nos itens do menu
        document.querySelectorAll('.menu-item, .submenu-item').forEach(item => {
            item.addEventListener('mouseenter', function() {
                this.style.transform = 'translateX(8px)';
            });
            
            item.addEventListener('mouseleave', function() {
                this.style.transform = 'translateX(0)';
            });
        });
    }

    // User menu
    function initUserMenu() {
        const userMenuToggle = document.getElementById('userMenuToggle');
        const userMenuDropdown = document.getElementById('userMenuDropdown');

        function toggleUserMenu() {
            userMenuDropdown.classList.toggle('show');
        }

        function closeUserMenu() {
            userMenuDropdown.classList.remove('show');
        }

        userMenuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleUserMenu();
        });

        // Close user menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!userMenuToggle.contains(e.target) && !userMenuDropdown.contains(e.target)) {
                closeUserMenu();
            }
        });

        // Close user menu on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeUserMenu();
            }
        });
    }

    // Responsive layout
    function handleResponsiveLayout() {
        const sidebar = document.getElementById('sidebar');
        const content = document.getElementById('content');
        
        if (window.innerWidth >= 769) {
            sidebar.classList.remove('mobile-open', 'collapsed');
            content.classList.remove('expanded');
        } else {
            sidebar.classList.add('collapsed');
            content.classList.add('expanded');
        }
    }

    // Sistema de notificações
    function initNotifications() {
        // Verificar status do sistema
        checkSystemStatus();
        
        // Verificar atualizações
        checkForUpdates();
    }

    function checkSystemStatus() {
        // Simular verificação de status
        const statusIndicator = document.querySelector('.status-indicator');
        if (statusIndicator) {
            // Em uma aplicação real, isso viria de uma API
            statusIndicator.innerHTML = '<i class="fas fa-circle status-online"></i> Sistema Online';
        }
    }

    function checkForUpdates() {
        // Simular verificação de atualizações
        setTimeout(() => {
            // Em uma aplicação real, isso verificaria uma API
        }, 2000);
    }

    // Initialize everything when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        applyTheme();
        initSidebar();
        initUserMenu();
        initNotifications();
        handleResponsiveLayout();

        // Add loaded class for animations
        setTimeout(() => {
            document.body.classList.add('loaded');
        }, 100);
    });

    // Handle window resize
    window.addEventListener('resize', function() {
        handleResponsiveLayout();
        
        // Close mobile sidebar when resizing to desktop
        if (window.innerWidth >= 769) {
            const sidebarOverlay = document.getElementById('sidebarOverlay');
            sidebarOverlay.classList.remove('show');
            document.body.style.overflow = '';
        }
    });

    // Adicionar animações CSS dinâmicas
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .menu-item, .submenu-item {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
    `;
    document.head.appendChild(style);

    // Make functions globally available
    window.toggleTheme = toggleTheme;
    window.applyTheme = applyTheme;

})();