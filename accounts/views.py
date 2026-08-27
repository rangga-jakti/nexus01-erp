"""
accounts/views.py — Auth + User management + Role management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse

from .models import User, Role, Permission, UserCompany


class LoginView(DjangoLoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        from core.models import AuditLog
        response = super().form_valid(form)
        AuditLog.log(
            user=form.get_user(),
            action=AuditLog.Action.LOGIN,
            message='User login',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        return response


class LogoutView(DjangoLogoutView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            from core.models import AuditLog
            AuditLog.log(
                user=request.user,
                action=AuditLog.Action.LOGOUT,
                company=getattr(request, 'company', None),
                message='User logout',
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        return super().dispatch(request, *args, **kwargs)


@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {'page_title': 'Profil Saya'})


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        company = self.request.company
        if company:
            return User.objects.filter(
                usercompany__company=company,
                usercompany__is_active=True,
            ).select_related().prefetch_related('usercompany_set__role').distinct()
        return User.objects.none()


class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    template_name = 'accounts/user_form.html'
    fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        messages.success(self.request, 'User berhasil dibuat.')
        return super().form_valid(form)


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/user_detail.html'
    slug_field = 'uid'
    slug_url_kwarg = 'uid'


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'accounts/user_form.html'
    fields = ['email', 'first_name', 'last_name', 'phone', 'bio']
    slug_field = 'uid'
    slug_url_kwarg = 'uid'

    def get_success_url(self):
        return reverse_lazy('accounts:user_detail', kwargs={'uid': self.object.uid})


class RoleListView(LoginRequiredMixin, ListView):
    model = Role
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'


class RoleCreateView(LoginRequiredMixin, CreateView):
    model = Role
    template_name = 'accounts/role_form.html'
    fields = ['name', 'code', 'description']
    success_url = reverse_lazy('accounts:role_list')


class RoleDetailView(LoginRequiredMixin, DetailView):
    model = Role
    template_name = 'accounts/role_detail.html'


class RoleUpdateView(LoginRequiredMixin, UpdateView):
    model = Role
    template_name = 'accounts/role_form.html'
    fields = ['name', 'description', 'permissions']

    def get_success_url(self):
        return reverse_lazy('accounts:role_detail', kwargs={'pk': self.object.pk})


@login_required
def htmx_user_companies(request, uid):
    """HTMX endpoint — load daftar company membership seorang user."""
    user = get_object_or_404(User, uid=uid)
    memberships = UserCompany.objects.filter(
        user=user
    ).select_related('company', 'role')
    return render(request, 'accounts/partials/user_companies.html', {
        'memberships': memberships,
        'target_user': user,
    })
