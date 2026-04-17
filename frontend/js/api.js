// ==========================================================================
// Configuración Global de la API
// ==========================================================================
// Backend en el puerto 8000; frontend en otro puerto (p. ej. 8001).
// Usar el mismo hostname de la página evita errores de CORS por mezclar
// localhost y 127.0.0.1.
const API_BASE_URL = (() => {
    if (typeof window === 'undefined') return 'http://127.0.0.1:8000/api/v1';
    const host = window.location.hostname || '127.0.0.1';
    return `http://${host}:8000/api/v1`;
})();

// ==========================================================================
// RF19 — Mapa de permisos por página (Frontend Guard)
// ==========================================================================
const ROUTE_PERMISSIONS = {
    'usuarios.html': ['ADMIN'],
    'bitacora.html': ['ADMIN'],
    'auditoria.html': ['ADMIN'],
    'configuracion.html': ['ADMIN'],
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

        const navAuditoria = document.getElementById('navAuditoria');
        if (navAuditoria) {
            if (SecurityService.hasRole(['ADMIN'])) {
                navAuditoria.classList.remove('d-none');
            }
        }

        const navConfig = document.getElementById('navConfig');
        if (navConfig) {
            if (SecurityService.hasRole(['ADMIN'])) {
                navConfig.classList.remove('d-none');
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
    const isAuthEndpoint =
        endpoint.includes('/auth/token/') && !endpoint.includes('/auth/token/refresh/');

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Login: no enviar Bearer; un token viejo no debe interferir con obtener uno nuevo.
    if (token && !isAuthEndpoint) {
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
