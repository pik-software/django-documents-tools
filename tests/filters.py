import rest_framework_filters as filters

from .models import Book


class BookFilter(filters.FilterSet):
    class Meta:
        model = Book
        fields = {
            'uid': ['exact'],
        }
