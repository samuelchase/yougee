import salesforce.converters as conv
import models

def test_converters():
    for model_name, sf_object, converter in conv.ordered_converters:
        klass = getattr(models, model_name)
        if hasattr(klass, "query"):
            instance = klass.query().get()
        else:
            instance = klass.all().get()
        result = converter(instance)
        assert isinstance(result, dict)

