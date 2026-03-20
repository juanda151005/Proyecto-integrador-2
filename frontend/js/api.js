// Configuración Global de la API
const API_BASE_URL = 'http://localhost:8000/api/v1';

const SecurityService = {
    // Guarda los datos de sesión (RF02)
    saveSession: (data) => {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('user', JSON.stringify(data.user));
    },

    // Obtener token actual
    getToken: () => localStorage.getItem('access_token'),

    // Obtener usuario actual
    getUser: () => {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    },

    // Cerrar sesión
    logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    },

    // Verifica si está logueado
    isAuthenticated: () => !!localStorage.getItem('access_token'),

    // RF19: Verifica si el usuario tiene permiso según roles permitidos
    hasRole: (allowedRoles) => {
        const user = SecurityService.getUser();
        if (!user) return false;
        return allowedRoles.includes(user.role);
    }
};

// Wrapper para hacer peticiones fetch con el Token automáticamente
async function fetchAPI(endpoint, options = {}) {
    const token = SecurityService.getToken();
    
    // Configurar headers por defecto
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

        // Si devuelve 401 (No Autorizado) y no es el login, cerramos sesión
        if (response.status === 401 && !endpoint.includes('/auth/token/')) {
            SecurityService.logout();
            return null;
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
