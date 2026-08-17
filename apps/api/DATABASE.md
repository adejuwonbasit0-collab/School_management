# Database Setup & Migrations

## Starting completely fresh (wipe everything and rebuild)

If you're on SQLite (the default) and just want a clean slate:

```bash
rm -f instance/*.db
flask db upgrade
python -m scripts.seed
```

That's it. `flask db upgrade` builds every table from the single consolidated
migration (`migrations/versions/e93cfb58aeeb_initial_schema.py`), and
`scripts/seed.py` creates your admin account and default content.

Your admin login after seeding:
```
adejuwonbasit0@gmail.com / baskid555
```

You can change that password anytime from Profile Settings once logged in —
you never need to run a script again for that.

## If you ever get locked out of admin

Run:
```bash
python -m scripts.fix_admin_account
```
This restores `adejuwonbasit0@gmail.com` to the admin role and resets the
password to `baskid555`, regardless of what happened to the account. Edit
the `CURRENT_EMAIL` variable at the top of that file first if you're
currently logged in under a different email.

## Whenever a model changes (adding a new field, new table, etc.)

Anytime I (or another AI) change a model in `app/models/`, a new migration
file needs generating. The command to run is always the same:

```bash
flask db migrate -m "short description of the change"
flask db upgrade
```

- `flask db migrate` looks at your models and auto-writes a new file in
  `migrations/versions/` describing the difference.
- `flask db upgrade` actually applies it to your database.

**Always run both, in that order, after pulling in any code that touches
`app/models/`.** If a change is shipped to you as a `.py` file directly
inside `migrations/versions/` (rather than asking you to run `flask db
migrate`), just run `flask db upgrade` — the file's already written for you.

## Checking things are healthy

```bash
flask db current    # shows which migration your database is on
flask db heads      # shows the latest migration available in the code
```

If `current` and `heads` don't match, run `flask db upgrade`. If `heads`
ever shows more than one line, that means two migrations were branched
from the same point — tell me and I'll merge them, don't try to fix it
by hand.
