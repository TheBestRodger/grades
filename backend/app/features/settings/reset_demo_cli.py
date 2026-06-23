from __future__ import annotations

import json

from ...core.config import Settings
from ...core.db import Database
from ...models import Employee
from ..imports.demo_seed import seed_demo_data
from .demo_reset import reset_demo_data


def main() -> None:
    settings = Settings.from_env()
    database = Database(settings.database_url)
    database.migrate()
    with database.session() as session:
        seed_demo_data(session, settings.work_staffing_file)
        actor = session.query(Employee).filter(
            Employee.email == "hr@profile.local",
            Employee.is_demo.is_(True),
        ).one()
        result = reset_demo_data(session, actor, settings.work_staffing_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
