# db/manager.py

import csv
import random
from typing import Any, Optional, Tuple, Union
from functools import wraps
from pathlib import Path
from tenacity import retry, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy import create_engine, Column, inspect, func

from .models import tables
from utils.log import logger
from config import DB_PATH


Base = declarative_base()


def create_model(table_name: str, columns: dict) -> type:
    attrs = {"__tablename__": table_name, "__table_args__": {"extend_existing": True}}
    for name, options in columns.items():
        col_type = options["type"]
        col_kwargs = options.get("kwargs", {})
        attrs[name] = Column(col_type, **col_kwargs)
    return type(table_name.capitalize(), (Base,), attrs)


def handle_db_errors(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        with self.Session() as session:
            try:
                return fn(self, session, *args, **kwargs)
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"[DB][{fn.__name__}] Error: {e}")
                return None

    return wrapper


class DBManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = Path(db_path)
        self.exports_path = self.db_path.parent / "db_exports"
        self.exports_path.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.db_path.as_posix()}", echo=False, future=True)
        self.Session = sessionmaker(bind=self.engine)
        self.models = {
            name: create_model(name, columns) for name, columns in tables.items()
        }
        self._create_missing_tables()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clcoree()

    def close(self):
        self.engine.dispose()

    def create_table(
        self, table_name: str, columns: dict, recreate: bool = False
    ) -> None:
        with self.engine.connect() as conn:
            exists = inspect(self.engine).has_table(table_name)

        if recreate and exists:
            if table_name in Base.metadata.tables:
                Base.metadata.tables[table_name].drop(self.engine, checkfirst=True)
            self.models.pop(table_name, None)
            exists = False

        if not exists:
            model = create_model(table_name, columns)
            model.metadata.create_all(self.engine)
            self.models[table_name] = model

    def _create_missing_tables(self) -> None:
        inspector = inspect(self.engine)
        for name, model in self.models.items():
            if not inspector.has_table(name):
                model.metadata.create_all(self.engine)

    def _get_model(self, name: str) -> type:
        if name not in self.models:
            raise ValueError(f"Model '{name}' not found")
        return self.models[name]

    def _get_primary_key_column(self, model: type):
        return list(model.__table__.primary_key.columns)[0]

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=64),
        retry=retry_if_exception_type(OperationalError),
        reraise=True,
    )
    def _safe_commit(self, session) -> None:
        session.commit()

    # --- Read ---
    @handle_db_errors
    def get(
        self, session, table_name: str, selector: Union[dict, Any]
    ) -> Optional[Any]:
        model = self._get_model(table_name)
        if not isinstance(selector, dict):
            pk_column = self._get_primary_key_column(model)
            return session.query(model).filter(pk_column == selector).one_or_none()
        return session.query(model).filter_by(**selector).one_or_none()

    @handle_db_errors
    def get_many(
        self,
        session,
        table_name: str,
        filters: Optional[dict] = None,
        column_name: Optional[str] = None,
    ) -> list:
        model = self._get_model(table_name)
        query = (
            session.query(getattr(model, column_name))
            if column_name
            else session.query(model)
        )

        if filters:
            query = query.filter_by(**filters)

        results = query.all()
        return [r[0] for r in results] if column_name else results

    @handle_db_errors
    def get_random(self, session, table_name: str) -> Optional[Any]:
        model = self._get_model(table_name)
        records = session.query(model).all()
        return random.choice(records) if records else None

    @handle_db_errors
    def exists(self, session, table_name: str, **filters) -> bool:
        return (
            session.query(self._get_model(table_name))
            .filter_by(**filters)
            .one_or_none()
            is not None
        )

    @handle_db_errors
    def count(self, session, table_name: str, **filters) -> int:
        model = self._get_model(table_name)
        query = session.query(func.count()).select_from(model)
        if filters:
            query = query.filter_by(**filters)
        return query.scalar()

    # --- Create ---
    def insert(
        self, table_name: str, data: Union[dict, Any], overwrite: bool = False
    ) -> Tuple[str, Optional[Any]]:
        model = self._get_model(table_name)
        primary_keys = [key.name for key in inspect(model).primary_key]
        assert len(primary_keys) == 1, "Only single-PK tables supported"
        pk_name = primary_keys[0]

        if not isinstance(data, dict):
            data = {pk_name: data}

        with self.Session() as session:
            instance = (
                session.query(model).filter_by(**{pk_name: data[pk_name]}).one_or_none()
            )
            if instance:
                if overwrite:
                    for key, value in data.items():
                        setattr(instance, key, value)
                    self._safe_commit(session)
                    return "updated"
                return "skipped"
            try:
                instance = model(**data)
                session.add(instance)
                self._safe_commit(session)
                return "inserted"
            except IntegrityError:
                session.rollback()
                return "failed"

    def insert_many(
        self,
        table_name: str,
        data_list: list[Union[dict, Any]],
        overwrite: bool = False,
    ) -> dict:
        results = {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}
        for data in data_list:
            status = self.insert(table_name, data, overwrite=overwrite)
            if status in results:
                results[status] += 1
            else:
                results["failed"] += 1
        return results

    # --- Update ---
    @handle_db_errors
    def update(
        self,
        session,
        table_name: str,
        condition: Union[Any, dict],
        updates: dict,
        create_if_missing: bool = False,
    ) -> Union[None, int, str]:
        model = self._get_model(table_name)

        if isinstance(condition, dict):
            # Обновление по фильтру
            query = session.query(model).filter_by(**condition)
            rows = query.all()
            if not rows and create_if_missing:
                new_data = {**condition, **updates}
                session.add(model(**new_data))
                self._safe_commit(session)
                return "created"
            for row in rows:
                for k, v in updates.items():
                    setattr(row, k, v)
            self._safe_commit(session)
            return len(rows)

        else:
            # Обновление по primary key
            pk_column = self._get_primary_key_column(model)
            row = session.query(model).filter(pk_column == condition).one_or_none()
            if not row:
                if create_if_missing:
                    new_data = {pk_column.name: condition, **updates}
                    session.add(model(**new_data))
                    self._safe_commit(session)
                    return "created"
                logger.warning(f"[DB][update] Not found: {condition}")
                return None
            for k, v in updates.items():
                setattr(row, k, v)
            self._safe_commit(session)
            return "updated"

    # --- Delete ---
    @handle_db_errors
    def delete(
        self,
        session,
        table_name: str,
        condition: Union[Any, dict, None] = None,
    ) -> Union[Optional[Any], int]:
        model = self._get_model(table_name)

        if condition is None:
            # Удаление всех записей из таблицы
            count = session.query(model).delete(synchronize_session=False)
            self._safe_commit(session)
            return count

        if isinstance(condition, dict):
            # Удаление по фильтру
            count = (
                session.query(model)
                .filter_by(**condition)
                .delete(synchronize_session=False)
            )
            self._safe_commit(session)
            return count
        else:
            # Удаление по первичному ключу
            pk_column = self._get_primary_key_column(model)
            instance = session.query(model).filter(pk_column == condition).one_or_none()
            if instance:
                session.delete(instance)
                self._safe_commit(session)
                return 1
            return 0


    def export(self) -> None:
        with self.Session() as session:
            for table_name, model in self.models.items():
                file_path = self.exports_path / f"{table_name}.csv"
                rows = session.query(model).all()
                if not rows:
                    continue  # Пропускаем пустые таблицы

                with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f, delimiter=";")
                    columns = [col.name for col in model.__table__.columns]
                    writer.writerow(columns)
                    for row in rows:
                        writer.writerow([getattr(row, col) for col in columns])
