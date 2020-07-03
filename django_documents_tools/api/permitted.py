from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ValidationError


class PermittedFieldsPermissionMixIn:
    def has_field_permission(self, user, model, field, obj=None):
        permitted_fields = getattr(self, 'permitted_fields',
                                   getattr(model, 'permitted_fields', None))
        if not permitted_fields:
            return False
        for permission, _fields in permitted_fields.items():
            meta = model._meta  # noqa: protected-access
            permission = permission.format(app_label=meta.app_label.lower(),
                                           model_name=meta.object_name.lower())
            has_perm = (field in _fields and user.has_perm(permission))
            if has_perm:
                return True
        return False


class PermittedFieldsSerializerMixIn(PermittedFieldsPermissionMixIn):
    default_error_messages = {
        'field_permission_denied': _('У вас нет прав для '
                                     'редактирования этого поля.')
    }

    def to_internal_value(self, request_data):
        errors = {}
        ret = super().to_internal_value(request_data)
        user = self.context['request'].user
        model = self.Meta.model

        for field in ret.keys():
            if self.has_field_permission(user, model, field, self.instance):
                continue
            errors[field] = [self.error_messages['field_permission_denied']]

        if errors:
            raise ValidationError(errors)

        return ret
