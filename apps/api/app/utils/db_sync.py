from sqlalchemy import inspect, text
from app.extensions import db
import importlib

def verify_and_update_sqlite_schema(app):
    """Verifies that all columns declared in the SQLAlchemy models exist in the actual
    SQLite database tables. If any columns are missing (e.g. due to desynchronized migrations),
    it automatically executes ALTER TABLE to add them.
    This provides maximum resilience against OperationalError in SQLite."""
    with app.app_context():
        # Check if the DB is SQLite
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if not db_uri or not db_uri.startswith("sqlite"):
            return
        
        # Force import of all models to populate the SQLAlchemy registry/metadata
        try:
            importlib.import_module("app.models")
        except Exception as import_err:
            app.logger.error(f"Error importing app.models in schema sync: {import_err}")
            
        try:
            # Create any completely missing tables (safe: only creates tables that don't exist yet)
            db.create_all()
        except Exception as create_err:
            app.logger.error(f"Error creating missing tables: {create_err}")
        
        try:
            inspector = inspect(db.engine)
            # Iterate through all declared models
            for mapper in db.Model.registry.mappers:
                model_cls = mapper.class_
                if not hasattr(model_cls, "__tablename__"):
                    continue
                table_name = model_cls.__tablename__
                
                # Check if table exists in DB
                if table_name not in inspector.get_table_names():
                    continue
                
                # Get actual columns in the database (lowercase comparison)
                db_cols = {c["name"].lower() for c in inspector.get_columns(table_name)}
                
                # Iterate through declared columns in the model mapper
                for attr in mapper.column_attrs:
                    if not attr.columns:
                        continue
                    col = attr.columns[0]
                    col_name = col.name
                    
                    if col_name.lower() not in db_cols:
                        # Determine column type string for SQLite DDL
                        from sqlalchemy.types import String, Integer, Float, Boolean, Text, DateTime
                        t = col.type
                        if isinstance(t, String):
                            type_str = f"VARCHAR({t.length})" if t.length else "TEXT"
                        elif isinstance(t, Integer):
                            type_str = "INTEGER"
                        elif isinstance(t, Float):
                            type_str = "FLOAT"
                        elif isinstance(t, Boolean):
                            type_str = "BOOLEAN"
                        elif isinstance(t, Text):
                            type_str = "TEXT"
                        elif isinstance(t, DateTime):
                            type_str = "DATETIME"
                        else:
                            type_str = "TEXT"
                            
                        # Construct alter table query
                        query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {type_str}"
                        app.logger.warning(f"Database out of sync: table '{table_name}' is missing column '{col_name}'. Adding it automatically...")
                        try:
                            db.session.execute(text(query))
                            db.session.commit()
                            app.logger.warning(f"Successfully added missing column '{col_name}' to table '{table_name}'.")
                        except Exception as alter_err:
                            db.session.rollback()
                            app.logger.error(f"Failed to add column '{col_name}' to '{table_name}': {alter_err}")
        except Exception as e:
            app.logger.error(f"Error verifying database schema: {e}")
