from django.utils.deprecation import MiddlewareMixin
from posApp.models import UserProfile
from posApp.translations_configs.utils.translation import load_translation

class TranslationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            user_profile = UserProfile.objects.filter(user=request.user).first()
            if user_profile:
                language = user_profile.preferred_language
            else:
                language = 'en'
        else:
            language = 'en'

        # Check if the language is set in the session
        if 'preferred_language' in request.session:
            language = request.session['preferred_language']
        else:
            request.session['preferred_language'] = language
        request.translations = load_translation(language)
