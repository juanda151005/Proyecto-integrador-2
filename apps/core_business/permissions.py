from rest_framework import permissions

class IsAnalistaOrAdmin(permissions.BasePermission):
    """
    Permiso que valida que el usuario pertenezca al grupo 'Analista',
    al grupo 'Administrador' o sea un superusuario/staff.
    """
    message = "Acceso restringido. Solo los Analistas y Administradores pueden realizar esta acción."

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        if not (request.user and request.user.is_authenticated):
            return False
            
        if request.user.is_staff or request.user.is_superuser:
            return True
            
        return request.user.groups.filter(
            name__in=['Analista', 'Administrador']
        ).exists()
