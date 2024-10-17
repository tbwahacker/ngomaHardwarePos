from posApp.models import UserProfile
from posApp.translations_configs.utils.translation import load_translation

def translation_context(request):
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if user_profile:
            language = user_profile.preferred_language
        else:
            language = 'en'
    else:
        language = 'en'

    translations = load_translation(language)
    return {'translations': translations}
