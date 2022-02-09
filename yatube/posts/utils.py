from django.conf import settings
from django.core.paginator import Paginator


def paginator_func(page_name, request, numbers=settings.POST_QUANTITY):
    paginator = Paginator(page_name, numbers)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return page_obj
