from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, CreateView, UpdateView
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from hotels.models import UserProfile
from .forms import CustomUserCreationForm, ProfileUpdateForm


class CustomLoginView(LoginView):
    """Custom login view with dark theme"""
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'¡Bienvenido {self.request.user.first_name or self.request.user.username}!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Credenciales incorrectas. Por favor verifica tu usuario y contraseña.')
        return super().form_invalid(form)


class RegisterView(LoginRequiredMixin, CreateView):
    """User registration view - only for admins"""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'authentication/register.html'
    success_url = reverse_lazy('dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow admin users to register new users
        if not request.user.is_superuser:
            messages.error(request, 'No tienes permisos para registrar usuarios.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        
        # Create user profile
        UserProfile.objects.create(
            user=user,
            role='viewer',  # Default role
            email_notifications=True
        )
        
        messages.success(self.request, f'Usuario {user.username} creado exitosamente.')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view"""
    template_name = 'authentication/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        context['profile'] = profile
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Update user profile"""
    template_name = 'authentication/profile_update.html'
    form_class = ProfileUpdateForm
    success_url = reverse_lazy('profile')
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update user fields if provided
        user = self.request.user
        if form.cleaned_data.get('first_name'):
            user.first_name = form.cleaned_data['first_name']
        if form.cleaned_data.get('last_name'):
            user.last_name = form.cleaned_data['last_name']
        if form.cleaned_data.get('email'):
            user.email = form.cleaned_data['email']
        user.save()
        
        messages.success(self.request, 'Perfil actualizado exitosamente.')
        return response
    
    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial.update({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })
        return initial
