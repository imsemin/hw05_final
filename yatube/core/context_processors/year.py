from django.utils import timezone


def year(request):
    """Добавляет переменную с текущим годом.
    Можно использовать при рендеренге страницы:
    {% now 'Y' %} is the correct syntax
    """

    now = timezone.now().year

    return {"year": now}
