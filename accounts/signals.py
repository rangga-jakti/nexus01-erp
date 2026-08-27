"""
accounts/signals.py
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def user_post_save(sender, instance, created, **kwargs):
    """Hook setelah User dibuat/diupdate."""
    if created:
        # Bisa kirim welcome email, setup default preferences, dll
        pass
