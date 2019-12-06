## Django documents tools

Toolset to work with documents and snapshots

### HowToUse ###

* install

```buildoutcfg
pip install django-documents-tools
```

* Default settings:
```python
DOCUMENTS_TOOLS = {
    'BASE_SERIALIZER': serializers.ModelSerializer,
    'BASE_VIEW_SET': viewsets.ModelViewSet,
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': False}
```

* settings:
    * **BASE_SERIALIZER**: Base Serializer for Change and Snapshot
    * **BASE_VIEW_SET**: Base ViewSet for Change and Snapshot
    * **CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED**: Allow to create new 
object by Change

* Add `DocumentedRouter` in `urls.py` module:

```python
from django_documents_tools.api.router import DocumentedRouter

router = DocumentedRouter()
```

* For connect Changes in your original model you need:

```python
from django_documents_tools.models import Changes, BaseDocumented
    
class YourModel(BaseDocumented):
    changes = Changes()
```
