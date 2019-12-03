from rest_framework.fields import CharField

from django_documents_tools.api.serializers import clone_serializer_field


def test_field_clone():
    src_field = CharField(required=False)
    dst_field = clone_serializer_field(src_field, required=True)
    assert dst_field.required
