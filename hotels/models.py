from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Hotel(models.Model):
    """Modelo para hoteles"""
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('pending', 'Pendiente'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Nombre")
    # Allow longer URLs (some sources include long query strings)
    url = models.URLField(max_length=1000, verbose_name="URL de Scraping")
    # Source and description (used in forms/templates)
    source = models.CharField(max_length=50, blank=True, verbose_name="Fuente")
    description = models.TextField(blank=True, verbose_name="Descripción")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ciudad")
    country = models.CharField(max_length=100, blank=True, verbose_name="País")
    
    # OTASync Integration
    otasync_property_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="OTASync Property ID")
    otasync_room_type_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="OTASync Room Type ID")
    otasync_pricing_plan_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="OTASync Pricing Plan ID")
    otasync_enabled = models.BooleanField(default=False, verbose_name="Sincronización OTASync Habilitada")
    otasync_sync_days = models.IntegerField(default=20, verbose_name="Días de Sincronización")
    
    # Pricing
    price_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, verbose_name="Ajuste de Precio (%)")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Estado")
    enabled = models.BooleanField(default=True, verbose_name="Habilitado")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(null=True, blank=True, verbose_name="Última Sincronización")
    
    # User tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hotels_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hotels_updated')
    
    class Meta:
        verbose_name = "Hotel"
        verbose_name_plural = "Hoteles"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_status_display_class(self):
        """Return CSS class for status"""
        status_classes = {
            'active': 'success',
            'inactive': 'secondary',
            'pending': 'warning',
        }
        return status_classes.get(self.status, 'secondary')


class ScrapingResult(models.Model):
    """Resultados de scraping para un hotel"""
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('success', 'Exitoso'),
        ('error', 'Error'),
        ('failed', 'Fallido'),
    ]
    
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='scraping_results')
    check_in = models.DateField(verbose_name="Fecha de Entrada")
    check_out = models.DateField(verbose_name="Fecha de Salida")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Precio")
    currency = models.CharField(max_length=10, default='MXN', verbose_name="Moneda")
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Estado")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    scraped_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Scraping")
    method = models.CharField(max_length=50, default='intelligent', verbose_name="Método de Scraping")
    success = models.BooleanField(default=True, verbose_name="Éxito")
    error_message = models.TextField(blank=True, verbose_name="Mensaje de Error")
    
    # OTASync sync
    otasync_synced = models.BooleanField(default=False, verbose_name="Sincronizado con OTASync")
    otasync_sync_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Sincronización OTASync")
    
    class Meta:
        verbose_name = "Resultado de Scraping"
        verbose_name_plural = "Resultados de Scraping"
        ordering = ['-scraped_at']
        unique_together = ['hotel', 'check_in', 'check_out']
    
    def __str__(self):
        return f"{self.hotel.name} - {self.check_in} al {self.check_out}: ${self.price}"
    
    def get_status_display_css(self):
        """Return CSS class for status"""
        status_classes = {
            'success': 'success',
            'error': 'danger',
            'failed': 'danger',
            'pending': 'warning',
        }
        return status_classes.get(self.status, 'secondary')


class UserProfile(models.Model):
    """Perfil extendido del usuario"""
    
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('manager', 'Manager'),
        ('viewer', 'Visualizador'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer', verbose_name="Rol")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Avatar")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    
    # Preferences
    dark_mode = models.BooleanField(default=True, verbose_name="Modo Oscuro")
    email_notifications = models.BooleanField(default=True, verbose_name="Notificaciones por Email")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"
    
    def can_edit_hotels(self):
        return self.role in ['admin', 'manager']
    
    def can_manage_users(self):
        return self.role == 'admin'
