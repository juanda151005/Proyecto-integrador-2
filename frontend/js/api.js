// ==========================================================================
// Configuración Global de la API
// ==========================================================================
const API_BASE_URL = 'http://localhost:8000/api/v1';

// ==========================================================================
// RF19 — Mapa de permisos por página (Frontend Guard)
// ==========================================================================
const ROUTE_PERMISSIONS = {
    'usuarios.html': ['ADMIN'],
    'bitacora.html': ['ADMIN'],
};

// ==========================================================================
// SecurityService — Servicio centralizado de seguridad
// ==========================================================================
const SecurityService = {
    // RF02: Guarda tokens y datos del usuario
    saveSession: (data) => {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('user', JSON.stringify(data.user));
    },

    getToken: () => localStorage.getItem('access_token'),

    getUser: () => {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    },

    logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    },

    isAuthenticated: () => !!localStorage.getItem('access_token'),

    // RF19: Verifica si el usuario tiene el rol requerido
    hasRole: (allowedRoles) => {
        const user = SecurityService.getUser();
        if (!user) return false;
        return allowedRoles.includes(user.role);
    },

    // RF19: Guard centralizado — redirige si no tiene permisos
    requireRole: (allowedRoles) => {
        if (!SecurityService.isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }
        if (!SecurityService.hasRole(allowedRoles)) {
            window.location.href = 'acceso-denegado.html';
            return false;
        }
        return true;
    },

    /**
     * RF19: Inicialización centralizada de página protegida.
     * 
     * Uso: SecurityService.initPage({ requiredRoles: ['ADMIN'] })
     * 
     * - Verifica autenticación
     * - Verifica rol (si se especifica)
     * - Carga datos del usuario en elementos del DOM
     * - Muestra/oculta elementos según rol
     */
    initPage: (config = {}) => {
        // 1. Verificar autenticación
        if (!SecurityService.isAuthenticated()) {
            window.location.href = 'login.html';
            return false;
        }

        // 2. Auto-detect required roles from ROUTE_PERMISSIONS
        const currentPage = window.location.pathname.split('/').pop();
        const pageRoles = ROUTE_PERMISSIONS[currentPage];
        const requiredRoles = config.requiredRoles || pageRoles;

        // 3. Verificar RBAC si hay roles requeridos
        if (requiredRoles && !SecurityService.hasRole(requiredRoles)) {
            window.location.href = 'acceso-denegado.html';
            return false;
        }

        // 4. Cargar datos del usuario en el DOM
        const user = SecurityService.getUser();
        if (user) {
            const nameEl = document.getElementById('userName');
            const roleEl = document.getElementById('userRole');
            if (nameEl) nameEl.innerText = user.first_name || user.username;
            if (roleEl) roleEl.innerText = user.role_display;
        }

        // 5. Mostrar/ocultar elementos según rol
        SecurityService.applyRBAC();

        return true;
    },

    /**
     * RF19: Aplica visibilidad de elementos según rol del usuario.
     * 
     * Busca todos los elementos con atributo data-rbac-roles="ADMIN,ANALYST"
     * y los muestra solo si el usuario tiene uno de esos roles.
     */
    applyRBAC: () => {
        const user = SecurityService.getUser();
        if (!user) return;

        // Mostrar elementos del sidebar según rol
        const navUsers = document.getElementById('navUsers');
        if (navUsers) {
            if (SecurityService.hasRole(['ADMIN'])) {
                navUsers.classList.remove('d-none');
            }
        }

        const navBitacora = document.getElementById('navBitacora');
        if (navBitacora) {
            if (SecurityService.hasRole(['ADMIN'])) {
                navBitacora.classList.remove('d-none');
            }
        }

        // Manejar elementos genéricos con data-rbac-roles
        document.querySelectorAll('[data-rbac-roles]').forEach(el => {
            const roles = el.getAttribute('data-rbac-roles').split(',');
            if (!SecurityService.hasRole(roles)) {
                el.classList.add('d-none');
            } else {
                el.classList.remove('d-none');
            }
        });
    }
};

// ==========================================================================
// Wrapper para peticiones API con JWT automático
// ==========================================================================
async function fetchAPI(endpoint, options = {}) {
    const token = SecurityService.getToken();

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });

        // 401 = Token expirado → cerrar sesión
        if (response.status === 401 && !endpoint.includes('/auth/token/')) {
            SecurityService.logout();
            return null;
        }

        // RF19: 403 = Sin permisos → redirigir
        if (response.status === 403) {
            const data = await response.json().catch(() => ({}));
            console.warn('RBAC: Acceso denegado', data);
            throw { status: 403, data };
        }

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw { status: response.status, data };
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}
