"""
Database routers for handling read replicas and database sharding.
"""

class PrimaryReplicaRouter:
    """
    A router to control all database operations on models in the
    auth and contenttypes applications.
    """
    route_app_labels = {'auth', 'contenttypes', 'sessions', 'admin'}
    
    def db_for_read(self, model, **hints):
        """
        Reads go to a randomly-chosen replica.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return 'replica' if self._is_read_operation(hints) else 'default'
    
    def db_for_write(self, model, **hints):
        """
        Writes always go to primary.
        """
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Relations between objects are allowed if both objects are
        in the primary/replica pool.
        """
        db_set = {'default', 'replica'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        All non-auth models end up in this pool.
        """
        if app_label in self.route_app_labels:
            return db == 'default'
        return db == 'default'
    
    def _is_read_operation(self, hints):
        """
        Determine if this is a read operation.
        """
        return hints.get('readonly', False)


class DatabaseRouter:
    """
    A router to control all database operations on models.
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read from the appropriate database.
        """
        # Add logic to route read operations
        return 'default'
    
    def db_for_write(self, model, **hints):
        """
        Always write to the default database.
        """
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both models are in the same database.
        """
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure all apps end up in the same database.
        """
        return True
