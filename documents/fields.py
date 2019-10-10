from django.db import models


def copy_openwrt(field):
    field.__class__ = models.IntegerField
    return field


def copy_foreign_key(field):
    old_field = field
    old_swappable = old_field.swappable
    old_field.swappable = False
    try:
        _name, _path, args, field_args = old_field.deconstruct()
    finally:
        old_field.swappable = old_swappable
    if getattr(old_field, "one_to_one", False) or isinstance(
            old_field, models.OneToOneField
    ):
        field_type = models.ForeignKey
    else:
        field_type = type(old_field)

    # If field_args['to'] is 'self' then we have a case where the object
    # has a foreign key to itself. If we pass the historical record's
    # field to = 'self', the foreign key will point to an historical
    # record rather than the base record. We can use old_field.model here.
    if field_args.get("to", None) == "self":
        field_args["to"] = old_field.model

    # Override certain arguments passed when creating the field
    # so that they work for the historical field.
    field_args.update(
        db_constraint=False,
        related_name='+',
        null=True,
        blank=True,
        primary_key=False,
        db_index=True,
        serialize=True,
        unique=False,
        on_delete=models.DO_NOTHING,
    )
    field = field_type(*args, **field_args)
    field.name = old_field.name
    return field


def copy_other(field):
    """Customize field appropriately for use in historical model"""
    field.name = field.attname
    if isinstance(field, models.AutoField):
        field.__class__ = models.IntegerField

    elif isinstance(field, models.FileField):
        # Don't copy file, just path.
        field.__class__ = models.TextField

    # Historical instance shouldn't change create/update timestamps
    field.auto_now = False
    field.auto_now_add = False

    if field.primary_key:
        opts = field.model._meta  # noqa: protected-access
        field = models.ForeignKey(
            field.model,
            on_delete=models.DO_NOTHING,
            name=opts.model_name,
            verbose_name=opts.verbose_name.title())

    field.blank = True
    field.null = True

    if field.primary_key or field.unique:
        # Unique fields can no longer be guaranteed unique,
        # but they should still be indexed for faster lookups.
        field.primary_key = False
        field._unique = False  # noqa protected-access
        field.db_index = True
        field.serialize = True

    return field


def copy_boolean(field):
    field.__class__ = models.NullBooleanField
    return field


FIELDS_PROCESSORS = {
    models.ForeignKey: copy_foreign_key,
    models.OrderWrt: copy_openwrt,
    models.BooleanField: copy_boolean,
    None: copy_other
}
