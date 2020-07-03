from django.urls import path, include

from django_documents_tools.api.router import DocumentedRouter
from tests.viewsets import BookViewSet

router = DocumentedRouter()  # noqa: pylint=invalid-name
router.register('book-list', BookViewSet, base_name='book')

api_urlpatterns = [  # noqa: pylint=invalid-name
    path('api/v1/', include((router.urls, 'api'))),
]

urlpatterns = api_urlpatterns  # noqa: pylint=invalid-name
