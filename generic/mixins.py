from django.db import models

class Inheritable(object):
    def get_leaf_object(self):
        """Returns the model instance object as instance of the outermost leaf class,
        by searching through its related descriptors to find the right model."""
        for obj in self._meta.get_all_related_objects():
            related_model = getattr(obj, 'related_model', obj.model)
            if related_model != self.__class__ and obj.field.rel.parent_link:
                try:
                    return getattr(self, obj.get_accessor_name()).get_leaf_object()
                except related_model.DoesNotExist:
                    pass
        return self

    def __unicode__(self):
        # Display the unicode representation of the leaf model instance
        leaf = self.get_leaf_object()
        if leaf.__class__ != self.__class__:
            return "%s: %s" % (leaf._meta.verbose_name, unicode(leaf))
        # Simulate what Django does in Model.__str__, so that when no
        # __unicode__ method is defined on the model, this mixin doesn't
        # affect the unicode representation
        if hasattr(super(Inheritable, self), '__unicode__'):
            return super(Inheritable, self).__unicode__()
        return '%s object' % self.__class__.__name__


class HousekeepingMixin(models.Model):
    """Abstract mixin class to collect creation and update timestamps."""
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
