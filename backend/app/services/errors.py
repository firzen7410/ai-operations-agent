from sqlalchemy.exc import IntegrityError


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


def is_constraint_error(
    exc: IntegrityError, *, sqlite_code: str, constraint: str
) -> bool:
    return (
        getattr(exc.orig, "sqlite_errorname", None) == sqlite_code
        or getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == constraint
    )
